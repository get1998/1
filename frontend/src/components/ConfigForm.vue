<script setup lang="ts">
import { EMOJI_PER_SEND_PRESETS } from '@/composables/useAppConfig'
import EmojiPicker from '@/components/EmojiPicker.vue'
import type { AppConfig } from '@/api/types'

/** 配置表单：单次评论一种表情，可视化选择抖音表情 */
defineProps<{
  /** 配置表单数据 */
  form: AppConfig
  /** 发送预览 */
  emojiSendPreview: string
  /** 单次表情数说明 */
  emojiQuantityText: string
  /** 指定表情说明 */
  emojiIndexText: string
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
  /** 启动任务（进入直播间） */
  start: []
  /** 开始发送评论 */
  beginSend: []
  /** 停止任务 */
  stop: []
}>()
</script>

<template>
  <el-card shadow="never" class="panel-card">
    <template #header>
      <span class="panel-title">运行配置</span>
    </template>

    <el-form :model="form" label-width="130px">
      <el-form-item label="直播间 URL" required>
        <el-input
          v-model="form.liveRoomUrl"
          placeholder="https://live.douyin.com/123456789"
          clearable
        />
      </el-form-item>

      <el-form-item label="发送间隔" required>
        <el-input-number v-model="form.intervalSeconds" :min="5" :max="3600" :step="5" />
        <span class="form-tip">秒</span>
      </el-form-item>

      <el-form-item label="等待登录">
        <el-input-number v-model="form.waitLoginSeconds" :min="0" :max="300" :step="5" />
        <span class="form-tip">秒（首次打开浏览器后等待手动登录）</span>
      </el-form-item>

      <el-form-item label="选择表情" required>
        <EmojiPicker
          v-model="form.emojiIndex"
          :live-room-url="form.liveRoomUrl"
          :wait-login-seconds="form.waitLoginSeconds"
          :running="running"
        />
        <div class="form-desc">{{ emojiIndexText }}</div>
      </el-form-item>

      <el-form-item label="单次表情数" required>
        <div class="emoji-count-row">
          <el-input-number v-model="form.emojisPerSend" :min="1" :max="20" :step="1" />
          <div class="preset-group">
            <el-button
              v-for="count in EMOJI_PER_SEND_PRESETS"
              :key="`qty-${count}`"
              :type="form.emojisPerSend === count ? 'primary' : 'default'"
              plain
              @click="form.emojisPerSend = count"
            >
              {{ count }} 个
            </el-button>
          </div>
        </div>
        <div class="form-desc">{{ emojiQuantityText }}</div>
      </el-form-item>

      <el-form-item label="发送预览">
        <div class="order-preview">{{ emojiSendPreview }}</div>
      </el-form-item>

      <el-form-item label="发评后截图">
        <el-switch v-model="form.screenshotEnabled" />
        <span class="form-tip">关闭后仅发评论，不保存截图</span>
      </el-form-item>

      <el-form-item v-if="form.screenshotEnabled" label="截图目录" required>
        <el-input v-model="form.screenshotDir" placeholder="./screenshots" clearable />
      </el-form-item>

      <el-form-item v-if="form.screenshotEnabled" label="截图等待">
        <el-input-number v-model="form.screenshotWaitSeconds" :min="1" :max="30" :step="1" />
        <span class="form-tip">秒（等待评论出现在聊天区后再截图）</span>
      </el-form-item>

      <el-form-item label="Excel 统计">
        <el-switch v-model="form.excelReportEnabled" />
        <span class="form-tip">每次发评写入 Excel 记录</span>
      </el-form-item>

      <el-form-item v-if="form.excelReportEnabled" label="报表目录" required>
        <el-input v-model="form.excelReportDir" placeholder="./reports" clearable />
      </el-form-item>

      <el-form-item label="结束时间">
        <el-switch v-model="form.endTimeEnabled" />
        <span class="form-tip">到达设定时间后自动停止任务</span>
      </el-form-item>

      <el-form-item v-if="form.endTimeEnabled" label="停止时间" required>
        <el-date-picker
          v-model="form.endTime"
          type="datetime"
          placeholder="选择结束时间"
          format="YYYY-MM-DD HH:mm:ss"
          value-format="YYYY-MM-DD HH:mm:ss"
          :disabled-date="(date: Date) => date.getTime() < Date.now() - 86400000"
        />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="emit('save')">保存配置</el-button>
        <el-button type="success" :disabled="running" :loading="starting" @click="emit('start')">
          启动任务
        </el-button>
        <el-button
          type="warning"
          :disabled="!ready || sending"
          :loading="beginningSend"
          @click="emit('beginSend')"
        >
          开始发送
        </el-button>
        <el-button type="danger" :disabled="!running" :loading="stopping" @click="emit('stop')">
          停止任务
        </el-button>
      </el-form-item>
    </el-form>
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

.form-tip {
  margin-left: 8px;
  color: #6b7280;
  font-size: 13px;
}

.form-desc {
  margin-top: 8px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.emoji-count-row {
  display: flex;
  flex-direction: column;
}

.preset-group {
  display: flex;
  flex-wrap: wrap;
  margin-top: 12px;
}

.preset-group .el-button {
  margin-right: 8px;
  margin-bottom: 8px;
}

.order-preview {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  color: #374151;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-all;
}

.el-button + .el-button {
  margin-left: 12px;
}
</style>
