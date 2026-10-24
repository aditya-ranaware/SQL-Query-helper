import { useEffect, useRef, useState } from 'react'
import { highlight } from '../utils/highlight'

// Used when the browser does not allow the modern clipboard (for example on a plain http page)
function legacyCopy(text) {
  const area = document.createElement('textarea')
  area.value = text
  area.style.position = 'fixed'
  area.style.opacity = '0'
  document.body.appendChild(area)
  area.select()
  document.execCommand('copy')
  document.body.removeChild(area)
}

export default function SqlPanel({ title, sql, tone }) {
  const [copied, setCopied] = useState(false)
  const timer = useRef(null)

  useEffect(() => () => clearTimeout(timer.current), [])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(sql)
    } catch {
      legacyCopy(sql)
    }
    setCopied(true)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setCopied(false), 1800)
  }

  return (
    <figure className={`sql-panel ${tone ? `is-${tone}` : ''}`}>
      <figcaption className="sql-head">
        <span className="sql-title">{title}</span>
        <button type="button" className="sql-copy" onClick={copy}>
          <i className={`bi ${copied ? 'bi-check2' : 'bi-clipboard'}`} aria-hidden="true" />
          {copied ? 'Copied' : 'Copy'}
        </button>
      </figcaption>
      <pre tabIndex={0}>
        <code>
          {highlight(sql).map((token, i) => (
            <span key={i} className={`tok-${token.type}`}>
              {token.text}
            </span>
          ))}
        </code>
      </pre>
      <span className="visually-hidden" role="status">
        {copied ? 'Query copied to the clipboard' : ''}
      </span>
    </figure>
  )
}