/* ── Global Article Store (avoids broken onclick JSON) ── */
const _store = {};
function _save(a) {
  const k = 'a' + Math.random().toString(36).slice(2, 10);
  _store[k] = a;
  return k;
}
function _get(k) { return _store[k] || {}; }

/* ── State ── */
const state = {
  all: [], news: [], newspapers: [], youtube: [], trends: [], social: [],
  bookmarks: JSON.parse(localStorage.getItem('kpk_bookmarks') || '[]'),
  activeTab: 'all',
  filters: { source: '', region: '', date: '' },
  allPage: 0,
  PAGE_SIZE: 12,
};

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
  loadTab('all');
  fetchStatus();
  document.getElementById('search-input').addEventListener('keyup', e => {
    if (e.key === 'Enter') searchNews();
  });
  setInterval(() => fetchStatus(), 60000);
  // Auto-refresh every 15 minutes
  setInterval(() => { if (state.activeTab !== 'bookmarks') loadTab(state.activeTab, true); }, 900000);
});

/* ── Tab Switching ── */
function switchTab(tab, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.remove('hidden');
  btn.classList.add('active');
  state.activeTab = tab;
  if (tab === 'bookmarks') { renderBookmarks(); return; }
  if (!state[tab] || state[tab].length === 0) loadTab(tab);
  else render(tab);
}

/* ── Data Loading ── */
const ENDPOINTS = {
  all: '/api/all', news: '/api/news',
  newspapers: '/api/newspapers', youtube: '/api/youtube',
  trends: '/api/trends', social: '/api/social',
  govt: '/api/govt',
};

async function loadTab(tab, silent = false) {
  if (!ENDPOINTS[tab]) return;
  if (!silent) showSpinner(tab);
  try {
    const resp = await fetch(ENDPOINTS[tab]);
    const json = await resp.json();
    state[tab] = json.data || [];
    if (tab === 'all') state.allPage = 0;
    render(tab);
    setLastUpdated();
    if (tab === 'all' || tab === 'news') checkBreaking(state[tab]);
  } catch (e) {
    showToast('Failed to load data. Check your connection.', 'error');
  } finally {
    hideSpinner(tab);
  }
}

function refreshAll() {
  showToast('Refreshing all data…');
  fetch('/api/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ modules: [] }),
  }).then(() => loadTab(state.activeTab));
}

/* ── Rendering ── */
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

function parseDateFilter(val) {
  return val === '1h' ? 3600000 : val === '6h' ? 21600000 : val === '24h' ? 86400000 : Infinity;
}

function renderAll(data) {
  const grid  = document.getElementById('all-grid');
  const count = document.getElementById('all-count');
  count.textContent = data.length;
  const slice = data.slice(0, (state.allPage + 1) * state.PAGE_SIZE);
  grid.innerHTML = slice.map(a => cardHTML(a)).join('');
  const btn = document.getElementById('load-more-all');
  data.length > slice.length ? btn.classList.remove('hidden') : btn.classList.add('hidden');
}

function loadMore(tab) {
  if (tab === 'all') { state.allPage++; render('all'); }
}

function renderCards(data, gridId, countId) {
  document.getElementById(countId).textContent = data.length;
  const grid = document.getElementById(gridId);
  grid.innerHTML = data.length
    ? data.map(a => cardHTML(a)).join('')
    : '<p class="empty-state">No stories found.</p>';
}

function renderYoutube(data) {
  document.getElementById('youtube-count').textContent = data.length;
  const grid = document.getElementById('youtube-grid');
  grid.innerHTML = data.length
    ? data.map(v => youtubeCardHTML(v)).join('')
    : '<p class="empty-state">No videos found. Check your YouTube API key.</p>';
}

