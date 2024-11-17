import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit-element@2.4.0/lit-element.js?module";

class BambuPrintJobsCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
    };
  }

  render() {
    const printJobs = this._getPrintJobs();
    
    return html`
      <ha-card header="Available Print Jobs">
        <div class="card-content">
          ${printJobs.length === 0 
            ? html`<div class="no-jobs">No print jobs available</div>`
            : html`
              <div class="print-jobs-grid">
                ${printJobs.map(job => html`
                  <div class="print-job" @click=${() => this._startPrint(job)}>
                    <img src="${job.image}" alt="${job.name}">
                    <div class="name">${job.name}</div>
                  </div>
                `)}
              </div>
            `}
        </div>
      </ha-card>
    `;
  }

  _getPrintJobs() {
    if (!this.hass) return [];
    
    return Object.entries(this.hass.states)
      .filter(([entityId, state]) => 
        entityId.startsWith('image.') && 
        entityId.includes('_printjob_'))
      .map(([entityId, state]) => ({
        name: state.attributes.friendly_name || entityId.split('_').pop(),
        image: `/local/bambu_lab/cache/${state.attributes.friendly_name}/Metadata/plate_1.png`,
        entityId
      }));
  }

  async _startPrint(job) {
    try {
      await this.hass.callService('image', 'press', {
        entity_id: job.entityId
      });
    } catch (e) {
      console.error('Error starting print:', e);
    }
  }

  static get styles() {
    return css`
      :host {
        --grid-columns: 3;
      }
      .card-content {
        padding: 16px;
      }
      .print-jobs-grid {
        display: grid;
        grid-template-columns: repeat(var(--grid-columns), 1fr);
        gap: 16px;
      }
      .print-job {
        cursor: pointer;
        text-align: center;
        background: var(--ha-card-background, var(--card-background-color, white));
        border-radius: 8px;
        padding: 8px;
        transition: transform 0.2s;
        box-shadow: var(--ha-card-box-shadow, none);
      }
      .print-job:hover {
        transform: scale(1.02);
      }
      .print-job img {
        width: 100%;
        border-radius: 4px;
        aspect-ratio: 1;
        object-fit: cover;
      }
      .name {
        margin-top: 8px;
        font-size: 14px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .no-jobs {
        text-align: center;
        padding: 32px;
        color: var(--primary-text-color);
        font-style: italic;
      }
      @media (max-width: 600px) {
        :host {
          --grid-columns: 2;
        }
      }
      @media (max-width: 400px) {
        :host {
          --grid-columns: 1;
        }
      }
    `;
  }
}

customElements.define("bambu-printjobs-card", BambuPrintJobsCard);