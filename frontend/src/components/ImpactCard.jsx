import { rowsText } from '../utils/format'
import DataTable from './DataTable'

const PAST = { DELETE: 'deleted', UPDATE: 'changed', INSERT: 'added' }

// Shows what an INSERT, UPDATE or DELETE would do, as tried on a copy of the data
export default function ImpactCard({ preview }) {
  const { kind, affected, table, table_rows: total, sample } = preview
  const share = total && kind !== 'INSERT' ? Math.min(100, Math.round((affected / total) * 100)) : null
  const heavy = share !== null && share >= 50

  return (
    <section className={`impact is-${kind.toLowerCase()} ${heavy ? 'is-heavy' : ''}`} aria-label="Preview on a copy of your data">
      <div className="impact-main">
        <span className="impact-number">{affected.toLocaleString('en-US')}</span>
        <span className="impact-text">
          {kind === 'INSERT'
            ? `${affected === 1 ? 'row' : 'rows'} would be added${table ? ` to ${table}` : ''}${total !== null ? ` (it has ${rowsText(total)} now)` : ''}`
            : total !== null && table
              ? `of ${rowsText(total)} in ${table} would be ${PAST[kind]}`
              : `${affected === 1 ? 'row' : 'rows'} would be ${PAST[kind]}`}
        </span>
      </div>

      {share !== null && (
        <div className="impact-share">
          <div className="impact-bar" role="img" aria-label={`${share} percent of the table`}>
            <span style={{ width: `${Math.max(share, 2)}%` }} />
          </div>
          <span className="impact-percent">{share}% of the table</span>
        </div>
      )}

      {sample?.rows?.length > 0 && (
        <>
          <p className="impact-sub">Example rows that match</p>
          <DataTable columns={sample.columns} rows={sample.rows} label="Example rows that match" />
        </>
      )}
    </section>
  )
}