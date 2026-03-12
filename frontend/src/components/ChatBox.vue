<template>
  <el-card class="chat-card">
    <template #header>
      <div class="card-header">
        <el-icon><ChatDotRound /></el-icon>
        <span>追问简历</span>
        <el-tag v-if="!canChat" size="small" type="info" round>完成分析后可用</el-tag>
      </div>
    </template>

    <div class="chat-body" ref="chatBody">
      <div v-if="!messages.length" class="empty-state">
        <el-icon><ChatDotRound /></el-icon>
        <p>分析完成后，你可以继续追问 AI</p>
        <p class="hint">例如："帮我改写第一段项目经历" 或 "怎么突出我的技术能力？"</p>
      </div>

      <div v-for="(msg, i) in messages" :key="i" class="message" :class="`msg-${msg.role}`">
        <div class="msg-avatar">
          <el-icon v-if="msg.role === 'user'"><User /></el-icon>
          <el-icon v-else><Cpu /></el-icon>
        </div>
        <div class="msg-bubble">
          <div v-if="msg.role === 'assistant'" class="markdown-content" v-html="renderMd(msg.content)"></div>
          <div v-else>{{ msg.content }}</div>
        </div>
      </div>

      <div v-if="isReplying && !messages[messages.length - 1]?.content" class="message msg-assistant">
        <div class="msg-avatar"><el-icon><Cpu /></el-icon></div>
        <div class="msg-bubble typing-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="2"
        placeholder="输入问题，Enter 发送，Shift+Enter 换行"
        :disabled="!canChat || isReplying"
        resize="none"
        @keydown.enter.exact.prevent="sendMessage"
        @keydown.enter.shift.exact="() => {}"
      />
      <el-button
        type="primary"
        :disabled="!canSend"
        :loading="isReplying"
        @click="sendMessage"
      >
        <el-icon><Promotion /></el-icon>
        发送
      </el-button>
    </div>
    <div class="input-hint">Enter 发送 &nbsp;·&nbsp; Shift+Enter 换行</div>
  </el-card>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { marked } from 'marked'
import { useResumeStore } from '../stores/resume'
import { chat } from '../api/index'

const props = defineProps({
  jobTitle: { type: String, default: '' },
  jobDescription: { type: String, default: '' },
})

const store = useResumeStore()
const chatBody = ref(null)
const inputText = ref('')
const isReplying = ref(false)
const messages = computed(() => store.chatMessages)

const canChat = computed(() => store.hasReport && !!store.sessionId)
const canSend = computed(() => canChat.value && inputText.value.trim() && !isReplying.value)

function renderMd(text) {
  return marked.parse(text || '')
}

async function scrollToBottom() {
  await nextTick()
  if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
}

watch(() => store.hasReport, (v) => {
  if (v) scrollToBottom()
})

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || !canSend.value) return

  store.addChatMessage('user', text)
  inputText.value = ''
  isReplying.value = true
  await scrollToBottom()

  store.addChatMessage('assistant', '')
  const idx = store.chatMessages.length - 1

  let accumulated = ''
  try {
    await chat(store.sessionId, text, props.jobTitle, props.jobDescription, (chunk) => {
      accumulated += chunk
      store.chatMessages[idx].content = accumulated
      scrollToBottom()
    })
  } catch (e) {
    store.chatMessages[idx].content = `❌ ${e.message || '请求失败，请重试'}`
  } finally {
    isReplying.value = false
    store.persistChat()
    await scrollToBottom()
  }
}
</script>

<style scoped>
.chat-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.chat-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  height: calc(100% - 55px);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--el-text-color-placeholder);
  gap: 10px;
  text-align: center;
  padding: 20px;
}
.empty-state .el-icon { font-size: 40px; }
.hint { font-size: 12px; }
.message {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.msg-user {
  flex-direction: row-reverse;
}
.msg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 16px;
}
.msg-user .msg-avatar {
  background: var(--el-color-primary-light-8);
  color: var(--el-color-primary);
}
.msg-assistant .msg-avatar {
  background: var(--el-fill-color);
  color: var(--el-text-color-secondary);
}
.msg-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}
.msg-user .msg-bubble {
  background: var(--el-color-primary);
  color: #fff;
  border-radius: 12px 2px 12px 12px;
}
.msg-assistant .msg-bubble {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-regular);
  border-radius: 2px 12px 12px 12px;
}
.chat-input {
  display: flex;
  gap: 8px;
  padding: 12px 16px 4px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.chat-input .el-input {
  flex: 1;
}
.input-hint {
  text-align: center;
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  padding: 4px 0 8px;
}
.typing-dots {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 12px 16px !important;
}
.typing-dots span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--el-text-color-placeholder);
  display: inline-block;
  animation: dot-bounce 1.2s infinite ease-in-out;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dot-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-6px); opacity: 1; }
}

/* Markdown in chat */
.markdown-content :deep(p) { margin: 4px 0; }
.markdown-content :deep(ul), .markdown-content :deep(ol) { padding-left: 16px; margin: 4px 0; }
.markdown-content :deep(li) { margin: 2px 0; }
.markdown-content :deep(strong) { font-weight: 600; }
.markdown-content :deep(code) {
  background: rgba(0,0,0,0.06);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
}
</style>
