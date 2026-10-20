# VoiceNote

![VoiceNote：从语音到可追溯的知识](docs/assets/voicenote-social-preview.jpg)

**可纠错、可追溯、可扩展的语音知识处理工具包。**

将录音转换为原始转写、带审计记录的纠错文本、清晰笔记、财经会议纪要和执行简报。
提供 Python API 和命令行，保留每一级产物及其来源引用。

[English](README.md) · [项目路线图](docs/roadmap.md) · [贡献指南](CONTRIBUTING.md)

当前为 pre-alpha：主流程已实现，接口仍可能调整。模型输出需要结合转写核对。

## 先体验：不需要 API Key

从仓库安装核心包，然后运行合成文本演示：

```bash
git clone https://github.com/lynnfeng37-dot/voicenote-toolkit.git
cd voicenote-toolkit
python -m venv .venv
```

Windows PowerShell 激活环境：

```powershell
.venv\Scripts\Activate.ps1
```

macOS / Linux 激活环境：

```bash
source .venv/bin/activate
```

运行演示：

```bash
python -m pip install -e .
python examples/offline_correction_demo.py
```

演示使用手工编写的转写与纠错建议，调用真实的纠错策略和产物保存逻辑。
它不读取录音、不下载模型、不访问网络，也不代表模型准确率。

| 输入与建议 | 策略结果 |
| --- | --- |
| `Sharp ratio` → `Sharpe ratio`，置信度 0.97 | 应用并记录 |
| `15%` → `50%`，置信度 0.80，敏感数字 | 保留 `15%`，标记不确定 |

打开运行后生成的 `output/offline-demo/<run-id>/corrections.md` 查看完整审计。

## 五级处理流程

```text
录音 → 原始转写 → 纠错文本与审计 → 带来源的语义中间表示
                                  → 清晰笔记 → 财经会议纪要 → 执行简报
```

| 参数 | 处理终点 |
| --- | --- |
| `--until transcript` | 原始转写 |
| `--until corrected` | 纠错文本与修改记录 |
| `--until notes` | 语义中间表示与清晰笔记 |
| `--until minutes` | 领域会议纪要，需要指定 skill |
| `--until brief` | 执行简报，每条要点带来源引用 |

## 处理真实录音

安装所需 Provider：

```bash
python -m pip install -e ".[local-asr,openai]"
```

本地转写，显式允许首次下载模型：

```bash
voicenote meeting.m4a --provider local_whisper --allow-model-download --until transcript
```

模型已缓存时可以省略 `--allow-model-download`。

如需云端纠错和笔记整理，在 PowerShell 设置环境变量：

```powershell
$env:OPENAI_API_KEY="你的 API Key"
```

macOS / Linux：

```bash
export OPENAI_API_KEY="你的 API Key"
```

运行完整财经流程：

```bash
voicenote meeting.m4a --provider local_whisper --correction-provider openai --reasoning-provider openai --skill finance_meeting --allow-cloud --until brief
```

此配置的音频转写在本地完成；原始转写文本会发送到云端纠错 Provider，
纠错文本及语义中间表示会发送到云端推理 Provider。设置 API Key 本身不会授权上传。

## 财经会议 Skill

支持基金经理访谈、公司调研、内部投资会议、路演、策略讨论与组合复盘。
根据会议内容组织章节，并处理观点、估值、业绩、风险、催化剂、决策及行动项。
参考资料位于 `src/voicenote/skills/finance_meeting/references/`。

纠错策略针对敏感实体使用更高阈值。未知来源 ID、缺失的必要引用和冲突的修改
会被本地拒绝。引用校验只能验证来源编号是否合法，不能自动证明每句话都被来源支持。

## 输出与开发

命令会打印新的运行目录。默认同时输出 JSON 和 Markdown，包含原始转写、纠错审计、
语义中间表示、笔记、纪要及简报，不复制源录音。

完整 Python 示例、产物目录和 Provider 边界见 [英文 README](README.md)。
后续重点是阶段预检查、不确定性向下游传递、事实评测、失败后恢复及长录音支持，
详见 [路线图](docs/roadmap.md)。

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests examples
python -m mypy src/voicenote
```

采用 [Apache-2.0](LICENSE) 许可证。
