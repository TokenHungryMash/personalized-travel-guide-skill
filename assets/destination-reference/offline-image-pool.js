/* Resolve shared image payloads before the guide application reads its data. */
(() => {
  const pool = document.getElementById('offline-image-pool');
  if (!pool) return;
  const assets = JSON.parse(pool.textContent);
  for (const name of ['src', 'srcset', 'poster']) {
    document.querySelectorAll('[data-offline-asset-' + name + ']').forEach(element => {
      assets[element.getAttribute('data-offline-asset-' + name)] = element.getAttribute(name);
    });
  }
  const resolve = value => {
    if (typeof value === 'string' && value.startsWith('offline-image:')) {
      const id = value.slice('offline-image:'.length);
      if (!Object.hasOwn(assets, id)) throw new Error('Missing offline image: ' + id);
      return assets[id];
    }
    if (Array.isArray(value)) return value.map(resolve);
    if (value && typeof value === 'object') {
      for (const key of Object.keys(value)) value[key] = resolve(value[key]);
    }
    return value;
  };
  const guide = document.getElementById('guide-data');
  if (guide) guide.textContent = JSON.stringify(resolve(JSON.parse(guide.textContent)));
  for (const name of ['src', 'srcset', 'poster']) {
    document.querySelectorAll('[data-offline-' + name + ']').forEach(element => {
      element.setAttribute(name, resolve(element.getAttribute('data-offline-' + name)));
      element.removeAttribute('data-offline-' + name);
    });
  }
  pool.remove();
})();
