# 抖音直播间自动评论工具

基于 Python + Playwright 浏览器自动化的抖音直播间定时评论脚本，配套 **Vue 3** 配置页面，支持可视化设置直播间地址、评论间隔、截图存储路径，并在每次发送评论后自动截图留存。

## 功能特性

- **直播间自动评论**：通过浏览器打开抖音直播间，按设定间隔自动发送评论
- **Vue 3 配置页面**：Element Plus 表单，可视化配置与任务控制
- **评论截图**：每次发送评论后自动截取页面截图
- **页面录屏**：任务期间录制浏览器画面（webm），用于核对弹幕中是否出现自己的评论
- **双运行模式**：Web 配置页启动，或命令行直接运行
- **登录等待**：首次打开浏览器后可配置等待时间，便于手动登录

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+、FastAPI、Playwright |
| 前端 | Vue 3、TypeScript、Vite、Element Plus |
| 配置 | JSON 文件持久化 |

## 项目结构

```
评论/
├── README.md
├── requirements.txt
├── config/
│   └── config.example.json
├── config.json                    # 运行时配置（本地生成）
├── src/
│   ├── main.py                    # FastAPI 服务入口
│   ├── cli.py                     # 命令行直接运行脚本
│   ├── config_loader.py
│   ├── automation/
│   │   └── douyin_live.py         # 自动发评论核心脚本
│   └── screenshot/
│       └── capture.py
├── frontend/                      # Vue 3 前端工程
│   ├── src/
│   │   ├── App.vue
│   │   ├── api/
│   │   ├── composables/
│   │   └── components/
│   ├── package.json
│   └── vite.config.ts
├── screenshots/
└── videos/
```

## 配置项说明

| 配置项 | 字段名 | 说明 |
|--------|--------|------|
| 直播间 URL | `liveRoomUrl` | 抖音直播间完整链接 |
| 发送间隔 | `intervalSeconds` | 两次评论间隔（秒），最小 5 |
| 截图目录 | `screenshotDir` | 评论截图保存路径 |
| 评论内容 | `commentText` | 单条评论文案 |
| 评论列表 | `commentList` | 多条评论轮流发送（优先） |
| 发评后截图 | `screenshotEnabled` | 是否每次发评后截图 |
| 页面录屏 | `videoRecordEnabled` | 是否录制浏览器页面 |
| 录屏目录 | `videoDir` | 录屏保存路径（webm） |
| 等待登录 | `waitLoginSeconds` | 打开直播间后等待登录秒数 |

## 快速开始

### 1. 安装 Python 依赖

```powershell
Set-Location "D:\web\评论"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

### 2. 安装前端依赖

```powershell
Set-Location "D:\web\评论\frontend"
npm install
```

### 3. 开发模式（推荐）

**终端 1：启动 Python 后端**

```powershell
Set-Location "D:\web\评论"
python -m src.main
```

**终端 2：启动 Vue 3 开发服务器**

```powershell
Set-Location "D:\web\评论\frontend"
npm run dev
```

浏览器访问：**http://127.0.0.1:5173**（API 自动代理到 8765 端口）

### 4. 生产模式

```powershell
Set-Location "D:\web\评论\frontend"
npm run build

Set-Location "D:\web\评论"
python -m src.main
```

浏览器访问：**http://127.0.0.1:8765**

### 5. 命令行直接运行（无需 Web 页面）

```powershell
Set-Location "D:\web\评论"
Copy-Item "config\config.example.json" "config.json"
python -m src.cli --url "https://live.douyin.com/123456789" --interval 30 --comment "来了来了"
```

按 `Ctrl+C` 停止任务。

## 自动发评论脚本说明

核心逻辑位于 `src/automation/douyin_live.py`：

1. 使用 Playwright 持久化浏览器上下文（保留登录态）
2. 打开配置的直播间 URL
3. 等待指定秒数供用户手动登录
4. 循环执行：查找评论框 → 输入评论 → 点击发送/回车 → 截图保存
5. 按 `intervalSeconds` 间隔重复

支持多种评论输入框与发送按钮选择器，并会搜索 iframe 内元素；若抖音改版导致失败，可在该文件中追加选择器。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取配置 |
| POST | `/api/config` | 保存配置 |
| POST | `/api/task/start` | 启动任务 |
| POST | `/api/task/stop` | 停止任务 |
| GET | `/api/task/status` | 获取状态与日志 |

## 注意事项

1. **合规使用**：仅供学习研究，请遵守抖音平台规则。
2. **登录**：首次需在弹出的浏览器窗口手动登录抖音。
3. **发送频率**：建议间隔 ≥ 10 秒。
4. **页面改版**：若评论发不出去，查看运行日志并更新选择器。

## 许可证

仅供个人学习使用。
