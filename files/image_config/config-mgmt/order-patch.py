#!/usr/bin/env python3

import argparse
import jsonpatch
import json
import copy
import re
import os
from collections import deque
from common import run_command
from jsonChange import JsonChange

verbose = False
dry_run = False
current_json_path = None
algorithm = 1
optimize = False

def get_running_config():
    if dry_run and current_json_path != None:
        with open(current_json_path) as fh:
            text = fh.read()
    else:
        text = run_command('show runningconfiguration all')

    return json.loads(text)

def divide_islands(jsonPatch):
    # assume 1 island for simplicity for now
    return [JsonChange(jsonPatch)]

def group_islands(list_of_list_of_jsonChanges):
    # assume 1 island
    return list_of_list_of_jsonChanges[0]

def hash_json(json_config):
    return json.dumps(json_config, sort_keys=True)

def hash_operation(operation):
    value = ""
    if 'value' in operation:
        value = json.dumps(operation['value'])
    return f"{operation['op']}::{operation['path']}::{value}"

def validate_ethernet(id, operation, current_json):
    if operation['path'].startswith(f"/PORT/Ethernet{id}/"):
        return False

    if operation['path'].startswith(f"/PORT/Ethernet{id}") and operation['op'] == 'replace':
        return False

    if operation['path'].startswith(f"/PORT/Ethernet{id}") and operation['op'] == 'add' and exists(["PORT", f"Ethernet{id}"], current_json):
        return False

    return True

def value_has_dependencies(current_json):
    for i in list(range(0, 5)) + [56]:
        i_str = str(i)
        if exists(["ACL_TABLE", "NO-NSW-PACL-V4", "ports", "Ethernet"+i_str], current_json) or \
            exists(["VLAN_MEMBER", "Vlan100|Ethernet" + i_str], current_json) or \
            exists(["VLAN_MEMBER", "Vlan1000|Ethernet" + i_str], current_json):
            if exists(["PORT", "Ethernet" + i_str], current_json):
                return True
    
    return False



def valid_operation(operation, current_json):
    # Just for fun, enable this option and the one below. Now the only way to update DHCP_SERVER is by replacing the whole file
    # if operation['path'].startswith("/DHCP_SERVER"):
    #     return False

    if operation['path'].startswith("/DHCP_SERVER/"):
        return False

    for i in list(range(0, 5)) + [56]:
        if not(validate_ethernet(i, operation, current_json)):
            return False

    if operation['path'] == "/PORT":
        return False

    if operation['path'] == "/VLAN_MEMBER":
        return False

    if operation['path'] == "" and operation['op'] == "remove":
        return False

    # hack to make samples/dpb_1_to_4.json-patch work, otherwise it will always fail to update ports list
    if not(optimize) and operation['path'].startswith('/ACL_TABLE/NO-NSW-PACL-V4/ports/'):
        return False

    if 'value' in operation and value_has_dependencies(operation['value']):
        return False

    return True

def exists(tokens, current_json):
    for token in tokens:
        if not(token in current_json):
            return False
        
        if type(current_json) is dict:
            current_json = current_json[token]
    return True

def valid_json(current_json):
    for i in list(range(0, 5)) + [56]:
        i_str = str(i)
        if exists(["ACL_TABLE", "NO-NSW-PACL-V4", "ports", "Ethernet"+i_str], current_json) or \
            exists(["VLAN_MEMBER", "Vlan100|Ethernet" + i_str], current_json) or \
            exists(["VLAN_MEMBER", "Vlan1000|Ethernet" + i_str], current_json):
            if not(exists(["PORT", "Ethernet" + i_str], current_json)):
                return False

    return True

def apply_operation(current_json, operation):
    patch = jsonpatch.JsonPatch([operation])

    return patch.apply(current_json)

def convert_to_json_change(operation):
    return JsonChange(jsonpatch.JsonPatch([operation]))

def generate_operation(operation, lvl, target_json):
    if lvl == 0:
        return operation

    tokens = operation['path'].split('/')[1:]

    if lvl > len(tokens):
        return None

    modified_tokens = tokens[:-1*lvl]
    for token in modified_tokens:
        target_json = target_json[token]

    new_path = f"/{'/'.join(modified_tokens)}"
    if new_path == "/":
        new_path = ""

    return {'op':'replace', 'path':new_path, 'value': target_json}

mem = {}
vis = {}
target_json = None

import re

def get_index(path, value, current_json):
    tokens = path.split('/')[1:]

    for token in tokens:
        current_json = current_json[token]

    i = 0
    for item in current_json:
        if item == value:
            return i
        i = i+1

def get_references(path, current_json):
    references = []
    match = re.search("/PORT/Ethernet(\d+)", path)
    if match:
        id = match.groups()[0]
        acl_path = "/ACL_TABLE/NO-NSW-PACL-V4/ports"
        if exists(["ACL_TABLE", "NO-NSW-PACL-V4", "ports", "Ethernet"+id], current_json):
            references.append(acl_path + '/' + str(get_index(acl_path, "Ethernet"+id, current_json)))
        if exists(["VLAN_MEMBER", "Vlan100|Ethernet"+str(id)], current_json):
            references.append("/VLAN_MEMBER/Vlan100|Ethernet"+str(id))
        if exists(["VLAN_MEMBER", "Vlan1000|Ethernet"+str(id)], current_json):
            references.append("/VLAN_MEMBER/Vlan1000|Ethernet"+str(id))

    return references

