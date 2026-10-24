import { useEffect, useRef, useState } from 'react'
import Composer from './components/Composer'
import DataSetup from './components/DataSetup'
import DatabaseRail from './components/DatabaseRail'
import Hero from './components/Hero'
import RunCard from './components/RunCard'
import useAsk from './hooks/useAsk'
import useDataset from './hooks/useDataset'
import { examplesFor } from './utils/examples'

const SOURCE_PILL = { sample: 'Sample shop', csv: 'CSV files', schema: 'Pasted tables' }

export default function App() {
  const data = useDataset()
  const { dataset } = data
  const chat = useAsk(dataset?.id, data.expire)
  const [railOpen, setRailOpen] = useState(false) // the tables panel slides in when the Tables button is clicked
  const tablesButton = useRef(null)
  const wasOpen = useRef(false)
  const newestId = chat.runs[chat.runs.length - 1]?.id

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') setRailOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // Move focus into the panel when it opens, and back to the Tables button when it closes
  useEffect(() => {
    if (railOpen) document.querySelector('.rail-close')?.focus()
    else if (wasOpen.current) tablesButton.current?.focus()
    wasOpen.current = railOpen
  }, [railOpen])

  // Bring the newest result into view
  useEffect(() => {
    if (newestId) {
      document.getElementById(`run-${newestId}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [newestId])

  // The AI asked a question: send the original request together with the answer
  const reply = (run, answer) => chat.ask(`${run.request.replace(/[.?!\s]+$/, '')}. ${answer}`)

  // Before any data is added, the whole screen is the welcome page
  if (!dataset && !data.restoring) {
    return (
      <DataSetup busy={data.busy} error={data.error} onCsv={data.addCsv} onSchema={data.addSchema} onSample={data.useSample} />
    )
  }

  const hasRuns = chat.runs.length > 0
  const examples = examplesFor(dataset)

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div className="topbar-left">
          <div className="app-brand">
            <span className="app-brand-mark">
              <i className="bi bi-database" aria-hidden="true" />
            </span>
            SQL Query Helper
          </div>
        </div>
        <div className="topbar-right">
          {dataset && (
            <button
              ref={tablesButton}
              type="button"
              className="topbar-tables"
              aria-expanded={railOpen}
              aria-controls="tables-drawer"
              onClick={() => setRailOpen(true)}
            >
              <i className="bi bi-table" aria-hidden="true" />
              <span>Tables</span>
            </button>
          )}
          {dataset && <span className="db-pill is-quiet">{SOURCE_PILL[dataset.source]}</span>}
          <span className="db-pill">MySQL</span>
        </div>
      </header>

      <div className="app-body">
        <main className="app-main">
          {data.restoring ? (
            <p className="loading" role="status">
              <span className="spinner-border spinner-border-sm" aria-hidden="true" /> Loading your tables…
            </p>
          ) : hasRuns ? (
            <>
              <div className="runs-head">
                <h2>Results</h2>
                <button type="button" className="link-btn" onClick={chat.clear} disabled={chat.busy}>
                  Clear
                </button>
              </div>
              <div className="runs" aria-live="polite">
                {chat.runs.map((run) => (
                  <div key={run.id} id={`run-${run.id}`} className="run-slot">
                    <RunCard run={run} hasData={dataset.has_data} busy={chat.busy} onReply={reply} />
                  </div>
                ))}
              </div>
            </>
          ) : (
            <Hero busy={chat.busy} examples={examples} onPick={chat.ask} />
          )}
        </main>
      </div>

      {dataset && <Composer busy={chat.busy} examples={examples} showExamples={hasRuns} onAsk={chat.ask} />}

      {dataset && (
        <>
          <DatabaseRail
            dataset={dataset}
            open={railOpen}
            onClose={() => setRailOpen(false)}
            onChange={() => {
              setRailOpen(false)
              data.reset()
            }}
          />
          {railOpen && <div className="drawer-backdrop" onClick={() => setRailOpen(false)} />}
        </>
      )}
    </div>
  )
}