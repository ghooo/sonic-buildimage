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
def lcs(S1, S2):
    m=len(S1)
    n=len(S2)
    L = [[0 for x in range(n+1)] for x in range(m+1)]

    # Building the mtrix in bottom-up way
    for i in range(m+1):
        for j in range(n+1):
            if i == 0 or j == 0:
                L[i][j] = 0
            elif S1[i-1] == S2[j-1]:
                L[i][j] = L[i-1][j-1] + 1
            else:
                L[i][j] = max(L[i-1][j], L[i][j-1])

    index = L[m][n]

    lcs_algo = [""] * (index+1)
    lcs_algo[index] = ""

    i = m
    j = n
    while i > 0 and j > 0:

        if S1[i-1] == S2[j-1]:
            lcs_algo[index-1] = S1[i-1]
            i -= 1
            j -= 1
            index -= 1

        elif L[i-1][j] > L[i][j-1]:
            i -= 1
        else:
            j -= 1
    

    result = [x for x in lcs_algo if x != '']

    return result

def get_common_list(src, dst):
    common = []
    for item in src:
        if type(item) is dict or type(item) is list:
            raise AttributeError(f"does not work on list or dict. Found {type(item)}")
    
    return lcs(src, dst)

def get_common_dict(src, dst):
    common = {}

    common_keys = src.keys() & dst.keys()
    for key in common_keys:
        src_val = src[key]
        dst_val = dst[key]

        if type(src_val) != type(dst_val):
            continue
        elif type(src_val) is dict:
            common[key] = get_common_dict(src_val, dst_val)
        elif type(src_val) is list:
            common[key] = get_common_list(src_val, dst_val)
        elif src_val == dst_val:
            common[key] = src_val
        else:
            continue
    
    return common

def get_common_json(src, dst):
    if type(src) != type(dst):
        raise AttributeError(f"cannot get common elements between different JSON types. src type: {type(src)}, dst type: {type(dst)}")
    
    if type(src) is dict:
        return get_common_dict(src, dst)
    elif type(src) is list:
        return get_common_list(src, dst)
    else:
        raise AttributeError(f"only dict or list is supported. found {type(src)}")
    
def get_common(src, dst):
    print("\n----------\nGetting source JSON...", flush=True)
    src_config = get_config(src)

    print("\n----------\nGetting destination JSON...", flush=True)
    dst_config = get_config(dst)

    print("\n----------\nGetting common JSON...", flush=True)
    common_config = get_common_json(src_config, dst_config)

    print("\n----------\nPrinting common JSON...", flush=True)
    print(json.dumps(common_config, sort_keys = True))

def main():
    parser=argparse.ArgumentParser(description="Gets common JSON between 2 JSON files")
    parser.add_argument("-s", "--source", help="name of source JSON file", required=True)
    parser.add_argument("-d", "--destination", help="name of destination JSON file", required=True)

    args = parser.parse_args()

    src = args.source
    dst = args.destination

    get_common(src, dst)

if __name__ == "__main__":
    main()