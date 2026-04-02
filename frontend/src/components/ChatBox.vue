<template>
  <el-card class="chat-card" shadow="never">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon class="header-icon"><ChatDotRound /></el-icon>
          <span>追问简历</span>
        </div>
        <el-tag v-if="!canChat" size="small" type="info" effect="plain" round>
          分析完成后解锁
        </el-tag>
      </div>
    </template>

    <div class="chat-body custom-scrollbar" ref="chatBody">
      <div v-if="!messages.length" class="empty-state">
        <div class="empty-bubble">
          <el-icon><ChatLineRound /></el-icon>
        </div>
        <p class="empty-title">AI 简历顾问随时待命</p>
        <p class="empty-desc">您可以针对简历中的任何细节进行追问</p>
        <div class="quick-questions">
          <el-tag
            v-for="q in quickQuestions"
            :key="q"
            class="quick-tag"
            effect="plain"
            round
            @click="useQuickQuestion(q)"
          >
            {{ q }}
          </el-tag>
        </div>
      </div>

      <div v-for="(msg, i) in messages" :key="i" class="message" :class="`msg-${msg.role}`">
        <div class="msg-avatar">
          <el-icon v-if="msg.role === 'user'"><User /></el-icon>
          <img v-else src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" alt="AI" class="ai-avatar" />
        </div>
        <div class="msg-content">
          <div class="msg-bubble">
            <div v-if="msg.role === 'assistant'" class="markdown-content" v-html="renderMd(msg.content)"></div>
            <div v-else>{{ msg.content }}</div>
          </div>
          <span class="msg-time" v-if="msg.timestamp">{{ formatTime(msg.timestamp) }}</span>
        </div>
      </div>

      <div v-if="isReplying && !messages[messages.length - 1]?.content" class="message msg-assistant">
        <div class="msg-avatar">
          <img src="https://cdn-icons-png.flaticon.com/512/4712/4712035.png" alt="AI" class="ai-avatar" />
        </div>
        <div class="msg-bubble typing-bubble">
          <div class="typing-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-footer">
      <div class="input-wrapper" :class="{ 'is-focus': isInputFocus }">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="1"
          autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="输入您的问题..."
          :disabled="!canChat || isReplying"
          resize="none"
          class="chat-input"
          @focus="isInputFocus = true"
          @blur="isInputFocus = false"
          @keydown.enter.exact.prevent="sendMessage"
          @keydown.enter.shift.exact="() => {}"
        />
        <el-button
          type="primary"
          circle
          class="send-btn"
          :disabled="!canSend"
          :loading="isReplying"
          @click="sendMessage"
        >
          <el-icon v-if="!isReplying"><Promotion /></el-icon>
        </el-button>
      </div>
      <div class="input-hint">Enter 发送 / Shift+Enter 换行</div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { marked } from 'marked'
import { useResumeStore } from '../stores/resume'
import { chat } from '../api/index'
import { ChatDotRound, ChatLineRound, User, Promotion } from '@element-plus/icons-vue'

const props = defineProps<{
  jobTitle: string
  jobDescription: string
}>()

const store = useResumeStore()
const chatBody = ref<HTMLElement | null>(null)
const inputText = ref<string>('')
const isReplying = ref<boolean>(false)
const isInputFocus = ref<boolean>(false)
const messages = computed(() => store.chatMessages)

const canChat = computed(() => store.hasReport && !!store.sessionId)
const canSend = computed(() => canChat.value && inputText.value.trim() && !isReplying.value)

const quickQuestions: string[] = [
  '如何优化项目经历描述？',
  '我的技能栈是否匹配？',
  '怎么体现我的领导力？',
]

function renderMd(text: string): string {
  // 聊天同样采用“累计后整体 parse”策略，确保流式阶段 Markdown 语法尽量稳定。
  return marked.parse(text || '') as string
}

function formatTime(ts?: number): string {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

async function scrollToBottom(): Promise<void> {
  await nextTick()
  if (chatBody.value) {
    chatBody.value.scrollTop = chatBody.value.scrollHeight
  }
}

function useQuickQuestion(q: string): void {
  if (!canChat.value) return
  inputText.value = q
  sendMessage()
}

watch(() => store.hasReport, (v: boolean) => {
  if (v) scrollToBottom()
})

async function sendMessage(): Promise<void> {
  const text = inputText.value.trim()
  if (!text || !canSend.value) return

  store.addChatMessage('user', text)
  inputText.value = ''
  isReplying.value = true
  await scrollToBottom()

  store.addChatMessage('assistant', '')
  const idx = store.chatMessages.length - 1

  // 每收到一个 chunk 先累加，再整段替换到最后一条 assistant 消息里。
  // 这样即使 chunk 在 Markdown 语法中间断开，也能在下一次累加后恢复正确渲染。
  let accumulated = ''
  try {
    await chat(store.sessionId, text, props.jobTitle, props.jobDescription, (chunk: string) => {
      accumulated += chunk
      store.chatMessages[idx].content = accumulated
      scrollToBottom()
    })
  } catch (e) {
    store.chatMessages[idx].content = `❌ ${(e as Error).message || '请求失败，请重试'}`
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
  background: #fff;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
  color: #303133;
}

.header-icon {
  font-size: 20px;
  color: #e6a23c;
  background: #fdf6ec;
  padding: 4px;
  border-radius: 6px;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: #f9fafc;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: #909399;
  text-align: center;
}

.empty-bubble {
  font-size: 48px;
  color: #e6a23c;
  background: #fdf6ec;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 13px;
  margin-bottom: 24px;
}

.quick-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 80%;
}

.quick-tag {
  cursor: pointer;
  transition: all 0.2s;
  border-color: #d9ecff;
  color: #409eff;
  background: #fff;
}

.quick-tag:hover {
  background: #ecf5ff;
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  max-width: 90%;
}

.msg-user {
  flex-direction: row-reverse;
  align-self: flex-end;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
  overflow: hidden;
}

.ai-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  padding: 4px;
}

.msg-user .msg-avatar {
  background: #409eff;
  color: #fff;
  font-size: 20px;
}

.msg-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 100%;
}

.msg-bubble {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
  position: relative;
  box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}

.msg-user .msg-bubble {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg-assistant .msg-bubble {
  background: #fff;
  color: #303133;
  border-bottom-left-radius: 4px;
  border: 1px solid #ebeef5;
}

.msg-time {
  font-size: 11px;
  color: #c0c4cc;
  padding: 0 4px;
}

.msg-user .msg-time { text-align: right; }

.chat-footer {
  padding: 16px 20px;
  background: #fff;
  border-top: 1px solid #ebeef5;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  background: #f5f7fa;
  border-radius: 24px;
  padding: 8px 12px 8px 20px;
  border: 1px solid transparent;
  transition: all 0.3s;
}

.input-wrapper.is-focus {
  background: #fff;
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.chat-input :deep(.el-textarea__inner) {
  background: transparent;
  box-shadow: none;
  border: none;
  padding: 6px 0;
  font-size: 14px;
  color: #303133;
}

.send-btn {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
}

.input-hint {
  text-align: center;
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 8px;
}

/* Typing Dots Animation */
.typing-bubble {
  padding: 16px 20px !important;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  background: #909399;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }
</style>