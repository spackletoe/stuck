class StuckOnboardingCard extends HTMLElement {
  setConfig(config) {
    this.config = {
      onboardingEntity: 'sensor.stuck_onboarding_state',
      tagInventoryEntity: 'sensor.stuck_available_ha_tags',
      title: 'Add Object to Stuck',
      ...config,
    };
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  getCardSize() {
    return 6;
  }

  _state(entityId) {
    return this._hass?.states?.[entityId] ?? null;
  }

  async _callService(service, data = {}) {
    const [domain, name] = service.split('.');
    return this._hass.callService(domain, name, data);
  }

  _renderChoosePath() {
    return `
      <div class="section">
        <div class="title">How do you want to connect a tag?</div>
        <div class="actions two-up">
          <button data-action="choose-new">Use a New Sticker</button>
          <button data-action="choose-existing">Use an Existing HA Tag</button>
        </div>
        <div class="actions">
          <button class="secondary" data-action="cancel">Cancel</button>
        </div>
      </div>
    `;
  }

  _renderNewTagHandoff() {
    return `
      <div class="section">
        <div class="title">Use a New Sticker</div>
        <ol>
          <li>Open Home Assistant Tags</li>
          <li>Create or write the tag</li>
          <li>Return here</li>
          <li>Continue setup</li>
        </ol>
        <div class="actions two-up">
          <button data-action="open-tags">Open Home Assistant Tags</button>
          <button data-action="resume-pending">I'm Back</button>
        </div>
        <div class="actions">
          <button class="secondary" data-action="back">Back</button>
          <button class="secondary" data-action="cancel">Cancel</button>
        </div>
      </div>
    `;
  }

  _renderExistingTagSelect(availableTags, selectedTag) {
    const items = availableTags.length
      ? availableTags
          .map(
            (tag) => `
              <button class="list-item ${selectedTag && (selectedTag.tag_id === tag.tag_id || selectedTag.entity_id === tag.entity_id) ? 'selected' : ''}"
                      data-action="select-tag"
                      data-tag-id="${tag.tag_id || ''}"
                      data-tag-entity-id="${tag.entity_id || ''}">
                <span class="name">${tag.name || tag.tag_id || tag.entity_id}</span>
                <span class="meta">${tag.entity_id || tag.tag_id || ''}</span>
              </button>
            `
          )
          .join('')
      : '<div class="empty">No available HA tags.</div>';

    return `
      <div class="section">
        <div class="title">Choose an Existing HA Tag</div>
        <div class="list">${items}</div>
        <div class="selected-summary">
          ${selectedTag ? `<strong>Selected:</strong> ${selectedTag.name || selectedTag.tag_id || selectedTag.entity_id}` : 'No tag selected yet.'}
        </div>
        <div class="actions two-up">
          <button ${selectedTag ? '' : 'disabled'} data-action="continue-details">Continue</button>
          <button class="secondary" data-action="back">Back</button>
        </div>
        <div class="actions">
          <button class="secondary" data-action="cancel">Cancel</button>
        </div>
      </div>
    `;
  }

  _renderObjectDetails(selectedTag) {
    return `
      <div class="section">
        <div class="title">Finish Setup</div>
        <div class="selected-summary">
          ${selectedTag ? `<strong>Selected tag:</strong> ${selectedTag.name || selectedTag.tag_id || selectedTag.entity_id}` : 'No tag selected yet.'}
        </div>
        <div class="field-group">
          <label>
            Object name
            <input id="stuck-name" type="text" placeholder="Litter Box" />
          </label>
          <label>
            Interval value
            <input id="stuck-interval-value" type="number" min="1" value="30" />
          </label>
          <label>
            Interval unit
            <select id="stuck-interval-unit">
              <option value="day">day</option>
              <option value="week">week</option>
              <option value="month">month</option>
            </select>
          </label>
        </div>
        <div class="actions two-up">
          <button ${selectedTag ? '' : 'disabled'} data-action="finish-onboarding">Create Object</button>
          <button class="secondary" data-action="back">Back</button>
        </div>
        <div class="actions">
          <button class="secondary" data-action="cancel">Cancel</button>
        </div>
      </div>
    `;
  }

  render() {
    if (!this._hass || !this.config) return;

    const onboarding = this._state(this.config.onboardingEntity);
    const tagInventory = this._state(this.config.tagInventoryEntity);
    const mode = onboarding?.state || 'idle';
    const attrs = onboarding?.attributes || {};
    const selectedTag = attrs.selected_tag || null;
    const availableTags = tagInventory?.attributes?.available_tags || [];

    if (!this.shadowRoot) {
      this.attachShadow({ mode: 'open' });
    }

    let content = '';
    if (mode === 'choose_tag_path') {
      content = this._renderChoosePath();
    } else if (mode === 'new_tag_handoff') {
      content = this._renderNewTagHandoff();
    } else if (mode === 'existing_tag_select') {
      content = this._renderExistingTagSelect(availableTags, selectedTag);
    } else if (mode === 'object_details') {
      content = this._renderObjectDetails(selectedTag);
    } else {
      content = `
        <div class="section">
          <div class="title">${this.config.title}</div>
          <div class="actions">
            <button data-action="start">Add Object to Stuck</button>
          </div>
        </div>
      `;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host { display:block; }
        ha-card { padding: 16px; }
        .section { display:flex; flex-direction:column; gap:12px; }
        .title { font-size: 1.1rem; font-weight: 600; }
        .actions { display:flex; gap:8px; flex-wrap:wrap; }
        .actions.two-up > * { flex:1; }
        button {
          border:none; border-radius:12px; padding:12px 14px; cursor:pointer;
          background: var(--primary-color); color: var(--text-primary-color, white);
          font: inherit;
        }
        button.secondary { background: var(--secondary-background-color); color: var(--primary-text-color); }
        button[disabled] { opacity:0.5; cursor:not-allowed; }
        .list { display:flex; flex-direction:column; gap:8px; }
        .list-item { display:flex; flex-direction:column; align-items:flex-start; background: var(--card-background-color); color: var(--primary-text-color); border:1px solid var(--divider-color); }
        .list-item.selected { outline: 2px solid var(--primary-color); }
        .name { font-weight:600; }
        .meta { font-size:0.85rem; opacity:0.75; }
        .selected-summary, .empty { color: var(--secondary-text-color); }
        .field-group { display:flex; flex-direction:column; gap:12px; }
        label { display:flex; flex-direction:column; gap:6px; font-size:0.95rem; }
        input, select {
          padding:10px 12px; border-radius:10px; border:1px solid var(--divider-color);
          background: var(--card-background-color); color: var(--primary-text-color); font:inherit;
        }
      </style>
      <ha-card>
        ${content}
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll('[data-action]').forEach((el) => {
      el.addEventListener('click', async (event) => {
        const action = event.currentTarget.dataset.action;
        const configEntryId = this.config.config_entry_id;

        if (action === 'start') {
          await this._callService('stuck.set_onboarding_mode', {
            config_entry_id: configEntryId,
            mode: 'choose_tag_path',
            return_path: '/stuck-dashboard',
          });
        } else if (action === 'choose-new') {
          await this._callService('stuck.set_onboarding_mode', {
            config_entry_id: configEntryId,
            mode: 'new_tag_handoff',
            return_path: '/stuck-dashboard',
          });
        } else if (action === 'choose-existing') {
          await this._callService('stuck.set_onboarding_mode', {
            config_entry_id: configEntryId,
            mode: 'existing_tag_select',
            return_path: '/stuck-dashboard',
          });
        } else if (action === 'open-tags') {
          window.open('/config/tags', '_blank', 'noopener');
        } else if (action === 'resume-pending') {
          await this._callService('stuck.resume_latest_pending_tag', {
            config_entry_id: configEntryId,
          });
        } else if (action === 'select-tag') {
          await this._callService('stuck.select_existing_tag', {
            config_entry_id: configEntryId,
            selected_tag_id: event.currentTarget.dataset.tagId || undefined,
            selected_tag_entity_id: event.currentTarget.dataset.tagEntityId || undefined,
            selected_tag_source: 'existing',
          });
        } else if (action === 'continue-details') {
          await this._callService('stuck.set_onboarding_mode', {
            config_entry_id: configEntryId,
            mode: 'object_details',
            return_path: '/stuck-dashboard',
          });
        } else if (action === 'finish-onboarding') {
          const name = this.shadowRoot.getElementById('stuck-name')?.value?.trim();
          const intervalValue = parseInt(this.shadowRoot.getElementById('stuck-interval-value')?.value || '0', 10);
          const intervalUnit = this.shadowRoot.getElementById('stuck-interval-unit')?.value;
          if (!name || !intervalValue || !intervalUnit) return;
          await this._callService('stuck.finish_onboarding', {
            config_entry_id: configEntryId,
            name,
            interval_value: intervalValue,
            interval_unit: intervalUnit,
          });
        } else if (action === 'back') {
          await this._callService('stuck.set_onboarding_mode', {
            config_entry_id: configEntryId,
            mode: 'choose_tag_path',
            return_path: '/stuck-dashboard',
          });
        } else if (action === 'cancel') {
          await this._callService('stuck.clear_onboarding_mode', {
            config_entry_id: configEntryId,
          });
          await this._callService('stuck.clear_selected_existing_tag', {
            config_entry_id: configEntryId,
          });
        }
      });
    });
  }
}

customElements.define('stuck-onboarding-card', StuckOnboardingCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'stuck-onboarding-card',
  name: 'Stuck Onboarding Card',
  description: 'Guided onboarding flow for creating Stuck objects from new or existing HA tags.',
});
