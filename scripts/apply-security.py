"""Apply the policy supported by the current GitHub Pages host to public HTML."""
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parent.parent
POLICY = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'; upgrade-insecure-requests"
for name in subprocess.check_output(['git','ls-files','*.html'],text=True,cwd=ROOT).splitlines():
    file = ROOT / name
    text = file.read_text(encoding='utf-8')
    if 'http-equiv="Content-Security-Policy"' not in text:
        text = text.replace('<head>', '<head>\n    <meta http-equiv="Content-Security-Policy" content="' + POLICY + '">\n    <meta name="referrer" content="strict-origin-when-cross-origin">', 1)
        file.write_text(text,encoding='utf-8',newline='\n')