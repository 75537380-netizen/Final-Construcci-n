/* ===================================================================
   Steam Price Checker — Frontend
   =================================================================== */

const CC_TO_CURRENCY = {
  US:'USD', PE:'PEN', AR:'ARS', BR:'BRL',
  MX:'MXN', CL:'CLP', GB:'GBP', DE:'EUR',
  AU:'AUD', CA:'CAD',
};

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------
const API = {
  async search(q, cc = 'US') {
    const r = await fetch(`/api/search?q=${encodeURIComponent(q)}&cc=${cc}`);
    if (!r.ok) throw new Error(r.status);
    return r.json();
  },
  async getGame(appid, cc = 'US') {
    const r = await fetch(`/api/game/${appid}?cc=${cc}`);
    if (!r.ok) throw new Error(r.status);
    return r.json();
  },
  async getFeatured(category = 'specials', cc = 'US', start = 0, tags = '') {
    const p = new URLSearchParams({category, cc, start: String(start)});
    if (tags) p.set('tags', tags);
    const r = await fetch(`/api/featured-deals?${p}`);
    if (!r.ok) throw new Error(r.status);
    return r.json();
  },
  async getDeals(page = 0, pageSize = 24, cc = 'US') {
    const r = await fetch(`/api/deals?page=${page}&page_size=${pageSize}&cc=${cc}`);
    if (!r.ok) throw new Error(r.status);
    return r.json();
  },
  async getByGenre(tags, cc = 'US', start = 0) {
    const r = await fetch(`/api/genre?tags=${encodeURIComponent(tags)}&cc=${cc}&start=${start}`);
    if (!r.ok) throw new Error(r.status);
    return r.json();
  },
  async getGenres() {
    const r = await fetch('/api/genres');
    if (!r.ok) throw new Error(r.status);
    return r.json();
  },
};

// ---------------------------------------------------------------------------
// Utils
// ---------------------------------------------------------------------------
function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

