<template>
  <el-card class="agent-card">
    <template #header>
      <div class="card-header">
        <el-icon class="spin-icon" v-if="isAnalyzing"><Loading /></el-icon>
        <el-icon v-else><Cpu /></el-icon>
        <span>Agent 分析过程</span>
        <el-tag v-if="displaySteps.length" size="small" type="info" round>
          {{ displaySteps.length }} 步
        </el-tag>
      </div>
    </template>

    <div v-if="!displaySteps.length" class="empty-state">
      <el-icon><Cpu /></el-icon>
      <p>上传简历后，Agent 的思考过程将实时显示在这里</p>
    </div>

    <div v-else class="steps-list" ref="stepsList">
      <div
        v-for="step in displaySteps"
        :key="step.id"
        class="step-item"
        :class="`step-${step.type}`"
      >
        <div class="step-icon">
          <el-icon v-if="step.type === 'thinking'"><ChatDotRound /></el-icon>
          <el-icon v-else><Tools /></el-icon>
        </div>
        <div class="step-body">
          <div class="step-label">
            <span v-if="step.type === 'thinking'">思考</span>
            <span v-else>
              工具调用
              <el-tag v-if="step.tool" size="small" type="warning" class="tool-tag">
                {{ step.tool }}
              </el-tag>
            </span>
          </div>
          <div class="step-content">{{ step.displayed }}<span v-if="step.typing" class="type-cursor">|</span></div>
        </div>
      </div>

      <div v-if="isAnalyzing" class="step-item step-thinking">
        <div class="step-icon">
          <el-icon class="spin-icon"><Loading /></el-icon>
        </div>
        <div class="step-body">
          <div class="step-label">思考中...</div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed, watch, nextTick, ref } from 'vue'
import { useResumeStore } from '../stores/resume'

const store = useResumeStore()
const stepsList = ref(null)

// 从 localStorage 恢复时直接显示完成状态，不重放动画
const restoredSteps = store.agentSteps.map(s => ({ ...s, displayed: s.content, typing: false, full: s.content }))
const displaySteps = ref(restoredSteps)
const typingQueue = ref([])
let isTypingActive = false
let knownCount = store.agentSteps.length   // 记录已处理过的步骤数，避免重放

const isAnalyzing = computed(() => store.isAnalyzing)
const isTyping = computed(() => displaySteps.value.some(s => s.typing))

async function scrollBottom() {
  await nextTick()
  if (stepsList.value) stepsList.value.scrollTop = stepsList.value.scrollHeight
}

// 逐字打印单个步骤
function typeStep(stepIdx) {
  // #region agent log
  fetch('http://127.0.0.1:7500/ingest/f60e4ff7-5f4b-44e9-8293-177c66b632b9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'291064'},body:JSON.stringify({sessionId:'291064',location:'AgentProcess.vue:typeStep',message:'typewriter start',data:{stepIdx,queueLen:typingQueue.value.length,t:Date.now()},hypothesisId:'H-B',timestamp:Date.now()})}).catch(()=>{})
  // #endregion
  const step = displaySteps.value[stepIdx]
  if (!step) { processQueue(); return }

  const full = step.full
  let i = step.displayed.length
  step.typing = true

  const speed = full.length > 60 ? 12 : 20   // 长文字快一点

  const tick = () => {
    const s = displaySteps.value[stepIdx]
    if (!s) return
    if (i < full.length) {
      // 每次多吐几个字符，避免太慢
      const chunkSize = full.length > 100 ? 3 : 1
      s.displayed = full.slice(0, Math.min(i + chunkSize, full.length))
      i = s.displayed.length
      scrollBottom()
      setTimeout(tick, speed)
    } else {
      s.displayed = full
      s.typing = false
      // #region agent log
      fetch('http://127.0.0.1:7500/ingest/f60e4ff7-5f4b-44e9-8293-177c66b632b9',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'291064'},body:JSON.stringify({sessionId:'291064',location:'AgentProcess.vue:typeStep',message:'typewriter done',data:{stepIdx,queueRemaining:typingQueue.value.length,t:Date.now()},hypothesisId:'H-B',timestamp:Date.now()})}).catch(()=>{})
      // #endregion
      processQueue()
    }
  }
  setTimeout(tick, speed)
}

function processQueue() {
  if (typingQueue.value.length === 0) {
    isTypingActive = false
    return
  }
  isTypingActive = true
  const stepIdx = typingQueue.value.shift()
  // 步骤间加 400ms 停顿，让每一步感觉像真实 Agent 在逐步思考
  setTimeout(() => typeStep(stepIdx), 400)
}

// 监听 store 里新增的步骤（只处理新增的，不重放恢复的）
watch(
  () => store.agentSteps.length,
  (newLen) => {
    if (newLen === 0) {
      displaySteps.value = []
      typingQueue.value = []
      isTypingActive = false
      knownCount = 0
      return
    }
    for (let i = knownCount; i < newLen; i++) {
      const s = store.agentSteps[i]
      displaySteps.value.push({ ...s, displayed: '', typing: false, full: s.content })
      typingQueue.value.push(displaySteps.value.length - 1)
    }
    knownCount = newLen
    if (!isTypingActive) processQueue()
  }
)
</script>

<style scoped>
.agent-card { height: 100%; }
.agent-card :deep(.el-card__body) {
  height: calc(100% - 55px);
  overflow: hidden;
  padding: 0;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: var(--el-text-color-placeholder);
  gap: 12px;
  padding: 20px;
  text-align: center;
}
.empty-state .el-icon { font-size: 40px; }
.steps-list {
  height: 100%;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.step-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.step-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
}
.step-thinking .step-icon {
  background: var(--el-color-primary-light-8);
  color: var(--el-color-primary);
}
.step-observation .step-icon {
  background: var(--el-color-warning-light-8);
  color: var(--el-color-warning);
}
.step-body { flex: 1; min-width: 0; }
.step-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.tool-tag { margin-left: 4px; }
.step-content {
  font-size: 13px;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: 8px 12px;
  line-height: 1.6;
  word-break: break-word;
  white-space: pre-wrap;
}
.type-cursor {
  display: inline-block;
  color: var(--el-color-primary);
  font-weight: 300;
  animation: blink-cursor 0.7s step-end infinite;
  margin-left: 1px;
}
@keyframes blink-cursor {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.spin-icon { animation: spin 1s linear infinite; }
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
