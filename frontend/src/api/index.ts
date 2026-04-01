const BASE_URL = ''

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
      const data = dataLines.join('\n')
      if (eventType === 'chat_chunk') onChunk(data)
      if (eventType === 'chat_end') return
    }
    await yieldToRenderer()
  }
}
