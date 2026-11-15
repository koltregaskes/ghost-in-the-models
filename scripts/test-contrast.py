"""Offline CSS cascade contract. Unsupported cases fail explicitly."""
from pathlib import Path
import json
from css_cascade import audit_sources
ROOT=Path(__file__).resolve().parent.parent

def audit():
    return audit_sources([(p.name,p.read_text(encoding="utf-8")) for p in sorted((ROOT/"assets").glob("*.css"))])

if __name__=="__main__":
    report=audit()
    print(f"CSS cascade: {len(report['declarations'])} rule records, {len(report['pairs'])} pairs, {len(report['failures'])} contrast failures, {len(report['unsupported'])} unsupported cases")
    for kind in ['failures','unsupported']:
        unique={json.dumps(item,sort_keys=True) for item in report[kind]}
        for line in sorted(unique)[:60]:print(kind+": "+line)
    raise SystemExit(bool(report['failures'] or report['unsupported']))
