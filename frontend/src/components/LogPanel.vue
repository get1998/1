<script setup lang="ts">
/** 运行日志面板（紧凑，固定高度） */
defineProps<{
  /** 日志行列表 */
  logs: string[]
}>()
</script>

<template>
  <el-card shadow="never" class="panel-card">
    <template #header>
      <span class="panel-title">日志信息</span>
      <span v-if="logs.length" class="panel-badge">{{ logs.length }} 条</span>
    </template>

    <div class="log-box">
      <template v-if="logs.length">
        <div v-for="(line, index) in logs" :key="index" class="log-line">{{ line }}</div>
      </template>
      <div v-else class="log-empty">暂无日志</div>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.panel-card {
  width: 100%;
  border-radius: 12px;

  :deep(.el-card__header) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px;
  }

  :deep(.el-card__body) {
    padding: 10px 12px 12px;
  }
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
}

.panel-badge {
  color: #9ca3af;
  font-size: 12px;
  font-weight: 400;
}

.log-box {
  height: 220px;
  padding: 10px 12px;
  overflow-y: auto;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
}

.log-line {
  white-space: pre-wrap;
}

.log-empty {
  color: #94a3b8;
}
</style>
