<template>
  <div class="app">
    <header class="app-header">
      <div class="header-inner">
        <div class="logo">
          <el-icon><MagicStick /></el-icon>
          <span>AI 简历诊断 Agent</span>
        </div>
        <div class="header-desc">上传简历 + 岗位 JD，AI 自动诊断匹配度并给出优化建议</div>
      </div>
    </header>

    <main class="app-main">
      <!-- 左栏：上传表单 -->
      <div class="col col-left">
        <ResumeUpload @update-job="onUpdateJob" />
      </div>

      <!-- 中栏：Agent 思考过程 -->
      <div class="col col-mid">
        <AgentProcess />
      </div>

      <!-- 右栏：报告 + 追问（竖向分割） -->
      <div class="col col-right">
        <div class="right-top">
          <ReportDisplay />
        </div>
        <div class="right-bottom">
          <ChatBox :job-title="jobTitle" :job-description="jobDescription" />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ResumeUpload from './components/ResumeUpload.vue'
import AgentProcess from './components/AgentProcess.vue'
import ReportDisplay from './components/ReportDisplay.vue'
import ChatBox from './components/ChatBox.vue'

interface SavedJob { title: string; desc: string }

const savedJob = JSON.parse(localStorage.getItem('resume_job') ?? 'null') as SavedJob | null
const jobTitle = ref<string>(savedJob?.title ?? '')
const jobDescription = ref<string>(savedJob?.desc ?? '')

function onUpdateJob({ title, desc }: { title: string; desc: string }): void {
  jobTitle.value = title
  jobDescription.value = desc
  if (title || desc) localStorage.setItem('resume_job', JSON.stringify({ title, desc }))
  else localStorage.removeItem('resume_job')
}
</script>

<style>
* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #f5f7fa;
  color: #303133;
  height: 100vh;
  overflow: hidden;
}

#app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 4px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
</style>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-image: radial-gradient(#e0eaff 1px, transparent 1px);
  background-size: 20px 20px;
  background-color: #f5f7fa;
}

.app-header {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  color: #303133;
  padding: 0 32px;
  height: 64px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  border-bottom: 1px solid #ebeef5;
  z-index: 10;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 700;
  color: #409eff;
  letter-spacing: -0.5px;
}

.logo .el-icon {
  font-size: 24px;
  background: #ecf5ff;
  padding: 6px;
  border-radius: 8px;
}

.header-desc {
  font-size: 14px;
  color: #909399;
  background: #f4f4f5;
  padding: 6px 12px;
  border-radius: 20px;
}

.app-main {
  flex: 1;
  display: flex;
  gap: 20px;
  padding: 24px 32px;
  overflow: hidden;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
}

.col {
  display: flex;
  flex-direction: column;
  min-height: 0;
  transition: all 0.3s ease;
}

.col-left {
  width: 340px;
  flex-shrink: 0;
}

.col-mid {
  width: 320px;
  flex-shrink: 0;
}

.col-right {
  flex: 1;
  gap: 20px;
  min-width: 0;
}

.right-top {
  flex: 1;
  min-height: 0;
}

.right-bottom {
  height: 380px;
  flex-shrink: 0;
}

/* 全局卡片样式覆盖 */
.col :deep(.el-card) {
  height: 100%;
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
  border-radius: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
}

.col :deep(.el-card:hover) {
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.06);
}

.col :deep(.el-card__header) {
  border-bottom: 1px solid #f2f6fc;
  padding: 16px 20px;
}

.col :deep(.el-card__body) {
  padding: 0;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
