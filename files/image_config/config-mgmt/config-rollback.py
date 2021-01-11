#!/usr/bin/env python3

import os
import argparse

verbose = False
dry_run = False
checkpoint_folder = '/home/admin/config-mgmt/checkpoints'

def run_command(command):
    stream = os.popen(f'{command} > ./output.log 2>&1; echo $?')
    result = int(stream.read())

    stream = os.popen('cat ./output.log')
    output = stream.read()

    if result:
        raise AttributeError(f'Apply command failed.\n  Command: {command}\n  Output: {output}')

    return output

def apply_rollback(checkpoint_name):
    command = f"./config-replace.py -j {checkpoint_folder}/{checkpoint_name}"
    if verbose:
        print(f"Applying the following command in CLI: {command}")

    if dry_run:
        return

    run_command(command)

def rollback(checkpoint_name):
    print("\n----------\nApplying rollback...", flush=True)
    apply_rollback(checkpoint_name)

    if dry_run:
        verbose_msg =  " If you wish to see detailed output use '-v, --verbose' option." if not(verbose) else ""
        print(f"Dry run completed.{verbose_msg}")
    else:
        print("Done.")

def main():
    parser=argparse.ArgumentParser(description="Rollback full ConfigDb JSON configs")
    parser.add_argument('-c', '--checkpoint-name', help='The name of the checkpoint', required=True)
    parser.add_argument("-d", "--dry-run", action='store_true', default=False, help="do a dry-run")
    parser.add_argument("-v", "--verbose", action='store_true', default=False, help="show logs on CLI")

    args = parser.parse_args()

    checkpoint_name = args.checkpoint_name
    global verbose, dry_run
    verbose = args.verbose
    dry_run = args.dry_run

    rollback(checkpoint_name)

if __name__ == "__main__":
    main()