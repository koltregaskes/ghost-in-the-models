"""CSP supported by the static GitHub Pages publication (no header-only claims)."""
CSP = "default-src 'self'; img-src 'self' data: https:; media-src 'self' https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'; upgrade-insecure-requests"
CSP_META = '<meta http-equiv="Content-Security-Policy" content="' + CSP + '">'
REFERRER_POLICY = 'strict-origin-when-cross-origin'
