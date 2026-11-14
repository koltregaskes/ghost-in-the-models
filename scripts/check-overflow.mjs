// Executed in the page by Playwright; page-level clipping is never an exemption.
export function findOverflow() {
  const problems=[];
  const tolerance=2;
  const labelledScroller=element=>{
    const style=getComputedStyle(element);
    const label=element.getAttribute('aria-label')?.trim() || (element.getAttribute('aria-labelledby')||'').split(/\s+/).map(id=>document.getElementById(id)?.textContent.trim()||'').join('').trim();
    return ['auto','scroll'].includes(style.overflowX) && element.tabIndex>=0 && !!label;
  };
  const intentional='.gitm-lifewire__viewport, .gitm-reader__portrait, .gitm-card__portrait';
  for (const element of document.querySelectorAll('body *')) {
    if (!(element instanceof HTMLElement)) continue;
    const rect=element.getBoundingClientRect(), style=getComputedStyle(element);
    if (!rect.width || !rect.height || style.visibility==='hidden' || style.opacity==='0') continue;
    if(element.matches(intentional))continue;
    const contentWide=element.clientWidth>0 && element.scrollWidth>element.clientWidth+tolerance;
    let clipped=false, textClipped=['hidden','clip'].includes(style.overflowX), permitted=labelledScroller(element);
    let innerClip=textClipped;
    for (let parent=element.parentElement;parent;parent=parent.parentElement) {
      const box=parent.getBoundingClientRect(), overflow=getComputedStyle(parent).overflowX;
      if (parent.matches(intentional)) { permitted=true; break; }
      if (!innerClip && labelledScroller(parent) && box.right<=innerWidth+1 && box.left>=-1) { permitted=true; break; }
      if (['hidden','clip'].includes(overflow)) { textClipped=true; innerClip=true; }
      if (['hidden','clip'].includes(overflow) && rect.right>box.right+1) clipped=true;
    }
    const textOverflow=contentWide && (textClipped || ['auto','scroll'].includes(style.overflowX));
    if (!permitted && (rect.right>innerWidth+1 || clipped || textOverflow)) problems.push({tag:element.tagName,id:element.id,class:element.className,right:Math.round(rect.right),clipped,textOverflow,scrollWidth:element.scrollWidth,clientWidth:element.clientWidth});
  }
  return problems;
}
