/**
 * Lovelace: 2×2 summary tiles (tracked / overdue / due soon / pending).
 * Tap a tile to expand a list of names and tag ids instead of opening entity history.
 */
class StuckSummaryTilesCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      objectCountEntity: 'sensor.stuck_object_count',
      overdueCountEntity: 'sensor.stuck_overdue_count',
      dueSoonCountEntity: 'sensor.stuck_due_soon_count',
      pendingCountEntity: 'sensor.stuck_pending_tag_count',
      ...config,
    };
    this._open = null;
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  getCardSize() {
    return this._open ? 10 : 4;
  }

  _state(entityId) {
    return this._hass?.states?.[entityId] ?? null;
  }

  _num(entityId) {
    const st = this._state(entityId);
    if (!st || st.state === 'unavailable' || st.state === 'unknown') return '—';
    const n = parseInt(st.state, 10);
    return Number.isFinite(n) ? String(n) : st.state;
  }

  _objects(entityId) {
    const st = this._state(entityId);
    return Array.isArray(st?.attributes?.objects) ? st.attributes.objects : [];
  }

  _pendingList() {
    const st = this._state(this.config.pendingCountEntity);
    return Array.isArray(st?.attributes?.pending_tags) ? st.attributes.pending_tags : [];
  }

  _escape(s) {
    return String(s ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;');
  }

  _toggle(kind) {
    this._open = this._open === kind ? null : kind;
    this.render();
  }

  _renderObjectRows(items) {
    if (!items.length) {
      return `<div class="empty">None right now.</div>`;
    }
    return items
      .map((o) => {
        const url = o.object_url || '#';
        const tag = o.tag_id ? `<span class="sub mono">${this._escape(o.tag_id)}</span>` : '';
        return `<div class="row">
          <a class="name" href="${this._escape(url)}">${this._escape(o.name || o.object_id)}</a>
          ${tag}
        </div>`;
      })
      .join('');
  }

  _renderPendingRows(items) {
    if (!items.length) {
      return `<div class="empty">No pending tags.</div>`;
    }
    return items
      .map((p) => {
        const meta = [
          p.scan_count != null ? `${p.scan_count} scans` : null,
          p.last_seen_at ? `last ${this._escape(p.last_seen_at)}` : null,
        ]
          .filter(Boolean)
          .join(' · ');
        return `<div class="row">
          <span class="name">${this._escape(p.tag_id)}</span>
          ${meta ? `<span class="sub">${this._escape(meta)}</span>` : ''}
        </div>`;
      })
      .join('');
  }

  _panel() {
    const kind = this._open;
    if (!kind) return '';

    let title = '';
    let body = '';
    if (kind === 'tracked') {
      title = 'Tracked objects';
      body = this._renderObjectRows(this._objects(this.config.objectCountEntity));
    } else if (kind === 'overdue') {
      title = 'Overdue';
      body = this._renderObjectRows(this._objects(this.config.overdueCountEntity));
    } else if (kind === 'dueSoon') {
      title = 'Due soon';
      body = this._renderObjectRows(this._objects(this.config.dueSoonCountEntity));
    } else if (kind === 'pending') {
      title = 'Unfinished setup (pending tags)';
      body = this._renderPendingRows(this._pendingList());
    }

    return `
      <div class="panel">
        <div class="panel-head">
          <span class="panel-title">${this._escape(title)}</span>
          <button type="button" class="panel-close" data-close="1">Close</button>
        </div>
        <div class="panel-body">${body}</div>
      </div>
    `;
  }

  render() {
    if (!this._hass || !this.config) return;

    if (!this.shadowRoot) {
      this.attachShadow({ mode: 'open' });
    }

    const c = this.config;
    const tiles = [
      {
        kind: 'tracked',
        label: 'Tracked Objects',
        value: this._num(c.objectCountEntity),
        icon: 'mdi:tag-multiple',
        active: this._open === 'tracked',
      },
      {
        kind: 'overdue',
        label: 'Overdue',
        value: this._num(c.overdueCountEntity),
        icon: 'mdi:alert-circle',
        active: this._open === 'overdue',
      },
      {
        kind: 'dueSoon',
        label: 'Due Soon',
        value: this._num(c.dueSoonCountEntity),
        icon: 'mdi:clock-alert',
        active: this._open === 'dueSoon',
      },
      {
        kind: 'pending',
        label: 'Unfinished Setup',
        value: this._num(c.pendingCountEntity),
        icon: 'mdi:progress-helper',
        active: this._open === 'pending',
      },
    ];

    const grid = tiles
      .map(
        (t) => `
      <button type="button" class="tile ${t.active ? 'active' : ''}" data-kind="${t.kind}">
        <ha-icon icon="${t.icon}"></ha-icon>
        <div class="tile-text">
          <span class="tile-label">${this._escape(t.label)}</span>
          <span class="tile-value">${this._escape(t.value)}</span>
        </div>
      </button>`
      )
      .join('');

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; }
        ha-card { padding: 12px; }
        .hint { font-size: 0.8rem; color: var(--secondary-text-color); margin: 0 0 10px; line-height: 1.35; }
        .grid { display:grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .tile {
          display:flex; flex-direction:row; align-items:center; gap: 12px; text-align: left;
          padding: 14px 12px; border-radius: 14px; cursor: pointer; font: inherit;
          border: 1px solid var(--divider-color);
          background: var(--card-background-color); color: var(--primary-text-color);
        }
        .tile ha-icon { color: var(--primary-color); --mdc-icon-size: 28px; flex-shrink: 0; }
        .tile:hover { border-color: var(--primary-color); }
        .tile.active { outline: 2px solid var(--primary-color); }
        .tile-label { font-weight: 600; font-size: 0.92rem; display:block; }
        .tile-value { font-size: 1.35rem; font-weight: 700; opacity: 0.95; }
        .tile-text { display:flex; flex-direction:column; gap: 2px; min-width: 0; }
        .panel { margin-top: 14px; border: 1px solid var(--divider-color); border-radius: 12px; overflow: hidden; }
        .panel-head { display:flex; align-items:center; justify-content: space-between; gap: 8px;
          padding: 10px 12px; background: var(--secondary-background-color); }
        .panel-title { font-weight: 600; }
        .panel-close { border:none; background: transparent; color: var(--primary-color); cursor: pointer; font: inherit; font-size: 0.9rem; }
        .panel-body { padding: 10px 12px 12px; max-height: 280px; overflow-y: auto; }
        .row { padding: 8px 0; border-bottom: 1px solid var(--divider-color); display:flex; flex-direction:column; gap: 4px; }
        .row:last-child { border-bottom: none; }
        .row .name { font-weight: 600; color: var(--primary-color); text-decoration: none; word-break: break-word; }
        .row .name:hover { text-decoration: underline; }
        .sub { font-size: 0.82rem; color: var(--secondary-text-color); }
        .mono { font-family: ui-monospace, monospace; }
        .empty { color: var(--secondary-text-color); font-size: 0.92rem; padding: 8px 0; }
      </style>
      <ha-card>
        <p class="hint">Tap a tile to list matching objects or pending tags. Links open your Stuck dashboard path for each object.</p>
        <div class="grid">${grid}</div>
        ${this._panel()}
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll('.tile[data-kind]').forEach((btn) => {
      btn.addEventListener('click', () => this._toggle(btn.dataset.kind));
    });
    const close = this.shadowRoot.querySelector('[data-close="1"]');
    if (close) {
      close.addEventListener('click', () => {
        this._open = null;
        this.render();
      });
    }
  }
}

customElements.define('stuck-summary-tiles-card', StuckSummaryTilesCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'stuck-summary-tiles-card',
  name: 'Stuck Summary Tiles',
  description: 'Tracked, overdue, due soon, and pending counts; tap for lists instead of history.',
});
