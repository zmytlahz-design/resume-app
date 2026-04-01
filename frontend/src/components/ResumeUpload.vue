<template>
  <el-card class="upload-card" shadow="never">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon class="header-icon"><DocumentChecked /></el-icon>
          <span>上传简历</span>
        </div>
        <el-button
          v-if="hasStarted"
          class="reset-btn"
          size="small"
          text
          bg
          @click="onReset"
        >
          <el-icon><RefreshRight /></el-icon> 重置
        </el-button>
      </div>
    </template>

    <div class="card-content">
      <!-- 文件拖拽区域 -->
      <div
        class="drop-zone"
        :class="{ 'is-dragover': isDragover, 'has-file': file }"
        @dragover.prevent="isDragover = true"
        @dragleave="isDragover = false"
        @drop.prevent="onDrop"
        @click="fileInput?.click()"
      >
        <input ref="fileInput" type="file" accept=".pdf" class="hidden-input" @change="onFileChange" />
        
        <transition name="fade" mode="out-in">
          <div v-if="file" class="file-info" key="file">
            <div class="file-icon-wrapper">
              <el-icon><Document /></el-icon>
            </div>
            <div class="file-details">
              <div class="file-name">{{ file.name }}</div>
              <div class="file-size">{{ (file.size / 1024).toFixed(1) }} KB</div>
            </div>
            <el-button class="reselect-btn" type="danger" link @click.stop="clearFile">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          
          <div v-else class="upload-placeholder" key="placeholder">
            <div class="icon-circle">
              <el-icon><UploadFilled /></el-icon>
            </div>
            <div class="upload-text">点击或拖拽 PDF 简历</div>
            <div class="upload-hint">支持最大 10MB</div>
          </div>
        </transition>
      </div>

      <transition name="el-fade-in">
        <div v-if="errorMsg" class="error-msg">
          <el-icon><WarningFilled /></el-icon> {{ errorMsg }}
        </div>
      </transition>

      <!-- 职位信息 -->
      <div class="form-section">
        <el-form label-position="top" @submit.prevent class="custom-form">
          <el-form-item label="目标职位">
            <el-input
              v-model="jobTitle"
              placeholder="例如：高级前端工程师"
              clearable
              :disabled="isAnalyzing"
            >
              <template #prefix>
                <el-icon><Suitcase /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="职位描述 (JD)" class="flex-grow-item">
            <el-input
              v-model="jobDescription"
              type="textarea"
              :rows="6"
              placeholder="请粘贴招聘 JD 要求..."
              :disabled="isAnalyzing"
              resize="none"
            />
          </el-form-item>
        </el-form>
      </div>

      <div class="action-footer">
        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :disabled="!canSubmit"
          :loading="isAnalyzing"
          @click="onSubmit"
          round
        >
          {{ isAnalyzing ? '正在智能诊断...' : '开始诊断' }}
          <el-icon v-if="!isAnalyzing" class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useResumeStore } from '../stores/resume'
import { analyzeResume } from '../api/index'
import { DocumentChecked, RefreshRight, Document, UploadFilled, Close, WarningFilled, Suitcase, ArrowRight } from '@element-plus/icons-vue'

const emit = defineEmits<{
  (e: 'updateJob', payload: { title: string; desc: string }): void
}>()

const store = useResumeStore()
const fileInput = ref<HTMLInputElement | null>(null)
const file = ref<File | null>(null)
const jobTitle = ref<string>('')
const jobDescription = ref<string>('')
const isDragover = ref<boolean>(false)
const errorMsg = ref<string>('')

const isAnalyzing = computed(() => store.isAnalyzing)
const canSubmit = computed(() => file.value && jobTitle.value.trim() && jobDescription.value.trim())
const hasStarted = computed(() => store.isAnalyzing || store.hasReport || store.agentSteps.length > 0)

function onFileChange(e: Event): void {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) selectFile(f)
}

function onDrop(e: DragEvent): void {
  isDragover.value = false
  const f = e.dataTransfer?.files[0]
  if (f?.type === 'application/pdf') {
    selectFile(f)
  } else {
    errorMsg.value = '只支持 PDF 格式'
  }
}

function selectFile(f: File): void {
  errorMsg.value = ''
  file.value = f
}

function clearFile(): void {
  file.value = null
  errorMsg.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

function onReset(): void {
  clearFile()
  jobTitle.value = ''
  jobDescription.value = ''
  store.reset()
  emit('updateJob', { title: '', desc: '' })
}

async function onSubmit(): Promise<void> {
  if (!canSubmit.value) return
  errorMsg.value = ''
  store.reset()
  store.isAnalyzing = true
  emit('updateJob', { title: jobTitle.value, desc: jobDescription.value })

  try {
    await analyzeResume(file.value!, jobTitle.value, jobDescription.value, (type, data) => {
      switch (type) {
        case 'session_id':
          store.setSessionIdFromServer(data)
          break
        case 'thinking':
          store.addAgentStep('thinking', data)
          break
        case 'observation':
          try {
            const parsed = JSON.parse(data) as { result: string; tool: string | null }
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
    errorMsg.value = (e as Error).message || '分析失败，请重试'
  } finally {
    store.isAnalyzing = false
    store.reportDone = true
  }
}
</script>

<style scoped>
.upload-card {
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
  color: #409eff;
  background: #ecf5ff;
  padding: 4px;
  border-radius: 6px;
  font-size: 20px;
}

.card-content {
  padding: 20px;
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.drop-zone {
  border: 2px dashed #dcdfe6;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: #fcfcfc;
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.drop-zone:hover,
.drop-zone.is-dragover {
  border-color: #409eff;
  background: #ecf5ff;
  transform: translateY(-2px);
}

.drop-zone.has-file {
  border-style: solid;
  border-color: #67c23a;
  background: #f0f9eb;
}

.icon-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #f2f6fc;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  color: #909399;
  transition: all 0.3s;
}

.drop-zone:hover .icon-circle {
  background: #fff;
  color: #409eff;
}

.upload-text {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  margin-bottom: 4px;
}

.upload-hint {
  font-size: 12px;
  color: #c0c4cc;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 0 10px;
}

.file-icon-wrapper {
  font-size: 32px;
  color: #67c23a;
}

.file-details {
  flex: 1;
  text-align: left;
  overflow: hidden;
}

.file-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: 12px;
  color: #909399;
}

.hidden-input { display: none; }

.error-msg {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #f56c6c;
  font-size: 12px;
  margin-top: 8px;
  background: #fef0f0;
  padding: 6px;
  border-radius: 4px;
}

.form-section {
  margin-top: 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.custom-form {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.flex-grow-item {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.flex-grow-item :deep(.el-form-item__content) {
  flex: 1;
}

.flex-grow-item :deep(.el-textarea),
.flex-grow-item :deep(.el-textarea__inner) {
  height: 100%;
}

.action-footer {
  margin-top: 20px;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  transition: all 0.3s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>