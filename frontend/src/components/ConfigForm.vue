<script setup lang="ts">
import CommentComposer from '@/components/CommentComposer.vue'
import type { AppConfig } from '@/api/types'

/** 配置表单：评论内容支持文字与表情自由组合 */
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
      <el-form-item label="抖音号" required>
        <el-input v-model="form.douyinId" placeholder="主播抖音号，例如 abc123" clearable />
        <div class="form-desc">
          未填直播间号时：启动后自动打开抖音，按抖音号搜索并进入正在直播的房间
        </div>
      </el-form-item>

      <el-form-item label="直播间号">
        <el-input v-model="form.webRid" placeholder="可选，如 421527298234" clearable />
        <div class="form-desc">
          可选。填了则直接打开 live.douyin.com/直播间号，不再搜索。
          {{ form.liveRoomUrl ? `当前：${form.liveRoomUrl}` : '' }}
        </div>
      </el-form-item>

      <el-form-item label="直播间 URL">
        <el-input
          v-model="form.liveRoomUrl"
          :readonly="!!form.webRid"
          placeholder="可选；有直播间号时自动生成，也可粘贴完整链接"
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

      <el-form-item label="评论内容" required>
        <CommentComposer
          v-model="form.commentParts"
          :douyin-id="form.douyinId"
          :web-rid="form.webRid"
          :live-room-url="form.liveRoomUrl"
          :wait-login-seconds="form.waitLoginSeconds"
          :running="running"
        />
      </el-form-item>

      <el-form-item label="发评后截图">
        <el-switch v-model="form.screenshotEnabled" />
        <span class="form-tip">关闭后仅发评论，不保存截图</span>
      </el-form-item>

      <el-form-item v-if="form.screenshotEnabled" label="截图目录">
        <el-input v-model="form.screenshotDir" readonly placeholder="./screenshots/房间号" />
        <div class="form-desc">按直播间号或抖音号自动生成</div>
      </el-form-item>

      <el-form-item v-if="form.screenshotEnabled" label="截图等待">
        <el-input-number v-model="form.screenshotWaitSeconds" :min="1" :max="30" :step="1" />
        <span class="form-tip">秒（等待评论出现在聊天区后再截图）</span>
      </el-form-item>

      <el-form-item label="Excel 统计">
        <el-switch v-model="form.excelReportEnabled" />
        <span class="form-tip">每次发评写入 Excel 记录</span>
      </el-form-item>

      <el-form-item v-if="form.excelReportEnabled" label="报表目录">
        <el-input v-model="form.excelReportDir" readonly placeholder="./reports/标识" />
        <div class="form-desc">按直播间号或抖音号自动生成</div>
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

.el-button + .el-button {
  margin-left: 12px;
}
</style>
