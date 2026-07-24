<script setup lang="ts">
/** 运行日志面板 */
defineProps<{
  /** 日志行列表 */
  logs: string[]
}>()
</script>

<template>
  <el-card shadow="never" class="panel-card">
    <template #header>
      <span class="panel-title">运行日志</span>
    </template>

    <div class="log-box">
      <template v-if="logs.length">
        <div v-for="(line, index) in logs" :key="index" class="log-line">{{ line }}</div>
      </template>
      <div v-else class="log-empty">暂无日志，启动任务后将在此显示。</div>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.panel-card {
  border-radius: 12px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
}

.log-box {
  min-height: 200px;
  max-height: 320px;
  padding: 16px;
  overflow-y: auto;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-line {
  white-space: pre-wrap;
}

.log-empty {
  color: #94a3b8;
}
</style>
