#!/usr/bin/env python3

import argparse
import jsonpatch
import json
import copy
import re
import os
from common import run_command

verbose = False
dry_run = False
current_json_path = None
running_config_json = None
order_config = None

class ExtendedConfiglet:
    def __init__(self, opType, configlet):
        self.opType = opType
        self.configlet = configlet
    
    def __str__(self):
        return f"{{ 'opType': '{self.opType}', 'configlet': {self.configlet}}}"

def print_ecs(ecs):
    print('[\n  %s\n]' % ',\n  '.join(map(str, ecs)))

def convertPatchToExtendedConfiglet(patch):
    extendedConfiglets = []
    for sub_patch in patch:
        extendedConfiglets.extend(convertSubPatchToExtendedConfiglet(sub_patch))
    if verbose:
        print_ecs(extendedConfiglets)
    return extendedConfiglets

def get_running_config():
    if dry_run and current_json_path != None:
        with open(current_json_path) as fh:
            text = fh.read()
    else:
        text = run_command('show runningconfiguration all')
    
    return json.loads(text)

def covertSubPatchWithNumberToExtendedConfiglet(sub_patch):
    global running_config_json
    if running_config_json == None:
        running_config_json = get_running_config()
    running_config_json = jsonpatch.JsonPatch([sub_patch]).apply(running_config_json)

    op = "replace"
    path = sub_patch['path'].rsplit('/', 1)[0]
    tokens = path.split('/')[1:]
    running_config_json_pointer = running_config_json
    for token in tokens:
        running_config_json_pointer = running_config_json_pointer[token]
    value = running_config_json_pointer

    new_patch = { 'op': op, 'path': path, 'value': value }

    return convertSubPatchToExtendedConfiglet(new_patch)

def convertSubPatchToExtendedConfiglet(sub_patch):
    if sub_patch['op'] == "add" or sub_patch['op'] == "replace":
        opType = "update"
    elif sub_patch['op'] == "remove":
        opType = "delete"
    else: raise AttributeError(f"patch op={sub_patch['op']} is not supported")

    path = sub_patch['path']
    value = sub_patch['value'] if opType == "update" else None

    if path == "":
        raise AttributeError("Modifying whole config is not allowed, the path specified can not be empty")
    
    if re.match("^/\s*$", path):
        raise AttributeError(f"There is no table with empty or whitespace name, the path specified should not be {path}")

    tokens = path.split("/")[1:]
    if any(re.match("^\d+$", token) for token in tokens[:-1]):
        raise AttributeError(f"The path cannot contain a number as key, as modifying a list is not supported, path: {path}")

    if re.match("^\d+$", tokens[-1]):
        return covertSubPatchWithNumberToExtendedConfiglet(sub_patch)

    del_configlet = {}
    configlet = {}
    configlet_pointer = configlet
    del_configlet_pointer = del_configlet

    global running_config_json
    if running_config_json == None:
        running_config_json = get_running_config()
    running_config_json_pointer = running_config_json

    for token in tokens[:-1]:
        running_config_json_pointer = running_config_json_pointer[token]
        configlet_pointer[token] = {}
        configlet_pointer = configlet_pointer[token]
        del_configlet_pointer[token] = {}
        del_configlet_pointer = del_configlet_pointer[token] 

    last_token = tokens[-1]
    configlet_pointer[last_token] = value
    del_configlet_pointer[last_token] = None
    if last_token in running_config_json_pointer and type(running_config_json_pointer[last_token]) is dict:
        del_configlet_pointer[last_token] = {}

    if opType == "update":
        return [ExtendedConfiglet("delete", del_configlet), ExtendedConfiglet("update", configlet)]
    else:
        return [ExtendedConfiglet("delete", del_configlet)]

def apply_extended_configlet(extended_configlet):
    if extended_configlet.opType == "service-restart":
        command = extended_configlet.configlet
        if verbose:
            print(f"Applying the following command in CLI: {command}")
            print()
        if dry_run:
            return
    else:
        flag = "-u" if extended_configlet.opType == "update" else "-d"
        command = f"configlet -j ./configlet.json {flag}"
        configlet_as_json = f'[{json.dumps(extended_configlet.configlet)}]'
        if verbose:
            print(f"Applying the following command in CLI: {command}")
            print(f"Content of ./configlet.json:{configlet_as_json}")
            print()
        if dry_run:
            return
        with open("./configlet.json", "w") as fh:
            fh.write(configlet_as_json)
    
    run_command(command)

