import type { ApiMessage, AppConfig, EmojiCatalogRequest, EmojiCatalogResponse, TaskStatus } from './types'

const JSON_HEADERS = {
  'Content-Type': 'application/json',
}

/**
 * 解析接口错误信息
 * @param response - Fetch 响应对象
 * @returns 错误文案
 */
async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: string | Array<{ msg?: string }> }
    if (typeof data.detail === 'string') {
      return data.detail
    }
    if (Array.isArray(data.detail) && data.detail[0]?.msg) {
      return data.detail[0].msg
    }
  } catch {
    // ignore json parse error
  }
  return `请求失败 (${response.status})`
}

/**
 * 获取当前配置
 * @returns 应用配置
 */
export async function fetchConfig(): Promise<AppConfig> {
  const response = await fetch('/api/config')
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json() as Promise<AppConfig>
}

/**
 * 保存配置
 * @param config - 应用配置
 * @returns 保存后的配置
 */
export async function saveConfigApi(config: AppConfig): Promise<AppConfig> {
  const response = await fetch('/api/config', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(config),
  })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json() as Promise<AppConfig>
}

/**
 * 启动任务（打开直播间，不立即发评）
 * @param config - 当前配置（启动时一并保存）
 * @returns 操作结果
 */
export async function startTaskApi(config: AppConfig): Promise<ApiMessage> {
  const response = await fetch('/api/task/start', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(config),
  })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json() as Promise<ApiMessage>
}

/**
 * 开始发送评论（须在直播间就绪后调用，开启录屏时同步录制）
 * @returns 操作结果
 */
export async function beginSendApi(): Promise<ApiMessage> {
  const response = await fetch('/api/task/begin-send', { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json() as Promise<ApiMessage>
}

/**
 * 停止自动评论任务
 * @returns 操作结果
 */
export async function stopTaskApi(): Promise<ApiMessage> {
  const response = await fetch('/api/task/stop', { method: 'POST' })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json() as Promise<ApiMessage>
}

/**
 * 获取已缓存的表情目录
 * @returns 表情目录（未缓存时 total 为 0）
 */
export async function getEmojiCatalogApi(): Promise<EmojiCatalogResponse> {
  const response = await fetch('/api/emoji/catalog')
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json() as Promise<EmojiCatalogResponse>
}

/**
 * 从直播间抓取表情目录并更新缓存
 * @param params - 抓取参数
 * @returns 表情目录
 */
export async function fetchEmojiCatalogApi(
  params: EmojiCatalogRequest,
): Promise<EmojiCatalogResponse> {
  const response = await fetch('/api/emoji/catalog', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(params),
  })
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json() as Promise<EmojiCatalogResponse>
}

/**
 * 获取任务状态
 * @returns 任务状态
 */
export async function fetchTaskStatus(): Promise<TaskStatus> {
  const response = await fetch('/api/task/status')
  if (!response.ok) {
    throw new Error(await parseError(response))
  }
  return response.json() as Promise<TaskStatus>
}