def extend_operation(operation, current_json):
    ops = []
    del_paths = get_references(operation['path'], current_json)

    for del_path in del_paths:
        ops.append({'op':'remove', 'path':del_path})

    top_operation = generate_operation(operation, 1, target_json)

    if top_operation != None:
        ops.append(top_operation)
        ops.append({'op':'remove', 'path':top_operation['path']})
        ops.append({'op':'add', 'path':top_operation['path'], 'value':top_operation['value']})
    
    return ops


def dp(current_json):
    if current_json == target_json:
        return []

    json_hash = hash_json(current_json)
    if json_hash in mem:
        return mem[json_hash]

    if json_hash in vis: # Already visited, just return None
        return None

    vis[json_hash] = True
    if not(valid_json(current_json)):
        mem[json_hash] = None
        return None

    patch = jsonpatch.make_patch(current_json, target_json)
    d = deque(patch)

    best_ops = None

    while len(d):
        operation = d.popleft()
        if valid_operation(operation, current_json):
            result_json = apply_operation(current_json, operation)

            ops = dp(result_json)
            if ops != None:
                if best_ops == None or len(ops)+1 < len(best_ops):
                    best_ops = [convert_to_json_change(operation)] + ops
                if not(optimize): # if optimization is not enabled, just break on the first answer although not the best answer
                    break
        
        d.extend(extend_operation(operation, current_json))
    
    mem[json_hash] = best_ops
    return best_ops

def topological_sort2(current_json, local_target_json):
    global target_json
    target_json = local_target_json

    if not(valid_json(target_json)):
        raise AttributeError("malformed target json")

    ops = dp(current_json)
    if ops == None:
        raise AttributeError("Was not able to find any valid moves")

    return ops

def topological_sort1(current_json, target_json):
    if current_json == target_json:
        return []

    patch = jsonpatch.make_patch(current_json, target_json)

    tried = {""}
    lvl = 0
    while True:
        noNewTries = True
        for operation in patch:
            generated_operation = generate_operation(operation, lvl, target_json)
            if generated_operation == None:
                continue
            generated_operation_hash = hash_operation(generated_operation)
            if generated_operation_hash in tried:
                continue

            noNewTries = False
            tried.add(generated_operation_hash)

            result_current_json = apply_operation(current_json, generated_operation)
            if valid_operation(generated_operation) and valid_json(result_current_json):
                return [convert_to_json_change(generated_operation)] + topological_sort1(result_current_json, target_json)

            if generated_operation['op'] == 'replace':
                remove_operation = {'op':'remove', 'path':generated_operation['path']}
                add_operation = {'op':'add', 'path':generated_operation['path'], 'value':generated_operation['value']}
                result_current_json = apply_operation(current_json, remove_operation)
                result_target_json = apply_operation(target_json, remove_operation)

                if valid_json(result_current_json) and \
                   valid_json(result_target_json) and \
                   valid_operation(remove_operation) and \
                   valid_operation(add_operation):
                    return [convert_to_json_change(remove_operation)] + topological_sort1(result_current_json, result_target_json) + [convert_to_json_change(add_operation)]
        lvl = lvl + 1
        if noNewTries:
            raise AttributeError("Was not able to find any valid moves")
    
    return [JsonChange(patch)]

def topological_order(jsonChange):
    current_json = get_running_config()
    target_json = jsonChange.apply(current_json)

    if algorithm == 1:
        jsonChanges = topological_sort1(current_json, target_json)
    elif algorithm == 2:
        jsonChanges = topological_sort2(current_json, target_json)
    else:
        raise AttributeError(f"There is no algorithm {algorithm} provided")

    for jsonChange in jsonChanges:
        print(jsonChange)
    return jsonChanges


def order_patch(patch):
    print("\n----------\nDivide patch into related jsonChanges...", flush=True)
    island_jsonChanges = divide_islands(patch)

    print("\n----------\nOrder changes...", flush=True)
    for jsonChange in island_jsonChanges:
        topological_json_changes = topological_order(jsonChange)
    
    print("\n----------\nGroup jsonChanges if possible...", flush=True)
    jsonChanges = group_islands(topological_json_changes)

    if dry_run:
        verbose_msg =  " If you wish to see detailed output use '-v, --verbose' option." if not(verbose) else ""
        print(f"Dry run completed.{verbose_msg}")
    else:
        print("Done.")

    return jsonChanges

def main():
    parser=argparse.ArgumentParser(description="Order JSON patch to apply to SONiC config")
    parser.add_argument('-p', '--patch-file', help='Path to patch file', required=True)
    parser.add_argument("-v", "--verbose", action='store_true', default=False, help="show logs on CLI")
    parser.add_argument("-d", "--dry-run", action='store_true', default=False, help="do a dry-run")
    parser.add_argument("-c", "--current-json", help="Path to current config file, use with '-d, --dry-run' option")
    parser.add_argument("-a", "--algorithm", default=1, help="algorithm index")
    parser.add_argument("-o", "--optimize", action='store_true', default=False, help="optimize solution")

    args = parser.parse_args()

    patch_file = args.patch_file
    global verbose, dry_run, current_json_path, algorithm, optimize
    verbose = args.verbose
    dry_run = args.dry_run
    current_json_path = args.current_json
    algorithm = int(args.algorithm)
    optimize = args.optimize

    with open(patch_file, "r") as fh:
        text = fh.read()
        data = jsonpatch.JsonPatch(json.loads(text))
        order_patch(data)

if __name__ == "__main__":
    main()
