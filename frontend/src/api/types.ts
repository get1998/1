/**
 * 应用运行配置
 */
export interface AppConfig {
  /** 抖音直播间 URL */
  liveRoomUrl: string
  /** 评论发送间隔（秒） */
  intervalSeconds: number
  /** 截图存储目录 */
  screenshotDir: string
  /** 单次评论中同一表情的数量 */
  emojisPerSend: number
  /** 任务指定表情序号，整次任务固定发送第 N 个表情 */
  emojiIndex: number
  /** 是否在发评后截图 */
  screenshotEnabled: boolean
  /** 发评后等待评论出现再截图（秒） */
  screenshotWaitSeconds: number
  /** 是否写入 Excel 评论统计 */
  excelReportEnabled: boolean
  /** Excel 报表存储目录 */
  excelReportDir: string
  /** 是否启用结束时间自动停止 */
  endTimeEnabled: boolean
  /** 任务结束时间 */
  endTime: string
  /** 启动前等待登录秒数 */
  waitLoginSeconds: number
}

/**
 * 任务运行状态
 */
export interface TaskStatus {
  /** 是否运行中（已启动任务，含等待发送） */
  running: boolean
  /** 是否已进入直播间并就绪（可点「开始发送」） */
  ready: boolean
  /** 是否已开始发送评论 */
  sending: boolean
  /** 已发送次数 */
  sentCount: number
  /** 最近截图路径 */
  lastScreenshot: string
  /** 最近错误信息 */
  lastError: string
  /** Excel 统计文件路径 */
  excelReportPath: string
  /** 计划结束时间 */
  endTimeText: string
  /** 运行日志 */
  logs: string[]
}

/**
 * API 通用响应
 */
export interface ApiMessage {
  /** 响应消息 */
  message: string
}

/**
 * 表情目录项
 */
export interface EmojiCatalogItem {
  /** 表情序号，从 1 开始 */
  index: number
  /** 表情图片地址 */
  imageUrl: string
}

/**
 * 表情目录响应
 */
export interface EmojiCatalogResponse {
  /** 表情列表 */
  items: EmojiCatalogItem[]
  /** 表情总数 */
  total: number
}

/**
 * 抓取表情目录请求
 */
export interface EmojiCatalogRequest {
  /** 直播间 URL */
  liveRoomUrl: string
  /** 等待登录秒数 */
  waitLoginSeconds: number
}
