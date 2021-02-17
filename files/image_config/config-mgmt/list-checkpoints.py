#!/usr/bin/env python3

import os
import argparse
from common import run_command

verbose = False
dry_run = False
checkpoint_folder = '/home/admin/config-mgmt/checkpoints'

def apply_list_checkpoints():
    command = f"ls -l {checkpoint_folder}"
    if verbose:
        print(f"Applying the following command in CLI: {command}")

    if dry_run:
        print(f'Not running command since this is a dry-run')
        return

    output = run_command(command)
    print(output)

def list_checkpoints():
    print("\n----------\nApplying list checkpoints...", flush=True)
    apply_list_checkpoints()

    if dry_run:
        verbose_msg =  " If you wish to see detailed output use '-v, --verbose' option." if not(verbose) else ""
        print(f"Dry run completed.{verbose_msg}")
    else:
        print("Done.")

def main():
    parser=argparse.ArgumentParser(description="Lists full ConfigDb JSON configs checkpoints")
    parser.add_argument("-v", "--verbose", action='store_true', default=False, help="show logs on CLI")
    parser.add_argument("-d", "--dry-run", action='store_true', default=False, help="do a dry-run")

    args = parser.parse_args()

    global verbose, dry_run
    verbose = args.verbose
    dry_run = args.dry_run

    list_checkpoints()

if __name__ == "__main__":
    main()