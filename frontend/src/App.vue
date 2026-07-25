<script setup lang="ts">

import LiveRoomPanel from '@/components/LiveRoomPanel.vue'

import LogPanel from '@/components/LogPanel.vue'

import RunConfigPanel from '@/components/RunConfigPanel.vue'

import TaskStatusPanel from '@/components/TaskStatusPanel.vue'

import { useAppConfig } from '@/composables/useAppConfig'

import { useTaskControl } from '@/composables/useTaskControl'



const { form, saving, buildPayload, saveConfig } = useAppConfig()

const { status, starting, beginningSend, stopping, startTask, beginSend, stopTask } =

  useTaskControl(() => buildPayload())

</script>



<template>

  <div class="config-page">

    <header class="page-header">

      <h1>抖音直播间自动评论</h1>

      <p>填抖音号可自动搜索进房。开始发送时自动录屏留证，停止发送后保存视频。</p>

    </header>



    <div class="page-body">

      <aside class="page-col page-col--room">

        <LiveRoomPanel :form="form" :running="status.running" />

      </aside>



      <section class="page-col page-col--config">

        <RunConfigPanel

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

      </section>



      <aside class="page-col page-col--log">

        <LogPanel :logs="status.logs" />

      </aside>

    </div>

  </div>

</template>



<style scoped lang="scss">

.config-page {

  max-width: 1480px;

  margin: 0 auto;

  padding: 24px 20px 32px;

}



.page-header {

  margin-bottom: 20px;



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



.page-body {
  display: flex;
  align-items: flex-start;
}

.page-col {
  min-width: 0;

  & + & {
    margin-left: 16px;
  }

  &--room {
    flex: 0 0 320px;
    width: 320px;
  }

  &--config {
    flex: 0 0 340px;
    width: 340px;
    display: flex;
    flex-direction: column;
  }

  &--log {
    flex: 1;
    min-width: 0;
  }
}

.page-col--config :deep(.panel-card) {
  margin-bottom: 16px;
}

@media (max-width: 1100px) {
  .page-body {
    flex-direction: column;
  }

  .page-col {
    width: 100% !important;
    flex: none !important;

    & + & {
      margin-left: 0;
      margin-top: 16px;
    }
  }
}

</style>

