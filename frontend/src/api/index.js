const BASE_URL = ''

// 让 Vue 在处理下一个 SSE 事件前先完成本次渲染
const yieldToRenderer = () => new Promise(resolve => setTimeout(resolve, 0))

/**
 * 上传简历并以 SSE 流式接收分析结果
 * @param {File} file - PDF 文件
 * @param {string} jobTitle - 目标职位
 * @param {string} jobDescription - 职位描述 JD
 * @param {Function} onEvent - 回调 (eventType, data)
 */
export async function analyzeResume(file, jobTitle, jobDescription, onEvent) {
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
    throw new Error(err.detail || '服务器错误')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop()

    for (const part of parts) {
      if (!part.trim()) continue
      let eventType = 'message'
      const dataLines = []
      for (const line of part.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7).trim()
        else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
      }
      if (eventType === 'message') continue   // 跳过 SSE 注释（": flush" 等）
      // #region agent log
      fetch('http://127.0.0.1:7500/ingest/f60e4ff7-5f4b-44e9-8293-177c66b632b9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'291064'},body:JSON.stringify({sessionId:'291064',location:'api/index.js:onEvent',message:'SSE event arrived',data:{eventType,dataLen:dataLines.join('').length,t:Date.now()},hypothesisId:'H-A',timestamp:Date.now()})}).catch(()=>{})
      // #endregion
      onEvent(eventType, dataLines.join('\n'))
      // report_chunk 是高频小包，不需要每次等渲染；其他事件让 Vue 先渲染
      if (eventType !== 'report_chunk') await yieldToRenderer()
    }
  }
}

/**
 * 追问接口：基于已分析简历继续对话（SSE 流）
 * @param {string} sessionId
 * @param {string} message
 * @param {string} jobTitle
 * @param {string} jobDescription
 * @param {Function} onChunk - 回调每个文本片段
 */
export async function chat(sessionId, message, jobTitle, jobDescription, onChunk) {
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
    throw new Error(err.detail || '服务器错误')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop()

    for (const part of parts) {
      if (!part.trim()) continue
      let eventType = 'message'
      const dataLines = []
      for (const line of part.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7).trim()
        else if (line.startsWith('data: ')) dataLines.push(line.slice(6))
      }
      const data = dataLines.join('\n')
      if (eventType === 'chat_chunk') onChunk(data)
      if (eventType === 'chat_end') return
    }
    await yieldToRenderer()   // 每批 chunk 渲染一次，保证打字机效果
  }
}
