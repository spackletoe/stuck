/**
 * Lovelace card: shows a status panel when Stuck fires `stuck_tag_scanned` (known or pending).
 * Add as a dashboard resource, then add card type `stuck-scan-status-card`.
 */
class StuckScanStatusCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      trackedObjectsEntity: 'sensor.stuck_tracked_objects',
      title: 'Last scan',
      ...config,
    };
  }

  set hass(hass) {
    const wasMissing = !this._hass;
    this._hass = hass;
    if (wasMissing && hass) {
      this._subscribeStuckEvents();
    }
    this._render();
  }

  getCardSize() {
    return this._payload ? 6 : 2;
  }

  disconnectedCallback() {
    this._teardownEvents();
  }

  _teardownEvents() {
    if (this._unsubEvents) {
      try {
        this._unsubEvents();
      } catch (e) {
        /* ignore */
      }
      this._unsubEvents = null;
    }
  }

  async _subscribeStuckEvents() {
    if (!this._hass?.connection || this._unsubEvents) return;
    try {
      this._unsubEvents = await this._hass.connection.subscribeEvents(
        (ev) => this._onStuckTagScanned(ev),
        'stuck_tag_scanned'
      );
    } catch (err) {
      console.error('stuck-scan-status-card: subscribeEvents failed', err);
    }
  }

  _onStuckTagScanned(ev) {
    const payload = ev?.data;
    if (!payload || typeof payload !== 'object') return;
    const want = this.config.config_entry_id;
    if (want && payload.config_entry_id && payload.config_entry_id !== want) {
      return;
    }
    this._payload = payload;
    this._render();
  }

  _mergeLiveRow(row) {
    if (!row?.object_id || !this._hass) return row;
    const inv = this._hass.states[this.config.trackedObjectsEntity]?.attributes?.tracked_objects;
    if (!Array.isArray(inv)) return row;
    const live = inv.find((r) => r.object_id === row.object_id);
    return live ? { ...row, ...live } : row;
  }

  _knownRow() {
    if (!this._payload || this._payload.kind !== 'known') return null;
    return this._mergeLiveRow(this._payload);
  }

  async _callService(domain, service, data) {
    return this._hass.callService(domain, service, data);
  }

  _statusStyle(status) {
    const s = status || '';
    if (s === 'overdue') return 'background: var(--error-color); color: var(--text-primary-color, #fff);';
    if (s === 'due_soon' || s === 'due_now')
      return 'background: var(--warning-color); color: var(--primary-text-color);';
    return 'background: var(--success-color); color: var(--text-primary-color, #fff);';
  }

  _escapeHtml(s) {
    return String(s ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;');
  }

  _renderKnown(row) {
    const interval = `${row.interval_value ?? '—'} ${row.interval_unit ?? ''}`.trim();
    const rows = [
      ['Status', row.status_label || row.status],
      ['Interval', interval],
      ['Last reset', row.last_reset_label || '—'],
      ['Next due', row.next_due_label || '—'],
      ['Time since reset', row.time_elapsed_label || '—'],
      ['Time until due', row.time_remaining_label || '—'],
    ];
    if (row.status === 'overdue' && row.overdue_duration_label) {
      rows.push(['Overdue by', row.overdue_duration_label]);
    }
    if (!row.active) {
      rows.push(['Note', 'This object is inactive in Stuck; status is shown as healthy.']);
    }

    const stats = rows
      .map(
        ([k, v]) => `
        <div class="stat">
          <span class="stat-k">${this._escapeHtml(k)}</span>
          <span class="stat-v">${this._escapeHtml(v)}</span>
        </div>`
      )
      .join('');

    return `
      <div class="head">
        <div class="name">${this._escapeHtml(row.name || 'Tracked object')}</div>
        <span class="pill" style="${this._statusStyle(row.status)}">${this._escapeHtml(
      row.status_label || row.status || 'unknown'
    )}</span>
      </div>
      <div class="stats">${stats}</div>
      <div class="actions">
        <button type="button" data-action="reset">Reset timer</button>
        <button type="button" class="secondary" data-action="open">Open in dashboard</button>
        <button type="button" class="secondary" data-action="dismiss">Dismiss</button>
      </div>
    `;
  }

  _renderPending(p) {
    return `
      <div class="head">
        <div class="name">New tag</div>
        <span class="pill" style="background: var(--secondary-background-color); color: var(--primary-text-color);">Unregistered</span>
      </div>
      <div class="stats">
        <div class="stat">
          <span class="stat-k">Tag ID</span>
          <span class="stat-v mono">${this._escapeHtml(p.tag_id)}</span>
        </div>
        <div class="stat">
          <span class="stat-k">Scans recorded</span>
          <span class="stat-v">${this._escapeHtml(String(p.scan_count ?? '—'))}</span>
        </div>
        <div class="stat">
          <span class="stat-k">Last seen</span>
          <span class="stat-v mono">${this._escapeHtml(p.last_seen_at || '—')}</span>
        </div>
      </div>
      <p class="hint">Use Stuck onboarding or <code>stuck.claim_pending_tag</code> to register this tag.</p>
      <div class="actions">
        <button type="button" class="secondary" data-action="dismiss">Dismiss</button>
      </div>
    `;
  }

  _render() {
    if (!this._hass || !this.config) return;

    if (!this.shadowRoot) {
      this.attachShadow({ mode: 'open' });
    }

    const p = this._payload;
    let body = '';
    if (!p) {
      body = `<div class="empty">Scan a Stuck-linked NFC tag to see live status, reset the timer, and jump to the dashboard.</div>`;
    } else if (p.kind === 'known') {
      body = this._renderKnown(this._knownRow());
    } else if (p.kind === 'pending') {
      body = this._renderPending(p);
    } else {
      body = `<div class="empty">Unknown scan payload.</div>`;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; }
        ha-card { padding: 16px; }
        .card-title { font-size: 0.85rem; font-weight: 600; opacity: 0.72; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.04em; }
        .head { display:flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
        .name { font-size: 1.15rem; font-weight: 700; line-height: 1.25; color: var(--primary-text-color); }
        .pill { font-size: 0.75rem; font-weight: 700; padding: 6px 10px; border-radius: 999px; white-space: nowrap; }
        .stats { display:grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; margin-bottom: 14px; }
        .stat { display:flex; flex-direction:column; gap: 4px; min-width: 0; }
        .stat-k { font-size: 0.78rem; opacity: 0.65; text-transform: uppercase; letter-spacing: 0.03em; }
        .stat-v { font-size: 0.95rem; color: var(--primary-text-color); word-break: break-word; }
        .mono { font-family: ui-monospace, monospace; font-size: 0.82rem; }
        .hint { font-size: 0.88rem; color: var(--secondary-text-color); margin: 0 0 12px; line-height: 1.45; }
        .hint code { font-size: 0.8rem; }
        .empty { color: var(--secondary-text-color); font-size: 0.95rem; line-height: 1.45; }
        .actions { display:flex; flex-wrap: wrap; gap: 8px; }
        button {
          border:none; border-radius:12px; padding:12px 14px; cursor:pointer;
          background: var(--primary-color); color: var(--text-primary-color, white);
          font: inherit;
        }
        button.secondary { background: var(--secondary-background-color); color: var(--primary-text-color); }
        button[disabled] { opacity:0.5; cursor:not-allowed; }
      </style>
      <ha-card>
        <div class="card-title">${this._escapeHtml(this.config.title)}</div>
        ${body}
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll('[data-action]').forEach((el) => {
      el.addEventListener('click', async (e) => {
        const action = e.currentTarget.dataset.action;
        const cur = this._payload;
        if (action === 'dismiss') {
          this._payload = null;
          this._render();
          return;
        }
        if (!cur) return;
        if (action === 'open' && cur.kind === 'known' && cur.object_url) {
          window.location.href = cur.object_url;
          return;
        }
        if (action === 'reset' && cur.kind === 'known') {
          const btn = e.currentTarget;
          btn.disabled = true;
          try {
            await this._callService('stuck', 'reset_object', {
              config_entry_id: cur.config_entry_id,
              object_id: cur.object_id,
            });
          } catch (err) {
            console.error('stuck.reset_object failed', err);
            alert('Could not reset timer. Check that the Stuck integration is loaded and config_entry_id matches.');
          } finally {
            btn.disabled = false;
            this._render();
          }
        }
      });
    });
  }
}

customElements.define('stuck-scan-status-card', StuckScanStatusCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'stuck-scan-status-card',
  name: 'Stuck Scan Status',
  description: 'Shows tag scan status, stats, and reset when a Stuck NFC tag is scanned.',
});
