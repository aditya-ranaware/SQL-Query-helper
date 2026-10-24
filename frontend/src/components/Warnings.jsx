export default function Warnings({ items }) {
  if (!items?.length) return null
  return (
    <ul className="warnings">
      {items.map((w, i) => (
        <li key={i} className={`warning is-${w.level}`} role={w.level === 'danger' ? 'alert' : undefined}>
          <i
            className={`bi ${w.level === 'danger' ? 'bi-exclamation-octagon-fill' : 'bi-exclamation-triangle'}`}
            aria-hidden="true"
          />
          <span>{w.text}</span>
        </li>
      ))}
    </ul>
  )
}