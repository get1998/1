import type { CommentPart } from '@/api/types'

/** 输入框中的表情占位，如 [表情3] */
const EMOJI_MARKER_RE = /\[表情(\d+)\]/g

/**
 * 清洗评论片段列表。
 * @param parts - 原始片段
 * @returns 有效片段
 */
export function normalizeCommentParts(parts: CommentPart[]): CommentPart[] {
  const result: CommentPart[] = []
  for (const part of parts) {
    if (part.type === 'text') {
      if (part.text === '') {
        continue
      }
      const last = result[result.length - 1]
      if (last?.type === 'text') {
        last.text = `${last.text}${part.text}`
      } else {
        result.push({ type: 'text', text: part.text })
      }
      continue
    }
    if (part.type === 'emoji' && part.index >= 1) {
      result.push({ type: 'emoji', index: part.index })
    }
  }
  return result
}

/**
 * 从旧版字段迁移为评论片段。
 * @param commentText - 评论文字
 * @param emojisPerSend - 表情数量
 * @param emojiIndex - 表情序号
 * @returns 片段列表
 */
export function migrateLegacyCommentParts(
  commentText: string,
  emojisPerSend: number,
  emojiIndex: number,
): CommentPart[] {
  const parts: CommentPart[] = []
  const text = commentText.trim()
  if (text) {
    parts.push({ type: 'text', text })
  }
  if (emojisPerSend >= 1 && emojiIndex >= 1) {
    for (let i = 0; i < emojisPerSend; i += 1) {
      parts.push({ type: 'emoji', index: emojiIndex })
    }
  }
  return parts
}

/**
 * 片段转输入框文本（表情显示为 [表情N]）。
 * @param parts - 评论片段
 * @returns 输入框文本
 */
export function partsToInputText(parts: CommentPart[]): string {
  return normalizeCommentParts(parts)
    .map((part) => (part.type === 'text' ? part.text : `[表情${part.index}]`))
    .join('')
}

/**
 * 输入框文本解析为片段（支持文字与 [表情N] 混排）。
 * @param input - 输入框文本
 * @returns 片段列表
 */
export function parseInputTextToParts(input: string): CommentPart[] {
  const parts: CommentPart[] = []
  const re = new RegExp(EMOJI_MARKER_RE.source, 'g')
  let lastIndex = 0
  let match: RegExpExecArray | null = re.exec(input)
  while (match !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', text: input.slice(lastIndex, match.index) })
    }
    parts.push({ type: 'emoji', index: Number(match[1]) })
    lastIndex = match.index + match[0].length
    match = re.exec(input)
  }
  if (lastIndex < input.length) {
    parts.push({ type: 'text', text: input.slice(lastIndex) })
  }
  return normalizeCommentParts(parts)
}

/**
 * 生成发送预览文案。
 * @param parts - 评论片段
 * @returns 预览文案
 */
export function formatCommentPartsPreview(parts: CommentPart[]): string {
  const text = partsToInputText(parts)
  return text || ''
}

/**
 * 是否包含可发送内容。
 * @param parts - 评论片段
 * @returns 是否非空
 */
export function hasCommentContent(parts: CommentPart[]): boolean {
  return normalizeCommentParts(parts).some((part) => {
    if (part.type === 'emoji') {
      return true
    }
    return part.text.trim().length > 0
  })
}
