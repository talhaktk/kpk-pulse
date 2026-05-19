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
  loadBookmarks();
  setInterval(() => fetchStatus(), 60000);
  setInterval(() => { if (state.activeTab !== 'bookmarks') loadTab(state.activeTab, true); }, 900000);
  document.getElementById('search-input').addEventListener('keyup', e => { if (e.key === 'Enter') searchNews(); });
});

/* ── Tab Switching ── */
function switchTab(tab, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById(`tab-${tab}`).classList.remove('hidden');
  btn.classList.add('active');
  state.activeTab = tab;
  if (tab === 'bookmarks') { renderBookmarks(); return; }
  if (state[tab] && state[tab].length === 0) loadTab(tab);
}

/* ── Data Loading ── */
const ENDPOINTS = {
  all: '/api/all', news: '/api/news',
  newspapers: '/api/newspapers', youtube: '/api/youtube',
  trends: '/api/trends', social: '/api/social',
};

async function loadTab(tab, silent = false) {
  if (!ENDPOINTS[tab]) return;
  if (!silent) showSpinner(tab);
  try {
    const resp = await fetch(ENDPOINTS[tab]);
    const json = await resp.json();
    state[tab] = json.data || [];
    if (tab === 'all') { state.allPage = 0; }
    render(tab);
    setLastUpdated();
    if (tab === 'all' || tab === 'news') checkBreaking(state[tab]);
  } catch (e) {
    toast('Failed to load data. Check your connection.', 'error');
  } finally {
    hideSpinner(tab);
  }
}

