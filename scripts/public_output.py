"""Shared artifact policy and complete-reference WHATWG host inspection."""
import json
import subprocess
from pathlib import Path
from public_artifact import ROOT_FILES, ASSET_TYPES, allowed, public_sources


def validate_inspection(value):
    if not isinstance(value,dict) or set(value)!={'hosts','resource_hosts','references'}:
        raise ValueError('Malformed public inspection output')
    for key in ['hosts','resource_hosts']:
        if not isinstance(value[key],list) or any(not isinstance(host,str) or not host for host in value[key]):
            raise ValueError('Malformed public host output')
    if not isinstance(value['references'],list) or any(not isinstance(ref,dict) or set(ref)!={'name','url'} or any(not isinstance(ref[key],str) for key in ['name','url']) for ref in value['references']):
        raise ValueError('Malformed public reference output')
    return value


def inspect_sources(sources,mentions=None):
    if mentions is None:mentions={'version':1,'mentions':[]}
    result=subprocess.run(['node',str(Path(__file__).with_name('privacy-hosts.mjs'))],input=json.dumps(dict(sources=sources,mentions=mentions)),text=True,encoding='utf-8',capture_output=True,timeout=90)
    if result.returncode:raise ValueError('Cannot parse complete public references; malformed or unsupported input')
    return validate_inspection(json.loads(result.stdout))


def hosts(text,kind='url'):
    return set(inspect_sources([dict(name='',kind=kind,source=text)])['hosts'])-{'ghostinthemodels.com'}
