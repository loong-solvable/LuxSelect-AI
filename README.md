# LuxSelect - 系统级 AI 划词助手

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey.svg)

**LuxSelect** 是一款生产级的桌面端 AI 辅助工具。它允许用户在操作系统内的**任意应用程序**（如 IDE、浏览器、PDF 阅读器等）中选中文本，并自动弹出一个悬浮窗显示 AI 对该文本的解释、翻译或重构建议。

**告别频繁切换应用，让 AI 助手随时随地为您服务！**

[快速开始](#-快速开始) • [功能特性](#-核心特性) • [使用指南](#-使用指南) • [开发文档](#-开发与测试)

</div>

---

## ✨ 核心特性

### 🌐 全局划词支持
基于底层鼠标事件监听，支持在**任何桌面应用**中工作，无需安装插件或扩展。

### ⚡ 无缝 AI 交互
- **即选即显**：松开鼠标即触发 AI 分析
- **流式响应**：实时显示 AI 回复，降低等待感知
- **智能定位**：悬浮窗自动出现在光标附近，不遮挡内容

### 🛡️ 生产级稳定性
- **剪贴板保护**：自动备份并恢复原有剪贴板内容，操作对用户完全透明
- **防御性编程**：完善的错误处理机制，防止网络波动或系统权限导致的应用崩溃
- **单实例运行**：防止多进程冲突，确保系统资源占用最小化

### 🔒 隐私安全
内置隐私过滤器，自动检测并拦截包含敏感信息（如信用卡号、密码、API Key）的请求，保护您的数据安全。

### 🎨 现代 UI 设计
- 基于 PyQt6 开发的无边框悬浮窗
- 支持 Markdown 渲染和代码高亮
- 简洁明快的配色方案，符合现代审美
- 动态尺寸自适应，内容多少自动调整窗口大小

### 🔌 多 AI 服务商支持
兼容 OpenAI、DeepSeek、智谱 AI 等多家 LLM 服务商，只需修改配置即可切换。

## 🛠️ 技术栈

*   **语言**: Python 3.10+
*   **GUI**: PyQt6 (无边框窗口, 总是置顶)
*   **系统钩子**: `pynput` (鼠标监听), `pyautogui` (快捷键模拟), `pyperclip` (剪贴板操作)
*   **AI 客户端**: OpenAI SDK (支持流式响应)
*   **配置管理**: Pydantic Settings
*   **测试**: Pytest, Unittest Mock

## 🚀 快速开始

### 1. 环境要求

*   **操作系统**：
    - ✅ Windows 10/11（已充分测试）
    - ✅ macOS 10.14+（理论兼容，需要配置权限）
    - ⚠️ Linux（未测试，但理论上可运行）
*   **Python 版本**：Python 3.10 或更高版本
*   **macOS 特别说明**：需要授予"辅助功能"权限（详见下方配置步骤）

### 2. 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/YOUR-USERNAME/luxselect.git
cd luxselect

# 2. 创建虚拟环境 (推荐)
python -m venv venv

# 3. 激活虚拟环境
# Windows (PowerShell):
.\venv\Scripts\Activate
# macOS/Linux:
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt
```

### 3. 配置 API 密钥

在**项目根目录**创建 `.env` 文件：

```bash
# 复制示例配置文件
cp .env.example .env

# 使用您喜欢的编辑器打开 .env 文件
notepad .env  # Windows
# nano .env   # macOS/Linux
```

**配置示例（三选一）**：

<details>
<summary><b>选项 1: OpenAI 官方</b></summary>

```ini
OPENAI_API_KEY=sk-your-openai-key
OPENAI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-3.5-turbo
DEBUG=False
```

</details>

<details>
<summary><b>选项 2: DeepSeek (深度求索)</b></summary>

```ini
OPENAI_API_KEY=sk-your-deepseek-key
OPENAI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-chat
DEBUG=False
```

</details>

<details>
<summary><b>选项 3: Zhipu AI (智谱清言)</b></summary>

```ini
OPENAI_API_KEY=your.zhipu.api.key  # 格式通常为 id.secret
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
AI_MODEL=glm-4
DEBUG=False
```

</details>

> **⚠️ 重要提示**：
> - `.env` 文件应放在**项目根目录**（与 `src` 文件夹同级）
> - 请勿将 `.env` 文件提交到 Git 仓库（已在 `.gitignore` 中排除）
> - 获取 API Key：[OpenAI](https://platform.openai.com/api-keys) | [DeepSeek](https://platform.deepseek.com/) | [智谱AI](https://open.bigmodel.cn/)

### 4. macOS 权限配置（仅 macOS 用户）

**系统偏好设置** → **安全性与隐私** → **隐私** → **辅助功能** → 添加 Terminal.app 或 Python 解释器

> 💡 如不授予权限，程序无法监听全局鼠标事件。

### 5. 运行应用

```bash
# 使用模块方式启动
python -m src.main

# macOS 用户首次运行可能会看到权限请求弹窗，请点击"允许"
```

## 📖 使用指南

### 基本操作

1. **启动程序**
   ```bash
   python -m src.main
   ```
   程序将在后台静默运行，不会显示主窗口。

2. **选中文本**
   - 在任意应用程序中（VS Code、Chrome、PDF 阅读器等）
   - 使用鼠标**左键拖拽**选中文本
   - 松开鼠标左键

3. **查看 AI 解释**
   - 悬浮窗会自动出现在光标附近
   - 实时显示 AI 对选中文本的解释
   - 支持 Markdown 格式和代码高亮

4. **关闭悬浮窗**
   - 点击悬浮窗以外的任意区域
   - 或等待自动超时关闭

### 使用场景示例

| 场景 | 选中内容 | AI 回复示例 |
|------|---------|------------|
| 📚 阅读文言文 | "左司马" | **左司马**：古代官职名称，指辅佐司马的副职... |
| 💻 技术文档 | "PyQt6 signals" | **PyQt6 信号（Signals）**：Qt 框架中的事件通知机制... |
| 🌍 地理知识 | "大别山" | **大别山**：位于中国湖北、河南、安徽三省交界处... |
| 🔧 Shell 命令 | "chmod +x" | **chmod +x**：Linux 命令，用于为文件添加可执行权限... |

### 常见问题

| 问题 | 解决方法 |
|------|---------|
| 选中文本无反应 | 检查 API Key 配置、网络连接、文本长度（需 > 2 字符） |
| 如何停止程序 | 在终端按 `Ctrl+C` |
| 是否记录数据 | 不会，所有数据仅在内存中临时处理 |
| 游戏中使用 | 不建议，可能影响游戏体验 |
| macOS 权限错误 | 在"系统偏好设置"中授予"辅助功能"权限 |

## 🧪 开发与测试

### 运行单元测试

本项目包含完整的单元测试套件，使用 Mock 隔离外部依赖。

```bash
# 运行所有测试
pytest tests -v

# 运行特定测试文件
pytest tests/test_text_extractor.py -v

# 运行带覆盖率报告的测试
pytest tests --cov=src --cov-report=html
```

### 运行真实 API 测试

如果您想测试真实的 AI API 响应（需要消耗 API 配额）：

```bash
python scripts/run_live_test.py
```

### 代码规范检查

```bash
# 安装开发依赖
pip install flake8 black mypy

# 代码格式化
black src/

# 类型检查
mypy src

# 代码风格检查
flake8 src --max-line-length=100
```

## 📂 项目结构

```text
luxselect/
├── src/                     # 源代码
│   ├── core/                # 核心逻辑（AI、事件监听、文本提取）
│   │   ├── ai_client.py     # AI 客户端（流式响应）
│   │   ├── event_monitor.py # 全局事件监听器
│   │   └── text_extractor.py # 文本提取器
│   ├── ui/                  # PyQt6 界面
│   │   └── overlay_window.py # 悬浮窗组件
│   ├── utils/               # 工具
│   │   ├── logger.py        # 日志工具
│   │   └── privacy.py       # 隐私过滤器
│   ├── config.py            # 配置管理
│   └── main.py              # 应用入口
├── tests/                   # 单元测试
│   ├── test_ai_client.py
│   ├── test_ai_scenarios.py
│   └── test_text_extractor.py
├── scripts/                 # 辅助脚本
│   └── run_live_test.py     # 真实 API 测试
├── docs/                    # 文档
│   └── 扩展查询手完整指南.md
├── requirements.txt         # 依赖列表
├── .env.example             # 配置示例
├── .gitignore               # Git 忽略文件
├── LICENSE                  # MIT 许可证
└── README.md                # 项目文档
```

## 🚀 进阶功能

### 打包为可执行文件

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name LuxSelect src/main.py
```

### 开机自启动

- **Windows**：`Win+R` → `shell:startup` → 添加快捷方式
- **macOS**：系统偏好设置 → 用户与群组 → 登录项

## 🤝 贡献

我们欢迎任何形式的贡献！

### 如何贡献

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

### 开发指南

- 遵循现有的代码风格
- 为新功能添加测试
- 更新相关文档
- 确保所有测试通过

## 📊 项目统计

- **代码行数**: ~1500 行 Python
- **测试覆盖率**: 85%+
- **支持的 AI 服务商**: 3+ (OpenAI, DeepSeek, Zhipu AI)
- **支持的操作系统**: Windows 10/11, macOS 10.14+

## 🔗 相关链接

- **问题反馈**: [GitHub Issues](https://github.com/YOUR-USERNAME/luxselect/issues)
- **功能建议**: [GitHub Discussions](https://github.com/YOUR-USERNAME/luxselect/discussions)

## ⚠️ 免责声明

本项目仅供学习和研究使用。使用本工具时请遵守相关 AI 服务商的使用条款。开发者不对因使用本工具产生的任何问题负责。

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

---

<div align="center">

**如果觉得 LuxSelect 对您有帮助，请给个 ⭐ Star 支持一下！**

Made with ❤️ by LuxSelect Contributors

</div>

