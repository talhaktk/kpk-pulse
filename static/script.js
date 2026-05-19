/* ── Global Article Store ── */
const _store = {};
function _save(a) {
  const k = 'a' + Math.random().toString(36).slice(2, 10);
  _store[k] = a;
  return k;
}
function _get(k) { return _store[k] || {}; }

/* ── State ── */
const state = {
  all: [], news: [], newspapers: [], youtube: [], trends: [],
  social: [], govt: [], bookmarks: [],
  activeTab: 'all',
  filters: { source: '', region: '', date: '' },
  allPage: 0,
  PAGE_SIZE: 12,
};

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
  state.bookmarks = JSON.parse(localStorage.getItem('kpk_bookmarks') || '[]');
  loadTab('all');
  fetchStatus();
  document.getElementById('search-input').addEventListener('keyup', e => {
    if (e.key === 'Enter') searchNews();
  });
  setInterval(fetchStatus, 60000);
  setInterval(() => {
    if (state.activeTab !== 'bookmarks') loadTab(state.activeTab, true);
  }, 900000);
});

/* ── Tab Switching ── */
function switchTab(tab, btn) {
  // hide all, deactivate all
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  // show target
  const target = document.getElementById('tab-' + tab);
  if (!target) return;
  target.classList.remove('hidden');
  btn.classList.add('active');
  state.activeTab = tab;

  if (tab === 'bookmarks') { renderBookmarks(); return; }
  const tabData = state[tab];
  if (!tabData || tabData.length === 0) {
    loadTab(tab);
  } else {
    render(tab);
  }
}

/* ── Data Loading ── */
const ENDPOINTS = {
  all: '/api/all', news: '/api/news',
  newspapers: '/api/newspapers', youtube: '/api/youtube',
  trends: '/api/trends', social: '/api/social', govt: '/api/govt',
};

async function loadTab(tab, silent = false) {
  if (!ENDPOINTS[tab]) return;
  if (!silent) showSpinner(tab);
  try {
    const resp = await fetch(ENDPOINTS[tab]);
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const json = await resp.json();
    state[tab] = json.data || [];
    if (tab === 'all') state.allPage = 0;
    render(tab);
    setLastUpdated();
    if (tab === 'all' || tab === 'news') checkBreaking(state[tab]);
  } catch (e) {
    console.error('loadTab error', tab, e);
    showToast('Failed to load ' + tab + '. Retrying…', 'error');
  } finally {
    hideSpinner(tab);
  }
}

function refreshAll() {
  showToast('Refreshing data…');
  fetch('/api/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ modules: [] }),
  }).then(() => loadTab(state.activeTab));
}

/* ── Render Router ── */
function render(tab) {
  const data = applyFiltersTo(state[tab] || []);
  if (tab === 'trends')  { renderTrends(data); return; }
  if (tab === 'youtube') { renderYoutube(data); return; }
  if (tab === 'all')     { renderAll(data); return; }
  renderCards(data, tab + '-grid', tab + '-count');
}

function applyFiltersTo(data) {
  const { source, region, date } = state.filters;
  return data.filter(item => {
    if (source && !(item.source || '').toLowerCase().includes(source.toLowerCase())) return false;
    if (region) {
      const text = ((item.title || '') + ' ' + (item.description || '')).toLowerCase();
      if (!text.includes(region.toLowerCase())) return false;
    }
    if (date) {
      const cutoff = new Date(Date.now() - parseDateFilter(date));
      if (item.published_at && new Date(item.published_at) < cutoff) return false;
    }
    return true;
  });
}

function parseDateFilter(v) {
  return v === '1h' ? 3600000 : v === '6h' ? 21600000 : v === '24h' ? 86400000 : Infinity;
}

/* ── Render Functions ── */
function renderAll(data) {
  document.getElementById('all-count').textContent = data.length;
  const slice = data.slice(0, (state.allPage + 1) * state.PAGE_SIZE);
  document.getElementById('all-grid').innerHTML = slice.map(cardHTML).join('');
  const btn = document.getElementById('load-more-all');
  data.length > slice.length ? btn.classList.remove('hidden') : btn.classList.add('hidden');
}

function loadMore(tab) {
  if (tab === 'all') { state.allPage++; render('all'); }
}

function renderCards(data, gridId, countId) {
  const countEl = document.getElementById(countId);
  const gridEl  = document.getElementById(gridId);
  if (!gridEl) return;
  if (countEl) countEl.textContent = data.length;
  gridEl.innerHTML = data.length
    ? data.map(cardHTML).join('')
    : '<p class="empty-state">No stories found.</p>';
}

function renderYoutube(data) {
  document.getElementById('youtube-count').textContent = data.length;
  document.getElementById('youtube-grid').innerHTML = data.length
    ? data.map(youtubeCardHTML).join('')
    : '<p class="empty-state">No videos found. Add your YouTube API key to .env</p>';
}

