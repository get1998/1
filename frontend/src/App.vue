<script setup lang="ts">
import ConfigForm from '@/components/ConfigForm.vue'
import LogPanel from '@/components/LogPanel.vue'
import TaskStatusPanel from '@/components/TaskStatusPanel.vue'
import { useAppConfig } from '@/composables/useAppConfig'
import { useTaskControl } from '@/composables/useTaskControl'

const { form, saving, buildPayload, saveConfig } = useAppConfig()
const { status, starting, beginningSend, stopping, startTask, beginSend, stopTask } =
  useTaskControl(() => buildPayload({ requireContent: true }))
</script>

<template>
  <div class="config-page">
    <header class="page-header">
      <h1>抖音直播间自动评论</h1>
      <p>填抖音号可自动搜索进房；也可填直播间号直达。先「启动任务」，再「开始发送」。</p>
    </header>

    <ConfigForm
      :form="form"
      :saving="saving"
      :starting="starting"
      :beginning-send="beginningSend"
      :stopping="stopping"
      :running="status.running"
      :ready="status.ready"
      :sending="status.sending"
      @save="saveConfig"
      @start="startTask"
      @begin-send="beginSend"
      @stop="stopTask"
    />

    <TaskStatusPanel :status="status" />
    <LogPanel :logs="status.logs" />
  </div>
</template>

<style scoped lang="scss">
.config-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 20px 48px;
}

.page-header {
  margin-bottom: 24px;

  h1 {
    margin: 0 0 8px;
    color: #1f2937;
    font-size: 28px;
  }

  p {
    margin: 0;
    color: #6b7280;
    font-size: 14px;
  }
}
</style>
