import { useRef, useState } from 'react'

export default function Composer({ busy, examples, showExamples, onAsk }) {
  const [text, setText] = useState('')
  const inputRef = useRef(null)

  const resize = (el) => {
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }

  const send = (request) => {
    const q = request.trim()
    if (q.length < 3 || busy) return
    setText('')
    if (inputRef.current) inputRef.current.style.height = 'auto'
    onAsk(q)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(text)
    }
  }

  return (
    <div className="composer">
      <div className="composer-inner">
        <div className="ask-card">
          <div className="ask-row">
            <textarea
              ref={inputRef}
              rows={1}
              value={text}
              placeholder="Describe what you want"
              aria-label="What do you want to do?"
              onChange={(e) => {
                setText(e.target.value)
                resize(e.target)
              }}
              onKeyDown={handleKeyDown}
            />
            <button
              type="button"
              className="btn btn-primary ask-send"
              disabled={busy || text.trim().length < 3}
              onClick={() => send(text)}
            >
              {busy ? (
                <span className="spinner-border spinner-border-sm" aria-hidden="true" />
              ) : (
                <i className="bi bi-magic" aria-hidden="true" />
              )}
              <span className="ask-label">{busy ? 'Working' : 'Write query'}</span>
            </button>
          </div>
        </div>

        {showExamples && examples.length > 0 && (
          <div className="chips" aria-label="Example requests">
            {examples.map((example) => (
              <button key={example.text} type="button" className="chip-btn" disabled={busy} onClick={() => send(example.text)}>
                <span className={`kind kind-${example.kind.toLowerCase()}`}>{example.kind}</span>
                {example.text}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}