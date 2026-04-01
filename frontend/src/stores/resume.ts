import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const LS_SESSION = 'resume_sessionId'
const LS_REPORT  = 'resume_report'
const LS_JOB     = 'resume_job'
const LS_STEPS   = 'resume_steps'
const LS_CHAT    = 'resume_chat'
const LS_EXPIRES = 'resume_expires_at'

const TTL_MS = 2 * 60 * 60 * 1000

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

function isLocalDataExpired(): boolean {
  const expires = localStorage.getItem(LS_EXPIRES)
  const sid = localStorage.getItem(LS_SESSION)
  if (!sid || !expires) return false
  return Date.now() > parseInt(expires, 10)
}

function clearExpiredLocalData(): void {
  if (!isLocalDataExpired()) return
  localStorage.removeItem(LS_SESSION)
  localStorage.removeItem(LS_REPORT)
  localStorage.removeItem(LS_JOB)
  localStorage.removeItem(LS_STEPS)
  localStorage.removeItem(LS_CHAT)
  localStorage.removeItem(LS_EXPIRES)
}

function saveSteps(steps: AgentStep[]): void {
  try { localStorage.setItem(LS_STEPS, JSON.stringify(steps)) } catch {}
}
function saveChat(msgs: ChatMessage[]): void {
  try { localStorage.setItem(LS_CHAT, JSON.stringify(msgs)) } catch {}
}

clearExpiredLocalData()

export const useResumeStore = defineStore('resume', () => {
  const sessionId    = ref<string>(localStorage.getItem(LS_SESSION) ?? '')
  const isAnalyzing  = ref<boolean>(false)
  const agentSteps   = ref<AgentStep[]>(JSON.parse(localStorage.getItem(LS_STEPS) ?? '[]'))
  const reportChunks = ref<string[]>(localStorage.getItem(LS_REPORT) ? [localStorage.getItem(LS_REPORT)!] : [])
  const reportDone   = ref<boolean>(!!localStorage.getItem(LS_REPORT))
  const chatMessages = ref<ChatMessage[]>(JSON.parse(localStorage.getItem(LS_CHAT) ?? '[]'))

  const report    = computed<string>(() => reportChunks.value.join(''))
  const hasReport = computed<boolean>(() => reportDone.value && report.value.length > 0)

  function addAgentStep(type: AgentStep['type'], content: string, tool: string | null = null): void {
    agentSteps.value.push({ type, content, tool, id: Date.now() + Math.random() })
    saveSteps(agentSteps.value)
  }

  function appendReport(chunk: string): void {
    reportChunks.value.push(chunk)
  }

  function addChatMessage(role: ChatMessage['role'], content: string): void {
    chatMessages.value.push({ role, content, timestamp: Date.now() })
    saveChat(chatMessages.value)
  }

  function updateLastChat(content: string): void {
    const last = chatMessages.value[chatMessages.value.length - 1]
    if (last) last.content = content
    saveChat(chatMessages.value)
  }

  function persistChat(): void {
    saveChat(chatMessages.value)
  }

  function setSessionIdFromServer(sid: string): void {
    sessionId.value = sid
    try {
      localStorage.setItem(LS_EXPIRES, String(Date.now() + TTL_MS))
    } catch {}
  }

  function reset(): void {
    sessionId.value = ''
    isAnalyzing.value = false
    agentSteps.value = []
    reportChunks.value = []
    reportDone.value = false
    chatMessages.value = []
    localStorage.removeItem(LS_SESSION)
    localStorage.removeItem(LS_REPORT)
    localStorage.removeItem(LS_JOB)
    localStorage.removeItem(LS_STEPS)
    localStorage.removeItem(LS_CHAT)
    localStorage.removeItem(LS_EXPIRES)
  }

  watch(sessionId, v => v ? localStorage.setItem(LS_SESSION, v) : localStorage.removeItem(LS_SESSION))
  watch(report,    v => v ? localStorage.setItem(LS_REPORT, v)  : localStorage.removeItem(LS_REPORT))

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
