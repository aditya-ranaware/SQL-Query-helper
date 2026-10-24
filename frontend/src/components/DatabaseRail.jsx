import { rowsText } from '../utils/format'

const SOURCE_LABEL = { sample: 'Sample shop', csv: 'Your CSV files', schema: 'Pasted tables' }

export default function DatabaseRail({ dataset, open, onClose, onChange }) {
  return (
    <aside id="tables-drawer" className={`app-rail ${open ? 'is-open' : ''}`} aria-label="Your tables">
      <div className="rail-head">
        <div>
          <h2 className="rail-title">Your tables</h2>
          <p className="rail-sub">{SOURCE_LABEL[dataset.source] || 'Your data'}</p>
        </div>
        <button type="button" className="rail-close" aria-label="Close tables" onClick={onClose}>
          <i className="bi bi-x-lg" aria-hidden="true" />
        </button>
      </div>

      <ul className="table-list">
        {dataset.tables.map((table) => (
          <li key={table.name}>
            <details className="table-item">
              <summary>
                <i className="bi bi-table" aria-hidden="true" />
                <span className="table-name">{table.name}</span>
                {table.rows !== null && <span className="table-count">{rowsText(table.rows)}</span>}
                <i className="bi bi-chevron-right chev" aria-hidden="true" />
              </summary>
              <ul className="col-list">
                {table.columns.map((col) => (
                  <li key={col.name} className="col-row">
                    <span className="col-name">{col.name}</span>
                    {col.type && <span className="col-type">{col.type}</span>}
                  </li>
                ))}
              </ul>
            </details>
          </li>
        ))}
      </ul>

      <p className="rail-note">
        <i className="bi bi-shield-lock" aria-hidden="true" />
        <span>
          {dataset.has_data
            ? 'Queries are only tried on a copy of this data, never on the original.'
            : 'No data was added, so queries are written and checked but not previewed.'}
        </span>
      </p>

      <button type="button" className="btn btn-outline-primary w-100 mt-3" onClick={onChange}>
        <i className="bi bi-arrow-repeat me-2" aria-hidden="true" />
        Use different data
      </button>
    </aside>
  )
}