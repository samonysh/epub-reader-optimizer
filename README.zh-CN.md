# EPUB 阅读优化器

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/samonysh/epub-reader-optimizer/releases)
[![License: MIT-0](https://img.shields.io/badge/license-MIT--0-green)](LICENSE)
[![clawhub](https://img.shields.io/badge/clawhub-samonysh/epub-reader-optimizer-purple)](https://clawhub.ai/samonysh/epub-reader-optimizer)

优化 EPUB 排版与中文阅读体验：重写 CSS、统一双语段落、修复公式即图片显示，并安全化构建工具链。

## 功能特性

- 双语支持：`SKILL.md`（英文）+ `SKILL.zh-CN.md`（中文）。
- 灵活输入：支持 Markdown/TXT、JSON 结构化数据、直接 LLM 上下文。
- 安全默认：默认离线、失败即止、禁用 `-shell-escape`、固定远程依赖版本。

## 🔒 安全模型

| 行为 | 默认值 |
|---|---|
| 网络访问 | 关闭 |
| 主机工具链安装 | 关闭 / 失败即止 |
| LaTeX `-shell-escape` | 关闭 |

> 详细说明见 `SKILL.zh-CN.md` 中的「安全与副作用声明」章节。

## 快速开始

1. 在 [OpenCode](https://opencode.ai) 或兼容 Agent 中安装本技能。
2. 根据需要安装手动依赖（如有）。
3. 按照技能说明提供输入。

## 安装

```bash
# clawhub
clawhub install samonysh/epub-reader-optimizer

# 或手动复制
cp -r .opencode/skills/epub-reader-optimizer /path/to/your/.opencode/skills/
```

## 许可证

本项目采用 [MIT No Attribution (MIT-0)](LICENSE) 许可。
