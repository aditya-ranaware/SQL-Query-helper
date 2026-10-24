// Numbers get thousands separators, except id-like columns (an id of 1,042 would look wrong)
const PLAIN_COLUMN = /(^|_)(id|year|zip|pin|phone|code)$/i

export function formatCell(value, column = '') {
  if (value === null || value === undefined) return null
  if (typeof value === 'number') {
    if (PLAIN_COLUMN.test(column)) return String(value)
    return Number.isInteger(value)
      ? value.toLocaleString('en-US')
      : value.toLocaleString('en-US', { maximumFractionDigits: 2 })
  }
  return String(value)
}

export const rowsText = (n) => `${n.toLocaleString('en-US')} ${n === 1 ? 'row' : 'rows'}`

// The AI sometimes uses special narrow spaces, which squash words together. Turn them into normal spaces.
export const tidyText = (text) => String(text ?? '').replace(/[\u00a0\u2007\u2009\u200a\u202f]/g, ' ')