function renderTrends(data) {
  document.getElementById('trends-count').textContent = data.length;
  const list = document.getElementById('trends-list');
  if (!data.length) {
    list.innerHTML = '<p class="empty-state">No trends data available right now.</p>';
    return;
  }
  list.innerHTML = data.map(t => {
    const score = t.score || 0;
    return `<div class="trend-item">
      <div class="trend-rank">#${t.rank}</div>
      <div class="trend-info">
        <div class="trend-title">${esc(t.title)}</div>
        ${score ? `<div class="trend-score-bar"><div class="trend-score-fill" style="width:${score}%"></div></div>` : ''}
        ${t.traffic ? `<div class="trend-traffic">🔍 ${esc(t.traffic)} (Pakistan)</div>` : ''}
        ${t.news_title ? `<div class="trend-news">📰 ${esc(t.news_title)}</div>` : ''}
      </div>
      <a href="${esc(t.url)}" target="_blank" rel="noopener" class="trend-link">Explore →</a>
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
    grid.innerHTML = state.bookmarks.map(a => cardHTML(a)).join('');
  }
}

/* ── Card HTML ── */
function cardHTML(a) {
  const k = _save(a);
  const isBreaking = hasBreakingWord(a.title || '');
  const isBookmarked = state.bookmarks.some(b => b.url === a.url && b.title === a.title);
  const desc = stripHtml((a.description || '')).slice(0, 180);
  const imgSection = a.image
    ? `<img class="card-img" src="${esc(a.image)}" alt="" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\'card-img-placeholder\'>${moduleIcon(a.module)}</div>'">`
    : `<div class="card-img-placeholder">${moduleIcon(a.module)}</div>`;
  const langBadge = a.lang === 'ur' ? '<span class="lang-badge">اردو</span>' : '';
  const platIcon = a.platform ? platformIcon(a.platform) : '';

  return `<div class="card">
    ${imgSection}
    <div class="card-body">
      <div class="card-source-row">
        <span class="card-source">${esc(a.source || '')}</span>
        <span class="card-time">${timeAgo(a.published_at)}</span>
      </div>
      <div class="card-tags">
        ${isBreaking ? '<span class="card-tag tag-breaking">⚡ Breaking</span>' : ''}
        ${langBadge}
        ${platIcon ? `<span class="card-tag tag-platform">${platIcon} ${esc(a.platform||'')}</span>` : ''}
        <span class="card-tag tag-module">${esc(a.module || '')}</span>
      </div>
      <div class="card-title">
        <a href="${esc(a.url || '#')}" target="_blank" rel="noopener">${esc(a.title || '')}</a>
      </div>
      ${desc ? `<div class="card-desc">${esc(desc)}${(a.description || '').length > 180 ? '…' : ''}</div>` : ''}
      <div class="card-actions">
        <button class="btn-bookmark ${isBookmarked ? 'bookmarked' : ''}" onclick="toggleBookmark(this,'${k}')" title="Bookmark">🔖</button>
        <button class="btn-alert" onclick="sendAlert('${k}')" title="Send Telegram alert">📲 Alert</button>
        <a class="btn-read" href="${esc(a.url || '#')}" target="_blank" rel="noopener">Read →</a>
      </div>
    </div>
  </div>`;
}

function youtubeCardHTML(v) {
  const thumb = v.thumbnail
    ? `<img src="${esc(v.thumbnail)}" alt="" loading="lazy">`
    : `<div class="yt-thumb-placeholder"><span style="font-size:48px">▶️</span></div>`;
  return `<div class="yt-card">
    <a href="${esc(v.url)}" target="_blank" rel="noopener" class="yt-thumb">
      ${thumb}
      <span class="yt-play">▶</span>
    </a>
    <div class="yt-body">
      <div class="yt-channel">${esc(v.channel || '')}</div>
      <div class="yt-title"><a href="${esc(v.url)}" target="_blank" rel="noopener">${esc(v.title || '')}</a></div>
      <div class="yt-meta">${timeAgo(v.published_at)}</div>
    </div>
  </div>`;
}

/* ── Actions ── */
function toggleBookmark(btn, key) {
  const article = _get(key);
  if (!article.title) { showToast('Could not bookmark — missing data', 'error'); return; }
  const idx = state.bookmarks.findIndex(b => b.url === article.url && b.title === article.title);
  if (idx === -1) {
    state.bookmarks.push(article);
    btn.classList.add('bookmarked');
    showToast('Story bookmarked! 🔖');
  } else {
    state.bookmarks.splice(idx, 1);
    btn.classList.remove('bookmarked');
    showToast('Bookmark removed.');
  }
  localStorage.setItem('kpk_bookmarks', JSON.stringify(state.bookmarks));
  document.getElementById('bookmarks-count').textContent = state.bookmarks.length;
}

function sendAlert(key) {
  const article = _get(key);
  if (!article.title) { showToast('Cannot send — missing article data', 'error'); return; }
  fetch('/api/send_alert', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ article }),
  })
    .then(r => r.json())
    .then(d => showToast(d.status === 'ok' ? '📲 Telegram alert sent!' : 'Alert skipped — configure Telegram in .env'))
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
      const tab = document.querySelector('[data-tab="news"]');
      switchTab('news', tab);
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
  ['filter-source', 'filter-region', 'filter-date'].forEach(id => document.getElementById(id).value = '');
  state.filters = { source: '', region: '', date: '' };
  render(state.activeTab);
}

/* ── Breaking News Banner ── */
const BREAKING_WORDS = ['breaking','urgent','alert','exclusive','just in','developing',
  'emergency','explosion','attack','killed','arrested','earthquake','flood','کشیدگی','حملہ'];

function hasBreakingWord(title) {
  const lower = title.toLowerCase();
  return BREAKING_WORDS.some(w => lower.includes(w));
}

function checkBreaking(articles) {
  const breaking = articles.filter(a => hasBreakingWord(a.title || ''));
  if (!breaking.length) return;
  document.getElementById('breaking-text').textContent =
    breaking.map(a => a.title).join('   ///   ');
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
      `<div class="dot ${v ? 'green' : 'grey'}" title="${k.replace(/_/g,' ')}: ${v ? 'OK' : 'not set'}" onclick="showApiModal()"></div>`
    ).join('');
    // store for modal
    dots.dataset.status = JSON.stringify(json);
  } catch (_) {}
}

function showApiModal() {
  const dots = document.getElementById('status-dots');
  let data = {};
  try { data = JSON.parse(dots.dataset.status || '{}'); } catch (_) {}
  const keys = data.api_keys || {};
  document.getElementById('api-status-list').innerHTML = Object.entries(keys).map(([k, v]) => `
    <div class="api-status-item">
      <span>${k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
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
  return { google_news: '📰', newspapers: '🗞️', youtube: '▶️', social_media: '💬', google_trends: '📈', kpk_govt: '🏛️' }[mod] || '📄';
}

function platformIcon(platform) {
  return { twitter: '🐦', facebook: '📘', instagram: '📸', reddit: '🔴', youtube: '▶️' }[platform] || '';
}

function stripHtml(str) {
  return (str || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
}

function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function showToast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = 'toast' + (type === 'error' ? ' error' : '');
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
