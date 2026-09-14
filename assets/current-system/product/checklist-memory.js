(function () {
  'use strict';

  var root = document.querySelector('#booking');
  if (!root) return;
  var inputs = Array.prototype.slice.call(root.querySelectorAll('input[type="checkbox"]'));
  if (!inputs.length) return;

  var destination = (document.body.dataset.handbookDestinationShort || document.title || 'travel').toLowerCase();
  var storageKey = 'travel-handbook-checklist:v2:' + destination;

  function itemKey(input, index) {
    if (input.dataset.memoryKey) return input.dataset.memoryKey;
    var label = input.closest('label') || input.closest('li') || input.parentElement;
    var text = label ? label.textContent : '';
    var key = text.replace(/\s+/g, ' ').trim().slice(0, 120) || ('item-' + index);
    input.dataset.memoryKey = key;
    return key;
  }

  function readState() {
    try {
      var parsed = JSON.parse(localStorage.getItem(storageKey) || '{}');
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
    } catch (error) {
      return {};
    }
  }

  function writeState(state) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(state));
      return true;
    } catch (error) {
      return false;
    }
  }

  function migrateLegacy(state) {
    if (Object.keys(state).length) return state;
    try {
      var legacy = JSON.parse(localStorage.getItem('bali-packing-2026') || '[]');
      if (Array.isArray(legacy)) {
        legacy.forEach(function (index) {
          if (inputs[index]) state[itemKey(inputs[index], index)] = true;
        });
      }
    } catch (error) {}
    return state;
  }

  function refreshVisuals() {
    inputs.forEach(function (input) {
      var row = input.closest('li');
      if (row) row.classList.toggle('is-packed', input.checked);
    });
    if (typeof window.updatePacking === 'function') window.updatePacking();
  }

  function restore() {
    var state = readState();
    inputs.forEach(function (input, index) {
      input.checked = state[itemKey(input, index)] === true;
    });
    refreshVisuals();
  }

  function save() {
    var state = {};
    inputs.forEach(function (input, index) {
      state[itemKey(input, index)] = input.checked;
    });
    writeState(state);
    refreshVisuals();
  }

  inputs.forEach(function (input) {
    input.addEventListener('change', save);
  });
  window.addEventListener('pageshow', restore);
  window.addEventListener('storage', function (event) {
    if (event.key === storageKey) restore();
  });

  var heading = root.querySelector('.section-heading');
  if (heading && !root.querySelector('.checklist-memory-status')) {
    var status = document.createElement('p');
    status.className = 'checklist-memory-status';
    status.textContent = '勾选进度会自动保存在这台设备上';
    heading.insertAdjacentElement('afterend', status);
  }
  restore();
})();
