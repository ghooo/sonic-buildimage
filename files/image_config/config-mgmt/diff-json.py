#!/usr/bin/env python3

import os
import argparse
import json
import jsonpatch
from common import run_command

def get_config(path):
    with open(f'{path}', "r") as fh:
        text = fh.read()
        return json.loads(text)

def generate_patch(src, dst):
    patch = jsonpatch.make_patch(src, dst)

    return patch


def diff(src, dst):
    print("\n----------\nGetting source JSON...", flush=True)
    src_config = get_config(src)

    print("\n----------\nGetting destination JSON...", flush=True)
    dst_config = get_config(dst)

    print("\n----------\nGenerating patch...", flush=True)
    patch = generate_patch(src_config, dst_config)

    print("\n----------\nPrinting patch...", flush=True)
    print(patch)

def main():
    parser=argparse.ArgumentParser(description="Diffs 2 JSON files")
    parser.add_argument("-s", "--source", help="name of source JSON file", required=True)
    parser.add_argument("-d", "--destination", help="name of destination JSON file", required=True)

    args = parser.parse_args()

    src = args.source
    dst = args.destination

    diff(src, dst)

if __name__ == "__main__":
    main()