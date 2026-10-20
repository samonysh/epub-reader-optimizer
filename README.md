# epub-reader-optimizer

优化已有 EPUB 的中文与中英双语阅读排版，保留正文、代码、公式、图片资源和锚点。可作为 Codex 技能使用，也可直接运行 Python 脚本；不需要翻译 API 或 API key。

[English](README.en.md) · [技能流程](SKILL.md) · [上游来源与适配记录](docs/upstream-styles.md)

当前内置基线固定为 [epub-translator v1.4.0](https://github.com/samonysh/epub-translator/tree/817c210af90555764a2f56a292c3cb007b7c3bb1)，提交 `817c210`（2026-10-19）。它是本项目已同步的版本，不表示每次运行会从上游自动更新。

## 排版能力

- 正文衬线、标题无衬线、代码等宽，包含中文字体回退；文楷嵌入为可选手动流程。
- 为已有中英段落提供配对间距，中文无底色与竖线；已有同行标题译文保留层级。优化器不会翻译、调整原文/译文顺序或自动合并标题。
- 代码保留缩进与空行，最外层使用浅底细框；长行局部横向滚动。
- 区分插图、照片、封面、公式与图标，修复插图被压成字高小图的问题；重复图片保留，超宽图局部滚动。
- 宽表、MathML 和独立公式使用局部滚动容器；适配旧出版社类名和 Sigil 图片公式。
- 默认浅色页面配深色文字，不添加暗色媒体规则；特殊出版社规则与阅读器主题仍需实际检查。

## 安装与快速使用

需要 Python 3.10+；默认规范检查需要命令行可用的 Java。以下命令从项目根目录执行：

```powershell
python -m pip install -r requirements.txt
java -version
python scripts/optimize_epub.py input.epub output.epub
```

`output.epub` 是完整输出文件名。相同输入输出路径表示原位更新；首次处理建议另存新文件。输入的 XHTML/HTML/HTM 必须是格式正确的 XML，不能把脚本当作任意损坏 HTML 的修复器。

| 产物或参数 | 行为 |
|---|---|
| `output.epub` | 优化结果；默认在内容检查和 EPUBCheck 通过后替换输出 |
| `output.style.json` | 输入/输出哈希、扫描文档数、内容保留状态、规范检查结果 |
| `output.epubcheck.json` | EPUBCheck 成功运行时的诊断，包含不通过的检查结果；工具启动失败时不保证生成新报告 |
| `--skip-epubcheck` | 显式跳过规范检查，报告标记 `not_run` |
| `--style-review` | 优化完成后生成抽样截图，需额外审阅依赖 |
| `--review-dir PATH` | 指定截图目录；省略时使用输出旁的 `.style-review-文件名` |
| `--browser-executable PATH` | 为截图步骤指定已安装的 Chrome/Edge |

HTML 会重新序列化，内容检查针对解析后的正文、图片引用、代码、MathML/SVG 和锚点；不承诺 XHTML 字节相同。其他原始资源逐项核对字节，HTML、OPF 和项目自有 `translated.css` 除外。报告中的 `chapters` 统计扫描到的全部 HTML 文档，可能包含导航页。

内容检查、规范检查失败或检查器不可用时，命令返回非零，不替换已有输出 EPUB。截图审阅在 EPUB 和 `.style.json` 写入后执行；截图失败时命令也返回非零，但输出 EPUB 可能已存在。`--skip-epubcheck` 不等于检查通过。

## 截图与反馈

仅优化 EPUB 无需 Playwright。需要截图时安装：

```powershell
python -m pip install -r requirements-review.txt
python -m playwright install chromium
python scripts/optimize_epub.py input.epub output.epub --style-review --review-dir .style-review-book
```

若使用已有浏览器，可省略 Chromium 下载并传入路径：

```powershell
python scripts/review_epub.py output.epub --output .style-review-book --scan-all --browser-executable 'C:\Program Files\Google\Chrome\Application\chrome.exe'
```

每轮渲染需使用新的审阅目录；已有 `report.json` 的目录会被拒绝覆盖，登记反馈时则使用对应报告目录。上面两种浏览器配置是替代用法，不要在同一目录连续运行。

默认视口为 1050×1080 与 420×1080。独立 `review_epub.py` 支持 `--scan-all`（扫描全书窄屏布局）、`--spread`（默认最多抽样 6 个阅读顺序位置并额外抽取内容类别）、`--plan` 和 `--compare`；这些参数不属于优化入口。集成 `--style-review` 默认只做抽样，独立审阅不会运行 EPUBCheck。

检查 `gallery.html`、PNG 和 `report.json`，并留意报告中的 `missing_categories`。状态 `awaiting_agent_review` 表示等待实际看图，`render_failed` 表示渲染失败，`agent_reviewed` 表示反馈已登记。自动指标为零不能代替实际审阅。

修正样式并生成 `updated.epub` 后，可复用样点比较新旧结果：

```powershell
python scripts/review_epub.py updated.epub --output .style-review-updated --scan-all --plan .style-review-book/samples.json --compare .style-review-book/report.json
```

按 `review-task.md` 实际看图后，将 `feedback.template.json` 填写为 `feedback.json`，记录最终产物哈希、全部审阅截图与问题处置，再登记反馈：

```powershell
python scripts/review_epub.py updated.epub --output .style-review-updated --accept-feedback .style-review-updated/feedback.json
```

截图是重排 XHTML 视口，不是稳定页码或真实阅读器认证。

## 文件与样式维护

```text
epub-reader-optimizer/
├── SKILL.md                       # Codex 技能入口
├── README.md / README.en.md        # 中英文使用说明
├── requirements.txt               # 基础依赖
├── requirements-review.txt        # 基础依赖 + Playwright
├── assets/
│   ├── translated.css             # 上游原样快照
│   ├── reader-compat.css          # 本地定制与出版社兼容层
│   ├── stylesheet.template.css    # 生成的独立通用模板
│   └── stylesheet.formula-image.css # 独立模板 + 可选文楷声明
├── scripts/
│   ├── optimize_epub.py            # 完整 EPUB 样式优化入口
│   ├── reading_layout.py           # 共享排版、图片分类、打包与校验
│   ├── review_epub.py              # 截图、布局扫描与反馈
│   ├── sync_styles.py              # 重建两个 CSS 模板
│   ├── optimize_formula_images.py  # 解包后的布局修复
│   ├── subset_fonts.py             # 文楷字体子集化
│   └── build_epub.py               # 解包目录打包
├── tests/                         # 排版与内容保留回归
└── docs/upstream-styles.md         # 来源、适配与历史验证
```

本地定制优先写入 `assets/reader-compat.css`，保留 `assets/translated.css` 作为上游快照；随后运行 `python scripts/sync_styles.py`。两个生成模板会被覆盖，不能只修改它们。优化器注入通用模板，归档中仍命名为 `translated.css`，放在出版社样式之后加载；仅复制 CSS 不会自动分类图片或创建滚动容器。

## 手动布局与字体定制

解包副本后，可运行 `python scripts/optimize_formula_images.py EXTRACT_DIR`，递归原位处理 `.xhtml/.html/.htm` 并添加布局标记。它不负责 CSS 引用、OPF 登记、打包或 EPUBCheck。

文楷字体不随项目分发，优化器不会下载或嵌入字体。手动嵌入需额外安装 `python -m pip install fonttools brotli`，准备源字体并修正最终样式的字体路径、登记 OPF。`subset_fonts.py` 只扫描 `OEBPS_DIR/Text/*.xhtml`，且成功转换后删除工作副本中的对应源 TTF；其他章节结构需先调整字符收集逻辑。完整文件名、目录与操作顺序见 [SKILL.md](SKILL.md#解包后定制与可选字体)。

建议先优化，再做最终字体定制；再次运行优化器会重置为通用模板。`stylesheet.formula-image.css` 是可选手动模板，不会被优化入口自动选用。

`python scripts/build_epub.py EXTRACT_DIR final.epub` 只打包并检查 ZIP 的 `mimetype`，会覆盖已有输出；输出应放在解包目录之外。它不运行 EPUBCheck，也不执行完整优化入口的内容比较和候选替换保护。打包后需另做规范与视觉检查。不要用 PowerShell `Compress-Archive` 打包 EPUB。

## 验证

```powershell
python -m unittest discover -s tests -v
```

缺少 Java 或 EPUBCheck 时规范集成测试会跳过；未设置 `EPUB_REVIEW_BROWSER` 时浏览器回归会跳过。完整回归需要审阅依赖，以及可用的 Java 和浏览器路径：

```powershell
python -m pip install -r requirements-review.txt
$env:EPUB_REVIEW_BROWSER = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
python -m unittest discover -s tests -v
```

测试成功但含跳过项不代表完整验证。固定样书的历史检查结果见[同步记录](docs/upstream-styles.md#本次验证)，不能替代当前书籍的实际检查。配套翻译项目为 [epub-translator](https://github.com/samonysh/epub-translator)。
