<template>
  <el-card class="report-card" shadow="never">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon class="header-icon"><DataAnalysis /></el-icon>
          <span>诊断报告</span>
        </div>
        <div class="status-tags">
          <el-tag v-if="hasReport" size="small" type="success" effect="dark" round>
            <el-icon><Select /></el-icon> 已完成
          </el-tag>
          <el-tag v-else-if="isAnalyzing" size="small" type="warning" effect="light" round class="pulse-tag">
            <el-icon class="is-loading"><Loading /></el-icon> 生成中...
          </el-tag>
        </div>
      </div>
    </template>

    <div v-if="!report && !isAnalyzing" class="empty-state">
      <div class="empty-bg">
        <el-icon><DocumentCopy /></el-icon>
      </div>
      <p class="empty-text">等待分析结果</p>
      <p class="empty-hint">AI 将为您生成详细的简历优化建议</p>
    </div>

    <div v-else class="report-body custom-scrollbar" ref="reportBody">
      <div class="markdown-content" v-html="renderedReport"></div>
      <div v-if="isAnalyzing && !reportDone" class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed, watch, nextTick, ref } from 'vue'
import { marked } from 'marked'
import { useResumeStore } from '../stores/resume'
import { DataAnalysis, Select, Loading, DocumentCopy } from '@element-plus/icons-vue'

const store = useResumeStore()
const reportBody = ref(null)

const report = computed(() => store.report)
const hasReport = computed(() => store.hasReport)
const isAnalyzing = computed(() => store.isAnalyzing)
const reportDone = computed(() => store.reportDone)

const renderedReport = computed(() => {
  if (!report.value) return ''
  return marked.parse(report.value)
})

watch(report, async () => {
  await nextTick()
  if (reportBody.value) {
    reportBody.value.scrollTop = reportBody.value.scrollHeight
  }
})
</script>

<style scoped>
.report-card {
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
  color: #67c23a;
  background: #f0f9eb;
  padding: 4px;
  border-radius: 6px;
}

.status-tags .el-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

.report-body {
  padding: 32px 40px;
  overflow-y: auto;
  flex: 1;
  background: #fff;
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

.empty-bg {
  width: 96px;
  height: 96px;
  background: #f2f6fc;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  color: #dcdfe6;
  font-size: 48px;
}

.empty-text {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 13px;
  color: #909399;
}

/* Markdown Styling */
.markdown-content {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  line-height: 1.8;
  color: #2c3e50;
  font-size: 15px;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 700;
  line-height: 1.4;
  color: #1a1a1a;
}

.markdown-content :deep(h1) {
  font-size: 24px;
  padding-bottom: 12px;
  border-bottom: 2px solid #eaecef;
}

.markdown-content :deep(h2) {
  font-size: 20px;
  padding-left: 12px;
  border-left: 4px solid #409eff;
  background: linear-gradient(90deg, #ecf5ff 0%, transparent 100%);
  padding: 8px 12px;
  border-radius: 0 4px 4px 0;
  margin-top: 32px;
}

.markdown-content :deep(h3) {
  font-size: 17px;
  color: #409eff;
  margin-top: 24px;
}

.markdown-content :deep(p) {
  margin-bottom: 16px;
  text-align: justify;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 24px;
  margin-bottom: 16px;
}

.markdown-content :deep(li) {
  margin-bottom: 8px;
  position: relative;
}

.markdown-content :deep(strong) {
  color: #e6a23c;
  font-weight: 700;
  background: #fdf6ec;
  padding: 0 4px;
  border-radius: 4px;
}

.markdown-content :deep(code) {
  font-family: 'Fira Code', monospace;
  background-color: #f6f8fa;
  padding: 2px 6px;
  border-radius: 4px;
  color: #e83e8c;
  font-size: 13px;
}

.markdown-content :deep(blockquote) {
  margin: 20px 0;
  padding: 16px 20px;
  color: #606266;
  background-color: #f4f4f5;
  border-left: 4px solid #dcdfe6;
  border-radius: 0 8px 8px 0;
  font-style: italic;
}

.markdown-content :deep(a) {
  color: #409eff;
  text-decoration: none;
  border-bottom: 1px dashed #409eff;
}

.markdown-content :deep(hr) {
  border: 0;
  border-top: 1px solid #eaecef;
  margin: 32px 0;
}

.pulse-tag {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.6; }
  100% { opacity: 1; }
}

.typing-indicator {
  display: flex;
  gap: 6px;
  padding: 12px 0;
  justify-content: center;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #c0c4cc;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
</style>