import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { deleteSession } from '../api/index'

export interface AgentStep {
  id: number
  type: 'thinking' | 'observation'
  content: string
  tool: string | null
  timestamp?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: number
}

export const useResumeStore = defineStore('resume', () => {
  const sessionId    = ref<string>('')
  const isAnalyzing  = ref<boolean>(false)
  const agentSteps   = ref<AgentStep[]>([])
  const reportChunks = ref<string[]>([])
  const reportDone   = ref<boolean>(false)
  const chatMessages = ref<ChatMessage[]>([])

  // 报告流渲染关键点：先把所有 chunk 累加成完整字符串，再交给组件做 Markdown parse。
  const report    = computed<string>(() => reportChunks.value.join(''))
  const hasReport = computed<boolean>(() => reportDone.value && report.value.length > 0)

  function addAgentStep(type: AgentStep['type'], content: string, tool: string | null = null): void {
    agentSteps.value.push({ type, content, tool, id: Date.now() + Math.random() })
  }

  function appendReport(chunk: string): void {
    // 不在这里做 marked.parse：只负责"累加原始文本"，避免半截 Markdown 被提前解析。
    reportChunks.value.push(chunk)
  }

  function addChatMessage(role: ChatMessage['role'], content: string): void {
    chatMessages.value.push({ role, content, timestamp: Date.now() })
  }

  function updateLastChat(content: string): void {
    const last = chatMessages.value[chatMessages.value.length - 1]
    if (last) last.content = content
  }

  function persistChat(): void {
    // no-op：持久化由后端 PostgreSQL 负责
  }

  function setSessionIdFromServer(sid: string): void {
    sessionId.value = sid
  }

  function reset(): void {
    const sidToDelete = sessionId.value
    sessionId.value = ''
    isAnalyzing.value = false
    agentSteps.value = []
    reportChunks.value = []
    reportDone.value = false
    chatMessages.value = []
    if (sidToDelete) deleteSession(sidToDelete)
  }

  return {
    sessionId,
    isAnalyzing,
    agentSteps,
    report,
    reportDone,
    hasReport,
    chatMessages,
    addAgentStep,
    appendReport,
    addChatMessage,
    updateLastChat,
    persistChat,
    setSessionIdFromServer,
    reset,
  }
})
