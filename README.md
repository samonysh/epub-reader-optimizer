# EPUB Reader Optimizer

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/samonysh/epub-reader-optimizer/releases)
[![License: MIT-0](https://img.shields.io/badge/license-MIT--0-green)](LICENSE)
[![clawhub](https://img.shields.io/badge/clawhub-samonysh/epub-reader-optimizer-purple)](https://clawhub.ai/samonysh/epub-reader-optimizer)

Optimize EPUB layout for Chinese reading: rewrite CSS, normalize bilingual paragraphs, fix formula-as-image display, and harden build tooling.

## Features

- Bilingual support: `SKILL.md` (English) + `SKILL.zh-CN.md` (Chinese).
- Flexible input: Markdown/TXT, JSON structured data, direct LLM context.
- Secure defaults: offline by default, fail-closed, `-shell-escape` disabled, pinned remote deps.

## 🔒 Security Model

| Behaviour | Default |
|---|---|
| Network access | OFF |
| Host toolchain install | OFF / fail-closed |
| LaTeX `-shell-escape` | OFF |

> See the "Security & Side-Effects Disclosure" section in `SKILL.md` for details.

## Quick Start

1. Install this skill in [OpenCode](https://opencode.ai) or a compatible agent.
2. Install manual dependencies if required.
3. Provide input as described in the skill documentation.

## Installation

```bash
# clawhub
clawhub install samonysh/epub-reader-optimizer

# or manual copy
cp -r .opencode/skills/epub-reader-optimizer /path/to/your/.opencode/skills/
```

## License

This project is licensed under the [MIT No Attribution (MIT-0)](LICENSE) license.