function renderTrends(data) {
  document.getElementById('trends-count').textContent = data.length;
  const list = document.getElementById('trends-list');
  if (!data.length) {
    list.innerHTML = '<p class="empty-state">Fetching live trends from Google…</p>';
    return;
  }
  list.innerHTML = data.map(t => {
    const score = t.score || 0;
    return `<div class="trend-item">
      <div class="trend-rank">#${t.rank}</div>
      <div class="trend-info">
        <div class="trend-title">${esc(t.title)}</div>
        ${score ? `<div class="trend-score-bar"><div class="trend-score-fill" style="width:${score}%"></div></div>` : ''}
        ${t.traffic ? `<div class="trend-traffic">🔍 ${esc(t.traffic)} — Pakistan</div>` : ''}
        ${t.news_title ? `<div class="trend-news">📰 ${esc(t.news_title)}</div>` : ''}
      </div>
      <a href="${t.url}" target="_blank" rel="noopener" class="trend-link">Explore →</a>
    </div>`;
  }).join('');
}

function renderBookmarks() {
  const grid  = document.getElementById('bookmarks-grid');
  const empty = document.getElementById('bookmarks-empty');
  document.getElementById('bookmarks-count').textContent = state.bookmarks.length;
  if (!state.bookmarks.length) {
    grid.innerHTML = ''; empty.classList.remove('hidden');
  } else {
    empty.classList.add('hidden');
    grid.innerHTML = state.bookmarks.map(cardHTML).join('');
  }
}

/* ── Card HTML ── */
function cardHTML(a) {
  const k = _save(a);
  const isBreaking   = hasBreakingWord(a.title || '');
  const isBookmarked = state.bookmarks.some(b => b.url === a.url && b.title === a.title);
  const desc   = stripHtml(a.description || '').slice(0, 180);
  const hasUrl = a.url && a.url !== '#' && a.url.startsWith('http');
  const imgSection = a.image
    ? `<img class="card-img" src="${a.image}" alt="" loading="lazy" onerror="this.style.display='none'">`
    : `<div class="card-img-placeholder">${moduleIcon(a.module)}</div>`;

  return `<div class="card">
    ${imgSection}
    <div class="card-body">
      <div class="card-source-row">
        <span class="card-source">${esc(a.source || '')}</span>
        <span class="card-time">${timeAgo(a.published_at)}</span>
      </div>
      <div class="card-tags">
        ${isBreaking ? '<span class="card-tag tag-breaking">⚡ Breaking</span>' : ''}
        ${a.lang === 'ur' ? '<span class="lang-badge">اردو</span>' : ''}
        ${a.platform ? `<span class="card-tag tag-platform">${platIcon(a.platform)} ${esc(a.platform)}</span>` : ''}
        <span class="card-tag tag-module">${esc(a.module || '')}</span>
      </div>
      <div class="card-title">
        ${hasUrl
          ? `<a href="${a.url}" target="_blank" rel="noopener noreferrer">${esc(a.title || '')}</a>`
          : esc(a.title || '')}
      </div>
      ${desc ? `<div class="card-desc">${esc(desc)}${(a.description||'').length > 180 ? '…' : ''}</div>` : ''}
      <div class="card-actions">
        <button class="btn-bookmark ${isBookmarked ? 'bookmarked' : ''}" onclick="toggleBookmark(this,'${k}')" title="Bookmark">🔖</button>
        <button class="btn-alert" onclick="sendAlert('${k}')" title="Send Telegram alert">📲</button>
        ${hasUrl
          ? `<a class="btn-read" href="${a.url}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">Read →</a>`
          : `<span class="btn-read disabled">No link</span>`}
      </div>
    </div>
  </div>`;
}

function youtubeCardHTML(v) {
  const thumb = v.thumbnail
    ? `<img src="${v.thumbnail}" alt="" loading="lazy">`
    : `<div class="yt-thumb-placeholder"><span style="font-size:48px">▶️</span></div>`;
  return `<div class="yt-card">
    <a href="${v.url}" target="_blank" rel="noopener noreferrer" class="yt-thumb">
      ${thumb}
      <span class="yt-play">▶</span>
    </a>
    <div class="yt-body">
      <div class="yt-channel">${esc(v.channel || '')}</div>
      <div class="yt-title"><a href="${v.url}" target="_blank" rel="noopener noreferrer">${esc(v.title || '')}</a></div>
      <div class="yt-meta">${timeAgo(v.published_at)}</div>
    </div>
  </div>`;
}

