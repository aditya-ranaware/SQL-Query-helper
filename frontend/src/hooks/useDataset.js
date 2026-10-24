import { useEffect, useState } from 'react'
import { createFromCsv, createFromSchema, createSample, getDataset } from '../api/client'

const KEY = 'sql-helper-dataset'

// sessionStorage can be blocked (private mode), so every use is guarded
const recall = () => {
  try {
    return sessionStorage.getItem(KEY)
  } catch {
    return null
  }
}
const remember = (id) => {
  try {
    sessionStorage.setItem(KEY, id)
  } catch {
    /* not available, the data simply will not survive a refresh */
  }
}
const forget = () => {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    /* nothing to do */
  }
}

export default function useDataset() {
  const [dataset, setDataset] = useState(null)
  const [restoring, setRestoring] = useState(() => Boolean(recall()))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  // After a page refresh, bring back the data the visitor was using
  useEffect(() => {
    const id = recall()
    if (!id) return
    getDataset(id)
      .then(setDataset)
      .catch(forget)
      .finally(() => setRestoring(false))
  }, [])

  const run = async (make) => {
    setBusy(true)
    setError('')
    try {
      const created = await make()
      remember(created.id)
      setDataset(created)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return {
    dataset,
    restoring,
    busy,
    error,
    addCsv: (files) => run(() => createFromCsv(files)),
    addSchema: (text) => run(() => createFromSchema(text)),
    useSample: () => run(createSample),
    reset: () => {
      forget()
      setDataset(null)
      setError('')
    },
    expire: () => {
      forget()
      setDataset(null)
      setError('Your data has expired. Please add it again.')
    },
  }
}