function formatDate(ts) {
  if (!ts) return '';
  return new Date(ts * 1000).toLocaleDateString('es-PE', { year: 'numeric', month: 'short' });
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

const SYMBOLS = {
  USD:'$', PEN:'S/', ARS:'$', BRL:'R$', MXN:'$',
  CLP:'$', GBP:'£', EUR:'€', AUD:'A$', CAD:'C$',
};
function symOf(currency) { return SYMBOLS[currency] || '$'; }

// ---------------------------------------------------------------------------
// Deal score analysis
// ---------------------------------------------------------------------------
function dealScore(price, hl) {
  if (price.is_free) return { label: 'Gratis', cls: 'score-great' };
  if (!hl || hl.price == null) {
    if (price.discount >= 75) return { label: 'Oferta excepcional', cls: 'score-legendary' };
    if (price.discount >= 50) return { label: 'Gran oferta', cls: 'score-great' };
    if (price.is_on_sale)     return { label: 'En oferta', cls: 'score-ok' };
    return { label: 'Precio regular', cls: 'score-normal' };
  }
  const hlRef = hl._converted || hl;
  const cur = price.final, low = hlRef.price;
  if (low <= 0 || cur <= 0) return { label: 'Gratis', cls: 'score-great' };
  const ratio = cur / low;
  if (ratio <= 1.05) return { label: 'Mejor precio histórico', cls: 'score-legendary' };
  if (ratio <= 1.25) return { label: 'Cerca del mínimo histórico', cls: 'score-excellent' };
  if (ratio <= 1.6)  return { label: 'Gran oferta', cls: 'score-great' };
  if (price.is_on_sale) return { label: 'En oferta', cls: 'score-ok' };
  return { label: 'Precio regular', cls: 'score-normal' };
}

function dealAnalysisText(price, hl) {
  if (price.is_free) return 'Este juego es completamente gratuito.';
  if (!hl) {
    if (price.is_on_sale) return `${price.discount}% de descuento sobre el precio base.`;
    return 'Sin descuento. Agrégalo a tu lista de deseos para recibir alertas.';
  }
  const hlRef = hl._converted || hl;
  const cur = price.final, low = hlRef.price;
  const d = formatDate(hl.date);
  const above = low > 0 ? Math.round(((cur - low) / low) * 100) : 0;
  if (cur <= low * 1.05) return `Precio igual o mejor al mínimo histórico${d ? ` (${d})` : ''}. Compra ideal.`;
  if (cur <= low * 1.25) return `Solo ${above}% sobre el mínimo histórico de ${hlRef.formatted}${d ? ` (${d})` : ''}. Excelente oferta.`;
  if (price.is_on_sale)  return `${price.discount}% de descuento. El mejor precio registrado fue ${hlRef.formatted}${d ? ` en ${d}` : ''}.`;
  return `Sin descuento. El mejor precio registrado fue ${hlRef.formatted}${d ? ` en ${d}` : ''}.`;
}

// ---------------------------------------------------------------------------
// Render helpers
// ---------------------------------------------------------------------------
function renderPriceTag(price) {
  if (!price) return '<span class="price-na">N/A</span>';
  if (price.is_free) return '<span class="price-free">Gratis</span>';

  const finalLabel = price.final_formatted || (price.final != null ? `${symOf(price.currency)}${price.final.toFixed(2)}` : null);
  if (!finalLabel) return '<span class="price-na">N/A</span>';

  if (price.is_on_sale && price.initial_formatted && price.initial_formatted !== finalLabel)
    return `<span class="price-original">${escapeHtml(price.initial_formatted)}</span><span class="price-final">${escapeHtml(finalLabel)}</span>`;
  return `<span class="price-final">${escapeHtml(finalLabel)}</span>`;
}

function renderGameCard(game) {
  const card = document.createElement('div');
  card.className = 'game-card';
  card.dataset.appid = game.appid;
  const img   = game.image || game.header_image || '';
  const badge = game.price?.is_on_sale
    ? `<div class="discount-badge">-${game.price.discount}%</div>` : '';
  card.innerHTML = `
    <div class="card-img-wrap">
      ${img
        ? `<img src="${escapeHtml(img)}" alt="${escapeHtml(game.name)}" loading="lazy">`
        : `<div style="width:100%;height:100%;background:var(--bg-primary)"></div>`}
      ${badge}
    </div>
    <div class="card-body">
      <div class="card-title">${escapeHtml(game.name)}</div>
      <div class="card-price">${renderPriceTag(game.price || {})}</div>
    </div>`;
  card.addEventListener('click', () => App.openGame(game.appid));
  return card;
}

function renderSkeletons(container, n = 8) {
  container.innerHTML = Array(n).fill(`
    <div class="skeleton-card">
      <div class="skeleton-img"></div>
      <div class="skeleton-lines">
        <div class="skeleton-line"></div><div class="skeleton-line"></div>
      </div>
    </div>`).join('');
}

function renderEmpty(container, title, desc) {
  container.innerHTML = `
    <div class="state-box" style="grid-column:1/-1">
      <h3>${escapeHtml(title)}</h3><p>${escapeHtml(desc)}</p>
    </div>`;
}

function normalizeHistoricalLow(game) {
  const price = game.price || {};
  const hl = game.historical_low;
  if (!hl || hl.price == null || price.is_free || price.final == null || price.final <= 0) return;

  const currentCurrency = price.currency || 'USD';
  const currentFormatted = price.final_formatted || `${symOf(currentCurrency)}${price.final.toFixed(2)}`;
  const comparable = hl._converted || hl;

  if (comparable.price > price.final) {
    hl._converted = {
      price: price.final,
      formatted: currentFormatted,
      currency: currentCurrency,
      current_is_historical_low: true,
    };
  }
}

// ---------------------------------------------------------------------------
// Price comparison line chart (Chart.js)
// ---------------------------------------------------------------------------
let _activeChart = null;

function renderPriceChart(canvasId, price, hl) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (_activeChart) { _activeChart.destroy(); _activeChart = null; }

  const labels = [], data = [], pointColors = [], currencies = [];

  if (!price.is_free && price.initial > 0) {
    labels.push('Precio base');
    data.push(parseFloat(price.initial.toFixed(2)));
    pointColors.push('#4a8ab8');
    currencies.push(price.currency || 'USD');
  }
  if (!price.is_free && price.final >= 0) {
    labels.push('Precio actual');
    data.push(parseFloat(price.final.toFixed(2)));
    pointColors.push('#66c0f4');
    currencies.push(price.currency || 'USD');
  }
  if (hl && hl.price != null) {
    const hlRef = hl._converted || hl;
    labels.push('Mínimo histórico');
    data.push(parseFloat(hlRef.price.toFixed(2)));
    pointColors.push('#4fa94d');
    currencies.push(hlRef.currency || 'USD');
  }

  if (data.length < 2) return;

  _activeChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data,
        borderColor: 'rgba(102,192,244,0.45)',
        backgroundColor: 'rgba(102,192,244,0.06)',
        pointBackgroundColor: pointColors,
        pointBorderColor: pointColors,
        pointRadius: 7,
        pointHoverRadius: 9,
        borderWidth: 2,
        fill: true,
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => {
              const cur = currencies[ctx.dataIndex] || 'USD';
              return `${cur} ${symOf(cur)}${ctx.parsed.y.toFixed(2)}`;
            },
          },
        },
      },
      scales: {
        y: {
          ticks: { color: '#8f98a0', font: { size: 11 }, callback: v => `${v.toFixed(0)}` },
          grid: { color: 'rgba(42,71,94,0.5)' },
        },
        x: {
          ticks: { color: '#c6d4df', font: { size: 11 } },
          grid: { display: false },
        },
      },
    },
  });
}