function refreshAll() {
  fetch('/api/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ modules: [] }) })
    .then(() => { loadTab(state.activeTab); toast('Data refreshed!'); });
}

/* ── Rendering ── */
function render(tab) {
  const data = applyFiltersTo(state[tab]);
  if (tab === 'trends') { renderTrends(data); return; }
  if (tab === 'youtube') { renderYoutube(data); return; }
  if (tab === 'all') { renderAll(data); return; }
  renderCards(data, `${tab}-grid`, `${tab}-count`);
}

function applyFiltersTo(data) {
  const { source, region, date } = state.filters;
  return data.filter(item => {
    if (source && !item.source?.toLowerCase().includes(source.toLowerCase())) return false;
    if (region) {
      const text = `${item.title || ''} ${item.description || ''}`.toLowerCase();
      if (!text.includes(region.toLowerCase())) return false;
    }
    if (date) {
      const cutoff = new Date(Date.now() - parseDateFilter(date));
      if (new Date(item.published_at) < cutoff) return false;
    }
    return true;
  });
}

function parseDateFilter(val) {
  if (val === '1h') return 3600000;
  if (val === '6h') return 21600000;
  if (val === '24h') return 86400000;
  return Infinity;
}

function renderAll(data) {
  const grid = document.getElementById('all-grid');
  const count = document.getElementById('all-count');
  count.textContent = data.length;
  const slice = data.slice(0, (state.allPage + 1) * state.PAGE_SIZE);
  grid.innerHTML = slice.map(a => cardHTML(a)).join('');
  const btn = document.getElementById('load-more-all');
  if (data.length > slice.length) btn.classList.remove('hidden'); else btn.classList.add('hidden');
}

function loadMore(tab) {
  if (tab === 'all') { state.allPage++; render('all'); }
}

function renderCards(data, gridId, countId) {
  document.getElementById(countId).textContent = data.length;
  document.getElementById(gridId).innerHTML = data.length
    ? data.map(a => cardHTML(a)).join('')
    : '<p class="empty-state">No stories found.</p>';
}

function renderYoutube(data) {
  const grid = document.getElementById('youtube-grid');
  document.getElementById('youtube-count').textContent = data.length;
  grid.innerHTML = data.length
    ? data.map(v => youtubeCardHTML(v)).join('')
    : '<p class="empty-state">No videos found. Add your YouTube API key.</p>';
}

function renderTrends(data) {
  const list = document.getElementById('trends-list');
  document.getElementById('trends-count').textContent = data.length;
  list.innerHTML = data.length
    ? data.map(t => `
        <div class="trend-item">
          <div class="trend-rank">#${t.rank}</div>
          <div class="trend-title">${escHtml(t.title)}</div>
          <a href="${t.url}" target="_blank" class="trend-link">Explore →</a>
        </div>`).join('')
    : '<p class="empty-state">No trends data available.</p>';
}

function renderBookmarks() {
  const grid = document.getElementById('bookmarks-grid');
  const empty = document.getElementById('bookmarks-empty');
  document.getElementById('bookmarks-count').textContent = state.bookmarks.length;
  if (state.bookmarks.length === 0) {
    grid.innerHTML = '';
    empty.classList.remove('hidden');
  } else {
    empty.classList.add('hidden');
    grid.innerHTML = state.bookmarks.map(a => cardHTML(a)).join('');
  }
}

function loadBookmarks() {
  state.bookmarks = JSON.parse(localStorage.getItem('kpk_bookmarks') || '[]');
}

/* ── Card HTML ── */
function cardHTML(a) {
  const isBreaking = isBreakingTitle(a.title || '');
  const isBookmarked = state.bookmarks.some(b => b.url === a.url && b.title === a.title);
  const imgSection = a.image
    ? `<img class="card-img" src="${escHtml(a.image)}" alt="" loading="lazy" onerror="this.style.display='none'">`
    : `<div class="card-img-placeholder">${moduleIcon(a.module)}</div>`;
  return `
    <div class="card" data-url="${escHtml(a.url || '')}">
      ${imgSection}
      <div class="card-body">
        <div class="card-source-row">
          <span class="card-source">${escHtml(a.source || '')}</span>
          <span class="card-time">${timeAgo(a.published_at)}</span>
        </div>
        <div>
          ${isBreaking ? '<span class="card-tag tag-breaking">⚡ Breaking</span>' : ''}
          <span class="card-tag tag-module">${escHtml(a.module || '')}</span>
        </div>
        <div class="card-title">
          <a href="${escHtml(a.url || '#')}" target="_blank" rel="noopener">${escHtml(a.title || '')}</a>
        </div>
        <div class="card-desc">${escHtml((a.description || '').slice(0, 180))}${a.description && a.description.length > 180 ? '…' : ''}</div>
        <div class="card-actions">
          <button class="btn-bookmark ${isBookmarked ? 'bookmarked' : ''}" onclick="toggleBookmark(this, ${escJson(a)})" title="Bookmark">🔖</button>
          <button class="btn-alert" onclick="sendAlert(${escJson(a)})" title="Send Telegram Alert">📲 Alert</button>
        </div>
      </div>
    </div>`;
}

function youtubeCardHTML(v) {
  const thumb = v.thumbnail
    ? `<img src="${escHtml(v.thumbnail)}" alt="" loading="lazy">`
    : `<div class="yt-thumb-placeholder">▶️</div>`;
  return `
    <div class="yt-card">
      <a href="${escHtml(v.url)}" target="_blank" rel="noopener" class="yt-thumb">
        ${thumb}
        <span class="yt-play">▶️</span>
      </a>
      <div class="yt-body">
        <div class="yt-channel">${escHtml(v.channel || '')}</div>
        <div class="yt-title"><a href="${escHtml(v.url)}" target="_blank" rel="noopener">${escHtml(v.title || '')}</a></div>
        <div class="yt-meta">${timeAgo(v.published_at)}</div>
      </div>
    </div>`;
}

/* ── Actions ── */
function toggleBookmark(btn, article) {
  const idx = state.bookmarks.findIndex(b => b.url === article.url && b.title === article.title);
  if (idx === -1) {
    state.bookmarks.push(article);
    btn.classList.add('bookmarked');
    toast('Story bookmarked!');
  } else {
    state.bookmarks.splice(idx, 1);
    btn.classList.remove('bookmarked');
    toast('Bookmark removed.');
  }
  localStorage.setItem('kpk_bookmarks', JSON.stringify(state.bookmarks));
  document.getElementById('bookmarks-count').textContent = state.bookmarks.length;
}

function sendAlert(article) {
  fetch('/api/send_alert', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ article }),
  }).then(r => r.json()).then(d => {
    toast(d.status === 'ok' ? '📲 Telegram alert sent!' : 'Alert skipped (configure Telegram token).');
  });
}

