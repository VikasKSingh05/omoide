/* Omoide overlay controller. All clip content is inserted as text nodes. */
(() => {
  'use strict';

  const byId = (id) => document.getElementById(id);
  const ui = {
    search: byId('search-input'),
    results: byId('results'),
    resultCount: byId('result-count'),
    footerCount: byId('footer-count'),
    footerTiming: byId('footer-timing'),
    previewKind: byId('preview-kind'),
    previewApp: byId('preview-app'),
    previewTime: byId('preview-time'),
    previewBody: byId('preview-body'),
    previewMeta: byId('preview-meta'),
    themeToggle: byId('theme-toggle'),
    settingsToggle: byId('settings-toggle'),
    drawer: byId('settings-drawer'),
    settingsClose: byId('settings-close'),
    settingsForm: byId('settings-form'),
    hotkey: byId('set-hotkey'),
    capture: byId('set-capture'),
    ocr: byId('set-ocr'),
    storeTitles: byId('set-store-titles'),
    redactAgent: byId('set-redact-agent'),
    mcp: byId('set-mcp'),
    retention: byId('set-retention'),
    excluded: byId('set-excluded'),
    statsLine: byId('stats-line'),
    toasts: byId('toasts'),
    onboarding: byId('onboarding'),
    onboardStepLabel: byId('onboarding-step-label'),
    onboardCapture: byId('onboard-capture'),
    onboardOcr: byId('onboard-ocr'),
    onboardHotkey: byId('onboard-hotkey'),
    onboardBack: byId('onboard-back'),
    onboardNext: byId('onboard-next'),
    onboardFinish: byId('onboard-finish'),
  };

  const state = {
    hits: [],
    selected: -1,
    query: '',
    searchId: 0,
    previewId: 0,
    settings: null,
    settingsOpen: false,
    onboardStep: 0,
    started: false,
  };

  const apiNames = {
    search: 'search',
    paste: 'paste',
    copy_only: 'copy',
    pin: 'pin',
    delete: 'delete',
    get_settings: 'load settings',
    update_settings: 'save settings',
    get_stats: 'load stats',
    get_image: 'load image',
    hide: 'close',
  };

  let debounceTimer = null;

  /* Bridge ---------------------------------------------------------------- */

  function callApi(name, args = [], silent = false) {
    return new Promise((resolve) => {
      const api = window.pywebview && window.pywebview.api;
      if (!api || typeof api[name] !== 'function') {
        if (!silent) showToast('Bridge is not ready yet', 'error');
        resolve(null);
        return;
      }
      try {
        Promise.resolve(api[name](...args)).then(resolve, (error) => {
          if (!silent) reportApiError(name, error);
          resolve(null);
        });
      } catch (error) {
        if (!silent) reportApiError(name, error);
        resolve(null);
      }
    });
  }

  function reportApiError(name, error) {
    const detail = error && error.message ? String(error.message) : 'unknown error';
    showToast(`Failed to ${apiNames[name] || name}: ${detail}`, 'error');
  }

  function showToast(message, kind = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast' + (kind === 'error' ? ' is-error' : kind === 'success' ? ' is-success' : '');
    toast.textContent = String(message);
    ui.toasts.append(toast);
    while (ui.toasts.children.length > 3) ui.toasts.firstElementChild.remove();
    setTimeout(() => toast.remove(), kind === 'error' ? 4200 : 2800);
  }

  /* Small DOM helpers ----------------------------------------------------- */

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = String(text);
    return node;
  }

  function textNode(value) {
    return document.createTextNode(String(value));
  }

  function kbd(label) {
    return el('kbd', null, label);
  }

  function svgIcon(paths) {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '1.6');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true');
    for (const path of paths) {
      const node = document.createElementNS(ns, 'path');
      node.setAttribute('d', path);
      svg.append(node);
    }
    return svg;
  }

  function kindLabel(kind) {
    if (kind === 'image') return 'IMG';
    if (kind === 'html') return 'HTML';
    return 'TXT';
  }

  function kindBadge(kind) {
    const badge = el('span', 'kind-badge', kindLabel(kind));
    if (kind === 'image') badge.classList.add('kind-image');
    return badge;
  }

  function flatten(value) {
    return String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
  }

  function truncate(value, max) {
    return value.length > max ? value.slice(0, max) + '…' : value;
  }

  function relativeTime(timestamp) {
    const value = Number(timestamp);
    if (!Number.isFinite(value) || value <= 0) return 'unknown time';
    const seconds = Math.max(0, Math.floor((Date.now() - value) / 1000));
    if (seconds < 5) return 'just now';
    if (seconds < 60) return `${seconds} sec ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} min ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hr${hours === 1 ? '' : 's'} ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`;
    const weeks = Math.floor(days / 7);
    if (weeks < 5) return `${weeks} week${weeks === 1 ? '' : 's'} ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} month${months === 1 ? '' : 's'} ago`;
    const years = Math.floor(days / 365);
    return `${years} year${years === 1 ? '' : 's'} ago`;
  }

  // Build highlighted text from DOM nodes; no HTML parsing of clip content.
  function appendHighlighted(container, value, terms) {
    const source = String(value == null ? '' : value);
    const lower = source.toLowerCase();
    const ranges = [];
    const seen = new Set();

    for (const term of Array.isArray(terms) ? terms.slice(0, 32) : []) {
      if (typeof term !== 'string') continue;
      const needle = term.trim().toLowerCase();
      if (!needle || seen.has(needle)) continue;
      seen.add(needle);
      let from = 0;
      while (from < lower.length) {
        const start = lower.indexOf(needle, from);
        if (start === -1) break;
        ranges.push([start, start + needle.length]);
        from = start + Math.max(1, needle.length);
      }
    }

    if (!ranges.length) {
      container.append(textNode(source));
      return;
    }

    ranges.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const merged = [];
    for (const range of ranges) {
      const last = merged[merged.length - 1];
      if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]);
      else merged.push(range.slice());
    }

    let cursor = 0;
    for (const [start, end] of merged) {
      if (start > cursor) container.append(textNode(source.slice(cursor, start)));
      container.append(el('mark', null, source.slice(start, end)));
      cursor = end;
    }
    if (cursor < source.length) container.append(textNode(source.slice(cursor)));
  }

  /* Rendering ------------------------------------------------------------- */

  function renderState(title, sub) {
    const view = el('div', 'state-view');
    const icon = el('div', 'state-icon');
    icon.append(svgIcon(['M4.5 5.5h15v11h-8.2L7.8 20v-3.5H4.5z', 'M8.5 10.2h7']));
    view.append(icon, el('div', 'state-title', title), el('div', 'state-sub', sub));
    return view;
  }

  function renderEmptyState() {
    ui.results.replaceChildren();
    const view = renderState(
      'Search your clipboard',
      'Type a word, snippet, URL, or error text. Text inside screenshots is searchable too.'
    );
    const keys = el('div', 'state-keys');
    keys.append(kbd('↑'), kbd('↓'), textNode(' navigate'), el('span', 'dot-separator', '·'), kbd('↵'), textNode(' paste'));
    view.append(keys);
    ui.results.append(view);
  }

  function renderMessage(title, sub) {
    ui.results.replaceChildren(renderState(title, sub));
  }

  function buildRow(hit, index) {
    const row = el('div', 'result-row');
    row.dataset.id = String(hit.id);
    row.setAttribute('role', 'option');
    row.setAttribute('aria-selected', index === state.selected ? 'true' : 'false');
    if (index === state.selected) row.classList.add('is-selected');

    const top = el('div', 'row-top');
    top.append(kindBadge(hit.kind));
    top.append(el('span', 'row-source', hit.source_app || 'unknown app'));
    top.append(el('span', 'row-spacer'));
    if (hit.pinned) top.append(el('span', 'row-pin', 'PIN'));
    const pastes = Number(hit.paste_count) || 0;
    if (pastes > 0) top.append(el('span', 'row-count', `×${pastes}`));
    top.append(el('span', 'row-time', relativeTime(hit.created_at)));

    const line = el('div', 'row-text');
    const full = flatten(hit.text);
    if (!full) {
      line.classList.add('is-empty');
      line.textContent = hit.kind === 'image' ? 'Screenshot (no recognized text)' : 'Empty clip';
    } else {
      appendHighlighted(line, truncate(full, 180), hit.terms);
    }
    row.append(top, line);
    row.title = truncate(full || kindLabel(hit.kind) + ' clip', 300);
    return row;
  }

  function renderResults() {
    ui.results.replaceChildren();
    if (!state.hits.length) {
      renderEmptyState();
      return;
    }
    const fragment = document.createDocumentFragment();
    state.hits.forEach((hit, index) => fragment.append(buildRow(hit, index)));
    ui.results.append(fragment);
  }

  function currentHit() {
    return state.hits[state.selected] || null;
  }

  function selectIndex(index, scroll = false) {
    if (!state.hits.length) return;
    state.selected = (index + state.hits.length) % state.hits.length;
    renderResults();
    renderPreview();
    if (scroll) {
      const row = ui.results.querySelector('.result-row.is-selected');
      if (row) row.scrollIntoView({ block: 'nearest' });
    }
  }

  function renderPreviewEmpty() {
    ui.previewKind.textContent = '—';
    ui.previewApp.textContent = 'No selection';
    ui.previewTime.textContent = '';
    ui.previewBody.replaceChildren(renderState('Nothing to preview', 'Select a result to see the full clip here.'));
    ui.previewMeta.replaceChildren();
  }

  async function renderPreview() {
    const hit = currentHit();
    if (!hit) {
      state.previewId++;
      renderPreviewEmpty();
      return;
    }

    const request = ++state.previewId;
    ui.previewKind.className = 'kind-badge' + (hit.kind === 'image' ? ' kind-image' : '');
    ui.previewKind.textContent = kindLabel(hit.kind);
    ui.previewApp.textContent = hit.source_app || 'unknown app';
    ui.previewTime.textContent = relativeTime(hit.created_at);
    ui.previewBody.replaceChildren();
    ui.previewMeta.replaceChildren();

    const pastes = Number(hit.paste_count) || 0;
    ui.previewMeta.append(textNode(`#${hit.id}`), el('span', 'dot-separator', '·'));
    ui.previewMeta.append(textNode(`${pastes} paste${pastes === 1 ? '' : 's'}`));
    if (hit.blob_hash) {
      ui.previewMeta.append(el('span', 'dot-separator', '·'));
      ui.previewMeta.append(textNode(truncate(String(hit.blob_hash), 14)));
    }

    if (hit.kind === 'image' && hit.blob_hash) {
      const frame = el('div', 'image-frame');
      const image = document.createElement('img');
      image.alt = 'Clipboard screenshot';
      image.style.display = 'none';
      frame.append(image);
      const note = el('div', 'image-note', 'Loading image…');
      ui.previewBody.append(frame, note);

      const source = await callApi('get_image', [hit.blob_hash], true);
      if (request !== state.previewId || currentHit() !== hit) return;
      if (typeof source === 'string' && source) {
        image.src = source;
        image.style.display = 'block';
        note.textContent = hit.text ? 'Recognized text below' : 'No recognized text for this image.';
      } else {
        frame.remove();
        note.textContent = 'Image preview unavailable.';
      }
    }

    if (hit.text) {
      ui.previewBody.append(el('div', 'section-label', hit.kind === 'image' ? 'Recognized text' : 'Full text'));
      const block = el('div', 'preview-text' + (hit.kind === 'html' ? ' is-code' : ''));
      appendHighlighted(block, hit.text, hit.terms);
      ui.previewBody.append(block);
    } else if (hit.kind !== 'image') {
      ui.previewBody.append(el('div', 'preview-text is-empty', 'Empty clip'));
    }

    if (hit.kind === 'html') {
      ui.previewBody.append(el('div', 'preview-note', 'HTML source shown as plain text.'));
    }
  }

  function updateFooter(result) {
    if (!result || !Array.isArray(result.hits)) {
      ui.footerCount.textContent = state.query ? 'Searching…' : 'No results';
      ui.footerTiming.textContent = state.query ? 'Waiting for results' : 'Type to search';
      ui.resultCount.textContent = '—';
      return;
    }
    const count = Number(result.count);
    const shown = Number.isFinite(count) ? count : result.hits.length;
    ui.footerCount.textContent = `${shown} result${shown === 1 ? '' : 's'}`;
    ui.footerTiming.textContent = `${Math.round(Number(result.took_ms) || 0)} ms`;
    ui.resultCount.textContent = String(shown);
  }

  /* Search ---------------------------------------------------------------- */

  function scheduleSearch() {
    state.query = ui.search.value.trim();
    state.searchId++;
    clearTimeout(debounceTimer);

    if (!state.query) {
      state.hits = [];
      state.selected = -1;
      renderEmptyState();
      renderPreview();
      updateFooter(null);
      return;
    }

    updateFooter(null);
    renderMessage('Searching…', 'Looking through your clipboard history.');
    const request = state.searchId;
    debounceTimer = setTimeout(() => performSearch(state.query, request), 120);
  }

  async function performSearch(query, request) {
    const result = await callApi('search', [query]);
    if (request !== state.searchId) return;

    if (!result || !Array.isArray(result.hits)) {
      renderMessage('Search failed', 'Try a different query or check the Omoide service.');
      updateFooter(null);
      return;
    }

    state.hits = result.hits;
    state.selected = state.hits.length ? 0 : -1;
    renderResults();
    renderPreview();
    updateFooter(result);

    if (!state.hits.length) {
      renderMessage('No matches', `Nothing found for “${truncate(query, 60)}”.`);
    }
  }

  /* Actions --------------------------------------------------------------- */

  function focusSearch() {
    try {
      ui.search.focus();
    } catch (_) {
      requestAnimationFrame(() => ui.search.focus());
    }
  }

  async function pasteSelected() {
    const hit = currentHit();
    if (!hit) {
      showToast('Select a result first');
      return;
    }
    focusSearch();
    const result = await callApi('paste', [hit.id]);
    if (result && result.ok === false) showToast(result.error || 'Could not paste this clip', 'error');
  }

  async function copySelected() {
    const hit = currentHit();
    if (!hit) {
      showToast('Select a result first');
      return;
    }
    focusSearch();
    const result = await callApi('copy_only', [hit.id]);
    if (result && result.ok === false) showToast('Could not copy this clip', 'error');
    else if (result) showToast('Copied to clipboard', 'success');
  }

  async function togglePin() {
    const hit = currentHit();
    if (!hit) {
      showToast('Select a result first');
      return;
    }
    focusSearch();
    const next = !hit.pinned;
    const result = await callApi('pin', [hit.id, next]);
    if (!result || result.ok === false) {
      showToast('Could not update pin', 'error');
      return;
    }
    hit.pinned = next;
    renderResults();
    renderPreview();
    showToast(next ? 'Clip pinned' : 'Clip unpinned', 'success');
  }

  async function deleteSelected() {
    const hit = currentHit();
    if (!hit) {
      showToast('Select a result first');
      return;
    }
    focusSearch();
    const index = state.selected;
    state.hits.splice(index, 1);
    state.selected = Math.min(index, state.hits.length - 1);
    ui.footerCount.textContent = `${state.hits.length} result${state.hits.length === 1 ? '' : 's'}`;
    ui.resultCount.textContent = String(state.hits.length);
    renderResults();
    renderPreview();

    const result = await callApi('delete', [hit.id]);
    if (!result || result.ok === false) {
      state.hits.splice(index, 0, hit);
      state.selected = index;
      renderResults();
      renderPreview();
      showToast('Could not delete this clip', 'error');
      return;
    }
    showToast('Clip deleted', 'success');
  }

  async function hideOverlay() {
    await callApi('hide', [], true);
  }

  /* Theme and settings ---------------------------------------------------- */

  function storedTheme() {
    try {
      return localStorage.getItem('omoide.theme');
    } catch (_) {
      return null;
    }
  }

  function applyTheme(theme) {
    const value = theme === 'light' ? 'light' : 'dark';
    document.documentElement.dataset.theme = value;
    try {
      localStorage.setItem('omoide.theme', value);
    } catch (_) {
      // Storage can be unavailable in embedded webviews; the API still persists it.
    }
  }

  async function toggleTheme() {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    focusSearch();
    const result = await callApi('update_settings', [{ theme: next }]);
    if (!result || result.ok === false) showToast('Theme could not be saved', 'error');
  }

  function fillSettingsForm(settings) {
    ui.hotkey.value = typeof settings.hotkey === 'string' ? settings.hotkey : '';
    ui.capture.checked = settings.capture_enabled !== false;
    ui.ocr.checked = settings.ocr_enabled === true;
    ui.storeTitles.checked = settings.store_titles === true;
    ui.redactAgent.checked = settings.redact_agent === true;
    ui.mcp.checked = settings.mcp_enabled === true;
    const retention = Number(settings.retention_days);
    ui.retention.value = Number.isFinite(retention) ? String(retention) : '30';
    ui.excluded.value = Array.isArray(settings.excluded_apps) ? settings.excluded_apps.join('\n') : '';
  }

  async function loadStats() {
    const stats = await callApi('get_stats');
    if (!stats || typeof stats !== 'object') return;
    const number = (value) => Number(value) || 0;
    const parts = [
      `${number(stats.total).toLocaleString()} clips`,
      `${number(stats.text).toLocaleString()} text`,
      `${number(stats.image).toLocaleString()} images`,
      `${number(stats.blocked).toLocaleString()} blocked`,
    ];
    if (stats.oldest_day) parts.push(`oldest ${stats.oldest_day}`);
    ui.statsLine.textContent = parts.join(' · ');
  }

  async function saveSettings(event) {
    event.preventDefault();
    const parsedRetention = Number.parseInt(ui.retention.value, 10);
    const fallbackRetention = Number(state.settings && state.settings.retention_days);
    const patch = {
      hotkey: ui.hotkey.value.trim(),
      capture_enabled: ui.capture.checked,
      ocr_enabled: ui.ocr.checked,
      store_titles: ui.storeTitles.checked,
      redact_agent: ui.redactAgent.checked,
      mcp_enabled: ui.mcp.checked,
      retention_days: Number.isFinite(parsedRetention) && parsedRetention >= 0
        ? parsedRetention
        : (Number.isFinite(fallbackRetention) ? fallbackRetention : 30),
      excluded_apps: ui.excluded.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean),
    };

    const result = await callApi('update_settings', [patch]);
    if (!result || result.ok === false) {
      showToast('Settings could not be saved', 'error');
      return;
    }
    state.settings = Object.assign({}, state.settings, patch);
    showToast('Settings saved', 'success');
  }

  function openDrawer() {
    state.settingsOpen = true;
    ui.drawer.classList.add('is-open');
    ui.drawer.setAttribute('aria-hidden', 'false');
    ui.settingsToggle.setAttribute('aria-expanded', 'true');
    loadStats();
    ui.hotkey.focus();
  }

  function closeDrawer() {
    state.settingsOpen = false;
    ui.drawer.classList.remove('is-open');
    ui.drawer.setAttribute('aria-hidden', 'true');
    ui.settingsToggle.setAttribute('aria-expanded', 'false');
    focusSearch();
  }

  /* First-run setup ------------------------------------------------------- */

  function renderOnboardingStep() {
    const step = state.onboardStep;
    const labels = ['What to capture', 'Choose your hotkey', 'Privacy, by default'];
    ui.onboardStepLabel.textContent = `Step ${step + 1} of 3 · ${labels[step]}`;
    ui.onboarding.querySelectorAll('.onboarding-step').forEach((node) => {
      node.classList.toggle('is-active', Number(node.dataset.step) === step);
    });
    ui.onboarding.querySelectorAll('.onboarding-progress span').forEach((node, index) => {
      node.classList.toggle('is-active', index <= step);
    });
    ui.onboardBack.disabled = step === 0;
    ui.onboardNext.hidden = step === 2;
    ui.onboardFinish.hidden = step !== 2;
  }

  function openOnboarding(settings) {
    ui.onboardCapture.checked = settings.capture_enabled !== false;
    ui.onboardOcr.checked = settings.ocr_enabled !== false;
    ui.onboardHotkey.value = typeof settings.hotkey === 'string' && settings.hotkey
      ? settings.hotkey
      : 'ctrl+shift+v';
    state.onboardStep = 0;
    renderOnboardingStep();
    ui.onboarding.classList.add('is-open');
    ui.onboarding.setAttribute('aria-hidden', 'false');
    setTimeout(() => {
      (state.onboardStep === 1 ? ui.onboardHotkey : ui.onboardCapture).focus();
    }, 0);
  }

  function closeOnboarding() {
    ui.onboarding.classList.remove('is-open');
    ui.onboarding.setAttribute('aria-hidden', 'true');
    focusSearch();
  }

  async function finishOnboarding() {
    const patch = {
      capture_enabled: ui.onboardCapture.checked,
      ocr_enabled: ui.onboardOcr.checked,
      hotkey: ui.onboardHotkey.value.trim() || 'ctrl+shift+v',
      onboarded: true,
    };
    const result = await callApi('update_settings', [patch]);
    if (!result || result.ok === false) {
      showToast('Could not save your setup. Try again.', 'error');
      return;
    }
    state.settings = Object.assign({}, state.settings, patch);
    closeOnboarding();
    fillSettingsForm(state.settings);
    showToast('You are ready. Try searching for something you copied.', 'success');
  }

  /* Events ---------------------------------------------------------------- */

  function rowFromEvent(event) {
    const target = event.target;
    return target && typeof target.closest === 'function' ? target.closest('.result-row') : null;
  }

  function bindEvents() {
    ui.search.addEventListener('input', scheduleSearch);

    ui.onboardBack.addEventListener('click', () => {
      state.onboardStep = Math.max(0, state.onboardStep - 1);
      renderOnboardingStep();
    });
    ui.onboardNext.addEventListener('click', () => {
      state.onboardStep = Math.min(2, state.onboardStep + 1);
      renderOnboardingStep();
      if (state.onboardStep === 1) ui.onboardHotkey.focus();
    });
    ui.onboardFinish.addEventListener('click', finishOnboarding);

    ui.results.addEventListener('mousedown', (event) => {
      if (rowFromEvent(event)) event.preventDefault();
    });
    ui.results.addEventListener('click', (event) => {
      const row = rowFromEvent(event);
      if (!row) return;
      const index = state.hits.findIndex((hit) => String(hit.id) === row.dataset.id);
      if (index >= 0) selectIndex(index);
    });
    ui.results.addEventListener('dblclick', (event) => {
      if (rowFromEvent(event)) pasteSelected();
    });

    document.addEventListener('keydown', (event) => {
      if (ui.onboarding.classList.contains('is-open')) {
        if (event.key === 'Escape') event.preventDefault();
        return;
      }
      if (event.key === 'Escape') {
        event.preventDefault();
        if (state.settingsOpen) closeDrawer();
        else hideOverlay();
        return;
      }
      if (state.settingsOpen) return;

      const target = event.target;
      const typingElsewhere = target && target !== ui.search &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);
      if (typingElsewhere) return;

      if (event.key === 'ArrowDown') {
        event.preventDefault();
        selectIndex(state.selected + 1, true);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        selectIndex(state.selected - 1, true);
      } else if (event.key === 'Enter') {
        event.preventDefault();
        if (event.ctrlKey || event.metaKey) copySelected();
        else pasteSelected();
      } else if ((event.ctrlKey || event.metaKey) && (event.key === 'p' || event.key === 'P')) {
        event.preventDefault();
        togglePin();
      } else if (event.key === 'Delete') {
        event.preventDefault();
        deleteSelected();
      }
    });

    ui.themeToggle.addEventListener('click', toggleTheme);
    ui.settingsToggle.addEventListener('click', () => {
      if (state.settingsOpen) closeDrawer();
      else openDrawer();
    });
    ui.settingsClose.addEventListener('click', closeDrawer);
    ui.settingsForm.addEventListener('submit', saveSettings);

    window.addEventListener('error', (event) => {
      if (event.message) showToast(`Unexpected error: ${event.message}`, 'error');
    });
    window.addEventListener('unhandledrejection', (event) => {
      event.preventDefault();
      showToast('Something went wrong', 'error');
    });
  }

  /* Boot ------------------------------------------------------------------ */

  async function init() {
    if (state.started) return;
    state.started = true;
    bindEvents();
    applyTheme(storedTheme());
    renderEmptyState();
    renderPreview();
    updateFooter(null);
    focusSearch();

    const settings = await callApi('get_settings');
    let needsOnboarding = false;
    if (settings && typeof settings === 'object') {
      state.settings = settings;
      if (settings.theme === 'light' || settings.theme === 'dark') applyTheme(settings.theme);
      fillSettingsForm(settings);
      needsOnboarding = settings.onboarded !== true;
      if (needsOnboarding) openOnboarding(settings);
    }
    await loadStats();
    if (!needsOnboarding) focusSearch();
  }

  if (window.pywebview && window.pywebview.api) init();
  else window.addEventListener('pywebviewready', init, { once: true });
})();
