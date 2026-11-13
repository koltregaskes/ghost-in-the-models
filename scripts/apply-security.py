"""Apply the shared meta policy without altering other page content."""
from pathlib import Path
import subprocess,re
from security_policy import CSP_META
ROOT=Path(__file__).resolve().parent.parent
for name in subprocess.check_output(['git','ls-files','*.html'],cwd=ROOT,text=True).splitlines():
    p=ROOT/name
    text=p.read_text(encoding='utf-8')
    updated=re.sub(r'<meta http-equiv="Content-Security-Policy" content="[^"]+">',lambda _:CSP_META,text)
    if updated != text: p.write_text(updated,encoding='utf-8',newline='\n')