function searchNews() {
  const q = document.getElementById('search-input').value.trim();
  if (!q) return;
  showSpinner('news');
  fetch(`/api/news?q=${encodeURIComponent(q)}`)
    .then(r => r.json())
    .then(json => {
      state.news = json.data || [];
      switchTab('news', document.querySelector('[data-tab="news"]'));
      render('news');
      toast(`Found ${state.news.length} results for "${q}"`);
    }).catch(() => toast('Search failed.', 'error'))
    .finally(() => hideSpinner('news'));
}

function applyFilters() {
  state.filters.source = document.getElementById('filter-source').value;
  state.filters.region = document.getElementById('filter-region').value;
  state.filters.date = document.getElementById('filter-date').value;
  render(state.activeTab);
}

function clearFilters() {
  document.getElementById('filter-source').value = '';
  document.getElementById('filter-region').value = '';
  document.getElementById('filter-date').value = '';
  state.filters = { source: '', region: '', date: '' };
  render(state.activeTab);
}

/* ── Breaking News ── */
const BREAKING_WORDS = ['breaking', 'urgent', 'alert', 'exclusive', 'just in', 'developing', 'emergency', 'explosion', 'attack', 'killed', 'arrested', 'earthquake', 'flood'];

function isBreakingTitle(title) {
  const lower = title.toLowerCase();
  return BREAKING_WORDS.some(w => lower.includes(w));
}

function checkBreaking(articles) {
  const breaking = articles.filter(a => isBreakingTitle(a.title || ''));
  if (breaking.length === 0) return;
  const banner = document.getElementById('breaking-banner');
  const text = document.getElementById('breaking-text');
  text.textContent = breaking.map(a => a.title).join('  ///  ');
  banner.classList.remove('hidden');
}

function closeBanner() {
  document.getElementById('breaking-banner').classList.add('hidden');
}

/* ── Status ── */
async function fetchStatus() {
  try {
    const resp = await fetch('/api/status');
    const json = await resp.json();
    const keys = json.api_keys;
    const dots = document.getElementById('status-dots');
    dots.innerHTML = Object.entries(keys).map(([k, v]) =>
      `<div class="dot ${v ? 'green' : 'grey'}" title="${k}: ${v ? 'configured' : 'not set'}" onclick="showApiModal(${JSON.stringify(json)})"></div>`
    ).join('');
  } catch (e) { /* silent */ }
}

function showApiModal(data) {
  const list = document.getElementById('api-status-list');
  const keys = data.api_keys;
  list.innerHTML = Object.entries(keys).map(([k, v]) => `
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
function showSpinner(tab) { document.getElementById(`spinner-${tab}`)?.classList.remove('hidden'); }
function hideSpinner(tab) { document.getElementById(`spinner-${tab}`)?.classList.add('hidden'); }

function setLastUpdated() {
  document.getElementById('last-updated').textContent = 'Updated ' + timeAgo(new Date().toISOString());
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d)) return '';
  const diff = Math.floor((Date.now() - d) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString();
}

function moduleIcon(mod) {
  const icons = { google_news: '📰', newspapers: '🗞️', youtube: '▶️', social_media: '💬', google_trends: '📈' };
  return icons[mod] || '📄';
}

function escHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escJson(obj) {
  return "'" + JSON.stringify(obj).replace(/'/g, "\\'") + "'";
}

function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type === 'error' ? 'error' : ''}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}
