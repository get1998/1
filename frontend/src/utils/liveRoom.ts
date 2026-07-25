/**
 * 清洗抖音号 / 直播间号（去掉 @ 与空白）。
 * @param value - 原始值
 * @returns 清洗后的值
 */
export function normalizeAccountId(value: string): string {
  return value.trim().replace(/^@+/, '')
}

/**
 * 由直播间号生成直播间 URL。
 * @param webRid - live.douyin.com 路径后缀（web_rid）
 * @returns 直播间地址；为空时返回空字符串
 */
export function buildLiveRoomUrl(webRid: string): string {
  const id = normalizeAccountId(webRid)
  return id ? `https://live.douyin.com/${id}` : ''
}

/**
 * 从直播间 URL 提取末段直播间号（web_rid）。
 * @param url - 直播间地址
 * @returns web_rid；无法解析时返回空字符串
 */
export function extractLiveRoomId(url: string): string {
  const trimmed = url.trim()
  if (!trimmed) {
    return ''
  }
  try {
    const parsed = new URL(trimmed)
    const parts = parsed.pathname.split('/').filter(Boolean)
    return parts[parts.length - 1] ?? ''
  } catch {
    const withoutQuery = trimmed.split(/[?#]/)[0] ?? ''
    const parts = withoutQuery.split('/').filter(Boolean)
    return parts[parts.length - 1] ?? ''
  }
}

/**
 * 按抖音号或直播间号生成截图目录。
 * @param key - 目录标识
 * @returns 相对目录路径
 */
export function buildScreenshotDir(key: string): string {
  return key ? `./screenshots/${key}` : './screenshots'
}

/**
 * 按抖音号或直播间号生成 Excel 报表目录。
 * @param key - 目录标识
 * @returns 相对目录路径
 */
export function buildExcelReportDir(key: string): string {
  return key ? `./reports/${key}` : './reports'
}
