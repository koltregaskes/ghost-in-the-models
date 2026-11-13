/* One public contact setting. Null preserves the existing contact journey. */
(async () => {
  const target = document.getElementById('publication-contact');
  if (!target) return;
  try {
    const response = await fetch(new URL('../config/contact.json', document.currentScript.src));
    if (!response.ok) return;
    const { address } = await response.json();
    if (typeof address !== 'string' || !/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(address)) return;
    const link = document.createElement('a');
    link.href = `mailto:${address}`;
    link.textContent = address;
    target.replaceChildren('Questions or feedback: ', link, '.');
  } catch { /* Keep the existing contact wording if configuration is unavailable. */ }
})();