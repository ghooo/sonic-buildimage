#!/usr/bin/env python3

import argparse
import jsonpatch
import json
import copy
import re
import os
from common import run_command

class JsonChange:
    def __init__(self, jsonPatch):
        self.jsonPatch = jsonPatch

    def apply(self, current_json):
        return self.jsonPatch.apply(current_json)
    
    def __str__(self):
        return f"{{ 'jsonPatch': '{self.jsonPatch}' }}"