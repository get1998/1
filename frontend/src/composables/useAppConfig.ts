import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchConfig, saveConfigApi } from '@/api'
import type { AppConfig, CommentPart } from '@/api/types'
import {
  formatCommentPartsPreview,
  hasCommentContent,
  migrateLegacyCommentParts,
  normalizeCommentParts,
} from '@/utils/commentParts'
import {
  buildExcelReportDir,
  buildLiveRoomUrl,
  buildScreenshotDir,
  buildVideoDir,
  extractLiveRoomId,
  normalizeAccountId,
} from '@/utils/liveRoom'

/**
 * 默认配置
 */
const DEFAULT_CONFIG: AppConfig = {
  douyinId: '',
  webRid: '',
  liveRoomUrl: '',
  intervalSeconds: 30,
  screenshotDir: './screenshots',
  commentParts: [],
  commentText: '',
  emojisPerSend: 0,
  emojiIndex: 1,
  screenshotEnabled: false,
  screenshotWaitSeconds: 3,
  videoRecordEnabled: true,
  videoDir: './videos',
  excelReportEnabled: true,
  excelReportDir: './reports',
  endTimeEnabled: false,
  endTime: '',
  waitLoginSeconds: 30,
}

/**
 * 更新截图/报表/录屏目录
 * @param form - 配置表单
 */
function updateStorageDirs(form: AppConfig): void {
  const storageKey = form.webRid || form.douyinId || extractLiveRoomId(form.liveRoomUrl)
  form.screenshotDir = buildScreenshotDir(storageKey)
  form.excelReportDir = buildExcelReportDir(storageKey)
  form.videoDir = buildVideoDir(storageKey)
}

/**
 * 同步直播间直达字段与存储目录（加载/保存时用）
 * @param form - 配置表单
 */
function syncLiveRoomFields(form: AppConfig): void {
  form.douyinId = normalizeAccountId(form.douyinId)
  const webRid = normalizeAccountId(form.webRid)
  if (webRid) {
    form.webRid = webRid
    form.liveRoomUrl = buildLiveRoomUrl(webRid)
  } else {
    form.webRid = ''
    // 保留单独填写的 URL，不从 URL 反填 webRid
    form.liveRoomUrl = form.liveRoomUrl.trim()
  }
  updateStorageDirs(form)
}

/**
 * 由 commentParts 同步兼容字段
 * @param form - 配置表单
 */
function syncLegacyFieldsFromParts(form: AppConfig): void {
  const parts = normalizeCommentParts(form.commentParts)
  form.commentText = parts
    .filter((part): part is Extract<CommentPart, { type: 'text' }> => part.type === 'text')
    .map((part) => part.text)
    .join('')
  const emojiIndices = parts
    .filter((part): part is Extract<CommentPart, { type: 'emoji' }> => part.type === 'emoji')
    .map((part) => part.index)
  form.emojisPerSend = emojiIndices.length
  form.emojiIndex = emojiIndices[0] ?? 1
}

/**
 * 配置表单与保存逻辑
 */
