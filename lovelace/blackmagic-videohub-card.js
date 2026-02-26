class BlackmagicVideohubCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
    this._pending = new Set();
  }

  setConfig(config) {
    if (!config) {
      throw new Error("Invalid configuration");
    }
    this._config = {
      title: "Videohub Routing",
      auto_discover: true,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    const rows = this._getOutputRows().length || 4;
    return Math.max(3, Math.min(2 + rows, 12));
  }

  _getOutputRows() {
    if (!this._hass || !this._config) {
      return [];
    }

    const configured = Array.isArray(this._config.entities)
      ? this._config.entities
      : null;

    if (configured && configured.length) {
      return configured
        .map((item) => (typeof item === "string" ? { entity: item } : item))
        .map((item) => {
          const stateObj = this._hass.states[item.entity];
          return stateObj ? { ...item, stateObj } : null;
        })
        .filter(Boolean);
    }

    if (this._config.auto_discover === false) {
      return [];
    }

    return Object.values(this._hass.states)
      .filter((stateObj) => {
        if (!stateObj.entity_id.startsWith("select.")) return false;
        const id = stateObj.entity_id.toLowerCase();
        const name = String(stateObj.attributes.friendly_name || "").toLowerCase();
        return (
          id.includes("videohub") &&
          (name.includes("output") || id.includes("output"))
        );
      })
      .sort((a, b) => this._extractOutputIndex(a) - this._extractOutputIndex(b))
      .map((stateObj) => ({ entity: stateObj.entity_id, stateObj }));
  }

  _extractOutputIndex(stateObj) {
    const source = `${stateObj.entity_id} ${stateObj.attributes.friendly_name || ""}`;
    const match = source.match(/output[_\s]+(\d+)/i);
    return match ? Number(match[1]) : 9999;
  }

  _friendlyEntityLabel(row) {
    if (row.name) return row.name;
    const friendly = row.stateObj.attributes.friendly_name;
    return friendly || row.entity;
  }

  _render() {
    if (!this._config || !this._hass) {
      return;
    }

    const rows = this._getOutputRows();
    const presets = Array.isArray(this._config.presets) ? this._config.presets : [];

    const style = `
      <style>
        :host { display: block; }
        ha-card { padding: 12px; }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
          gap: 8px;
        }
        .title {
          font-size: 1.05rem;
          font-weight: 600;
          line-height: 1.2;
        }
        .subtle {
          color: var(--secondary-text-color);
          font-size: 0.8rem;
        }
        .rows {
          display: grid;
          gap: 10px;
        }
        .row {
          display: grid;
          grid-template-columns: minmax(120px, 1.1fr) minmax(150px, 1.9fr);
          gap: 8px;
          align-items: center;
          padding: 8px;
          border-radius: 10px;
          background: color-mix(in srgb, var(--card-background-color) 85%, var(--primary-color) 15%);
        }
        .row-label {
          display: flex;
          flex-direction: column;
          min-width: 0;
        }
        .row-name {
          font-weight: 600;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .row-id {
          color: var(--secondary-text-color);
          font-size: 0.75rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        select {
          width: 100%;
          min-height: 38px;
          border-radius: 8px;
          border: 1px solid var(--divider-color);
          background: var(--card-background-color);
          color: var(--primary-text-color);
          padding: 6px 8px;
          font: inherit;
        }
        select:disabled,
        button:disabled {
          opacity: 0.7;
          cursor: wait;
        }
        .presets {
          margin-top: 12px;
          display: grid;
          gap: 8px;
        }
        .preset-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 8px;
        }
        button {
          min-height: 38px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          padding: 6px 10px;
          text-align: left;
          font: inherit;
          cursor: pointer;
        }
        .empty {
          padding: 10px;
          border: 1px dashed var(--divider-color);
          border-radius: 10px;
          color: var(--secondary-text-color);
        }
        @media (max-width: 600px) {
          .row {
            grid-template-columns: 1fr;
          }
        }
      </style>
    `;

    const rowsHtml = rows.length
      ? rows
          .map((row) => {
            const attrs = row.stateObj.attributes || {};
            const options = Array.isArray(attrs.options) ? attrs.options : [];
            const current = row.stateObj.state;
            const disabled = this._pending.has(row.entity) ? "disabled" : "";
            const selectId = `route-${row.entity.replace(/[^\w-]/g, "_")}`;
            return `
              <div class="row">
                <div class="row-label">
                  <div class="row-name">${this._escape(this._friendlyEntityLabel(row))}</div>
                  <div class="row-id">${this._escape(row.entity)}</div>
                </div>
                <div>
                  <select id="${selectId}" data-entity="${this._escapeAttr(row.entity)}" ${disabled}>
                    ${options
                      .map((option) => {
                        const selected = option === current ? "selected" : "";
                        return `<option value="${this._escapeAttr(option)}" ${selected}>${this._escape(
                          option
                        )}</option>`;
                      })
                      .join("")}
                  </select>
                </div>
              </div>
            `;
          })
          .join("")
      : `<div class="empty">No Videohub output select entities found. Add entity IDs in card config or verify the integration is loaded.</div>`;

    const presetsHtml = presets.length
      ? `
        <div class="presets">
          <div class="subtle">Presets</div>
          <div class="preset-grid">
            ${presets
              .map((preset, index) => {
                const key = `preset-${index}`;
                const disabled = this._pending.has(key) ? "disabled" : "";
                return `<button type="button" data-preset-index="${index}" ${disabled}>${this._escape(
                  preset.name || `Preset ${index + 1}`
                )}</button>`;
              })
              .join("")}
          </div>
        </div>
      `
      : "";

    this.shadowRoot.innerHTML = `
      ${style}
      <ha-card>
        <div class="header">
          <div class="title">${this._escape(this._config.title || "Videohub Routing")}</div>
          <div class="subtle">${rows.length} output${rows.length === 1 ? "" : "s"}</div>
        </div>
        <div class="rows">${rowsHtml}</div>
        ${presetsHtml}
      </ha-card>
    `;

    this.shadowRoot.querySelectorAll("select[data-entity]").forEach((el) => {
      el.addEventListener("change", async (ev) => {
        const entityId = ev.currentTarget.dataset.entity;
        const option = ev.currentTarget.value;
        await this._routeEntity(entityId, option);
      });
    });

    this.shadowRoot.querySelectorAll("button[data-preset-index]").forEach((el) => {
      el.addEventListener("click", async (ev) => {
        const index = Number(ev.currentTarget.dataset.presetIndex);
        await this._runPreset(index);
      });
    });
  }

  async _routeEntity(entityId, option) {
    if (!this._hass || !entityId) return;
    this._pending.add(entityId);
    this._render();
    try {
      await this._hass.callService("select", "select_option", {
        entity_id: entityId,
        option,
      });
    } finally {
      this._pending.delete(entityId);
      this._render();
    }
  }

  async _runPreset(index) {
    if (!this._hass || !this._config?.presets?.[index]) return;
    const preset = this._config.presets[index];
    const key = `preset-${index}`;
    this._pending.add(key);
    this._render();
    try {
      if (preset.service) {
        const [domain, service] = String(preset.service).split(".", 2);
        await this._hass.callService(domain, service, preset.data || {});
      } else {
        await this._hass.callService("blackmagic_videohub", "route_output", {
          entry_id: preset.entry_id,
          output: preset.output,
          input: preset.input,
        });
      }
    } finally {
      this._pending.delete(key);
      this._render();
    }
  }

  _escape(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  _escapeAttr(value) {
    return this._escape(value).replace(/"/g, "&quot;");
  }

  static getStubConfig() {
    return {
      type: "custom:blackmagic-videohub-card",
      title: "Videohub Routing",
    };
  }
}

customElements.define("blackmagic-videohub-card", BlackmagicVideohubCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "blackmagic-videohub-card",
  name: "Blackmagic Videohub Card",
  description: "Quick routing UI for Blackmagic Videohub select entities",
});
