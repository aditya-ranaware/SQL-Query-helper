export default function Hero({ busy, examples, onPick }) {
  return (
    <section className="hero" aria-labelledby="hero-title">
      <h1 id="hero-title" className="hero-title">
        What do you want to do?
      </h1>
      <p className="hero-lead">
        Describe it in plain words: find, add, change or delete rows. Type below, or start with one of these.
      </p>

      {examples.length > 0 && (
        <>
          <h2 className="hero-sub">Try one of these</h2>
          <div className="example-grid">
            {examples.map((example) => (
              <button key={example.text} type="button" className="example-card" disabled={busy} onClick={() => onPick(example.text)}>
                <span className={`kind kind-${example.kind.toLowerCase()}`}>{example.kind}</span>
                <span>{example.text}</span>
              </button>
            ))}
          </div>
        </>
      )}

      <p className="hero-tip">
        <i className="bi bi-lightbulb" aria-hidden="true" /> Tip: name the table or column you mean for the most
        accurate query.
      </p>
    </section>
  )
}