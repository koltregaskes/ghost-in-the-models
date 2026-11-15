"""Build the shared allowlisted public artifact into a fresh directory."""
import argparse
from pathlib import Path
from public_artifact import build
ROOT=Path(__file__).resolve().parent.parent
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist');args=parser.parse_args()
    build(ROOT,args.output.resolve())
