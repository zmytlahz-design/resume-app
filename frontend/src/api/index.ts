const BASE_URL = ''

export interface SessionData {
  messages: { role: string; content: string }[]
  tool_results: Record<string, unknown>
  report_text: string
}

export async function fetchSession(sessionId: string): Promise<SessionData | null> {
  const res = await fetch(`${BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}`)
  if (res.status === 404) return null
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }))
    throw new Error((err as { detail?: string }).detail || '服务器错误')
  }
  return res.json() as Promise<SessionData>
}

export async function deleteSession(sessionId: string): Promise<void> {
  if (!sessionId) return
  await fetch(`${BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  }).catch(() => {})
}

const yieldToRenderer = (): Promise<void> => new Promise(resolve => setTimeout(resolve, 0))

export type SseEventCallback = (eventType: string, data: string) => void
export type ChunkCallback = (chunk: string) => void

export async function analyzeResume(
  file: File,
  jobTitle: string,
  jobDescription: string,
  onEvent: SseEventCallback,
): Promise<void> {
  const form = new FormData()
  form.append('file', file)
  form.append('job_title', jobTitle)
  form.append('job_description', jobDescription)

  const res = await fetch(`${BASE_URL}/api/analyze`, {
    method: 'POST',
    body: form,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }))
    throw new Error((err as { detail?: string }).detail || '服务器错误')
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      if (!part.trim()) continue
      let eventType = 'message'
      const dataLines: string[] = []
      for (const line of part.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7).trim()
        else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
      }
      if (eventType === 'message') continue
      // 流式处理关键点：
      // 后端每次只推送“文本片段”，这里把当前 SSE 帧的数据拼成一个 chunk 后上抛给 store。
      onEvent(eventType, dataLines.join('\n'))
      if (eventType !== 'report_chunk') await yieldToRenderer()
    }
  }
}

export async function chat(
  sessionId: string,
  message: string,
  jobTitle: string,
  jobDescription: string,
  onChunk: ChunkCallback,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      job_title: jobTitle,
      job_description: jobDescription,
    }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }))
    throw new Error((err as { detail?: string }).detail || '服务器错误')
  }

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      if (!part.trim()) continue
      let eventType = 'message'
      const dataLines: string[] = []
      for (const line of part.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7).trim()
        else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
      }
      // chat 接口同样是增量文本；每个事件只是一小段，不保证是完整 Markdown 语法单元。
      const data = dataLines.join('\n')
      if (eventType === 'chat_chunk') onChunk(data)
      if (eventType === 'chat_end') return
    }
    await yieldToRenderer()
  }
}
