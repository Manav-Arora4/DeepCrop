import React from 'react'

// Renders the small Markdown subset the LLM writes (### headings, numbered and bulleted lines, **bold**)
// as React elements; never injects raw HTML.
function inline(text: string): React.ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong> : part)
}

export default function AdviceText({ text }: { text: string }) {
  const blocks: React.ReactNode[] = []
  let list: { ordered: boolean; items: string[] } | null = null
  const flush = () => {
    if (!list) return
    const Tag = list.ordered ? 'ol' : 'ul'
    blocks.push(
      <Tag key={blocks.length} className={`${list.ordered ? 'list-decimal' : 'list-disc'} flex flex-col gap-1.5 pl-5 marker:text-muted`}>
        {list.items.map((it, i) => <li key={i}>{inline(it)}</li>)}
      </Tag>,
    )
    list = null
  }
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) { flush(); continue }
    const heading = line.match(/^#{1,6}\s+(.*)$/)
    const ordered = line.match(/^\d+[.)]\s+(.*)$/)
    const bullet = line.match(/^[-*•]\s+(.*)$/)
    if (heading) {
      flush()
      blocks.push(<h3 key={blocks.length} className="pt-2 text-[17px] font-semibold tracking-display text-ink">{inline(heading[1])}</h3>)
    } else if (ordered || bullet) {
      const isOrdered = Boolean(ordered)
      if (!list || list.ordered !== isOrdered) { flush(); list = { ordered: isOrdered, items: [] } }
      list.items.push((ordered || bullet)![1])
    } else {
      flush()
      blocks.push(<p key={blocks.length}>{inline(line)}</p>)
    }
  }
  flush()
  return <div className="flex max-w-[72ch] flex-col gap-2.5 text-[15px] leading-relaxed text-ink">{blocks}</div>
}
