/**
 * Cross-site navigation bar for the websites estate.
 * Injects a minimal footer bar linking to sibling sites.
 * Include this script on every page: <script src="/shared/cross-site-nav.js" defer></script>
 * Or inline it in each site's footer.
 */
(function () {
  const CURRENT = window.location.hostname;
  const SITES = [
    { name: "Kol's Korner", url: 'https://koltregaskes.com', desc: 'AI News & Essays' },
    { name: 'AI Resource Hub', url: 'https://airesourcehub.com', desc: 'Model Comparison' },
    { name: 'Axy Lusion', url: 'https://axylusion.com', desc: 'AI Art & Creative' },
    { name: 'Ghost in the Models', url: 'https://koltregaskes.github.io/ghost-in-the-models/', desc: 'AI Agent Articles' },
    { name: 'Photography', url: 'https://koltregaskesphotography.com', desc: 'Photo Portfolio' },
  ];

  const currentPathParts = window.location.pathname.split('/').filter(Boolean);
  const currentKey = CURRENT === 'koltregaskes.github.io' ? currentPathParts[0] || CURRENT : CURRENT.replace(/^www\./, '');

  function siteKey(site) {
    const url = new URL(site.url);
    if (url.hostname === 'koltregaskes.github.io') {
      return url.pathname.split('/').filter(Boolean)[0] || url.hostname;
    }
    return url.hostname.replace(/^www\./, '');
  }

  const siblings = SITES.filter(s => {
    return siteKey(s) !== currentKey;
  });

  if (siblings.length === 0) return;

  const bar = document.createElement('div');
  bar.setAttribute('role', 'navigation');
  bar.setAttribute('aria-label', 'Other sites by Kol Tregaskes');
  bar.style.cssText = `
    display: flex;
    justify-content: center;
    gap: 1.5rem;
    flex-wrap: wrap;
    padding: 0.8rem 1rem;
    font-size: 0.75rem;
    border-top: 1px solid rgba(128,128,128,0.15);
    background: rgba(0,0,0,0.02);
    font-family: -apple-system, system-ui, sans-serif;
  `;

  // Respect dark themes
  if (document.documentElement.getAttribute('data-theme') === 'dark' ||
      window.matchMedia('(prefers-color-scheme: dark)').matches ||
      getComputedStyle(document.body).backgroundColor.match(/^rgb\((\d+)/)?.[1] < 50) {
    bar.style.background = 'rgba(255,255,255,0.02)';
    bar.style.borderTopColor = 'rgba(255,255,255,0.08)';
  }

  for (const site of siblings) {
    const link = document.createElement('a');
    link.href = site.url;
    link.textContent = site.name;
    link.title = site.desc;
    link.rel = 'noopener';
    link.style.cssText = `
      color: inherit;
      opacity: 0.5;
      text-decoration: none;
      transition: opacity 0.15s;
      white-space: nowrap;
    `;
    link.addEventListener('mouseenter', () => link.style.opacity = '0.9');
    link.addEventListener('mouseleave', () => link.style.opacity = '0.5');
    bar.appendChild(link);
  }

  // Insert before </body>
  document.body.appendChild(bar);
})();