// ---------------------------------------------------------------------------
// Game detail modal content
// ---------------------------------------------------------------------------
function renderGameDetail(game) {
  const price = game.price || {};
  const hl    = game.historical_low;
  const score = dealScore(price, hl);
  const text  = dealAnalysisText(price, hl);

  const devs  = (game.developers || []).join(', ') || '—';
  const pubs  = (game.publishers || []).join(', ') || '—';
  const genreChips = (game.genres || []).map(g => `<span class="meta-chip">${escapeHtml(g)}</span>`).join('');
  const metaChip   = game.metacritic ? `<span class="meta-chip meta-score">Metacritic ${game.metacritic}</span>` : '';
  const dateChip   = game.release_date ? `<span class="meta-chip">${escapeHtml(game.release_date)}</span>` : '';

  let priceSec = '';
  if (price.is_free) {
    priceSec = `<div class="detail-price-main"><span class="price-free" style="font-size:1.4rem">Gratis</span></div>`;
  } else {
    const cur = price.final_formatted || (price.final != null ? `${symOf(price.currency)}${price.final.toFixed(2)}` : '—');
    priceSec = `
      <div class="detail-price-main">
        ${price.is_on_sale ? `<div class="discount-badge-lg">-${price.discount}%</div>` : ''}
        <div class="prices">
          ${price.is_on_sale && price.initial_formatted ? `<span class="original">${escapeHtml(price.initial_formatted)}</span>` : ''}
          <span class="current">${escapeHtml(cur)}</span>
        </div>
      </div>`;
  }

  const hlDisplay = hl ? (hl._converted || hl) : null;
  const hlSec = hlDisplay ? `
    <div class="divider-v"></div>
    <div class="historical-low-box">
      <div class="label">Mínimo Histórico</div>
      <div class="low-price">${escapeHtml(hlDisplay.formatted)}</div>
      ${hl.date ? `<div class="low-date">${formatDate(hl.date)}</div>` : ''}
    </div>` : '';

  const chartId = `price-chart-${game.appid}`;

  return `
    ${game.header_image
      ? `<img class="detail-hero" src="${escapeHtml(game.header_image)}" alt="${escapeHtml(game.name)}">`
      : `<div class="detail-hero-placeholder"></div>`}
    <button class="modal-close" id="modal-close-btn" aria-label="Cerrar">✕</button>
    <div class="detail-body">
      <h2 class="detail-title">${escapeHtml(game.name)}</h2>
      <div class="detail-meta-top">${metaChip}${dateChip}${genreChips}</div>

      <div class="detail-price-section">${priceSec}${hlSec}</div>

      <div class="deal-score-banner ${score.cls}">
        <strong>${score.label}</strong> — ${escapeHtml(text)}
      </div>

      ${(!price.is_free && price.initial > 0) ? `
      <div class="chart-section">
        <div class="chart-section-title">Comparación de precios</div>
        <div class="chart-wrap"><canvas id="${chartId}"></canvas></div>
        <div class="chart-note">
          Mínimo histórico vía CheapShark.
          <a href="https://steamdb.info/app/${game.appid}/charts/#price" target="_blank" rel="noopener">
            Ver historial completo en SteamDB →
          </a>
        </div>
      </div>` : ''}

      ${game.short_description
        ? `<div class="detail-description">${escapeHtml(game.short_description)}</div>`
        : ''}

      <div class="detail-info-grid">
        <div class="info-item">
          <div class="info-label">Desarrollador</div>
          <div class="info-value">${escapeHtml(devs)}</div>
        </div>
        <div class="info-item">
          <div class="info-label">Editor</div>
          <div class="info-value">${escapeHtml(pubs)}</div>
        </div>
      </div>

      <div class="detail-actions">
        <a class="btn-steam" href="${escapeHtml(game.steam_url)}" target="_blank" rel="noopener">
          Ver en Steam
        </a>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------
const PAGE_SIZE = 24;

const App = {
  cc:              'US',
  modalOpen:       false,
  currentCategory: 'specials',

  _selectedTags: new Set(),
  _tagLabels:    new Map(),

  _rates: null,

  _dealsPage:    0,
  _dealsLoading: false,

  _featuredOffset:  0,
  _featuredTotal:   0,
  _featuredLoading: false,

  _resultsAll:   [],
  _resultsShown: 0,

  els: {},

  async init() {
    this.els = {
      heroInput:        document.getElementById('hero-input'),
      headerInput:      document.getElementById('header-input'),
      ccSelect:         document.getElementById('cc-select'),
      featuredGrid:     document.getElementById('featured-grid'),
      featuredLoadMore: document.getElementById('featured-load-more'),
      btnFeaturedMore:  document.getElementById('btn-featured-more'),
      homeSection:      document.getElementById('home-section'),
      resultsSection:   document.getElementById('results-section'),
      resultsGrid:      document.getElementById('results-grid'),
      resultsTitle:     document.getElementById('results-title'),
      resultsLoadMore:  document.getElementById('results-load-more'),
      btnResultsMore:   document.getElementById('btn-results-more'),
      btnBack:          document.getElementById('btn-back'),
      modal:            document.getElementById('modal-overlay'),
      modalContent:     document.getElementById('modal-content'),
      genreDialog:      document.getElementById('genre-dialog'),
      genreDialogBody:  document.getElementById('genre-dialog-body'),
      genreSearchInput: document.getElementById('genre-search-input'),
      btnOpenGenres:    document.getElementById('btn-open-genres'),
      btnCloseGenres:   document.getElementById('btn-close-genres'),
      genreBar:         document.getElementById('genre-bar'),
      activeChips:      document.getElementById('active-chips'),
      btnAddGenre:      document.getElementById('btn-add-genre'),
      btnClearGenres:   document.getElementById('btn-clear-genres'),
      genreSteamLink:   document.getElementById('genre-steam-link'),
    };

    const debouncedSearch = debounce(q => this.handleSearch(q), 420);

    [this.els.heroInput, this.els.headerInput].forEach(inp => {
      inp.addEventListener('input', e => {
        const q = e.target.value.trim();
        this.els.heroInput.value = q;
        this.els.headerInput.value = q;
        if (q.length >= 2) {
          debouncedSearch(q);
        } else {
          this.showHome();
        }
      });
    });

    this.els.ccSelect.addEventListener('change', e => {
      this.cc = e.target.value;
      if (this.els.heroInput.value.trim().length >= 2) {
        this.handleSearch(this.els.heroInput.value.trim());
      } else {
        this._loadCurrentCategory();
      }
    });

    this.els.btnFeaturedMore.addEventListener('click', () => {
      if (this.currentCategory === 'specials' && this._selectedTags.size === 0) {
        this._loadMoreDeals();
      } else {
        this._loadMoreFeatured();
      }
    });

    this.els.btnResultsMore.addEventListener('click', () => {
      this._resultsShown = Math.min(this._resultsShown + PAGE_SIZE, this._resultsAll.length);
      this._renderResultsPage();
    });

    this.els.btnBack.addEventListener('click', () => {
      this.showHome();
      this.els.heroInput.value = '';
      this.els.headerInput.value = '';
    });

    this.els.modal.addEventListener('click', e => {
      if (e.target === this.els.modal) this.closeModal();
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        if (this.modalOpen) this.closeModal();
        else if (!this.els.genreDialog.classList.contains('hidden')) this.closeGenreDialog();
      }
    });

    this.els.btnOpenGenres.addEventListener('click', () => this.openGenreDialog());
    this.els.btnAddGenre.addEventListener('click',   () => this.openGenreDialog());
    this.els.btnCloseGenres.addEventListener('click', () => this.closeGenreDialog());
    this.els.btnClearGenres.addEventListener('click', () => this._clearGenres());
    this.els.genreDialog.addEventListener('click', e => {
      if (e.target === this.els.genreDialog) this.closeGenreDialog();
    });

    this.els.genreSearchInput.addEventListener('input', e => {
      const q = e.target.value.toLowerCase().trim();
      document.querySelectorAll('.genre-btn').forEach(btn => {
        btn.classList.toggle('hidden', !btn.textContent.toLowerCase().includes(q));
      });
      document.querySelectorAll('.genre-section-block').forEach(sec => {
        const visible = [...sec.querySelectorAll('.genre-btn')].some(b => !b.classList.contains('hidden'));
        sec.style.display = visible ? '' : 'none';
      });
    });

    await Promise.all([this.loadGenreDialog(), this._loadCurrentCategory()]);
  },

  // ─── Exchange rates ──────────────────────────────────────────────────────────
  async _getExchangeRates() {
    if (this._rates) return this._rates;
    try {
      const r = await fetch('https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json');
      const d = await r.json();
      this._rates = d.usd;
    } catch {
      this._rates = {};
    }
    return this._rates;
  },

  // ─── Genre Dialog ───────────────────────────────────────────────────────────
  async loadGenreDialog() {
    try {
      const sections = await API.getGenres();
      this.els.genreDialogBody.innerHTML = sections.map(sec => `
        <div class="genre-section-block">
          <div class="genre-section-title">${escapeHtml(sec.section)}</div>
          <div class="genre-grid">
            ${sec.items.map(it => `
              <button class="genre-btn" data-tag="${it.tag}" data-label="${escapeHtml(it.label)}">
                ${escapeHtml(it.label)}
              </button>`).join('')}
          </div>
        </div>`).join('');

      this.els.genreDialogBody.querySelectorAll('.genre-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const tag   = parseInt(btn.dataset.tag);
          const label = btn.dataset.label;
          if (this._selectedTags.has(tag)) {
            this._removeTag(tag);
          } else {
            this._addTag(tag, label);
          }
          this.closeGenreDialog();
        });
      });
    } catch {
      this.els.genreDialogBody.innerHTML = '<p style="color:var(--text-dim);padding:1rem">No se pudo cargar la lista de géneros.</p>';
    }
  },

  openGenreDialog() {
    this.els.genreDialogBody.querySelectorAll('.genre-btn').forEach(btn => {
      const tag = parseInt(btn.dataset.tag);
      btn.classList.remove('hidden');
      btn.classList.toggle('active', this._selectedTags.has(tag));
    });
    this.els.genreDialogBody.querySelectorAll('.genre-section-block').forEach(s => s.style.display = '');
    this.els.genreSearchInput.value = '';
    this.els.genreDialog.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    setTimeout(() => this.els.genreSearchInput.focus(), 60);
  },

  closeGenreDialog() {
    this.els.genreDialog.classList.add('hidden');
    document.body.style.overflow = this.modalOpen ? 'hidden' : '';
  },

  // ─── Genre tag management ────────────────────────────────────────────────────
  _addTag(tag, label) {
    this._selectedTags.add(tag);
    this._tagLabels.set(tag, label);
    this.els.genreBar.classList.remove('hidden');
    this._renderChips();
    this._loadCurrentCategory();
  },

  _removeTag(tag) {
    this._selectedTags.delete(tag);
    this._tagLabels.delete(tag);
    if (this._selectedTags.size === 0) {
      this._clearGenres();
    } else {
      this._renderChips();
      this._loadCurrentCategory();
    }
  },

  _clearGenres() {
    this._selectedTags.clear();
    this._tagLabels.clear();
    this.els.genreBar.classList.add('hidden');
    this.els.genreSteamLink.classList.add('hidden');
    this._loadCurrentCategory();
  },

  _renderChips() {
    this.els.activeChips.innerHTML = [...this._selectedTags].map(tag => {
      const label = this._tagLabels.get(tag) || String(tag);
      return `<span class="active-chip"><span>${escapeHtml(label)}</span><button class="chip-remove" data-tag="${tag}" aria-label="Quitar ${escapeHtml(label)}">×</button></span>`;
    }).join('');
    this.els.activeChips.querySelectorAll('.chip-remove').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        this._removeTag(parseInt(btn.dataset.tag));
      });
    });
  },

  _updateGenreSteamLink() {
    const tagsParam = [...this._selectedTags].join(',');
    let url = `https://store.steampowered.com/search/?tags=${encodeURIComponent(tagsParam)}`;
    url += '&specials=1';
    this.els.genreSteamLink.innerHTML = `<a href="${url}" target="_blank" rel="noopener">Ver más en Steam →</a>`;
    this.els.genreSteamLink.classList.remove('hidden');
  },

  // ─── Category / Featured ────────────────────────────────────────────────────
  async _loadCurrentCategory() {
    this.currentCategory = 'specials';
    if (this._selectedTags.size === 0) {
      await this._loadDealsFirstPage();
    } else {
      await this._loadFeaturedCategory();
    }
  },

  async _loadDealsFirstPage() {
    this._dealsPage = 0;
    renderSkeletons(this.els.featuredGrid, PAGE_SIZE);
    this.els.featuredLoadMore.classList.add('hidden');
    this.els.genreSteamLink.classList.add('hidden');
    await this._fetchAndAppendDeals();
  },

  async _loadMoreDeals() {
    if (this._dealsLoading) return;
    this._dealsPage++;
    await this._fetchAndAppendDeals();
  },

  async _fetchAndAppendDeals() {
    this._dealsLoading = true;
    this.els.btnFeaturedMore.disabled = true;
    this.els.btnFeaturedMore.textContent = 'Cargando...';
    try {
      const data     = await API.getDeals(this._dealsPage, PAGE_SIZE, this.cc);
      const newDeals = data.deals || [];
      if (this._dealsPage === 0) this.els.featuredGrid.innerHTML = '';
      newDeals.forEach(g => this.els.featuredGrid.appendChild(renderGameCard(g)));
      if (newDeals.length >= PAGE_SIZE) {
        this.els.btnFeaturedMore.textContent = 'Cargar más';
        this.els.featuredLoadMore.classList.remove('hidden');
      } else {
        this.els.featuredLoadMore.classList.add('hidden');
      }
    } catch {
      if (this._dealsPage === 0)
        renderEmpty(this.els.featuredGrid, 'No se pudieron cargar las ofertas', 'Intenta nuevamente.');
      this.els.featuredLoadMore.classList.add('hidden');
    } finally {
      this._dealsLoading = false;
      this.els.btnFeaturedMore.disabled = false;
    }
  },

  async _loadFeaturedCategory() {
    this._featuredOffset  = 0;
    this._featuredTotal   = 0;
    this._featuredLoading = false;
    renderSkeletons(this.els.featuredGrid, PAGE_SIZE);
    this.els.featuredLoadMore.classList.add('hidden');
    this.els.genreSteamLink.classList.add('hidden');
    await this._fetchAndAppendFeatured(false);
  },

  async _loadMoreFeatured() {
    if (this._featuredLoading) return;
    await this._fetchAndAppendFeatured(true);
  },

  async _fetchAndAppendFeatured(append) {
    if (this._featuredLoading) return;
    this._featuredLoading = true;
    if (append) {
      this.els.btnFeaturedMore.disabled    = true;
      this.els.btnFeaturedMore.textContent = 'Cargando...';
    }
    const tags = [...this._selectedTags].join(',');
    try {
      const data  = await API.getFeatured(this.currentCategory, this.cc, this._featuredOffset, tags);
      const items = data.deals || [];
      this._featuredTotal   = data.total_count || 0;
      this._featuredOffset += items.length;

      if (!append) this.els.featuredGrid.innerHTML = '';
      if (!items.length && !append) {
        renderEmpty(this.els.featuredGrid, 'Sin resultados', 'No hay juegos en esta categoría.');
      }
      items.forEach(g => this.els.featuredGrid.appendChild(renderGameCard(g)));

      if (items.length >= PAGE_SIZE && this._featuredOffset < this._featuredTotal) {
        this.els.btnFeaturedMore.textContent = 'Cargar más';
        this.els.btnFeaturedMore.disabled    = false;
        this.els.featuredLoadMore.classList.remove('hidden');
      } else {
        this.els.featuredLoadMore.classList.add('hidden');
        this.els.btnFeaturedMore.disabled = false;
      }

      if (this._selectedTags.size > 0) {
        this._updateGenreSteamLink();
      } else {
        this.els.genreSteamLink.classList.add('hidden');
      }
    } catch {
      if (!append) renderEmpty(this.els.featuredGrid, 'Error al cargar', 'Steam no respondió.');
      this.els.btnFeaturedMore.disabled = false;
    } finally {
      this._featuredLoading = false;
    }
  },

  // ─── Navigation ─────────────────────────────────────────────────────────────
  showHome() {
    this.els.homeSection.classList.remove('hidden');
    this.els.resultsSection.classList.add('hidden');
  },

  showResults() {
    this.els.homeSection.classList.add('hidden');
    this.els.resultsSection.classList.remove('hidden');
  },

  // ─── Text Search ─────────────────────────────────────────────────────────────
  async handleSearch(query) {
    this.showResults();
    this.els.resultsTitle.textContent = `Resultados para "${query}"`;
    renderSkeletons(this.els.resultsGrid, PAGE_SIZE);
    this.els.resultsLoadMore.classList.add('hidden');
    try {
      const data = await API.search(query, this.cc);
      this._resultsAll   = data.results || [];
      this._resultsShown = PAGE_SIZE;
      this._renderResultsPage();
    } catch {
      renderEmpty(this.els.resultsGrid, 'Error de búsqueda', 'No se pudo conectar con Steam.');
    }
  },

  _renderResultsPage() {
    const items = this._resultsAll.slice(0, this._resultsShown);
    this.els.resultsGrid.innerHTML = '';
    if (!items.length) {
      renderEmpty(this.els.resultsGrid, 'Sin resultados', 'Prueba otro nombre o género.');
      this.els.resultsLoadMore.classList.add('hidden');
      return;
    }
    items.forEach(g => this.els.resultsGrid.appendChild(renderGameCard(g)));
    const remaining = this._resultsAll.length - this._resultsShown;
    if (remaining > 0) {
      this.els.btnResultsMore.textContent = `Cargar más (${remaining} restantes)`;
      this.els.resultsLoadMore.classList.remove('hidden');
    } else {
      this.els.resultsLoadMore.classList.add('hidden');
    }
  },

  // ─── Modal ───────────────────────────────────────────────────────────────────
  async openGame(appid) {
    this.els.modalContent.innerHTML = `<div class="modal-loading"><div class="spinner"></div></div>`;
    this.openModal();
    try {
      const game = await API.getGame(appid, this.cc);

      // Convert historical low to selected currency
      const hl = game.historical_low;
      if (hl && hl.price != null && this.cc !== 'US') {
        try {
          const rates    = await this._getExchangeRates();
          const currency = CC_TO_CURRENCY[this.cc] || 'USD';
          const rate     = rates[currency.toLowerCase()];
          if (rate) {
            const converted = hl.price * rate;
            hl._converted = {
              price:     converted,
              formatted: `${symOf(currency)}${converted.toFixed(2)}`,
              currency,
            };
          }
        } catch { /* keep original if conversion fails */ }
      }
      normalizeHistoricalLow(game);

      this.els.modalContent.innerHTML = renderGameDetail(game);
      document.getElementById('modal-close-btn')?.addEventListener('click', () => this.closeModal());

      requestAnimationFrame(() => {
        renderPriceChart(`price-chart-${appid}`, game.price || {}, game.historical_low);
      });
    } catch {
      this.els.modalContent.innerHTML = `
        <div class="state-box" style="padding:3rem">
          <h3>No se pudieron cargar los detalles</h3>
          <p>Steam puede estar limitando solicitudes. Intenta en un momento.</p>
          <button class="btn-load-more" id="modal-close-btn" style="margin-top:1rem">Cerrar</button>
        </div>`;
      document.getElementById('modal-close-btn')?.addEventListener('click', () => this.closeModal());
    }
  },

  openModal() {
    this.els.modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    this.modalOpen = true;
  },

  closeModal() {
    if (_activeChart) { _activeChart.destroy(); _activeChart = null; }
    this.els.modal.classList.add('hidden');
    document.body.style.overflow = '';
    this.modalOpen = false;
    this.els.modalContent.innerHTML = '';
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
