<script setup lang="ts">
import type { AppConfig } from '@/api/types'

/** 运行参数与任务控制面板（中列，紧凑布局） */
defineProps<{
  /** 配置表单数据 */
  form: AppConfig
  /** 是否保存中 */
  saving: boolean
  /** 是否启动中 */
  starting: boolean
  /** 是否开始发送中 */
  beginningSend: boolean
  /** 是否停止中 */
  stopping: boolean
  /** 任务是否运行中 */
  running: boolean
  /** 直播间是否已就绪 */
  ready: boolean
  /** 是否已在发送中 */
  sending: boolean
}>()

const emit = defineEmits<{
  /** 保存配置 */
  save: []
  /** 启动任务 */
  start: []
  /** 开始发送评论 */
  beginSend: []
  /** 停止任务 */
  stop: []
}>()
</script>

<template>
  <el-card shadow="never" class="panel-card panel-card--compact">
    <template #header>
      <span class="panel-title">运行配置</span>
    </template>

    <el-form :model="form" size="small" label-width="72px" class="panel-form">
      <el-form-item label="发送间隔" required class="number-item">
        <div class="number-control">
          <el-input-number
            v-model="form.intervalSeconds"
            :min="5"
            :max="3600"
            :step="5"
            controls-position="right"
            class="number-input"
          />
          <span class="unit">秒</span>
        </div>
      </el-form-item>

      <el-form-item label="等待登录" class="number-item">
        <div class="number-control">
          <el-input-number
            v-model="form.waitLoginSeconds"
            :min="0"
            :max="300"
            :step="5"
            controls-position="right"
            class="number-input"
          />
          <span class="unit">秒</span>
        </div>
      </el-form-item>

      <div class="switch-row">
        <div class="switch-row__item">
          <span class="switch-row__label">录屏</span>
          <el-switch v-model="form.videoRecordEnabled" />
        </div>
        <div class="switch-row__item">
          <span class="switch-row__label">Excel</span>
          <el-switch v-model="form.excelReportEnabled" />
        </div>
        <div class="switch-row__item">
          <span class="switch-row__label">定时</span>
          <el-switch v-model="form.endTimeEnabled" />
        </div>
      </div>

      <el-form-item v-if="form.videoRecordEnabled" label="录屏" class="path-item">
        <el-input v-model="form.videoDir" readonly size="small" />
      </el-form-item>
      <el-form-item v-if="form.excelReportEnabled" label="报表" class="path-item">
        <el-input v-model="form.excelReportDir" readonly size="small" />
      </el-form-item>
      <el-form-item v-if="form.endTimeEnabled" label="停止" class="path-item" required>
        <el-date-picker
          v-model="form.endTime"
          type="datetime"
          placeholder="结束时间"
          format="MM-DD HH:mm"
          value-format="YYYY-MM-DD HH:mm:ss"
          :disabled-date="(date: Date) => date.getTime() < Date.now() - 86400000"
          size="small"
          style="width: 100%"
        />
      </el-form-item>
    </el-form>

    <div class="action-buttons">
      <el-button size="small" type="primary" :loading="saving" @click="emit('save')">保存</el-button>
      <el-button size="small" type="success" :disabled="running" :loading="starting" @click="emit('start')">
        启动
      </el-button>
      <el-button
        size="small"
        type="warning"
        :disabled="!ready || sending"
        :loading="beginningSend"
        @click="emit('beginSend')"
      >
        发送
      </el-button>
      <el-button size="small" type="danger" :disabled="!running" :loading="stopping" @click="emit('stop')">
        停止
      </el-button>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.panel-card {
  border-radius: 12px;

  &--compact {
    :deep(.el-card__header) {
      padding: 12px 16px;
    }

    :deep(.el-card__body) {
      padding: 12px 16px 14px;
    }
  }
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
}

.panel-form {
  :deep(.el-form-item) {
    margin-bottom: 10px;
  }

  :deep(.el-form-item__label) {
    padding-right: 6px;
    color: #4b5563;
    font-size: 12px;
  }
}

.number-item {
  :deep(.el-form-item__content) {
    flex: 1;
    min-width: 0;
  }
}

.number-control {
  display: flex;
  align-items: center;
  width: 100%;
}

.number-input {
  flex: 1;
  min-width: 140px;
  max-width: 100%;

  :deep(.el-input__wrapper) {
    padding-left: 8px;
    padding-right: 36px;
  }

  :deep(.el-input__inner) {
    text-align: left;
  }
}

.unit {
  flex: 0 0 auto;
  margin-left: 8px;
  color: #6b7280;
  font-size: 12px;
  white-space: nowrap;
}

.switch-row {
  display: flex;
  margin-bottom: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f9fafb;

  &__item {
    display: flex;
    flex: 1;
    align-items: center;
    justify-content: center;
  }

  &__label {
    margin-right: 6px;
    color: #374151;
    font-size: 12px;
    font-weight: 500;
  }
}

.path-item {
  margin-bottom: 8px !important;

  :deep(.el-input__inner) {
    font-size: 12px;
  }
}

.action-buttons {
  display: flex;
  padding-top: 10px;
  border-top: 1px solid #f0f2f5;

  .el-button {
    flex: 1;
    margin: 0 4px 0 0;
    cursor: pointer;

    &:last-child {
      margin-right: 0;
    }
  }
}
</style>
