<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchEmojiCatalogApi, getEmojiCatalogApi } from '@/api'
import type { EmojiCatalogItem } from '@/api/types'

/** 表情选择器：展示抖音直播间表情；支持单选或插入模式 */
const props = withDefaults(
  defineProps<{
    /** 当前选中的表情序号（单选模式） */
    modelValue?: number
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
    /** 插入模式：点击表情触发 pick，不强制单选 */
    insertMode?: boolean
    /** 紧凑模式 */
    compact?: boolean
  }>(),
  {
    modelValue: 0,
    douyinId: '',
    webRid: '',
    liveRoomUrl: '',
    insertMode: false,
    compact: false,
  },
)

const emit = defineEmits<{
  /** 更新选中表情序号 */
  'update:modelValue': [value: number]
  /** 点击表情（插入模式） */
  pick: [index: number]
  /** 表情目录加载完成 */
  catalogLoaded: [items: EmojiCatalogItem[]]
}>()

const loading = ref(false)
const refreshing = ref(false)
const items = ref<EmojiCatalogItem[]>([])
const lastPicked = ref(0)

/** 当前高亮序号 */
const highlightIndex = computed((): number => {
  if (props.insertMode) {
    return lastPicked.value || props.modelValue
  }
  return props.modelValue
})

/** 当前选中项 */
const selectedItem = computed((): EmojiCatalogItem | undefined => {
  return items.value.find((item) => item.index === highlightIndex.value)
})

/** 是否已有缓存的表情目录 */
const hasCachedCatalog = computed((): boolean => items.value.length > 0)

/**
 * 应用表情目录数据
 * @param catalogItems - 表情列表
 */
function applyCatalog(catalogItems: EmojiCatalogItem[]): void {
  items.value = catalogItems
  emit('catalogLoaded', catalogItems)
  if (
    !props.insertMode &&
    catalogItems.length > 0 &&
    props.modelValue > 0 &&
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
  if (!props.douyinId && !props.webRid && !props.liveRoomUrl?.trim()) {
    ElMessage.warning('请先填写抖音号，或填写直播间号/URL')
    return
  }
  if (props.running) {
    ElMessage.warning('任务运行中，请先停止任务再加载表情')
    return
  }

  refreshing.value = true
  try {
    const data = await fetchEmojiCatalogApi({
      douyinId: props.douyinId,
      webRid: props.webRid,
      liveRoomUrl: props.liveRoomUrl,
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
 * 选择 / 插入表情
 * @param index - 表情序号
 */
function selectEmoji(index: number): void {
  lastPicked.value = index
  if (!props.insertMode) {
    emit('update:modelValue', index)
  }
  emit('pick', index)
}

watch(
  () => props.modelValue,
  (value) => {
    if (value > 0) {
      lastPicked.value = value
    }
  },
)

onMounted(() => {
  void loadCachedCatalog()
})
</script>

<template>
  <div class="emoji-picker" :class="{ 'emoji-picker--compact': compact }">
    <div class="emoji-picker__toolbar">
      <el-button
        type="primary"
        plain
        :size="compact ? 'small' : 'default'"
        :loading="refreshing"
        :disabled="running || loading"
        @click="refreshEmojis"
      >
        {{ hasCachedCatalog ? '刷新表情' : '加载表情' }}
      </el-button>
      <span v-if="insertMode && !compact" class="emoji-picker__hint">
        点击表情插入到上方输入框光标处
      </span>
      <span v-else-if="selectedItem" class="emoji-picker__hint">
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
        :key="`${item.index}-${item.imageUrl}`"
        type="button"
        class="emoji-picker__item"
        :class="{ 'is-selected': item.index === highlightIndex }"
        @click="selectEmoji(item.index)"
      >
        <img :src="item.imageUrl" :alt="`表情${item.index}`" class="emoji-picker__img" />
        <span class="emoji-picker__badge">{{ item.index }}</span>
      </button>
    </div>

    <div v-else-if="!loading && !compact" class="emoji-picker__empty">
      填写抖音号（或直播间号）后点击「从直播间加载表情」，只需抓取一次；之后打开页面会自动读取本地缓存。
    </div>
    <div v-else-if="!loading && compact" class="emoji-picker__empty emoji-picker__empty--compact">
      填写抖音号后点击「加载表情」
    </div>
  </div>
</template>

<style scoped lang="scss">
.emoji-picker {
  width: 100%;

  &--compact {
    .emoji-picker__toolbar {
      margin-bottom: 8px;
    }

    .emoji-picker__grid {
      max-height: 140px;
      padding: 8px;
    }

    .emoji-picker__item {
      width: 40px;
      height: 40px;
      margin-right: 6px;
      margin-bottom: 6px;
    }

    .emoji-picker__empty--compact {
      padding: 10px;
      font-size: 12px;
    }
  }
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
