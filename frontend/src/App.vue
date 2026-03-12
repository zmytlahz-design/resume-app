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

<script setup>
import { ref } from 'vue'
import ResumeUpload from './components/ResumeUpload.vue'
import AgentProcess from './components/AgentProcess.vue'
import ReportDisplay from './components/ReportDisplay.vue'
import ChatBox from './components/ChatBox.vue'

const savedJob = JSON.parse(localStorage.getItem('resume_job') || 'null')
const jobTitle = ref(savedJob?.title || '')
const jobDescription = ref(savedJob?.desc || '')

function onUpdateJob({ title, desc }) {
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
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #f0f2f5;
  height: 100vh;
  overflow: hidden;
}

#app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: linear-gradient(135deg, #409eff 0%, #337ecc 100%);
  color: #fff;
  padding: 0 24px;
  height: 56px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.header-inner {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
}

.logo .el-icon {
  font-size: 22px;
}

.header-desc {
  font-size: 13px;
  opacity: 0.85;
  white-space: nowrap;
}

.app-main {
  flex: 1;
  display: flex;
  gap: 12px;
  padding: 12px;
  overflow: hidden;
  min-height: 0;
}

.col {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.col-left {
  width: 320px;
  flex-shrink: 0;
}

.col-mid {
  width: 280px;
  flex-shrink: 0;
}

.col-right {
  flex: 1;
  gap: 12px;
  min-width: 0;
}

.right-top {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.right-bottom {
  height: 340px;
  flex-shrink: 0;
}

/* el-card height 100% */
.col-left :deep(.el-card),
.col-mid :deep(.el-card),
.right-top :deep(.el-card),
.right-bottom :deep(.el-card) {
  height: 100%;
  overflow: hidden;
}
</style>
