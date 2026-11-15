"""Shared artifact policy and complete-reference WHATWG host inspection."""
import json
import subprocess
from pathlib import Path
from public_artifact import ROOT_FILES, ASSET_TYPES, allowed, public_sources


def inspect_sources(sources):
    result=subprocess.run(['node',str(Path(__file__).with_name('privacy-hosts.mjs'))],input=json.dumps(sources),text=True,encoding='utf-8',capture_output=True,timeout=90)
    if result.returncode:raise ValueError('Cannot parse complete public references; malformed or unsupported input')
    return json.loads(result.stdout)


def hosts(text,kind='url'):
    return set(inspect_sources([dict(name='',kind=kind,source=text)])['hosts'])-{'ghostinthemodels.com'}
