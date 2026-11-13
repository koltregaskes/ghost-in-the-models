// Executed in the page by Playwright; page-level clipping is never an exemption.
export function findOverflow() {
  const problems=[];
  const intentional='.gitm-lifewire__viewport, .gitm-reader__portrait, .gitm-card__portrait';
  for (const element of document.querySelectorAll('body *')) {
    if (!(element instanceof HTMLElement)) continue;
    const rect=element.getBoundingClientRect(), style=getComputedStyle(element);
    if (!rect.width || !rect.height || style.visibility==='hidden' || style.opacity==='0') continue;
    let clipped=false, permitted=false;
    for (let parent=element.parentElement;parent;parent=parent.parentElement) {
      const box=parent.getBoundingClientRect(), overflow=getComputedStyle(parent).overflowX;
      if (parent.matches(intentional)) { permitted=true; break; }
      if (['auto','scroll'].includes(overflow) && box.right<=innerWidth+1 && box.left>=-1) { permitted=true; break; }
      if (['hidden','clip'].includes(overflow) && rect.right>box.right+1) clipped=true;
    }
    if (!permitted && (rect.right>innerWidth+1 || clipped)) problems.push({tag:element.tagName,id:element.id,class:element.className,right:Math.round(rect.right),clipped});
  }
  return problems;
}
