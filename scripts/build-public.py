"""Create a new, allowlisted Pages artifact; refuse to reuse a dirty output."""
import argparse
import json
import shutil
from pathlib import Path
from public_output import public_sources

ROOT=Path(__file__).resolve().parent.parent


def build(root,output):
    if output.exists():raise ValueError('Output already exists; use a fresh directory (nothing is deleted).')
    files=public_sources(root)
    if not files:raise ValueError('No public inputs found')
    output.mkdir(parents=True)
    for source in files:
        target=output/source.relative_to(root)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
    # config/ is private build input, never an artifact directory. Export only
    # the already-public, verified contact value; null stays null.
    contact=json.loads((root/'config/contact.json').read_text(encoding='utf-8'))
    (output/'assets/contact.json').write_text(json.dumps({'address':contact.get('address')})+'\n',encoding='utf-8',newline='\n')
    (output/'.nojekyll').write_bytes(b'')
    print(f'Built {len(files)+2} public files into {output}')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist');args=parser.parse_args()
    build(ROOT,args.output.resolve())
