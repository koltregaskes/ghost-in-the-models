"""Preserve the existing CSP and disable legacy object embedding."""
from pathlib import Path
import subprocess, re
ROOT = Path(__file__).resolve().parent.parent
for name in subprocess.check_output(['git','ls-files','*.html'],text=True,cwd=ROOT).splitlines():
    file = ROOT / name
    text = file.read_text(encoding='utf-8')
    def policy(match):
        return match[1] + match[2] + ("; object-src 'none'" if 'object-src' not in match[2] else '')
    updated = re.sub(r'(http-equiv="Content-Security-Policy" content=")([^"]+)', policy, text)
    if updated != text:
        file.write_text(updated,encoding='utf-8',newline='\n')