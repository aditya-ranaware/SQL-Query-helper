import { deriveFlow } from '../utils/flow'

const ICONS = {
  write: 'bi-pencil-square',
  check: 'bi-patch-check',
  preview: 'bi-eye',
  explain: 'bi-chat-left-text',
}

function StageIcon({ stage }) {
  if (stage.state === 'active') return <span className="spinner-border spinner-border-sm" aria-hidden="true" />
  if (stage.state === 'done') return <i className="bi bi-check-lg" aria-hidden="true" />
  if (stage.state === 'retry' || stage.state === 'error') return <i className="bi bi-exclamation-lg" aria-hidden="true" />
  return <i className={`bi ${ICONS[stage.key]}`} aria-hidden="true" />
}

export default function WorkflowStrip({ run, hasData }) {
  const { stages, loop } = deriveFlow(run, hasData)

  return (
    <div className="flow-wrap">
      <ol className="flow" aria-label="Workflow progress">
        {stages.map((stage, i) => (
          <li
            key={stage.key}
            className={`flow-stage is-${stage.state} ${stages[i - 1]?.state === 'done' ? 'is-linked' : ''}`}
          >
            <span className="flow-icon">
              <StageIcon stage={stage} />
            </span>
            <span className="flow-text">
              <span className="flow-title">{stage.title}</span>
              <span className="flow-note">{stage.note}</span>
            </span>
          </li>
        ))}
      </ol>
      {loop && (
        <div className={`flow-loop is-${loop.tone}`}>
          <span>
            <i className="bi bi-arrow-repeat" aria-hidden="true" /> {loop.text}
          </span>
        </div>
      )}
    </div>
  )
}