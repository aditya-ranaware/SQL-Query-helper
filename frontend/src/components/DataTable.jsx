import { formatCell } from '../utils/format'

export default function DataTable({ columns, rows, label }) {
  return (
    <div className="table-wrap" role="region" aria-label={label} tabIndex={0}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c, i) => (
              <th key={i} scope="col">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, i) => {
                const text = formatCell(cell, columns[i])
                return (
                  <td key={i} className={typeof cell === 'number' ? 'is-num' : ''}>
                    {text === null ? <span className="is-null">NULL</span> : text}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}