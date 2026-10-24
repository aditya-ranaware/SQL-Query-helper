// A tiny SQL colouring helper. It only decides which words get which colour, nothing more.
const KEYWORDS = new Set(
  ('select from where and or not in is null like between join inner left right outer full cross on as group by order ' +
    'having limit offset distinct union all insert into values update set delete case when then else end asc desc ' +
    'exists with recursive interval default true false using duplicate key').split(' '),
)

const TOKEN =
  /(--[^\n]*|\/\*[\s\S]*?\*\/)|('(?:[^'\\]|\\.|'')*'|"(?:[^"\\]|\\.)*")|(`[^`]*`)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][\w$]*)|([\s\S])/g

export function highlight(sql) {
  const tokens = []
  for (const m of sql.matchAll(TOKEN)) {
    const [text, comment, string, quoted, number, word] = m
    let type = 'p'
    if (comment) type = 'comment'
    else if (string) type = 'str'
    else if (quoted) type = 'id'
    else if (number) type = 'num'
    else if (word) {
      if (KEYWORDS.has(word.toLowerCase())) type = 'kw'
      else if (/^\s*\(/.test(sql.slice(m.index + text.length))) type = 'fn'
      else type = 'id'
    }
    const last = tokens[tokens.length - 1]
    if (last && last.type === type && (type === 'p' || type === 'id')) last.text += text // merge plain pieces
    else tokens.push({ type, text })
  }
  return tokens
}