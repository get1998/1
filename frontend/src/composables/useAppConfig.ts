import { computed, onMounted, reactive, ref } from 'vue'

import { ElMessage } from 'element-plus'

import { fetchConfig, saveConfigApi } from '@/api'

import type { AppConfig } from '@/api/types'



/** 可选的单次表情数量 */

export const EMOJI_PER_SEND_PRESETS = [1, 2, 3, 4, 5, 6, 8, 10] as const



/** 可选的任务指定表情序号 */

export const EMOJI_INDEX_PRESETS = [1, 2, 3, 4, 5, 6, 8, 10] as const



/**

 * 默认配置

 */

const DEFAULT_CONFIG: AppConfig = {

  liveRoomUrl: '',

  intervalSeconds: 30,

  screenshotDir: './screenshots',

  emojisPerSend: 3,

  emojiIndex: 1,

  screenshotEnabled: true,

  screenshotWaitSeconds: 3,

  excelReportEnabled: true,

  excelReportDir: './reports',

  endTimeEnabled: false,

  endTime: '',

  waitLoginSeconds: 30,

}



/**

 * 配置表单与保存逻辑

 */

export function useAppConfig() {

  const form = reactive<AppConfig>({ ...DEFAULT_CONFIG })

  const loading = ref(false)

  const saving = ref(false)



  /** 发送预览 */

  const emojiSendPreview = computed((): string => {

    return `整次任务固定发送：第 ${form.emojiIndex} 个表情 × ${form.emojisPerSend} 个/次`

  })



  /** 单次表情数说明 */

  const emojiQuantityText = computed((): string => {

    return `单次评论只发 1 种表情，每种连续发 ${form.emojisPerSend} 个后发送`

  })



  /** 指定表情说明 */

  const emojiIndexText = computed((): string => {

    return `点击表情图选择；任务运行期间始终发送第 ${form.emojiIndex} 个表情，每种连续发 ${form.emojisPerSend} 个`

  })



  /**

   * 构建提交配置

   * @returns 完整配置对象

   */

  function buildPayload(): AppConfig {

    return { ...form }

  }



  /**

   * 加载配置

   */

  async function loadConfig(): Promise<void> {

    loading.value = true

    try {

      const data = await fetchConfig()

      Object.assign(form, {

        liveRoomUrl: data.liveRoomUrl ?? '',

        intervalSeconds: data.intervalSeconds ?? 30,

        screenshotDir: data.screenshotDir ?? './screenshots',

        emojisPerSend: data.emojisPerSend ?? 3,

        emojiIndex: data.emojiIndex ?? 1,

        screenshotEnabled: data.screenshotEnabled ?? true,

        screenshotWaitSeconds: data.screenshotWaitSeconds ?? 3,

        excelReportEnabled: data.excelReportEnabled ?? true,

        excelReportDir: data.excelReportDir ?? './reports',

        endTimeEnabled: data.endTimeEnabled ?? false,

        endTime: data.endTime ?? '',

        waitLoginSeconds: data.waitLoginSeconds ?? 30,

      })

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

      ElMessage.success('配置已保存')

      return true

    } catch (error) {

      ElMessage.error(error instanceof Error ? error.message : '保存配置失败')

      return false

    } finally {

      saving.value = false

    }

  }



  onMounted(() => {

    void loadConfig()

  })



  return {

    form,

    emojiSendPreview,

    emojiQuantityText,

    emojiIndexText,

    loading,

    saving,

    buildPayload,

    loadConfig,

    saveConfig,

  }

}