export function useAppConfig() {
  const form = reactive<AppConfig>({ ...DEFAULT_CONFIG, commentParts: [] })
  const loading = ref(false)
  const saving = ref(false)

  /** 发送预览 */
  const emojiSendPreview = computed((): string => {
    return formatCommentPartsPreview(form.commentParts)
  })

  /**
   * 构建提交配置
   * @param options - 构建选项
   * @param options.requireContent - 是否要求评论内容非空（启动任务时为 true）
   * @returns 完整配置对象
   */
  function buildPayload(options?: { requireContent?: boolean }): AppConfig {
    syncLiveRoomFields(form)
    syncLegacyFieldsFromParts(form)
    if (options?.requireContent) {
      if (!form.douyinId && !form.webRid && !form.liveRoomUrl) {
        throw new Error('请填写抖音号，或填写直播间号/URL')
      }
      if (!hasCommentContent(form.commentParts)) {
        throw new Error('请在评论输入框中输入文字或插入表情')
      }
    }
    return {
      ...form,
      commentParts: normalizeCommentParts(form.commentParts),
    }
  }

  /**
   * 加载配置
   */
  async function loadConfig(): Promise<void> {
    loading.value = true
    try {
      const data = await fetchConfig()
      const parts =
        data.commentParts && data.commentParts.length > 0
          ? normalizeCommentParts(data.commentParts)
          : migrateLegacyCommentParts(
              data.commentText ?? '',
              data.emojisPerSend ?? 0,
              data.emojiIndex ?? 1,
            )
      Object.assign(form, {
        douyinId: data.douyinId ?? '',
        webRid: data.webRid ?? '',
        liveRoomUrl: data.liveRoomUrl ?? '',
        intervalSeconds: data.intervalSeconds ?? 30,
        screenshotDir: data.screenshotDir ?? './screenshots',
        commentParts: parts,
        commentText: data.commentText ?? '',
        emojisPerSend: data.emojisPerSend ?? 0,
        emojiIndex: data.emojiIndex ?? 1,
        screenshotEnabled: data.screenshotEnabled ?? false,
        screenshotWaitSeconds: data.screenshotWaitSeconds ?? 3,
        videoRecordEnabled: data.videoRecordEnabled ?? true,
        videoDir: data.videoDir ?? './videos',
        excelReportEnabled: data.excelReportEnabled ?? true,
        excelReportDir: data.excelReportDir ?? './reports',
        endTimeEnabled: data.endTimeEnabled ?? false,
        endTime: data.endTime ?? '',
        waitLoginSeconds: data.waitLoginSeconds ?? 30,
      })
      syncLiveRoomFields(form)
      syncLegacyFieldsFromParts(form)
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '加载配置失败')
    } finally {
      loading.value = false
    }
  }

  /**
   * 保存配置
   * @returns 是否保存成功
   */
  async function saveConfig(): Promise<boolean> {
    saving.value = true
    try {
      const saved = await saveConfigApi(buildPayload())
      Object.assign(form, saved)
      if (!form.commentParts?.length) {
        form.commentParts = migrateLegacyCommentParts(
          form.commentText,
          form.emojisPerSend,
          form.emojiIndex,
        )
      }
      syncLiveRoomFields(form)
      syncLegacyFieldsFromParts(form)
      ElMessage.success('配置已保存')
      return true
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '保存配置失败')
      return false
    } finally {
      saving.value = false
    }
  }

  watch(
    () => form.webRid,
    (newValue, oldValue) => {
      const rid = normalizeAccountId(newValue)
      const prevRid = normalizeAccountId(oldValue ?? '')
      if (rid) {
        form.webRid = rid
        form.liveRoomUrl = buildLiveRoomUrl(rid)
      } else {
        form.webRid = ''
        const urlRid = extractLiveRoomId(form.liveRoomUrl)
        // 清空直播间号时，同步清掉由该号自动生成的 URL，避免又被反填回来
        if (prevRid && urlRid === prevRid) {
          form.liveRoomUrl = ''
        }
      }
      updateStorageDirs(form)
    },
  )

  watch(
    () => form.liveRoomUrl,
    () => {
      if (normalizeAccountId(form.webRid)) {
        return
      }
      form.liveRoomUrl = form.liveRoomUrl.trim()
      updateStorageDirs(form)
    },
  )

  watch(
    () => form.douyinId,
    () => {
      form.douyinId = normalizeAccountId(form.douyinId)
      updateStorageDirs(form)
    },
  )

  watch(
    () => form.commentParts,
    () => {
      syncLegacyFieldsFromParts(form)
    },
    { deep: true },
  )

  onMounted(() => {
    void loadConfig()
  })

  return {
    form,
    emojiSendPreview,
    loading,
    saving,
    buildPayload,
    loadConfig,
    saveConfig,
  }
}
