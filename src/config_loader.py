"""配置读写模块。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config" / "config.example.json"


class AppConfig(BaseModel):
    """应用运行配置。"""

    liveRoomUrl: str = Field(default="", description="抖音直播间 URL")
    intervalSeconds: int = Field(default=30, ge=5, description="评论发送间隔（秒）")
    screenshotDir: str = Field(default="./screenshots", description="截图存储目录")
    emojisPerSend: int = Field(
        default=3,
        ge=1,
        le=20,
        description="单次评论中同一表情的数量",
    )
    emojiIndex: int = Field(
        default=1,
        ge=1,
        le=100,
        description="任务指定表情序号，整次任务固定发送第 N 个表情",
    )
    screenshotEnabled: bool = Field(default=True, description="是否启用发评后截图")
    screenshotWaitSeconds: int = Field(
        default=3,
        ge=1,
        le=30,
        description="发评后等待评论出现在聊天区再截图（秒）",
    )
    excelReportEnabled: bool = Field(default=True, description="是否写入 Excel 评论统计")
    excelReportDir: str = Field(default="./reports", description="Excel 报表存储目录")
    endTimeEnabled: bool = Field(default=False, description="是否启用结束时间自动停止")
    endTime: str = Field(default="", description="任务结束时间，格式 YYYY-MM-DD HH:mm:ss")
    waitLoginSeconds: int = Field(default=30, ge=0, le=300, description="打开直播间后等待登录秒数")

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
            data["emojisPerSend"] = 3
        if "emojiIndex" not in data:
            data["emojiIndex"] = 1
        if "screenshotWaitSeconds" not in data:
            data["screenshotWaitSeconds"] = 3
        if "excelReportEnabled" not in data:
            data["excelReportEnabled"] = True
        if "excelReportDir" not in data:
            data["excelReportDir"] = "./reports"
        if "endTimeEnabled" not in data:
            data["endTimeEnabled"] = False
        if "endTime" not in data:
            data["endTime"] = ""
        return data

    def resolve_excel_report_dir(self) -> Path:
        """
        解析 Excel 报表目录绝对路径。

        @returns: 报表目录 Path
        """
        path = Path(self.excelReportDir)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

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
        解析截图目录绝对路径。

        @returns: 截图目录 Path
        """
        path = Path(self.screenshotDir)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path


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
