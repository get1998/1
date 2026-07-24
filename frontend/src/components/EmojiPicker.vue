<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchEmojiCatalogApi, getEmojiCatalogApi } from '@/api'
import type { EmojiCatalogItem } from '@/api/types'

/** 表情选择器：展示抖音直播间表情面板，点击选择 */
const props = defineProps<{
  /** 当前选中的表情序号 */
  modelValue: number
  /** 直播间 URL */
  liveRoomUrl: string
  /** 等待登录秒数 */
  waitLoginSeconds: number
  /** 任务是否运行中 */
  running: boolean
}>()

const emit = defineEmits<{
  /** 更新选中表情序号 */
  'update:modelValue': [value: number]
}>()

const loading = ref(false)
const refreshing = ref(false)
const items = ref<EmojiCatalogItem[]>([])

/** 当前选中项 */
const selectedItem = computed((): EmojiCatalogItem | undefined => {
  return items.value.find((item) => item.index === props.modelValue)
})

/** 是否已有缓存的表情目录 */
const hasCachedCatalog = computed((): boolean => items.value.length > 0)

/**
 * 应用表情目录数据
 * @param catalogItems - 表情列表
 */
function applyCatalog(catalogItems: EmojiCatalogItem[]): void {
  items.value = catalogItems
  if (
    catalogItems.length > 0 &&
    !catalogItems.some((item) => item.index === props.modelValue)
  ) {
    emit('update:modelValue', catalogItems[0]?.index ?? 1)
  }
}

/**
 * 从后端读取已缓存的表情目录
 */
async function loadCachedCatalog(): Promise<void> {
  loading.value = true
  try {
    const data = await getEmojiCatalogApi()
    applyCatalog(data.items)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '读取表情缓存失败')
  } finally {
    loading.value = false
  }
}

/**
 * 从直播间重新抓取表情目录
 */
async function refreshEmojis(): Promise<void> {
  const url = props.liveRoomUrl.trim()
  if (!url) {
    ElMessage.warning('请先填写直播间 URL')
    return
  }
  if (props.running) {
    ElMessage.warning('任务运行中，请先停止任务再加载表情')
    return
  }

  refreshing.value = true
  try {
    const data = await fetchEmojiCatalogApi({
      liveRoomUrl: url,
      waitLoginSeconds: props.waitLoginSeconds,
    })
    applyCatalog(data.items)
    if (data.total === 0) {
      ElMessage.warning('未读取到表情，请确认直播间已打开且已登录')
      return
    }
    ElMessage.success(`已更新 ${data.total} 个表情`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '加载表情失败')
  } finally {
    refreshing.value = false
  }
}

/**
 * 选择表情
 * @param index - 表情序号
 */
function selectEmoji(index: number): void {
  emit('update:modelValue', index)
}

onMounted(() => {
  void loadCachedCatalog()
})
</script>

<template>
  <div class="emoji-picker">
    <div class="emoji-picker__toolbar">
      <el-button
        type="primary"
        plain
        :loading="refreshing"
        :disabled="running || loading"
        @click="refreshEmojis"
      >
        {{ hasCachedCatalog ? '重新抓取表情' : '从直播间加载表情' }}
      </el-button>
      <span v-if="selectedItem" class="emoji-picker__hint">
        已选第 {{ modelValue }} 个表情（共 {{ items.length }} 个，本地已缓存）
      </span>
      <span v-else-if="items.length > 0" class="emoji-picker__hint">
        请点击选择表情（当前第 {{ modelValue }} 个）
      </span>
      <span v-else-if="loading" class="emoji-picker__hint">正在读取本地表情缓存…</span>
      <span v-else class="emoji-picker__hint">
        抖音表情为平台固定包，首次加载后会自动缓存，无需每次重新抓取
      </span>
    </div>

    <div v-if="items.length > 0" class="emoji-picker__grid">
      <button
        v-for="item in items"
        :key="item.index"
        type="button"
        class="emoji-picker__item"
        :class="{ 'is-selected': item.index === modelValue }"
        @click="selectEmoji(item.index)"
      >
        <img :src="item.imageUrl" :alt="`表情${item.index}`" class="emoji-picker__img" />
        <span class="emoji-picker__badge">{{ item.index }}</span>
      </button>
    </div>

    <div v-else-if="!loading" class="emoji-picker__empty">
      填写直播间 URL 后点击「从直播间加载表情」，只需抓取一次；之后打开页面会自动读取本地缓存。
    </div>
  </div>
</template>

<style scoped lang="scss">
.emoji-picker {
  width: 100%;
}

.emoji-picker__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 12px;
}

.emoji-picker__hint {
  margin-left: 12px;
  color: #6b7280;
  font-size: 13px;
}

.emoji-picker__grid {
  display: flex;
  flex-wrap: wrap;
  max-height: 280px;
  padding: 12px;
  overflow-y: auto;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f9fafb;
}

.emoji-picker__item {
  position: relative;
  width: 56px;
  height: 56px;
  margin-right: 8px;
  margin-bottom: 8px;
  padding: 4px;
  border: 2px solid transparent;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;

  &:hover {
    border-color: #93c5fd;
    box-shadow: 0 2px 8px rgb(59 130 246 / 12%);
  }

  &.is-selected {
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgb(37 99 235 / 20%);
  }
}

.emoji-picker__img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  pointer-events: none;
}

.emoji-picker__badge {
  position: absolute;
  top: 2px;
  right: 2px;
  min-width: 18px;
  padding: 0 4px;
  border-radius: 999px;
  background: rgb(17 24 39 / 72%);
  color: #fff;
  font-size: 10px;
  line-height: 18px;
  text-align: center;
}

.emoji-picker__empty {
  padding: 16px;
  border: 1px dashed #d1d5db;
  border-radius: 12px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}
</style>
