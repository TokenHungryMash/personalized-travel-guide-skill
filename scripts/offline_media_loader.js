/* Shared data-URI table: retain each repeated payload once in the portable file. */
(() => {
  const assets = __TRAVEL_MEDIA_TABLE__;
  const pattern = /data:application\/x-travel-asset,[a-f0-9]{64}/g;
  const resolve = value => value.replace(pattern, token => assets[token] || token);
  function hydrate(node) {
    if (node.nodeType !== 1) return;
    for (const name of ['src', 'href', 'poster', 'srcset', 'style']) {
      const value = node.getAttribute(name);
      if (value && value.includes('data:application/x-travel-asset,')) {
        node.setAttribute(name, resolve(value));
      }
    }
    if (node.tagName === 'STYLE' && node.textContent.includes('data:application/x-travel-asset,')) {
      node.textContent = resolve(node.textContent);
    }
    node.querySelectorAll('[src],[href],[poster],[srcset],[style],style').forEach(child => {
      // Descendants are handled once; do not recursively rescan each subtree.
      for (const name of ['src', 'href', 'poster', 'srcset', 'style']) {
        const value = child.getAttribute(name);
        if (value && value.includes('data:application/x-travel-asset,')) child.setAttribute(name, resolve(value));
      }
      if (child.tagName === 'STYLE' && child.textContent.includes('data:application/x-travel-asset,')) child.textContent = resolve(child.textContent);
    });
  }
  new MutationObserver(records => records.forEach(record => {
    if (record.type === 'attributes') hydrate(record.target);
    else record.addedNodes.forEach(hydrate);
  })).observe(document.documentElement, {subtree:true,childList:true,attributes:true,attributeFilter:['src','href','poster','srcset','style']});
  document.addEventListener('DOMContentLoaded', () => hydrate(document.documentElement), {once:true});
  hydrate(document.documentElement);
})();
