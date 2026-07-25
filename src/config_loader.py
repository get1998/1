"""配置读写模块。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config" / "config.example.json"


def normalize_account_id(value: str) -> str:
    """
    清洗抖音号 / 直播间号。

    @param value: 原始值
    @returns: 去掉空白与前缀 @ 后的值
    """
    return value.strip().lstrip("@")


def normalize_web_rid(value: str) -> str:
    """
    清洗直播间号（web_rid）。

    @param value: 原始直播间号
    @returns: 去掉空白与前缀 @ 后的直播间号
    """
    return normalize_account_id(value)


def build_live_room_url(web_rid: str) -> str:
    """
    由直播间号生成直播间 URL。

    @param web_rid: live.douyin.com 路径后缀（web_rid）
    @returns: https://live.douyin.com/{web_rid}
    """
    cleaned = normalize_web_rid(web_rid)
    if not cleaned:
        return ""
    return f"https://live.douyin.com/{cleaned}"


def extract_live_room_id(url: str) -> str:
    """
    从直播间 URL 提取末段直播间号（web_rid）。

    @param url: 直播间地址，如 https://live.douyin.com/421527298234
    @returns: web_rid；无法解析时返回空字符串
    """
    trimmed = url.strip()
    if not trimmed:
        return ""
    parsed = urlparse(trimmed)
    parts = [part for part in parsed.path.split("/") if part]
    if parts:
        return parts[-1]
    # 兜底：非标准 URL 时按斜杠拆分
    fallback = trimmed.split("?", 1)[0].split("#", 1)[0]
    parts = [part for part in fallback.split("/") if part]
    return parts[-1] if parts else ""


class CommentPart(BaseModel):
    """评论片段：文字或表情，可自由穿插。"""

    type: Literal["text", "emoji"] = Field(description="片段类型")
    text: str = Field(default="", description="文字内容（type=text）")
    index: int = Field(default=1, ge=1, le=100, description="表情序号（type=emoji）")


def normalize_comment_parts(parts: list[CommentPart]) -> list[CommentPart]:
    """
    清洗评论片段：合并相邻文字、去除空片段。

    @param parts: 原始片段
    @returns: 清洗后的片段
    """
    result: list[CommentPart] = []
    for part in parts:
        if part.type == "text":
            text = part.text.strip()
            if not text:
                continue
            if result and result[-1].type == "text":
                result[-1] = CommentPart(type="text", text=f"{result[-1].text}{text}")
            else:
                result.append(CommentPart(type="text", text=text))
            continue
        if part.type == "emoji" and part.index >= 1:
            result.append(CommentPart(type="emoji", index=part.index))
    return result


def build_parts_from_legacy(
    comment_text: str,
    emojis_per_send: int,
    emoji_index: int,
) -> list[CommentPart]:
    """
    从旧版字段生成评论片段。

    @param comment_text: 评论文字
    @param emojis_per_send: 表情数量
    @param emoji_index: 表情序号
    @returns: 片段列表
    """
    parts: list[CommentPart] = []
    text = comment_text.strip()
    if text:
        parts.append(CommentPart(type="text", text=text))
    if emojis_per_send >= 1 and emoji_index >= 1:
        for _ in range(emojis_per_send):
            parts.append(CommentPart(type="emoji", index=emoji_index))
    return parts


def format_comment_parts_preview(parts: list[CommentPart]) -> str:
    """
    生成评论预览文案。

    @param parts: 评论片段
    @returns: 预览字符串
    """
    normalized = normalize_comment_parts(parts)
    if not normalized:
        return ""
    chunks: list[str] = []
    for part in normalized:
        if part.type == "text":
            chunks.append(part.text)
        else:
            chunks.append(f"[表情{part.index}]")
    return "".join(chunks)


class AppConfig(BaseModel):
    """应用运行配置。"""

    douyinId: str = Field(
        default="",
        description="主播抖音号；未配置直播间号/URL 时，自动搜索并进入直播间",
    )
    webRid: str = Field(
        default="",
        description="可选。直播间号 web_rid（live.douyin.com/ 后缀），填写后直接打开",
    )
    liveRoomUrl: str = Field(
        default="",
        description="可选。直播间 URL；有值时优先直接打开，无需搜索",
    )
    intervalSeconds: int = Field(default=30, ge=5, description="评论发送间隔（秒）")
    screenshotDir: str = Field(default="./screenshots", description="截图存储目录")
    commentParts: list[CommentPart] = Field(
        default_factory=list,
        description="评论内容片段（文字与表情自由组合，按顺序发送）",
    )
    commentText: str = Field(
        default="",
        max_length=500,
        description="评论文字（兼容旧配置，由 commentParts 同步）",
    )
    emojisPerSend: int = Field(
        default=0,
        ge=0,
        le=50,
        description="表情数量（兼容旧配置，由 commentParts 同步）",
    )
    emojiIndex: int = Field(
        default=1,
        ge=1,
        le=100,
        description="表情序号（兼容旧配置，由 commentParts 同步）",
    )
    screenshotEnabled: bool = Field(default=True, description="是否启用发评后截图")
    screenshotWaitSeconds: int = Field(
        default=3,
        ge=1,
        le=30,
        description="发评后等待评论出现在聊天区再截图（秒）",
    )
    videoRecordEnabled: bool = Field(
        default=True,
        description="是否录制浏览器页面（用于证明评论出现在弹幕/聊天区）",
    )
    videoDir: str = Field(default="./videos", description="录屏存储目录")
    excelReportEnabled: bool = Field(default=True, description="是否写入 Excel 评论统计")
    excelReportDir: str = Field(default="./reports", description="Excel 报表存储目录")
    endTimeEnabled: bool = Field(default=False, description="是否启用结束时间自动停止")
    endTime: str = Field(default="", description="任务结束时间，格式 YYYY-MM-DD HH:mm:ss")
    waitLoginSeconds: int = Field(default=30, ge=0, le=300, description="打开直播间后等待登录秒数")

    @field_validator("douyinId")
    @classmethod
    def validate_douyin_id(cls, value: str) -> str:
        """清洗抖音号。"""
        return normalize_account_id(value)

    @field_validator("webRid")
    @classmethod
    def validate_web_rid(cls, value: str) -> str:
        """清洗直播间号。"""
        return normalize_web_rid(value)

    @field_validator("liveRoomUrl")
    @classmethod
    def validate_live_room_url(cls, value: str) -> str:
        """校验直播间 URL 格式。"""
        trimmed = value.strip()
        if trimmed and "douyin.com" not in trimmed:
            raise ValueError("直播间 URL 需包含 douyin.com")
        return trimmed

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_fields(cls, data: Any) -> Any:
        """兼容旧版配置字段。"""
        if not isinstance(data, dict):
            return data
        if "emojisPerSend" not in data and "emojiPackCount" in data:
            data["emojisPerSend"] = data["emojiPackCount"]
        if "emojisPerSend" not in data:
            data["emojisPerSend"] = 0
        if "emojiIndex" not in data:
            data["emojiIndex"] = 1
        if "commentText" not in data:
            legacy_text = data.get("comment") or ""
            if not legacy_text and isinstance(data.get("commentList"), list):
                items = [str(item).strip() for item in data["commentList"] if str(item).strip()]
                legacy_text = items[0] if items else ""
            data["commentText"] = str(legacy_text or "")
        if "commentParts" not in data or not data.get("commentParts"):
            data["commentParts"] = [
                part.model_dump()
                for part in build_parts_from_legacy(
                    str(data.get("commentText") or ""),
                    int(data.get("emojisPerSend") or 0),
                    int(data.get("emojiIndex") or 1),
                )
            ]
        if "douyinId" not in data:
            data["douyinId"] = ""
        if "webRid" not in data or not str(data.get("webRid") or "").strip():
            # 仅当已有完整直播间 URL 时，从 URL 回填 webRid；不要把抖音号误当 webRid
            data["webRid"] = extract_live_room_id(str(data.get("liveRoomUrl") or ""))
        if "screenshotWaitSeconds" not in data:
            data["screenshotWaitSeconds"] = 3
        if "excelReportEnabled" not in data:
            data["excelReportEnabled"] = True
        if "excelReportDir" not in data:
            data["excelReportDir"] = "./reports"
        if "videoRecordEnabled" not in data:
            data["videoRecordEnabled"] = True
        if "videoDir" not in data:
            data["videoDir"] = "./videos"
        if "endTimeEnabled" not in data:
            data["endTimeEnabled"] = False
        if "endTime" not in data:
            data["endTime"] = ""
        return data

    @model_validator(mode="after")
    def sync_derived_fields(self) -> AppConfig:
        """
        同步直播间号、URL、目录与兼容字段。

        注意：有抖音号但无 webRid 时，不自动伪造 liveRoomUrl（应走搜索进房）。

        @returns: 同步后的配置
        """
        self.douyinId = normalize_account_id(self.douyinId)
        web_rid = normalize_web_rid(self.webRid)
        url_rid = extract_live_room_id(self.liveRoomUrl)

        if web_rid:
            self.webRid = web_rid
            self.liveRoomUrl = build_live_room_url(web_rid)
        elif url_rid:
            self.webRid = url_rid
            self.liveRoomUrl = build_live_room_url(url_rid)
        else:
            self.webRid = ""
            # 仅抖音号模式：清空直达 URL，避免误当成房间号打开
            if self.douyinId:
                self.liveRoomUrl = ""

        storage_key = self.webRid or self.douyinId or extract_live_room_id(self.liveRoomUrl)
        if storage_key:
            self.screenshotDir = f"./screenshots/{storage_key}"
            self.excelReportDir = f"./reports/{storage_key}"
            self.videoDir = f"./videos/{storage_key}"

        self.commentParts = normalize_comment_parts(self.commentParts)
        texts = [part.text for part in self.commentParts if part.type == "text"]
        emoji_indices = [part.index for part in self.commentParts if part.type == "emoji"]
        self.commentText = "".join(texts)
        self.emojisPerSend = len(emoji_indices)
        self.emojiIndex = emoji_indices[0] if emoji_indices else 1
        return self

    def resolve_live_room_url(self) -> str:
        """
        解析可直接打开的直播间 URL。

        仅当配置了 webRid / liveRoomUrl 时返回；仅抖音号时返回空，走搜索进房。

        @returns: 直播间完整 URL，或空字符串
        """
        if self.webRid:
            return build_live_room_url(self.webRid)
        url = self.liveRoomUrl.strip()
        if url and extract_live_room_id(url):
            return url
        return ""

    def has_entry_target(self) -> bool:
        """
        是否具备进房目标（抖音号或直达地址）。

        @returns: 可进房时为 True
        """
        return bool(self.douyinId or self.resolve_live_room_url())

    def resolved_comment_parts(self) -> list[CommentPart]:
        """
        获取可发送的评论片段。

        @returns: 清洗后的片段列表
        """
        parts = normalize_comment_parts(self.commentParts)
        if parts:
            return parts
        return build_parts_from_legacy(self.commentText, self.emojisPerSend, self.emojiIndex)

    def comment_preview(self) -> str:
        """
        评论内容预览。

        @returns: 预览字符串
        """
        return format_comment_parts_preview(self.resolved_comment_parts())

    def has_comment_content(self) -> bool:
        """
        是否配置了可发送内容。

        @returns: 有内容时为 True
        """
        return len(self.resolved_comment_parts()) > 0

    def resolve_storage_subdir(self, base_name: str, configured: str) -> Path:
        """
        按直播间 URL 末段解析存储子目录。

        @param base_name: 根目录名，如 screenshots / reports
        @param configured: 配置中的目录（无房间号时作为回退）
        @returns: 绝对路径
        """
        room_id = self.webRid or self.douyinId or extract_live_room_id(self.liveRoomUrl)
        if room_id:
            path = PROJECT_ROOT / base_name / room_id
        else:
            path = Path(configured)
            if not path.is_absolute():
                path = PROJECT_ROOT / path
        return path

    def resolve_excel_report_dir(self) -> Path:
        """
        解析 Excel 报表目录绝对路径（优先使用 URL 房间号子目录）。

        @returns: 报表目录 Path
        """
        return self.resolve_storage_subdir("reports", self.excelReportDir)

    def resolve_end_time(self) -> datetime | None:
        """
        解析任务结束时间。

        @returns: 结束时间，未启用或未配置时返回 None
        """
        if not self.endTimeEnabled or not self.endTime.strip():
            return None
        raw = self.endTime.strip().replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        raise ValueError("结束时间格式无效，请使用 YYYY-MM-DD HH:mm:ss")

    def resolve_screenshot_dir(self) -> Path:
        """
        解析截图目录绝对路径（优先使用 URL 房间号子目录）。

        @returns: 截图目录 Path
        """
        return self.resolve_storage_subdir("screenshots", self.screenshotDir)

    def resolve_video_dir(self) -> Path:
        """
        解析录屏目录绝对路径（优先使用房间号/抖音号子目录）。

        @returns: 录屏目录 Path
        """
        return self.resolve_storage_subdir("videos", self.videoDir)


def load_config(config_path: Path | None = None) -> AppConfig:
    """
    从 JSON 文件加载配置。

    @param config_path: 配置文件路径，默认项目根目录 config.json
    @returns: 应用配置对象
    """
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        if EXAMPLE_CONFIG_PATH.exists():
            return AppConfig.model_validate_json(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"))
        return AppConfig()

    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return AppConfig.model_validate(data)


def save_config(config: AppConfig, config_path: Path | None = None) -> None:
    """
    保存配置到 JSON 文件。

    @param config: 应用配置对象
    @param config_path: 配置文件路径，默认项目根目录 config.json
    """
    path = config_path or DEFAULT_CONFIG_PATH
    path.write_text(
        json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
