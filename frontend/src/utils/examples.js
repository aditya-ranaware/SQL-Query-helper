// Example requests shown as clickable chips. kind is only used for the little label on the chip.
const SHOP = [
  { kind: 'SELECT', text: 'Show the 3 most expensive products' },
  { kind: 'SELECT', text: 'Find all customers from Pune' },
  { kind: 'UPDATE', text: 'Increase the price of all Furniture products by 10 percent' },
  { kind: 'DELETE', text: 'Delete all cancelled orders' },
  { kind: 'INSERT', text: 'Add a customer named Zoya from Pune who joined on 2025-01-15' },
]

export function examplesFor(dataset) {
  if (dataset?.source === 'sample') return SHOP
  const first = dataset?.tables?.[0]?.name
  if (!first) return []
  return [
    { kind: 'SELECT', text: `Show the first 10 rows of ${first}` },
    { kind: 'SELECT', text: `How many rows are in ${first}?` },
  ]
}