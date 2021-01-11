#!/usr/bin/env python3

import os
import argparse
import json
import jsonpatch

checkpoint_folder = '/home/admin/config-mgmt/checkpoints'

def run_command(command):
    stream = os.popen(f'{command} > ./output.log 2>&1; echo $?')
    result = int(stream.read())

    stream = os.popen('cat ./output.log')
    output = stream.read()

    if result:
        raise AttributeError(f'Apply command failed.\n  Command: {command}\n  Output: {output}')

    return output

def get_running_config():
    text = run_command('show runningconfiguration all')
    
    return json.loads(text)

def get_checkpoint_config(checkpoint_name):
    with open(f'{checkpoint_folder}/{checkpoint_name}', "r") as fh:
        text = fh.read()
    return json.loads(text)

def generate_patch(src, dst):
    patch = jsonpatch.make_patch(src, dst)

    return patch


def diff_checkpoint(checkpoint_name):
    print("\n----------\nGetting running config...", flush=True)
    running_config = get_running_config()

    print("\n----------\nGetting checkpoint config...", flush=True)
    checkpoint_config = get_checkpoint_config(checkpoint_name)

    print("\n----------\nGenerating patch...", flush=True)
    patch = generate_patch(running_config, checkpoint_config)

    print("\n----------\nPrinting patch...", flush=True)
    print(patch)

def main():
    parser=argparse.ArgumentParser(description="Lists full ConfigDb JSON configs checkpoints")
    parser.add_argument("-c", "--checkpoint-name", help="name of checkpoint to compare with running", required=True)

    args = parser.parse_args()

    checkpoint_name = args.checkpoint_name

    diff_checkpoint(checkpoint_name)

if __name__ == "__main__":
    main()