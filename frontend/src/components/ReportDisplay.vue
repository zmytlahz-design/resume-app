<template>
  <el-card class="report-card">
    <template #header>
      <div class="card-header">
        <el-icon><Document /></el-icon>
        <span>诊断报告</span>
        <el-tag v-if="hasReport" size="small" type="success" round>已完成</el-tag>
        <el-tag v-else-if="isAnalyzing" size="small" type="warning" round>生成中...</el-tag>
      </div>
    </template>

    <div v-if="!report && !isAnalyzing" class="empty-state">
      <el-icon><Document /></el-icon>
      <p>AI 诊断报告将在分析完成后显示在这里</p>
    </div>

    <div v-else class="report-body" ref="reportBody">
      <div class="markdown-content" v-html="renderedReport"></div>
    </div>
  </el-card>
</template>

<script setup>
import { computed, watch, nextTick, ref } from 'vue'
import { marked } from 'marked'
import { useResumeStore } from '../stores/resume'

const store = useResumeStore()
const reportBody = ref(null)

const report = computed(() => store.report)
const hasReport = computed(() => store.hasReport)
const isAnalyzing = computed(() => store.isAnalyzing)

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
}
.report-card :deep(.el-card__body) {
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
.empty-state .el-icon {
  font-size: 40px;
}
.report-body {
  height: 100%;
  overflow-y: auto;
  padding: 20px 24px;
}
.cursor-blink {
  display: inline-block;
  animation: blink 1s step-end infinite;
  color: var(--el-color-primary);
  font-size: 18px;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* Markdown 样式 */
.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
  margin: 16px 0 8px;
  font-weight: 600;
  line-height: 1.4;
}
.markdown-content :deep(h1) { font-size: 20px; color: var(--el-color-primary); border-bottom: 2px solid var(--el-color-primary-light-7); padding-bottom: 6px; }
.markdown-content :deep(h2) { font-size: 17px; color: var(--el-text-color-primary); }
.markdown-content :deep(h3) { font-size: 15px; color: var(--el-text-color-regular); }
.markdown-content :deep(p) { margin: 8px 0; line-height: 1.8; color: var(--el-text-color-regular); }
.markdown-content :deep(ul),
.markdown-content :deep(ol) { padding-left: 20px; margin: 8px 0; }
.markdown-content :deep(li) { margin: 4px 0; line-height: 1.7; color: var(--el-text-color-regular); }
.markdown-content :deep(strong) { color: var(--el-text-color-primary); }
.markdown-content :deep(code) {
  background: var(--el-fill-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: var(--el-color-danger);
}
.markdown-content :deep(blockquote) {
  border-left: 4px solid var(--el-color-primary-light-5);
  margin: 12px 0;
  padding: 8px 16px;
  background: var(--el-color-primary-light-9);
  border-radius: 0 6px 6px 0;
  color: var(--el-text-color-secondary);
}
</style>
