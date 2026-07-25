<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { InputInstance } from 'element-plus'
import EmojiPicker from '@/components/EmojiPicker.vue'
import type { CommentPart } from '@/api/types'
import { parseInputTextToParts, partsToInputText } from '@/utils/commentParts'

/** 正常聊天输入框：直接打字，点表情插入光标处 */
const props = defineProps<{
  /** 评论片段 */
  modelValue: CommentPart[]
  /** 主播抖音号 */
  douyinId?: string
  /** 直播间号 web_rid */
  webRid?: string
  /** 直播间 URL */
  liveRoomUrl?: string
  /** 等待登录秒数 */
  waitLoginSeconds: number
  /** 任务是否运行中 */
  running: boolean
}>()

const emit = defineEmits<{
  /** 更新评论片段 */
  'update:modelValue': [value: CommentPart[]]
}>()

const inputRef = ref<InputInstance>()
const inputText = ref('')

/**
 * 提交输入内容为片段
 * @param value - 输入框文本
 */
function commitInput(value: string): void {
  emit('update:modelValue', parseInputTextToParts(value))
}

/**
 * 输入变化
 * @param value - 当前文本
 */
function handleInput(value: string): void {
  inputText.value = value
  commitInput(value)
}

/**
 * 获取原生 textarea
 * @returns textarea 元素
 */
function getTextarea(): HTMLTextAreaElement | null {
  const exposed = inputRef.value as InputInstance & { textarea?: HTMLTextAreaElement }
  return exposed?.textarea ?? null
}

/**
 * 在光标处插入表情（和正常聊天一样）
 * @param index - 表情序号
 */
async function handlePickEmoji(index: number): Promise<void> {
  const marker = `[表情${index}]`
  const el = getTextarea()
  const current = inputText.value
  const start = el?.selectionStart ?? current.length
  const end = el?.selectionEnd ?? current.length
  const next = `${current.slice(0, start)}${marker}${current.slice(end)}`
  inputText.value = next
  commitInput(next)
  await nextTick()
  const textarea = getTextarea()
  if (!textarea) {
    return
  }
  const caret = start + marker.length
  textarea.focus()
  textarea.setSelectionRange(caret, caret)
}

watch(
  () => props.modelValue,
  (parts) => {
    const next = partsToInputText(parts)
    if (next !== inputText.value) {
      inputText.value = next
    }
  },
  { immediate: true, deep: true },
)
</script>

<template>
  <div class="comment-composer">
    <el-input
      ref="inputRef"
      :model-value="inputText"
      type="textarea"
      :rows="3"
      maxlength="200"
      show-word-limit
      placeholder="像正常聊天一样输入，点下方表情会插入到光标位置"
      @update:model-value="handleInput"
    />
    <div class="composer-tip">表情在输入框里显示为 [表情N]，发送时会按顺序转成抖音表情</div>

    <EmojiPicker
      :douyin-id="douyinId"
      :web-rid="webRid"
      :live-room-url="liveRoomUrl"
      :wait-login-seconds="waitLoginSeconds"
      :running="running"
      insert-mode
      @pick="handlePickEmoji"
    />
  </div>
</template>

<style scoped lang="scss">
.comment-composer {
  width: 100%;
}

.composer-tip {
  margin-top: 8px;
  margin-bottom: 12px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}
</style>
