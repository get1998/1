<script setup lang="ts">
import type { TaskStatus } from '@/api/types'

/** 任务状态展示组件（紧凑） */
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
  if (status.sending && status.recording) {
    return '录屏/发送中'
  }
  if (status.sending) {
    return '发送中'
  }
  if (status.recording) {
    return '录屏中'
  }
  if (status.ready) {
    return '已就绪'
  }
  return '进房中…'
}
</script>

<template>
  <el-card shadow="never" class="panel-card">
    <template #header>
      <span class="panel-title">运行状态</span>
    </template>

    <div class="status-list">
      <div class="status-row">
        <span class="status-label">状态</span>
        <span
          class="status-value"
          :class="
            status.running
              ? status.sending || status.recording
                ? 'is-sending'
                : 'is-ready'
              : 'is-stopped'
          "
        >
          {{ phaseText(status) }}
        </span>
      </div>
      <div class="status-row">
        <span class="status-label">已发</span>
        <span class="status-value">{{ status.sentCount }} 次</span>
      </div>
      <div class="status-row">
        <span class="status-label">结束</span>
        <span class="status-value">{{ status.endTimeText || '未设置' }}</span>
      </div>
      <div v-if="status.lastVideo" class="status-row">
        <span class="status-label">录屏</span>
        <span class="status-value status-value--path">{{ status.lastVideo }}</span>
      </div>
      <div v-if="status.excelReportPath" class="status-row">
        <span class="status-label">报表</span>
        <span class="status-value status-value--path">{{ status.excelReportPath }}</span>
      </div>
      <div v-if="status.lastError" class="status-row">
        <span class="status-label">错误</span>
        <span class="status-value is-error">{{ status.lastError }}</span>
      </div>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.panel-card {
  margin-bottom: 0;
  border-radius: 12px;

  :deep(.el-card__header) {
    padding: 10px 16px;
  }

  :deep(.el-card__body) {
    padding: 8px 16px 12px;
  }
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
}

.status-list {
  display: flex;
  flex-direction: column;
}

.status-row {
  display: flex;
  align-items: flex-start;
  padding: 6px 0;
  border-bottom: 1px solid #f3f4f6;

  &:last-child {
    border-bottom: none;
  }
}

.status-label {
  flex: 0 0 36px;
  color: #9ca3af;
  font-size: 12px;
  line-height: 1.5;
}

.status-value {
  flex: 1;
  min-width: 0;
  color: #111827;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.5;
  word-break: break-all;

  &--path {
    font-size: 12px;
    font-weight: 500;
  }

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
