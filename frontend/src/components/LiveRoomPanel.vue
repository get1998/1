<script setup lang="ts">
import CommentComposer from '@/components/CommentComposer.vue'
import type { AppConfig } from '@/api/types'

/** 直播间信息与评论内容（左列） */
defineProps<{
  /** 配置表单数据 */
  form: AppConfig
  /** 任务是否运行中 */
  running: boolean
}>()
</script>

<template>
  <el-card shadow="never" class="panel-card">
    <template #header>
      <span class="panel-title">直播间信息</span>
    </template>

    <el-form :model="form" size="small" label-position="top" class="panel-form">
      <el-form-item label="抖音号" required>
        <el-input v-model="form.douyinId" placeholder="主播抖音号" clearable />
      </el-form-item>

      <el-form-item label="直播间号">
        <el-input v-model="form.webRid" placeholder="可选" clearable />
      </el-form-item>

      <el-form-item label="直播间 URL">
        <el-input
          v-model="form.liveRoomUrl"
          :readonly="!!form.webRid"
          placeholder="可选，有号时自动生成"
          clearable
        />
      </el-form-item>

      <el-form-item label="评论内容" class="comment-item">
        <CommentComposer
          v-model="form.commentParts"
          :douyin-id="form.douyinId"
          :web-rid="form.webRid"
          :live-room-url="form.liveRoomUrl"
          :wait-login-seconds="form.waitLoginSeconds"
          :running="running"
          compact
        />
      </el-form-item>
    </el-form>

    <div class="panel-footnote">
      未填直播间号时按抖音号搜索进房；发送前需填写评论内容。
    </div>
  </el-card>
</template>

<style scoped lang="scss">
.panel-card {
  border-radius: 12px;
  height: 100%;

  :deep(.el-card__header) {
    padding: 12px 16px;
  }

  :deep(.el-card__body) {
    padding: 12px 16px 14px;
  }
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
}

.panel-form {
  :deep(.el-form-item) {
    margin-bottom: 12px;
  }

  :deep(.el-form-item__label) {
    margin-bottom: 4px !important;
    color: #374151;
    font-size: 12px;
    font-weight: 600;
    line-height: 1.2;
  }

  :deep(.el-input) {
    width: 100%;
  }
}

.comment-item {
  margin-bottom: 0 !important;
}

.panel-footnote {
  margin-top: 10px;
  padding-top: 10px;
  color: #9ca3af;
  font-size: 12px;
  line-height: 1.5;
  border-top: 1px solid #f0f2f5;
}
</style>
