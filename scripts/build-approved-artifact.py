"""Run the shared public artifact builder from a pinned, isolated checkout."""
from pathlib import Path
import sys
import argparse
sys.path.insert(0,str(Path(__file__).resolve().parent))
from public_artifact import build

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    build(args.root.resolve(),args.output.resolve())
