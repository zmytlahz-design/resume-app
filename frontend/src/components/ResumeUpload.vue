<template>
  <el-card class="upload-card">
    <template #header>
      <div class="card-header">
        <el-icon><DocumentChecked /></el-icon>
        <span>上传简历</span>
        <el-button
          v-if="hasStarted"
          class="reset-btn"
          size="small"
          type="danger"
          plain
          @click="onReset"
        >
          <el-icon><RefreshLeft /></el-icon> 重置
        </el-button>
      </div>
    </template>

    <!-- 文件拖拽区域 -->
    <div
      class="drop-zone"
      :class="{ 'is-dragover': isDragover, 'has-file': file }"
      @dragover.prevent="isDragover = true"
      @dragleave="isDragover = false"
      @drop.prevent="onDrop"
      @click="fileInput.click()"
    >
      <input ref="fileInput" type="file" accept=".pdf" class="hidden-input" @change="onFileChange" />
      <template v-if="file">
        <el-icon class="file-icon"><Document /></el-icon>
        <div class="file-name">{{ file.name }}</div>
        <div class="file-size">{{ (file.size / 1024).toFixed(1) }} KB</div>
        <el-button type="danger" link size="small" @click.stop="clearFile">
          <el-icon><Delete /></el-icon> 重新选择
        </el-button>
      </template>
      <template v-else>
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">点击或拖拽 PDF 简历到此处</div>
        <div class="upload-hint">支持 PDF 格式，最大 10MB</div>
      </template>
    </div>

    <div v-if="errorMsg" class="error-msg">
      <el-icon><Warning /></el-icon> {{ errorMsg }}
    </div>

    <!-- 职位信息 -->
    <div class="form-section">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="目标职位">
          <el-input
            v-model="jobTitle"
            placeholder="例：前端工程师、产品经理、数据分析师"
            clearable
            :disabled="isAnalyzing"
          />
        </el-form-item>
        <el-form-item label="职位描述 (JD)">
          <el-input
            v-model="jobDescription"
            type="textarea"
            :rows="5"
            placeholder="粘贴招聘 JD，AI 将根据岗位要求诊断简历匹配度..."
            :disabled="isAnalyzing"
          />
        </el-form-item>
      </el-form>
    </div>

    <el-button
      type="primary"
      size="large"
      class="submit-btn"
      :disabled="!canSubmit"
      :loading="isAnalyzing"
      @click="onSubmit"
    >
      <el-icon v-if="!isAnalyzing"><MagicStick /></el-icon>
      {{ isAnalyzing ? 'AI 分析中...' : '开始诊断' }}
    </el-button>
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useResumeStore } from '../stores/resume'
import { analyzeResume } from '../api/index'

const emit = defineEmits(['updateJob'])

const store = useResumeStore()
const fileInput = ref(null)
const file = ref(null)
const jobTitle = ref('')
const jobDescription = ref('')
const isDragover = ref(false)
const errorMsg = ref('')

const isAnalyzing = computed(() => store.isAnalyzing)
const canSubmit = computed(() => file.value && jobTitle.value.trim() && jobDescription.value.trim())
const hasStarted = computed(() => store.isAnalyzing || store.hasReport || store.agentSteps.length > 0)

function onFileChange(e) {
  const f = e.target.files?.[0]
  if (f) selectFile(f)
}

function onDrop(e) {
  isDragover.value = false
  const f = e.dataTransfer?.files[0]
  if (f?.type === 'application/pdf') {
    selectFile(f)
  } else {
    errorMsg.value = '只支持 PDF 格式'
  }
}

function selectFile(f) {
  errorMsg.value = ''
  file.value = f
}

function clearFile() {
  file.value = null
  errorMsg.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function onReset() {
  clearFile()
  jobTitle.value = ''
  jobDescription.value = ''
  store.reset()
  emit('updateJob', { title: '', desc: '' })
}

async function onSubmit() {
  if (!canSubmit.value) return
  errorMsg.value = ''
  store.reset()
  store.isAnalyzing = true
  emit('updateJob', { title: jobTitle.value, desc: jobDescription.value })

  try {
    await analyzeResume(file.value, jobTitle.value, jobDescription.value, (type, data) => {
      switch (type) {
        case 'session_id':
          store.sessionId = data
          break
        case 'thinking':
          store.addAgentStep('thinking', data)
          break
        case 'observation':
          try {
            const parsed = JSON.parse(data)
            store.addAgentStep('observation', parsed.result, parsed.tool)
          } catch {
            store.addAgentStep('observation', data)
          }
          break
        case 'report_chunk':
          store.appendReport(data)
          break
        case 'report_end':
          store.reportDone = true
          break
        case 'error':
          errorMsg.value = data
          break
      }
    })
  } catch (e) {
    errorMsg.value = e.message || '分析失败，请重试'
  } finally {
    store.isAnalyzing = false
    store.reportDone = true
  }
}
</script>

<style scoped>
.upload-card {
  height: 100%;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
}
.reset-btn {
  margin-left: auto;
}
.drop-zone {
  border: 2px dashed var(--el-border-color);
  border-radius: 8px;
  padding: 32px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--el-fill-color-lighter);
}
.drop-zone:hover,
.drop-zone.is-dragover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.drop-zone.has-file {
  border-style: solid;
  border-color: var(--el-color-success);
  background: var(--el-color-success-light-9);
}
.hidden-input {
  display: none;
}
.upload-icon {
  font-size: 48px;
  color: var(--el-text-color-placeholder);
  margin-bottom: 8px;
}
.file-icon {
  font-size: 40px;
  color: var(--el-color-success);
  margin-bottom: 6px;
}
.upload-text {
  font-size: 15px;
  color: var(--el-text-color-regular);
  margin-bottom: 4px;
}
.upload-hint {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}
.file-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 2px;
  word-break: break-all;
}
.file-size {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}
.error-msg {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--el-color-danger);
  font-size: 13px;
  margin-top: 8px;
}
.form-section {
  margin-top: 20px;
}
.submit-btn {
  width: 100%;
  margin-top: 8px;
  height: 44px;
  font-size: 15px;
}
</style>
