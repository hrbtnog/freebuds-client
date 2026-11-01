# FreeBuds Client

[![CI](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml/badge.svg)](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml)
[![许可证: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[**English**](README.md) | [**Português (Brasil)**](README.pt-BR.md) | [**Español**](README.es.md) | [**Русский**](README.ru.md) | [**简体中文**](README.zh-CN.md)

> ⚠️ **注意：** 本文档由人工智能 (AI) 翻译，可能存在不准确或错误之处。原始参考文档请参阅[英文版](README.md)和[葡萄牙语版](README.pt-BR.md)。

用于在 Windows 上管理华为 HUAWEI FreeBuds 耳机的**非官方**桌面客户端，灵感来自 Galaxy Buds Client 的易用性设计。旨在无需登录华为账号、无需安装“智慧生活 (HUAWEI AI Life)”的情况下，直接查看电量、控制降噪、切换声音模式、设置手势、查看多点连接状态并进行硬件测试。

---

## ⚡ 快速概览 (TL;DR)

如果您只是路过并想了解核心内容：

- **它是什么：** 一款轻量级 Windows 应用程序（具有现代 HarmonyOS 风格的图形界面及命令行工具 CLI），可直接从电脑查看电量并配置 HUAWEI FreeBuds。
- **它能做什么：**
  - 实时显示左右双耳 (L/R) 及充电盒的电量百分比。
  - 切换降噪模式（ANC：降噪、关闭、透传/环境音）以及智慧动态降噪/自适应透传调节（11 档）。
  - 配置音效模式 (HUAWEI SOUND)、空间音频、佩戴检测以及触控/头部动作手势。
  - 无缝最小化至系统托盘常驻。
  - 支持多语言切换（提供首选项语言选择器）。
- **它不能做什么：** 它无法完全替代官方手机应用（无法进行固件升级、不支持高级自定义参数均衡器，也无法查找丢失的耳机）。
- **快速上手：** 前往 [Releases](https://github.com/hrbtnog/freebuds-client/releases) 页面下载开箱即用的可执行程序 (`.exe`)，或使用 Python 3.10+ 从源代码运行（执行 `pip install -e ".[ui]"`，然后运行 `freebuds-ui`）。
- **个人项目：** 由爱好者在 AI 协助下开发的非营利个人学习项目。非常欢迎提出宝贵意见、提交 Issue 和 Pull Request！

---

## 关于我与开发初衷

我**不是专业程序员**，也从未从事过软件开发工作。这是一个个人的学习与探索项目：我希望能直接在 Windows 电脑上查看 FreeBuds Pro 5 的电量并控制降噪，而无需频繁查看手机或安装庞大的官方管理套件。

需要说明的是，本软件并不是为了在所有场景下完全取代手机端的“智慧生活”或“华为音频连接”。如高级自定义调音、充电盒提示音开关、查找耳机、耳塞贴合度检测等深度功能目前尚未支持（部分可能由于技术限制无法实现）。

项目的初衷是完善日常桌面端的使用体验，提供便捷的核心控制，填补官方在 PC 端留下的功能空白。

本软件非商业产品，不提供官方售后支持或商业担保。代码在 AI 辅助下编写，并已在作者自有的硬件设备上经过实机验证。如果您在使用中发现问题，欢迎反馈以共同改进。

## 重要声明

- **风险自负：** 本程序通过经典蓝牙与耳机通信并修改设备设置。不保证兼容所有型号、未经验证的固件版本或硬件批次。
- **非官方项目：** 本项目与华为技术有限公司 (Huawei)、荣耀 (HONOR) 或任何硬件制造商均无隶属关系、赞助或背书。商标及外观版权归其合法拥有者所有；详见 [`NOTICE.md`](NOTICE.md)。
- **不支持固件升级：** 不支持刷写固件，亦不会试图绕过 Windows 配对流程、PIN 码或系统安全确认。
- **请勿泄露隐私数据：** 在提交 Issue、截图或 PR 时，请勿公开完整的蓝牙 MAC 地址、设备序列号、HCI 数据包原始转储或个人设备名称。

## 项目状态

> **状态：** 核心阶段已完成开发。通信核心、诊断 CLI 以及逆向分析文档于 **2026-10-21** 在 FreeBuds Pro 5 硬件（通道 `1`）上完成验证：设备发现、握手交互、电量上报以及三种 ANC 降噪模式均可正常工作。透传级别 `4` 已识别为支持 11 级调节的**自适应环境音**；降噪模式状态变更会通过 `0x2B2A` 推送即时更新。**2026-10-23**，在耳机同时连接电脑与手机的情况下完成了带有托盘功能的 PySide6 界面实机验证。降噪写入 (`0x2B04`) 及高级功能（HUAWEI SOUND、空间音频、动态响度、语音透传/通话增强、头部动作控制、佩戴检测、音质优先/低延迟与单耳降噪）均已实现并经过状态回读校验。**2026-10-28**，界面基于 HarmonyOS 设计规范进行了全面重构，包括侧边栏导航、卡片视图、分段控件、胶囊电量显示及完整国际化支持。自动化测试套件包含 **89 项测试全部通过**。出于安全性考虑，双设备多点管理和滑动调节当前保持只读。

## 文档导航

- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — 帧格式结构、CRC16 算法、TLV 定义及已知命令字。
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 架构分层、线程模型、CLI 探测与 UI 工作流。
- [`docs/CAPTURE_GUIDE.md`](docs/CAPTURE_GUIDE.md) — Android 蓝牙 HCI 日志抓取与命令分析指南。
- [`CHECKPOINT.md`](CHECKPOINT.md) — 项目里程碑、硬件验证记录与技术笔记。
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 参与测试、功能提议及提交代码指南。
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — 社区行为准则。
- [`SECURITY.md`](SECURITY.md) — 安全策略与负责任的漏洞披露。
- [`NOTICE.md`](NOTICE.md) — 第三方商标、开源组件许可与资源说明。
- [`LICENSE`](LICENSE) — 项目 MIT 开源许可证。
- [`docs/PUBLISHING.md`](docs/PUBLISHING.md) — 发行与版本发布指南。

## 界面设计

桌面端界面充分参考了现代移动系统的设计美学，并做了桌面适配：

- 固定式侧边栏导航，集成品牌标志与设备快速切换；
- 居中最大宽度内容布局，避免在带鱼屏或超宽显示器上产生拉伸；
- 圆角卡片设计（标准卡片 24px、顶部横幅 28px）与 1px 微质感分割线；
- 层级分明的排版体系与低对比度大写区块标题；
- 带有图形图标的分段降噪控件、多档选择芯片与平滑开关；
- 华为经典蓝 `#0A59F7` 专门用于激活状态、链接及主操作按钮；
- 采用高分辨率 SVG 矢量图标并置于彩色圆形底衬中；
- 竖向电量胶囊，环形进度圈直观呈现双耳与耳机盒电量；
- 分设**概览**、**声音**、**手势**、**连接**与**诊断**五个独立页面。

![FreeBuds Client Overview](docs/ui/visao-geral.png)

其他功能视图：[声音](docs/ui/audio.png)、[手势](docs/ui/gestos.png)、[连接](docs/ui/conexao.png)、[诊断日志](docs/ui/diagnostico.png)、[自适应透传](docs/ui/adaptavel.png) 以及 [未连接状态](docs/ui/desconectado.png)。

## 功能特性

- 基于 Windows 原生 API 的经典蓝牙 (Bluetooth Classic) 设备发现与枚举。
- 借助 `BluetoothAuthenticateDeviceEx` 的辅助配对机制，严格遵守系统安全流程。
- 基于 RFCOMM/SPP 协议传输，具备常用通道（`1` 与 `16`）自动回退及通道记忆缓存功能。
- 稳健的华为私有协议编解码器：处理 `0x5A` 引导帧、TLV 属性、CRC16/XMODEM 校验，流式解析器具备粘包分包处理及容错抗噪能力。
- 设备握手鉴定 (`0x0107`)、电量实时获取 (`0x0108`) 与降噪状态解析 (`0x2B2A`)。
- 完整的降噪控制指令 (`0x2B04`)：关闭、降噪（深度/轻度/均衡/动态）、环境音透传及 11 级自适应环境音调节。
- 高级客户端接口 (`core/client.py`)，具备后台工作线程、断线自动重连与状态快照即时广播。
- 功能强大的 CLI 工具：支持友好的格式化终端输出与 `--json` 数据输出、`--raw` 十六进制原始报文检查以及 `--listen` 实时事件监听。
- 基于 PySide6 构建的现代深色主题桌面 GUI，完美集成 Windows 系统托盘与常驻监控。
- 高级声音设置：HUAWEI SOUND 预设、空间音频、动态响度与人声透传增强。
- 手势控制自定义：按捏/长按、双击、三击、头部动作控制（点头/摇头）及滑动状态显示。
- 连接与无线管理：蓝牙编码音质优先选择、游戏低延迟模式、智能佩戴检测与多设备连接概览。
- 全界面多语言国际化支持。
- 本地配置持久化，保存在 `%APPDATA%\FreeBudsClient\settings.json`。

## 运行环境要求

- Windows 10 / 11 操作系统（需具备蓝牙硬件模块）。
- 耳机已在 Windows 蓝牙设置中成功配对，处于开机状态并已从充电盒中取出。

## 普通用户使用指南

我们在 [Releases](https://github.com/hrbtnog/freebuds-client/releases) 页面提供了已打包好的独立 `.exe` 可执行文件供直接下载。您也可以根据[打包独立可执行文件](#打包独立可执行文件-exe)一节自行构建。如需通过 Python 源码运行，请根据下文步骤操作。

## 源码安装与运行

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ui]"
```

若仅需使用命令行工具 (CLI)：
```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\freebuds.exe list
```

## 打包独立可执行文件 (.exe)

在 Windows PowerShell 下激活虚拟环境后运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui]" pyinstaller
.\.venv\Scripts\pyinstaller.exe FreeBudsClient.spec --clean -y
```

编译生成的可执行文件位于 `dist\FreeBudsClient.exe`。

## 命令行 (CLI) 操作示例

```powershell
# 查看程序版本
freebuds --version

# 列出当前系统中已配对的蓝牙设备
freebuds list
freebuds list --json

# 搜索附近的未配对经典蓝牙设备（扫描 8 秒）
freebuds scan --seconds 8

# 扫描附近所有经典蓝牙设备（不限于华为设备）
freebuds scan --seconds 8 --all

# 辅助蓝牙配对
freebuds pair AA:BB:CC:DD:EE:FF

# 综合探测：握手 + 电量 + 降噪（自动测试通道 1 与 16）
freebuds probe --name "FreeBuds"

# 指定通道、打印十六进制收发报文并以 JSON 格式输出
freebuds probe --address AA:BB:CC:DD:EE:FF --channel 1 --json --raw

# 状态快照获取后继续监听 15 秒的主动推送通知
freebuds probe --name FreeBuds --listen 15

# 解析十六进制字节串或文本文件中的报文
freebuds decode "5A0006002B03080100A79D"
freebuds decode --file capturas/spp.txt
```

## 图形界面 (GUI) 启动方式

PySide6 图形界面可通过以下任一命令启动：

```powershell
# 方式一：CLI 子命令
freebuds ui

# 方式二：专用启动命令
freebuds-ui

# 方式三：作为 Python 模块
python -m freebuds ui
```

指定 MAC 地址直接启动并连接：

```powershell
freebuds ui --address AA:BB:CC:DD:EE:FF
```

## 测试与代码验证

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m compileall -q src tests
```

项目测试套件对通信帧编解码、解析器稳定性、指令解析、RFCOMM 模拟会话及界面组件进行了全方位覆盖（**89 项自动化测试全部通过**）。

## 项目目录结构

```text
src/freebuds/
  core/
    protocol.py      # 通信帧格式、TLV 封包、CRC 校验及流式增量解析器
    commands.py      # 指令码定义、请求构建及语义解码逻辑
    client.py        # 供 CLI 与 UI 使用的高级客户端封装与快照管理
    transport.py     # RFCOMM/SPP 底层套接字通信
    session.py       # 读取工作线程与请求/响应对应逻辑
    windows_bt.py    # Windows 原生经典蓝牙枚举与发现
    models.py        # 状态数据结构类
  config/
    settings.py      # 用户偏好设置持久化
  cli/
    app.py           # 命令行功能入口
  ui/
    app.py           # QApplication 主程序启动入口
    main_window.py   # 主窗口、侧边栏导航与主要功能页面
    worker.py        # 连接维护、轮询及后台操作线程
    widgets.py       # 横幅卡片、电量胶囊、降噪面板、控件与日志组件
    tray.py          # 系统托盘图标与上下文菜单
    theme.py         # HarmonyOS 风格深色样式表
    icons.py         # 应用图标、托盘图标及侧边栏矢量图绘制
    svg_icons.py     # SVG 矢量图形渲染与着色
    assets/          # 本地静态图像资源与图标
docs/
  ARCHITECTURE.md
  PROTOCOL.md
  CAPTURE_GUIDE.md
  PUBLISHING.md
  ui/                # 文档插图资源
tests/
```

## 已知局限说明

- 协议与指令标识均源于公开社区研究（OpenFreebuds, LibreBuds, mmk.pw, Gadgetbridge）及 FreeBuds Pro 5 实机逆向。各功能在不同型号与固件版本上的支持度存在差异。
- 电量查询以 `0x0108` 指令为主；部分特定固件版本会采用 `0x0127` 进行主动推送。
- 充电状态显示需依赖设备回传数据结构符合标准定义。
- 软件不具备固件升级功能，亦不计划对此进行逆向。
- 当前 RFCOMM 端口根据型号预设（`1` 或 `16`）；未来可引入动态 SDP 查询以进一步增强适应性。

## 如何参与贡献

本项目非常欢迎来自社区的提议、纠错与 Pull Request！

- **发现 Bug？** 欢迎提交 Issue，并尽可能提供耳机型号、固件版本、Windows 版本以及相关日志信息。
- **有新功能想法？** 欢迎发表建议，无需具备编程经验。
- **贡献代码？** 请参阅 [`CONTRIBUTING.md`](CONTRIBUTING.md)，确保本地测试通过后提交 PR。
- **注意隐私保护：** 请务必在提交内容前对 MAC 地址、序列号等个人敏感数据进行脱敏。

## 安全与免责提示

- 仅可在您合法拥有的设备上使用本软件。
- 切勿在公开场合张贴未脱敏的蓝牙硬件地址或设备序列号。
- 建议优先使用只读查询命令；在发送修改指令前需确认具备清晰的数据包依据和回退手段。
- 提交日志前请仔细阅读 [`SECURITY.md`](SECURITY.md)。

## 开源许可证

本项目原创源代码采用 **MIT 许可证** — 详情请参见 [`LICENSE`](LICENSE)。产品实物外观照片、第三方图标资源及相关厂商商标版权归各自所有者所有；详见 [`NOTICE.md`](NOTICE.md)。

## 参考资料与致谢

- OpenFreebuds — https://github.com/melianmiko/OpenFreebuds
- LibreBuds — https://github.com/librebuds/librebuds
- FreeBuds 4i 协议分析 — https://mmk.pw/en/posts/freebuds-4i-proto/
- Freebuds playground — https://gist.github.com/melianmiko/02f7c6a550808e38d9b6760fb688e125
- Gadgetbridge (FreeBuds) — https://codeberg.org/Freeyourgadget/Gadgetbridge
- GalaxyBudsClient — https://github.com/timschneeb/GalaxyBudsClient

衷心感谢所有协助测试、反馈问题和贡献协议分析的开发者与爱好者们！
