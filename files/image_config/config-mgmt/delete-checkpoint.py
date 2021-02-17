#!/usr/bin/env python3

import os
import argparse
from common import run_command

verbose = False
dry_run = False
checkpoint_folder = '/home/admin/config-mgmt/checkpoints'

def apply_delete_checkpoint(checkpoint_name):
    command = f"rm {checkpoint_folder}/{checkpoint_name}"
    if verbose:
        print(f"Applying the following command in CLI: {command}")
    if dry_run:
        print(f"Not going to delete the checkpoint since it is a dry-run")
        return

    run_command(command)

def delete_checkpoint(checkpoint_name):
    print("\n----------\nDeleting checkpoint...", flush=True)
    apply_delete_checkpoint(checkpoint_name)

    if dry_run:
        verbose_msg =  " If you wish to see detailed output use '-v, --verbose' option." if not(verbose) else ""
        print(f"Dry run completed.{verbose_msg}")
    else:
        print("Done.")

def main():
    parser=argparse.ArgumentParser(description="Deletes a checkpoint of full ConfigDb JSON configs")
    parser.add_argument('-c', '--checkpoint-name', help='The name of the checkpoint', required=True)
    parser.add_argument("-d", "--dry-run", action='store_true', default=False, help="do a dry-run")
    parser.add_argument("-v", "--verbose", action='store_true', default=False, help="show logs on CLI")

    args = parser.parse_args()

    checkpoint_name = args.checkpoint_name
    global verbose, dry_run
    verbose = args.verbose
    dry_run = args.dry_run

    delete_checkpoint(checkpoint_name)

if __name__ == "__main__":
    main()