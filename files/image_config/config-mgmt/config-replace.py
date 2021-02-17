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

def get_running_config():
    if dry_run and current_json_path != None:
        with open(current_json_path) as fh:
            text = fh.read()
    else:
        text = run_command('show runningconfiguration all')
    
    if verbose:
        print(f"Running config consists of {len(text)} characters")

    return json.loads(text)

def generate_patch(src, dst):
    patch = jsonpatch.make_patch(src, dst)

    if verbose:
        print(f"Patch: {patch}")
    return patch

def apply_patch(patch):
    command = "./apply-patch.py -p ./patch.json"
    if verbose:
        print(f"Applying the following command in CLI: {command}")

    if dry_run:
        return

    with open("./patch.json", "w") as fh:
        fh.write(f'{patch}')

    run_command(command)

def verify_replace(data):
    if dry_run:
        if verbose:
            print("Dry run cannot be verified, so assume success.")
        return

    current = get_running_config()

    patch = generate_patch(current, data)

    if patch:
        raise AttributeError(f'Config replace failed, as there is still a patch to mitigate. Patch: {patch}')

    if verbose:
        print("Retrieved patch after config replace was empty, so verification succeeded")

def config_replace(data):
    print("\n----------\nGetting running config...", flush=True)
    current = get_running_config()

    print("\n----------\nGenerating patch...", flush=True)
    patch = generate_patch(current, data)

    print("\n----------\nApplying patch...", flush=True)
    apply_patch(patch)

    print("\n----------\nVerifying config replace...", flush=True)
    verify_replace(data)

    print('\n')
    if dry_run:
        verbose_msg =  " If you wish to see detailed output use '-v, --verbose' option." if not(verbose) else ""
        print(f"Dry run completed.{verbose_msg}")
    else:
        print("Done.")

def main():
    parser=argparse.ArgumentParser(description="Replace full ConfigDb JSON configs")
    parser.add_argument('-j', '--json', help='Path to json file containing full config', required=True)
    parser.add_argument("-v", "--verbose", action='store_true', default=False, help="show logs on CLI")
    parser.add_argument("-d", "--dry-run", action='store_true', default=False, help="do a dry-run")
    parser.add_argument("-c", "--current-json", help="Path to current config file, use with '-d, --dry-run' option")

    args = parser.parse_args()

    json_file = args.json
    global verbose, dry_run, current_json_path
    verbose = args.verbose
    dry_run = args.dry_run
    current_json_path = args.current_json

    with open(json_file, "r") as fh:
        text = fh.read()
        data = json.loads(text)
        config_replace(data)

if __name__ == "__main__":
    main()