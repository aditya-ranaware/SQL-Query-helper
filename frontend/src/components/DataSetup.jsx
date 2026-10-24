import { useRef, useState } from 'react'

const TABS = [
  { id: 'csv', label: 'Upload CSV', icon: 'bi-filetype-csv' },
  { id: 'paste', label: 'Paste tables', icon: 'bi-code-slash' },
  { id: 'sample', label: 'Try the sample', icon: 'bi-shop' },
]

const STEPS = [
  { title: 'Add your tables', text: 'Upload CSV files, paste your table names, or try the sample.' },
  { title: 'Say what you want', text: 'Find, add, change or delete rows, in plain English.' },
  { title: 'Get a checked query', text: 'Review the MySQL, the warnings and a safe preview before you run it.' },
]

const EXAMPLE_TABLES = `customers: id, name, city
orders: id, customer_id, order_date, status
products: id, name, price`

function HowItWorks() {
  return (
    <>
      <h2 className="how-title">How it works</h2>
      <ol className="how">
        {STEPS.map((step, i) => (
          <li key={step.title}>
            <span className="how-num" aria-hidden="true">
              {i + 1}
            </span>
            <span>
              <strong>{step.title}</strong>
              <span className="how-text">{step.text}</span>
            </span>
          </li>
        ))}
      </ol>
      <ul className="trust" aria-label="How your data is handled">
        <li>
          <i className="bi bi-shield-lock" aria-hidden="true" /> I only write queries. I never run them on your real
          database.
        </li>
        <li>
          <i className="bi bi-clock-history" aria-hidden="true" /> Your tables are forgotten after 60 minutes.
        </li>
      </ul>
    </>
  )
}

export default function DataSetup({ busy, error, onCsv, onSchema, onSample }) {
  const [tab, setTab] = useState('csv')
  const [text, setText] = useState('')
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef(null)

  const pickFiles = (list) => {
    const files = [...(list || [])]
    if (files.length) onCsv(files)
  }

  // Left and Right arrows move between the tabs, as people expect from a tab list
  const onTabKey = (e) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return
    const index = TABS.findIndex((t) => t.id === tab)
    const next = TABS[(index + (e.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length]
    setTab(next.id)
    document.getElementById(`tab-${next.id}`)?.focus()
  }

  return (
    <section className="split setup" aria-labelledby="setup-title">
      <div className="split-brand">
        <div className="brand-top">
          <span className="app-brand-mark">
            <i className="bi bi-database" aria-hidden="true" />
          </span>
          SQL Query Helper
        </div>

        <div className="brand-body">
          <h1 id="setup-title">Turn plain English into MySQL</h1>
          <p className="setup-lead">
            Describe what you want to find, add, change or delete. I write the query and check it against your tables
            before you run it.
          </p>
          <p className="setup-kinds" aria-label="Works with these kinds of queries">
            <span className="kind kind-select">SELECT</span>
            <span className="kind kind-insert">INSERT</span>
            <span className="kind kind-update">UPDATE</span>
            <span className="kind kind-delete">DELETE</span>
          </p>
        </div>

        <div className="brand-foot only-wide">
          <HowItWorks />
        </div>
      </div>

      <div className="split-form">
        <div className="form-wrap">
          <h2 className="form-title">Add your tables</h2>
          <p className="form-sub">Choose how you want to bring them in.</p>

          <div className="setup-card">
            <div className="tabs" role="tablist" aria-label="How do you want to add your tables?" onKeyDown={onTabKey}>
              {TABS.map((t) => (
                <button
                  key={t.id}
                  id={`tab-${t.id}`}
                  type="button"
                  role="tab"
                  aria-selected={tab === t.id}
                  aria-controls={`panel-${t.id}`}
                  tabIndex={tab === t.id ? 0 : -1}
                  className={`tab ${tab === t.id ? 'is-active' : ''}`}
                  onClick={() => setTab(t.id)}
                >
                  <i className={`bi ${t.icon}`} aria-hidden="true" />
                  <span>{t.label}</span>
                </button>
              ))}
            </div>

            <div className="tab-panel" role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
              {tab === 'csv' && (
                <>
                  <div
                    className={`dropzone ${dragging ? 'is-dragging' : ''}`}
                    onDragOver={(e) => {
                      e.preventDefault()
                      setDragging(true)
                    }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={(e) => {
                      e.preventDefault()
                      setDragging(false)
                      pickFiles(e.dataTransfer.files)
                    }}
                  >
                    <i className="bi bi-cloud-arrow-up dropzone-icon" aria-hidden="true" />
                    <p className="dropzone-title">Drop your CSV files here</p>
                    <p className="dropzone-hint">Each file becomes a table. Up to 8 files, 5 MB each.</p>
                    <button type="button" className="btn btn-primary" disabled={busy} onClick={() => fileInput.current.click()}>
                      {busy ? 'Reading files…' : 'Choose files'}
                    </button>
                    <input
                      ref={fileInput}
                      type="file"
                      accept=".csv,text/csv"
                      multiple
                      hidden
                      onChange={(e) => {
                        pickFiles(e.target.files)
                        e.target.value = ''
                      }}
                    />
                  </div>
                  <p className="setup-note">With real data you also get a preview: how many rows a change would affect.</p>
                </>
              )}

              {tab === 'paste' && (
                <>
                  <label htmlFor="schema-text" className="field-label">
                    Your tables and columns
                  </label>
                  <textarea
                    id="schema-text"
                    className="schema-text"
                    rows={7}
                    value={text}
                    disabled={busy}
                    spellCheck={false}
                    placeholder={'customers: id, name, city\norders: id, customer_id, order_date, status\n\nor paste CREATE TABLE statements from MySQL'}
                    onChange={(e) => setText(e.target.value)}
                  />
                  <div className="setup-actions">
                    <button type="button" className="btn btn-primary" disabled={busy || !text.trim()} onClick={() => onSchema(text)}>
                      {busy ? 'Reading…' : 'Use these tables'}
                    </button>
                    <button type="button" className="link-btn" disabled={busy} onClick={() => setText(EXAMPLE_TABLES)}>
                      Insert an example
                    </button>
                  </div>
                  <p className="setup-note">Without data I can still write and check the query, but I can't preview it.</p>
                </>
              )}

              {tab === 'sample' && (
                <>
                  <p className="sample-text">
                    A small online shop with <strong>30 customers</strong>, <strong>200 orders</strong> and{' '}
                    <strong>12 products</strong>. It has real data, so you get a full preview of every query. The fastest
                    way to see everything working.
                  </p>
                  <div className="setup-actions">
                    <button type="button" className="btn btn-primary" disabled={busy} onClick={onSample}>
                      {busy ? 'Loading…' : 'Load the sample shop'}
                    </button>
                  </div>
                </>
              )}

              {error && (
                <p className="setup-error" role="alert">
                  <i className="bi bi-exclamation-circle" aria-hidden="true" /> {error}
                </p>
              )}
            </div>
          </div>

          <div className="how-narrow only-narrow">
            <HowItWorks />
          </div>
        </div>
      </div>
    </section>
  )
}