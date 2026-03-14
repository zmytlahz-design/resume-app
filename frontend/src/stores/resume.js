import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const LS_SESSION = 'resume_sessionId'
const LS_REPORT  = 'resume_report'
const LS_JOB     = 'resume_job'
const LS_STEPS   = 'resume_steps'
const LS_CHAT    = 'resume_chat'
const LS_EXPIRES = 'resume_expires_at'

/** 与后端 Redis 一致：2 小时过期 */
const TTL_MS = 2 * 60 * 60 * 1000

function isLocalDataExpired() {
  const expires = localStorage.getItem(LS_EXPIRES)
  const sid = localStorage.getItem(LS_SESSION)
  if (!sid || !expires) return false
  return Date.now() > parseInt(expires, 10)
}

function clearExpiredLocalData() {
  if (!isLocalDataExpired()) return
  localStorage.removeItem(LS_SESSION)
  localStorage.removeItem(LS_REPORT)
  localStorage.removeItem(LS_JOB)
  localStorage.removeItem(LS_STEPS)
  localStorage.removeItem(LS_CHAT)
  localStorage.removeItem(LS_EXPIRES)
}

function saveSteps(steps) {
  try { localStorage.setItem(LS_STEPS, JSON.stringify(steps)) } catch {}
}
function saveChat(msgs) {
  try { localStorage.setItem(LS_CHAT, JSON.stringify(msgs)) } catch {}
}

// 进入应用时先清理过期数据，再读 localStorage
clearExpiredLocalData()

export const useResumeStore = defineStore('resume', () => {
  const sessionId    = ref(localStorage.getItem(LS_SESSION) || '')
  const isAnalyzing  = ref(false)
  const agentSteps   = ref(JSON.parse(localStorage.getItem(LS_STEPS) || '[]'))
  const reportChunks = ref(localStorage.getItem(LS_REPORT) ? [localStorage.getItem(LS_REPORT)] : [])
  const reportDone   = ref(!!localStorage.getItem(LS_REPORT))
  const chatMessages = ref(JSON.parse(localStorage.getItem(LS_CHAT) || '[]'))

  const report = computed(() => reportChunks.value.join(''))
  const hasReport = computed(() => reportDone.value && report.value.length > 0)

  function addAgentStep(type, content, tool = null) {
    agentSteps.value.push({ type, content, tool, id: Date.now() + Math.random() })
    saveSteps(agentSteps.value)
  }

  function appendReport(chunk) {
    reportChunks.value.push(chunk)
  }

  function addChatMessage(role, content) {
    chatMessages.value.push({ role, content })
    saveChat(chatMessages.value)
  }

  function updateLastChat(content) {
    const last = chatMessages.value[chatMessages.value.length - 1]
    if (last) last.content = content
    saveChat(chatMessages.value)
  }

  function persistChat() {
    saveChat(chatMessages.value)
  }

  /** 服务端返回新 session 时调用，同时写入 2h 过期时间 */
  function setSessionIdFromServer(sid) {
    sessionId.value = sid
    try {
      localStorage.setItem(LS_EXPIRES, String(Date.now() + TTL_MS))
    } catch {}
  }

  function reset() {
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
