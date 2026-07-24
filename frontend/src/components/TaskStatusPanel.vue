<script setup lang="ts">
import type { TaskStatus } from '@/api/types'

/** 任务状态展示组件 */
defineProps<{
  /** 任务状态数据 */
  status: TaskStatus
}>()

/**
 * 任务阶段文案
 * @param status - 任务状态
 * @returns 展示文案
 */
function phaseText(status: TaskStatus): string {
  if (!status.running) {
    return '已停止'
  }
  if (status.sending) {
    return '发送中'
  }
  if (status.ready) {
    return '已就绪（等待开始发送）'
  }
  return '进入直播间中…'
}
</script>

<template>
  <el-card shadow="never" class="panel-card">
    <template #header>
      <span class="panel-title">运行状态</span>
    </template>

    <div class="status-grid">
      <div class="status-item">
        <div class="status-label">任务状态</div>
        <div
          class="status-value"
          :class="status.running ? (status.sending ? 'is-sending' : 'is-ready') : 'is-stopped'"
        >
          {{ phaseText(status) }}
        </div>
      </div>

      <div class="status-item">
        <div class="status-label">已发送次数</div>
        <div class="status-value">{{ status.sentCount }}</div>
      </div>

      <div class="status-item">
        <div class="status-label">计划结束</div>
        <div class="status-value">{{ status.endTimeText || '未设置' }}</div>
      </div>

      <div class="status-item">
        <div class="status-label">Excel 报表</div>
        <div class="status-value">{{ status.excelReportPath || '暂无' }}</div>
      </div>

      <div class="status-item">
        <div class="status-label">最近截图</div>
        <div class="status-value">{{ status.lastScreenshot || '暂无' }}</div>
      </div>

      <div class="status-item">
        <div class="status-label">最近错误</div>
        <div class="status-value" :class="{ 'is-error': !!status.lastError }">
          {{ status.lastError || '无' }}
        </div>
      </div>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.panel-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
}

.status-grid {
  display: flex;
  flex-wrap: wrap;
  margin: -8px;
}

.status-item {
  flex: 1 1 180px;
  margin: 8px;
  padding: 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.status-label {
  margin-bottom: 6px;
  color: #6b7280;
  font-size: 12px;
}

.status-value {
  color: #111827;
  font-size: 18px;
  font-weight: 600;
  word-break: break-all;

  &.is-sending {
    color: #059669;
  }

  &.is-ready {
    color: #d97706;
  }

  &.is-stopped {
    color: #6b7280;
  }

  &.is-error {
    color: #dc2626;
  }
}
</style>
