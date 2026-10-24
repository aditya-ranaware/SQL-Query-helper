// In deployment, set VITE_API_URL to your hosted backend address
export const API_BASE =
  import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '/api' : 'http://127.0.0.1:8000/api')

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

// One place for every request, so errors always come out as a readable ApiError
async function send(path, options, fallback) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, options)
  } catch {
    throw new ApiError('Could not reach the server. Check that the backend is running.', 0)
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const detail =
      typeof body.detail === 'string'
        ? body.detail
        : Array.isArray(body.detail)
          ? 'Please check what you typed and try again.'
          : fallback
    throw new ApiError(detail, response.status)
  }
  return response
}

const json = (body) => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const getDataset = (id) =>
  send(`/dataset/${encodeURIComponent(id)}`, {}, 'Could not load your data.').then((r) => r.json())

export const createSample = () =>
  send('/dataset/sample', { method: 'POST' }, 'Could not load the sample.').then((r) => r.json())

export const createFromSchema = (text) =>
  send('/dataset/schema', json({ text }), 'Could not read those tables.').then((r) => r.json())

export const createFromCsv = (files) => {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  return send('/dataset/csv', { method: 'POST', body: form }, 'Could not read those files.').then((r) => r.json())
}

// Ask for a query. onStep is called for every workflow step as soon as it happens.
// (fetch is used because EventSource cannot send a POST request.)
export async function askStream(datasetId, request, onStep) {
  const response = await send('/ask/stream', json({ dataset_id: datasetId, request }), 'The request failed.')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result = null

  const handle = (block) => {
    if (!block.startsWith('data: ')) return
    const event = JSON.parse(block.slice(6))
    if (event.type === 'step') onStep(event.step)
    else if (event.type === 'final') result = event.result
    else if (event.type === 'error') throw new ApiError(event.message, 500)
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() // the last piece may be incomplete, keep it for the next read
    blocks.forEach(handle)
  }
  if (buffer.trim()) handle(buffer.trim())

  if (!result) throw new ApiError('The connection ended before the query was ready. Please try again.', 0)
  return result
}