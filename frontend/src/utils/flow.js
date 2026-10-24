export const MAX_ATTEMPTS = 4 // the first query plus up to 3 fixes (same limit as the server)

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

// Work out what each stage of the workflow looks like, from the steps received so far
export function deriveFlow(run, hasData) {
  const steps = run.steps
  const last = steps[steps.length - 1]
  const attempts = steps.filter((s) => s.node === 'write_sql').length
  const anyCheckOk = steps.some((s) => s.node === 'check' && s.ok)
  const previewDone = steps.some((s) => s.node === 'preview')
  const explained = steps.some((s) => s.node === 'explain')
  const lastCheckFailed = last?.node === 'check' && !last.ok
  const running = run.status === 'running'
  const result = run.result

  let write
  let check
  let preview
  let explain

  if (run.status === 'success') {
    write = check = explain = 'done'
    preview = hasData ? 'done' : 'skipped'
  } else if (run.status === 'failed') {
    write = 'done'
    check = 'error'
    preview = explain = 'skipped'
  } else if (run.status === 'unanswerable' || run.status === 'needs_info') {
    write = 'done'
    check = preview = explain = 'skipped'
  } else {
    // still running, or stopped by an error
    write = !last || lastCheckFailed ? 'active' : 'done'
    check = last?.node === 'write_sql' ? 'active' : lastCheckFailed ? 'retry' : anyCheckOk ? 'done' : 'idle'
    preview = !hasData && anyCheckOk ? 'skipped' : previewDone ? 'done' : last?.node === 'check' && last.ok ? 'active' : 'idle'
    explain = explained ? 'done' : previewDone ? 'active' : 'idle'
    if (!running) {
      // an error stopped the run: mark whichever stage was working as failed
      ;[write, check, preview, explain] = [write, check, preview, explain].map((s) =>
        s === 'active' || s === 'retry' ? 'error' : s,
      )
    }
  }

  const previewUnavailable = result?.preview && result.preview.available === false

  const stages = [
    {
      key: 'write',
      title: 'Write SQL',
      state: write,
      note:
        write === 'active'
          ? attempts === 0
            ? 'Writing the query…'
            : `Fixing it, try ${attempts + 1}…`
          : write === 'done'
            ? run.status === 'needs_info'
              ? 'Needs your answer'
              : run.status === 'unanswerable'
                ? 'Cannot be done'
                : attempts > 1
                  ? `Done after ${plural(attempts, 'try', 'tries')}`
                  : 'Query written'
            : write === 'error'
              ? 'Stopped'
              : 'Waiting',
    },
    {
      key: 'check',
      title: 'Check',
      state: check,
      note:
        check === 'active'
          ? 'Checking it…'
          : check === 'done'
            ? 'Tables and columns exist'
            : check === 'retry'
              ? 'Problem found, fixing'
              : check === 'error'
                ? 'Not accepted'
                : check === 'skipped'
                  ? 'Skipped'
                  : 'Waiting',
    },
    {
      key: 'preview',
      title: 'Preview',
      state: preview,
      note:
        preview === 'active'
          ? 'Trying it on a copy…'
          : preview === 'done'
            ? previewUnavailable
              ? 'Not available'
              : 'Tried on a copy'
            : preview === 'skipped'
              ? hasData
                ? 'Skipped'
                : 'No data to try'
              : preview === 'error'
                ? 'Stopped'
                : 'Waiting',
    },
    {
      key: 'explain',
      title: 'Explain',
      state: explain,
      note:
        explain === 'active'
          ? 'Writing it up…'
          : explain === 'done'
            ? 'Explained'
            : explain === 'skipped'
              ? 'Skipped'
              : explain === 'error'
                ? 'Stopped'
                : 'Waiting',
    },
  ]

  // The amber "fix loop" bracket under the first two stages
  let loop = null
  if (running && lastCheckFailed) {
    loop = { tone: 'live', text: `Fix loop: try ${attempts + 1} of ${MAX_ATTEMPTS}` }
  } else if (attempts > 1 && run.status === 'success') {
    loop = { tone: 'done', text: `Fixed after ${plural(attempts - 1, 'retry', 'retries')}` }
  } else if (attempts > 1 && run.status === 'failed') {
    loop = { tone: 'failed', text: `Gave up after ${attempts} tries` }
  }

  return { stages, loop }
}