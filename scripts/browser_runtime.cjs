/* Shared browser discovery for the portable QA entry points. */
const fs = require('node:fs');
const path = require('node:path');

function isFile(filename) {
  try {
    return fs.statSync(filename).isFile();
  } catch {
    return false;
  }
}

function loadChromium(workbench) {
  const modules = process.env.JOURNAL_CHECK_MODULES;
  const searchRoots = [path.resolve(workbench), path.resolve(__dirname, '..'), process.cwd()];
  let entry;
  try {
    entry = modules
      ? require.resolve(path.join(path.resolve(modules), 'playwright-core'))
      : require.resolve('playwright-core', { paths: searchRoots });
  } catch (error) {
    throw new Error(
      'Browser QA requires playwright-core. Run npm install in the workbench, or set ' +
      'JOURNAL_CHECK_MODULES to an existing node_modules directory containing playwright-core. ' +
      (modules ? `The supplied directory was ${path.resolve(modules)}.` : `Searched from ${searchRoots.join(', ')}.`),
      { cause: error }
    );
  }
  return require(entry).chromium;
}

function discoverBrowser(chromium) {
  if (process.env.JOURNAL_CHROME) {
    const configured = path.resolve(process.env.JOURNAL_CHROME);
    if (!isFile(configured)) {
      throw new Error(`JOURNAL_CHROME does not point to a browser executable: ${configured}`);
    }
    return configured;
  }

  const candidates = [chromium.executablePath()];
  if (process.platform === 'win32') {
    for (const base of [process.env.PROGRAMFILES, process.env['PROGRAMFILES(X86)'], process.env.LOCALAPPDATA]) {
      if (base) {
        candidates.push(path.join(base, 'Google', 'Chrome', 'Application', 'chrome.exe'));
        candidates.push(path.join(base, 'Microsoft', 'Edge', 'Application', 'msedge.exe'));
      }
    }
  } else if (process.platform === 'darwin') {
    candidates.push('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
    candidates.push('/Applications/Chromium.app/Contents/MacOS/Chromium');
    if (process.env.HOME) {
      candidates.push(path.join(process.env.HOME, 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome'));
    }
  }
  for (const directory of (process.env.PATH || '').split(path.delimiter).filter(Boolean)) {
    for (const name of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
      candidates.push(path.join(directory, name));
    }
  }
  const executable = candidates.find(isFile);
  if (!executable) {
    throw new Error('No Chromium browser was found. Set JOURNAL_CHROME to a Chrome, Edge or Chromium executable, or install the browser matching playwright-core.');
  }
  return executable;
}

function browserRuntime(workbench) {
  const chromium = loadChromium(workbench);
  return { chromium, executablePath: discoverBrowser(chromium) };
}

module.exports = { browserRuntime };
