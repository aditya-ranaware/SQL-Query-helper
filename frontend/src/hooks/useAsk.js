import { useEffect, useRef, useState } from 'react'
import { askStream } from '../api/client'

export default function useAsk(datasetId, onExpired) {
  const [runs, setRuns] = useState([]) // newest first
  const [busy, setBusy] = useState(false)
  const nextId = useRef(1)
  const currentData = useRef(datasetId)

  // New data means a fresh list of results
  useEffect(() => {
    currentData.current = datasetId
    setRuns([])
    setBusy(false)
  }, [datasetId])

  // change can be an object, or a function that receives the current run
  const update = (id, change) =>
    setRuns((prev) =>
      prev.map((r) => (r.id === id ? { ...r, ...(typeof change === 'function' ? change(r) : change) } : r)),
    )

  const ask = async (request) => {
    if (busy || !datasetId) return
    const askedData = datasetId
    const id = nextId.current++
    setRuns((prev) => [...prev, { id, request, status: 'running', steps: [], result: null, error: '' }].slice(-20))
    setBusy(true)
    try {
      const result = await askStream(askedData, request, (step) => update(id, (r) => ({ steps: [...r.steps, step] })))
      if (currentData.current !== askedData) return
      update(id, { status: result.status, result })
    } catch (e) {
      if (currentData.current !== askedData) return
      if (e.status === 404) onExpired?.()
      update(id, { status: 'error', error: e.message || 'Something went wrong. Please try again.' })
    } finally {
      if (currentData.current === askedData) setBusy(false)
    }
  }

  return { runs, busy, ask, clear: () => setRuns([]) }
}