def get_order_config():
    global order_config
    if order_config != None:
        return order_config
    with open("order-config.json", "r") as fh:
        text = fh.read()
        data = json.loads(text)
    
    order_config = data
    return order_config

def get_tables_in_order():
    data = get_order_config()

    sorted_groups = {k: v for k, v in sorted(data['groups'].items(), key=lambda item: item[1])}

    sorted_tables = []
    for group in sorted_groups.keys():
        tables_in_group_unsorted = {}
        for table in data['tables']:
            table_data = data['tables'][table]
            if table_data['order_group'] != group:
                continue
            tables_in_group_unsorted[table] = table_data['order_index']
        tables_in_group_sorted = {k: v for k, v in sorted(tables_in_group_unsorted.items(), key=lambda item: item[1])}
        sorted_tables.extend(tables_in_group_sorted.keys())
    return sorted_tables

def order_configlets(ecs):
    sorted_tables = get_tables_in_order()
    sorted_ecs = []
    for table in sorted_tables:
        for ec in ecs:
            if list(ec.configlet.keys())[0].lower() == table.lower():
                sorted_ecs.append(ec)
    
    if len(ecs) != len(sorted_ecs):
        raise AttributeError(f'Missing configlets after sorting. configlets count: {len(ecs)}, sorted configlets count: {len(sorted_ecs)}')

    if verbose:
        print_ecs(sorted_ecs)

    return sorted_ecs

def generate_service_restart_extended_configlet(service):
    return ExtendedConfiglet("service-restart", f"sudo service {service} restart")

def generate_service_restart_extended_configlets(services):
    ecs = []
    for service in services:
        ecs.append(generate_service_restart_extended_configlet(service))
    
    return ecs

def add_service_restarts(sorted_ecs):
    ecs_including_service_restart = []

    groups = []
    for ec in sorted_ecs:
        table = list(ec.configlet.keys())[0].lower()
        if not(len(groups)) or list(groups[-1].keys())[0] != table:
            groups.append({table: []})
        groups[-1][table].append(ec)
    
    order_config = get_order_config()

    for group in groups:
        table = list(group.keys())[0]
        ecs_including_service_restart.extend(group[table])
        services = order_config["tables"][table.upper()]["services_to_restart"]
        ecs_including_service_restart.extend(generate_service_restart_extended_configlets(services))
    
    if verbose:
        print_ecs(ecs_including_service_restart)

    return ecs_including_service_restart

def apply_patch(patch):
    print("\n----------\nGenerating configlets...", flush=True)
    ecs = convertPatchToExtendedConfiglet(patch)

    print("\n----------\nOrder configlets...", flush=True)
    sorted_ecs = order_configlets(ecs)
    
    print("\n----------\nAdd necessary service restarts...", flush=True)
    ecs_including_service_restart = add_service_restarts(sorted_ecs)

    print("\n----------\nApplying configlets...", flush=True)
    for ec in ecs_including_service_restart:
        apply_extended_configlet(ec)

    if dry_run:
        verbose_msg =  " If you wish to see detailed output use '-v, --verbose' option." if not(verbose) else ""
        print(f"Dry run completed.{verbose_msg}")
    else:
        print("Done.")

def main():
    parser=argparse.ArgumentParser(description="Apply JSON patch to ConfigDB")
    parser.add_argument('-p', '--patch-file', help='Path to patch file', required=True)
    parser.add_argument("-v", "--verbose", action='store_true', default=False, help="show logs on CLI")
    parser.add_argument("-d", "--dry-run", action='store_true', default=False, help="do a dry-run")
    parser.add_argument("-c", "--current-json", help="Path to current config file, use with '-d, --dry-run' option")

    args = parser.parse_args()

    patch_file = args.patch_file
    global verbose, dry_run, current_json_path
    verbose = args.verbose
    dry_run = args.dry_run
    current_json_path = args.current_json

    with open(patch_file, "r") as fh:
        text = fh.read()
        data = json.loads(text)
        apply_patch(data)

if __name__ == "__main__":
    main()
