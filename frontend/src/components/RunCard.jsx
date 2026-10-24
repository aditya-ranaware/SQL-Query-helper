import { useState } from 'react'
import DataTable from './DataTable'
import ImpactCard from './ImpactCard'
import SqlPanel from './SqlPanel'
import Warnings from './Warnings'
import WorkflowStrip from './WorkflowStrip'
import { tidyText } from '../utils/format'

// Plain text, with `backticked` words shown as small code labels
function Text({ children }) {
  return tidyText(children)
    .split(/`([^`]+)`/)
    .map((part, i) => (i % 2 ? <code key={i} className="inline-code">{part}</code> : part))
}

function ReplyForm({ question, busy, onSubmit }) {
  const [answer, setAnswer] = useState('')
  const submit = (e) => {
    e.preventDefault()
    if (answer.trim() && !busy) onSubmit(answer.trim())
  }
  return (
    <form className="reply" onSubmit={submit}>
      <label className="reply-q" htmlFor="reply-input">
        <i className="bi bi-question-circle" aria-hidden="true" />
        <span>{tidyText(question)}</span>
      </label>
      <div className="reply-row">
        <input
          id="reply-input"
          type="text"
          value={answer}
          placeholder="Your answer"
          disabled={busy}
          onChange={(e) => setAnswer(e.target.value)}
        />
        <button type="submit" className="btn btn-primary" disabled={busy || !answer.trim()}>
          Continue
        </button>
      </div>
    </form>
  )
}

function Preview({ result, hasData }) {
  const p = result.preview
  if (!hasData || p === null) {
    return (
      <p className="preview-note">
        <i className="bi bi-info-circle" aria-hidden="true" />
        No data was added, so there is nothing to preview. Upload a CSV to see what a query would do.
      </p>
    )
  }
  if (!p.available) {
    return (
      <p className="preview-note">
        <i className="bi bi-info-circle" aria-hidden="true" />
        {p.reason} The query above has still passed all checks.
      </p>
    )
  }
  if (p.kind === 'SELECT') {
    return (
      <section className="preview" aria-label="Result preview">
        <h4 className="preview-title">Result preview</h4>
        {p.rows.length === 0 ? (
          <p className="preview-note">
            <i className="bi bi-info-circle" aria-hidden="true" />
            The query ran, but no rows matched.
          </p>
        ) : (
          <DataTable columns={p.columns} rows={p.rows} label="Result preview" />
        )}
        <p className="preview-foot">
          {p.has_more ? `Showing the first ${p.rows.length} rows. ` : ''}
          <i className="bi bi-shield-check" aria-hidden="true" /> Tried on a copy of your data.
        </p>
      </section>
    )
  }
  return (
    <>
      <ImpactCard preview={p} />
      <p className="preview-foot">
        <i className="bi bi-shield-check" aria-hidden="true" /> Tried on a copy of your data. Your original data was
        not changed.
      </p>
    </>
  )
}

export default function RunCard({ run, hasData, busy, onReply }) {
  const { status, result } = run
  const kind = result?.kind
  const retries = result ? Math.max(0, result.attempts - 1) : 0
  const danger = result?.warnings?.some((w) => w.level === 'danger')

  return (
    <article className={`run ${kind ? `is-${kind.toLowerCase()}` : ''} ${danger ? 'is-danger' : ''}`} aria-busy={status === 'running'}>
      <header className="run-head">
        <i className="bi bi-chat-left-quote" aria-hidden="true" />
        <h3 className="run-request">{run.request}</h3>
        {kind && <span className={`kind kind-${kind.toLowerCase()}`}>{kind}</span>}
      </header>

      <WorkflowStrip run={run} hasData={hasData} />

      {status === 'success' && (
        <>
          <Warnings items={result.warnings} />
          <SqlPanel title="MySQL query" sql={result.sql} tone={danger ? 'danger' : undefined} />
          <p className="run-explanation">
            <Text>{result.explanation}</Text>
          </p>

          {result.check_query && (
            <details className="check-first">
              <summary>
                <i className="bi bi-search" aria-hidden="true" /> See which rows match first
              </summary>
              <p className="check-first-text">Run this in MySQL before the change. It lists the rows that would be affected.</p>
              <SqlPanel title="Check query" sql={result.check_query} tone="soft" />
            </details>
          )}

          <Preview result={result} hasData={hasData} />
        </>
      )}

      {status === 'needs_info' && (
        <ReplyForm question={result.message} busy={busy} onSubmit={(answer) => onReply(run, answer)} />
      )}

      {status === 'unanswerable' && (
        <p className="run-note">
          <i className="bi bi-info-circle" aria-hidden="true" />
          <span>
            <Text>{result.message}</Text>
          </span>
        </p>
      )}

      {status === 'failed' && (
        <>
          <p className="run-alert is-warn">
            <i className="bi bi-exclamation-triangle" aria-hidden="true" />
            <span>
              <Text>{result.message}</Text>
            </span>
          </p>
          {result.sql && <SqlPanel title="Last attempt (not accepted)" sql={result.sql} tone="soft" />}
        </>
      )}

      {status === 'error' && (
        <p className="run-alert is-error" role="alert">
          <i className="bi bi-exclamation-octagon" aria-hidden="true" />
          <span>{run.error}</span>
        </p>
      )}

      {result && (
        <footer className="run-foot">
          {status === 'success' &&
            (retries === 0 ? (
              <span className="chip chip-ok">
                <i className="bi bi-check2" aria-hidden="true" /> Passed the checks first try
              </span>
            ) : (
              <span className="chip chip-amber">
                <i className="bi bi-arrow-repeat" aria-hidden="true" /> Fixed after {retries} {retries === 1 ? 'retry' : 'retries'}
              </span>
            ))}
          <span className="chip">{(result.latency_ms / 1000).toFixed(1)} s</span>
        </footer>
      )}
    </article>
  )
}