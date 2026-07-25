import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { beginSendApi, fetchTaskStatus, startTaskApi, stopTaskApi } from '@/api'
import type { AppConfig, TaskStatus } from '@/api/types'

/**
 * 任务控制与状态轮询
 * @param getConfig - 获取当前表单配置
 */
export function useTaskControl(getConfig: () => AppConfig) {
  const status = reactive<TaskStatus>({
    running: false,
    ready: false,
    sending: false,
    recording: false,
    sentCount: 0,
    lastScreenshot: '',
    lastVideo: '',
    lastError: '',
    excelReportPath: '',
    endTimeText: '',
    logs: [],
  })
  const starting = ref(false)
  const beginningSend = ref(false)
  const stopping = ref(false)
  let pollTimer: number | undefined

  /**
   * 拉取任务状态
   */
  async function refreshStatus(): Promise<void> {
    try {
      const data = await fetchTaskStatus()
      Object.assign(status, data)
    } catch {
      // 轮询失败时静默忽略
    }
  }

  /**
   * 启动任务（打开直播间，等待「开始发送」）
   */
  async function startTask(): Promise<void> {
    starting.value = true
    try {
      await startTaskApi(getConfig())
      ElMessage.success('任务已启动，进入直播间后点击「开始发送」')
      await refreshStatus()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '启动任务失败')
    } finally {
      starting.value = false
    }
  }

  /**
   * 开始发送评论（同步开始录屏）
   */
  async function beginSend(): Promise<void> {
    beginningSend.value = true
    try {
      await beginSendApi()
      ElMessage.success('已开始发送')
      await refreshStatus()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '开始发送失败')
    } finally {
      beginningSend.value = false
    }
  }

  /**
   * 停止任务
   */
  async function stopTask(): Promise<void> {
    stopping.value = true
    try {
      await stopTaskApi()
      ElMessage.success('任务已停止')
      await refreshStatus()
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '停止任务失败')
    } finally {
      stopping.value = false
    }
  }

  onMounted(() => {
    void refreshStatus()
    pollTimer = window.setInterval(() => {
      void refreshStatus()
    }, 2000)
  })

  onUnmounted(() => {
    if (pollTimer) {
      window.clearInterval(pollTimer)
    }
  })

  return {
    status,
    starting,
    beginningSend,
    stopping,
    startTask,
    beginSend,
    stopTask,
    refreshStatus,
  }
}