/* ── Actions ── */
function toggleBookmark(btn, key) {
  const article = _get(key);
  if (!article.title) { showToast('Could not bookmark', 'error'); return; }
  const idx = state.bookmarks.findIndex(b => b.url === article.url && b.title === article.title);
  if (idx === -1) {
    state.bookmarks.push(article);
    btn.classList.add('bookmarked');
    showToast('Bookmarked! 🔖');
  } else {
    state.bookmarks.splice(idx, 1);
    btn.classList.remove('bookmarked');
    showToast('Removed from bookmarks');
  }
  localStorage.setItem('kpk_bookmarks', JSON.stringify(state.bookmarks));
  document.getElementById('bookmarks-count').textContent = state.bookmarks.length;
}

function sendAlert(key) {
  const article = _get(key);
  if (!article.title) { showToast('Missing article data', 'error'); return; }
  fetch('/api/send_alert', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ article }),
  })
    .then(r => r.json())
    .then(d => showToast(d.status === 'ok' ? '📲 Telegram alert sent!' : 'Alert skipped — check Telegram config'))
    .catch(() => showToast('Alert request failed', 'error'));
}

function searchNews() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) return;
  showSpinner('news');
  fetch('/api/news?q=' + encodeURIComponent(q))
    .then(r => r.json())
    .then(json => {
      state.news = json.data || [];
      const btn = document.querySelector('[data-tab="news"]');
      if (btn) switchTab('news', btn);
      showToast('Found ' + state.news.length + ' results for "' + q + '"');
    })
    .catch(() => showToast('Search failed', 'error'))
    .finally(() => hideSpinner('news'));
}

function applyFilters() {
  state.filters.source = document.getElementById('filter-source').value;
  state.filters.region = document.getElementById('filter-region').value;
  state.filters.date   = document.getElementById('filter-date').value;
  render(state.activeTab);
}

function clearFilters() {
  ['filter-source','filter-region','filter-date'].forEach(id => {
    document.getElementById(id).value = '';
  });
  state.filters = { source: '', region: '', date: '' };
  render(state.activeTab);
}

/* ── Breaking News ── */
const BREAKING_WORDS = ['breaking','urgent','alert','exclusive','just in','developing',
  'emergency','explosion','attack','killed','arrested','earthquake','flood','operation'];

function hasBreakingWord(title) {
  const lower = title.toLowerCase();
  return BREAKING_WORDS.some(w => lower.includes(w));
}

function checkBreaking(articles) {
  const breaking = articles.filter(a => hasBreakingWord(a.title || ''));
  if (!breaking.length) return;
  document.getElementById('breaking-text').textContent =
    breaking.slice(0, 5).map(a => a.title).join('   ///   ');
  document.getElementById('breaking-banner').classList.remove('hidden');
}

function closeBanner() {
  document.getElementById('breaking-banner').classList.add('hidden');
}

/* ── API Status ── */
async function fetchStatus() {
  try {
    const json = await fetch('/api/status').then(r => r.json());
    const keys = json.api_keys;
    const dots = document.getElementById('status-dots');
    dots.innerHTML = Object.entries(keys).map(([k, v]) =>
      `<div class="dot ${v ? 'green' : 'grey'}" title="${k.replace(/_/g,' ')}: ${v ? 'OK' : 'not set'}"></div>`
    ).join('');
    dots.dataset.status = JSON.stringify(json);
    dots.onclick = showApiModal;
  } catch (_) {}
}

function showApiModal() {
  const dots = document.getElementById('status-dots');
  let data = {};
  try { data = JSON.parse(dots.dataset.status || '{}'); } catch (_) {}
  const keys = data.api_keys || {};
  document.getElementById('api-status-list').innerHTML = Object.entries(keys).map(([k, v]) => `
    <div class="api-status-item">
      <span>${k.replace(/_/g,' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
      <span style="color:${v ? 'var(--green)' : 'var(--accent2)'}">${v ? '✓ Configured' : '✗ Not Set'}</span>
    </div>`).join('');
  document.getElementById('api-modal').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('api-modal').classList.add('hidden');
}

/* ── Helpers ── */
function showSpinner(tab) { document.getElementById('spinner-' + tab)?.classList.remove('hidden'); }
function hideSpinner(tab) { document.getElementById('spinner-' + tab)?.classList.add('hidden'); }

function setLastUpdated() {
  document.getElementById('last-updated').textContent = 'Updated ' + timeAgo(new Date().toISOString());
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d)) return '';
  const diff = Math.floor((Date.now() - d) / 1000);
  if (diff < 60)    return diff + 's ago';
  if (diff < 3600)  return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return d.toLocaleDateString('en-PK', { day: 'numeric', month: 'short' });
}

function moduleIcon(mod) {
  return { google_news:'📰', newspapers:'🗞️', youtube:'▶️', social_media:'💬', google_trends:'📈', kpk_govt:'🏛️' }[mod] || '📄';
}

function platIcon(p) {
  return { twitter:'𝕏', facebook:'📘', instagram:'📸', reddit:'🔴', youtube:'▶️' }[p] || '';
}

function stripHtml(str) {
  return (str || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function showToast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = 'toast' + (type === 'error' ? ' error' : '');
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
