<template>
  <el-card class="agent-card" shadow="never">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon class="header-icon" :class="{ 'is-spinning': isAnalyzing }">
            <Cpu v-if="!isAnalyzing" />
            <Loading v-else />
          </el-icon>
          <span>智能分析引擎</span>
        </div>
        <el-tag v-if="displaySteps.length" size="small" type="info" effect="plain" round>
          {{ displaySteps.length }} 步
        </el-tag>
      </div>
    </template>

    <div class="card-content" ref="stepsList">
      <div v-if="!displaySteps.length && !isAnalyzing" class="empty-state">
        <div class="empty-icon-bg">
          <el-icon><DataLine /></el-icon>
        </div>
        <p class="empty-title">等待任务启动</p>
        <p class="empty-desc">上传简历后，Agent 的思维链将在此实时展现</p>
      </div>

      <el-timeline v-else class="custom-timeline">
        <transition-group name="list">
          <el-timeline-item
            v-for="step in displaySteps"
            :key="step.id"
            :type="step.type === 'thinking' ? 'primary' : 'warning'"
            :hollow="step.type === 'thinking'"
            :timestamp="step.timestamp"
            placement="top"
            hide-timestamp
            size="large"
          >
            <div class="step-card" :class="`step-${step.type}`">
              <div class="step-header">
                <span class="step-title">
                  {{ step.type === 'thinking' ? '思考规划' : '调用工具' }}
                </span>
                <el-tag v-if="step.tool" size="small" type="warning" effect="dark" round class="tool-tag">
                  {{ step.tool }}
                </el-tag>
              </div>
              <div class="step-content">
                {{ step.displayed }}<span v-if="step.typing" class="typing-cursor">|</span>
              </div>
            </div>
          </el-timeline-item>

          <el-timeline-item v-if="isAnalyzing" key="thinking-node" type="primary" size="large">
            <div class="thinking-placeholder">
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
              <span class="thinking-text">AI 正在深入分析...</span>
            </div>
          </el-timeline-item>
        </transition-group>
      </el-timeline>
    </div>
  </el-card>
</template>

<script setup>
import { computed, watch, nextTick, ref } from 'vue'
import { useResumeStore } from '../stores/resume'
import { Cpu, Loading, DataLine, ChatDotRound, Tools } from '@element-plus/icons-vue'

const store = useResumeStore()
const stepsList = ref(null)

// 恢复状态
const restoredSteps = store.agentSteps.map(s => ({ ...s, displayed: s.content, typing: false, full: s.content }))
const displaySteps = ref(restoredSteps)
const typingQueue = ref([])
let isTypingActive = false
let knownCount = store.agentSteps.length

const isAnalyzing = computed(() => store.isAnalyzing)

async function scrollBottom() {
  await nextTick()
  if (stepsList.value) {
    stepsList.value.scrollTo({ top: stepsList.value.scrollHeight, behavior: 'smooth' })
  }
}

function typeStep(stepIdx) {
  const step = displaySteps.value[stepIdx]
  if (!step) { processQueue(); return }

  const full = step.full
  let i = step.displayed.length
  step.typing = true

  const speed = full.length > 60 ? 10 : 18 

  const tick = () => {
    const s = displaySteps.value[stepIdx]
    if (!s) return
    if (i < full.length) {
      const chunkSize = full.length > 100 ? 4 : 2
      s.displayed = full.slice(0, Math.min(i + chunkSize, full.length))
      i = s.displayed.length
      scrollBottom()
      setTimeout(tick, speed)
    } else {
      s.displayed = full
      s.typing = false
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
  setTimeout(() => typeStep(stepIdx), 300)
}

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
.agent-card {
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
  color: #409eff;
  background: #ecf5ff;
  padding: 4px;
  border-radius: 6px;
  transition: all 0.3s;
}

.is-spinning {
  animation: rotate 2s linear infinite;
  color: #67c23a;
  background: #f0f9eb;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.card-content {
  padding: 24px 20px;
  flex: 1;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
  text-align: center;
}

.empty-icon-bg {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #f2f6fc;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: #c0c4cc;
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
  color: #909399;
}

/* Timeline Customization */
.custom-timeline {
  padding-left: 2px;
}

.custom-timeline :deep(.el-timeline-item__node--primary) {
  background-color: #409eff;
  box-shadow: 0 0 0 4px #d9ecff;
}

.custom-timeline :deep(.el-timeline-item__node--warning) {
  background-color: #e6a23c;
  box-shadow: 0 0 0 4px #fdf6ec;
}

.custom-timeline :deep(.el-timeline-item__tail) {
  border-left: 2px solid #e4e7ed;
}

.step-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px 16px;
  border: 1px solid #ebeef5;
  transition: all 0.3s;
  position: relative;
  top: -6px;
}

.step-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  background: #fff;
  border-color: #dcdfe6;
}

.step-thinking .step-card {
  border-left: 3px solid #409eff;
}

.step-observation .step-card {
  border-left: 3px solid #e6a23c;
}

.step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.step-title {
  font-size: 13px;
  font-weight: 700;
  color: #303133;
}

.step-content {
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-word;
}

.tool-tag {
  height: 20px;
  padding: 0 8px;
  font-size: 11px;
}

.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 14px;
  background: #409eff;
  margin-left: 2px;
  animation: blink 0.8s infinite;
  vertical-align: middle;
}

.thinking-placeholder {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #f0f9eb;
  border-radius: 8px;
  border: 1px dashed #67c23a;
  color: #67c23a;
  font-size: 13px;
  font-weight: 500;
}

.typing-indicator {
  display: flex;
  gap: 4px;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  background: #67c23a;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* List Transitions */
.list-enter-active,
.list-leave-active {
  transition: all 0.4s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>