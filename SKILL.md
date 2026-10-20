---
name: epub-reader-optimizer
description: 优化已有 EPUB 的中文和中英双语阅读排版。适用于字体与段距调整、图片或公式尺寸异常、代码与宽表溢出，以及 EPUB 样式优化后的截图审阅；保留正文和资源，不执行正文翻译。
metadata:
  tags: epub, 排版优化, CSS, 中文字体, 公式, 阅读器
---

# EPUB Reader Optimizer

保留正文、代码、MathML/SVG、图片资源和锚点，通过排版 class、滚动容器、CSS 引用和必要的 OPF 登记优化已有 EPUB。HTML 会重新序列化，不能承诺 XHTML 字节不变；内容保留检查比较解析后的文本与关键节点。

仓库内的样式基线固定为 epub-translator v1.4.0，提交 `817c210af90555764a2f56a292c3cb007b7c3bb1`（2026-10-19）。来源、适配和历史验证见 [docs/upstream-styles.md](docs/upstream-styles.md)。不用于正文翻译或 PDF/Word 转换。

## 默认入口

以下命令从本技能目录执行；在其他目录调用时使用脚本和依赖文件的绝对路径。

```powershell
python -m pip install -r requirements.txt
python scripts/optimize_epub.py input.epub output.epub
```

需要 Python 3.10+ 和命令行可用的 Java。基础依赖包含 BeautifulSoup 与 EPUBCheck 5.3.0，不需要翻译 API、API key 或 OpenAI SDK。

- `output.epub` 是完整输出文件名；另存输出为默认做法，同一输入输出路径表示原位更新。
- 输入中的 XHTML/HTML/HTM 必须是格式正确的 XML；脚本不自动修复任意损坏 HTML。
- 内容检查比较解析后的正文、图片引用、MathML、SVG、`pre` 文本与锚点；其他原始资源与候选包逐项比较，HTML、OPF 和项目自有 `translated.css` 除外。
- 默认运行 EPUBCheck，检查不通过或工具不可用时返回非零状态，不替换已有输出 EPUB。检查器成功生成的诊断保存为 `output.epubcheck.json`，工具未启动时不保证有新报告。
- 成功时生成 `output.style.json`，包含输入/输出 SHA-256、HTML 文档数、内容保留状态与规范检查结果。`chapters` 包含扫描到的所有 HTML 文档，不仅是 spine 正文章节。
- `--skip-epubcheck` 显式跳过规范检查，报告标记 `not_run`，不能据此宣称 EPUBCheck 通过。

先探查 OPF、阅读顺序和典型章节，保留用户已说明的排版偏好。完成后结合报告与实际截图说明验证结果，不把历史样书结果当作当前书籍的验收。

## 默认样式与定制入口

正文采用衬线字体，标题无衬线，代码等宽；正文行距 1.7，中文译文 1.78。现有中英段落通过间距配对，中文无底色与竖线；优化器不会翻译、重排段落或合并双语标题。`.translated-inline` 只为原本已有的同行译文提供样式。

代码保留缩进与空行，最外层使用浅底细框和局部横向滚动。图片按结构、alt、资源名和像素大小分类，区分插图、人物照片、封面、公式和图标；普通插图通常限正文宽度 100%、高度 80vh，超宽图局部滚动。宽表和独立公式各有滚动容器。重复图片默认保留，图片字节不改动。

图片公式如 `x`、`x_i`、`v^2` 保持行内；只含公式图片的段落添加 `formula-block` 并解除行内高度限制。识别同时避开 `PIC` 等占位标签及散文中的蛇形命名，并保护含数学记号的图注。特殊出版社结构仍需抽样检查。

| 文件 | 用途 |
|---|---|
| `assets/translated.css` | 固定提交的上游原样快照 |
| `assets/reader-compat.css` | 本地定制及旧出版社、lang 中文段落、Sigil 公式兼容层 |
| `assets/stylesheet.template.css` | 生成的独立通用模板，优化器实际注入的内容 |
| `assets/stylesheet.formula-image.css` | 同一模板加可选文楷字体声明，默认不会自动选用 |

优先在 `reader-compat.css` 添加本地定制，保留上游快照便于对比。运行 `python scripts/sync_styles.py` 重建两个模板；生成文件会被覆盖。优化器将通用模板作为 `translated.css` 引入，并放在出版社样式后。仅复制 CSS 无法完成图片分类与容器创建；不需要通过 flex/grid 或脚本增强基础排版。

## 截图与反馈

仅优化样式不需要 Playwright。需要截图审阅时安装：

```powershell
python -m pip install -r requirements-review.txt
python -m playwright install chromium
python scripts/optimize_epub.py input.epub output.epub --style-review --review-dir .style-review-book
```

也可通过 `--browser-executable` 指定已安装的 Chrome/Edge，省略浏览器下载。默认截图视口为 1050×1080 和 420×1080；CLI 不提供视口尺寸参数。

每轮渲染使用新的审阅目录；目录已有 `report.json` 时会拒绝覆盖。登记反馈时继续使用对应报告目录。单独扫描已有产物或复用前一次样点时使用 `review_epub.py`：

```powershell
python scripts/review_epub.py output.epub --output .style-review-book --scan-all
python scripts/review_epub.py updated.epub --output .style-review-updated --scan-all --plan .style-review-book/samples.json --compare .style-review-book/report.json
```

`--scan-all`、`--plan`、`--compare` 和 `--spread` 属于独立审阅命令；集成的 `--style-review` 不会自动扫描全书。`--spread` 默认最多抽样 6 个阅读顺序位置，并额外抽取存在的内容类别，不代表截图总数。

查看 `gallery.html` 与实际 PNG，再读 `report.json`：检查标题、双语间距、代码缩进、表格、公式编号、插图与照片，以及局部滚动的右端截图。报告的 `missing_categories` 可用于识别未覆盖的类别，自动指标不能替代看图。修复共享 CSS 或分类逻辑后重新优化、规范检查和截图，不要只给截图注入修复 CSS。

审阅状态含义：`awaiting_agent_review` 等待实际看图；`render_failed` 表示渲染失败；`agent_reviewed` 表示反馈已登记。修复后未解决的当前 `issues` 必须逐项说明接受原因，否则继续修复再渲染。

实际看图后填写 `feedback.template.json` 对应的 `feedback.json`：设 `status` 为 `reviewed`，填写 `summary`、全部 `reviewed_screenshots`，并在 `findings` 中记录截图、原因、处理状态和关联 `issue_ids`。绑定最终 EPUB 哈希，然后登记：

```powershell
python scripts/review_epub.py output.epub --output .style-review-book --accept-feedback .style-review-book/feedback.json
```

截图审阅发生在输出 EPUB 和 `.style.json` 写入之后；审阅失败时命令返回非零，但输出 EPUB 可能已经存在。单独审阅不运行 EPUBCheck。截图是重排 XHTML 视口，不是稳定页码或真实阅读器认证。

## 解包后定制与可选字体

自定义嵌入字体时，先优化出基础 EPUB，再解包副本到临时目录。`optimize_formula_images.py FILE_OR_DIR` 可在解包后补加布局标记，递归处理 `.xhtml/.html/.htm` 并原位写回；不会注入 CSS、登记 OPF、打包或运行 EPUBCheck。

基础优化器不会下载、子集化或嵌入字体。若明确需要嵌入文楷：

1. 安装 `python -m pip install fonttools brotli`，准备可使用和嵌入的字体源文件；仅在工作副本中处理字体。
2. `subset_fonts.py OEBPS_DIR` 要求 `OEBPS_DIR/Fonts/` 已有 `LXGWWenKaiLite-Regular.ttf` 和/或 `LXGWWenKaiMonoLite-Regular.ttf`，分别输出 `LXGWWenKai.woff2` 和 `LXGWWenKaiMono.woff2`；缺少的源字体会跳过。
3. 脚本只从 `OEBPS_DIR/Text/*.xhtml` 收集字符，不递归、不扫描其他路径或扩展名，也不解码 HTML 实体。对照实际章节检查字符覆盖；不符合此结构时先调整字符收集逻辑。不能以生成了 WOFF2 就认定覆盖完整。
4. 脚本在成功转换每个字体后删除工作目录中的对应源 TTF，不自动修改 OPF 或 CSS。保留原字体副本，并清理 OPF 中失效的 TTF 引用。
5. 将 `stylesheet.formula-image.css` 作为最终样式引用，或用其内容替换解包副本中的 `translated.css`；按实际 CSS 位置修正 `../Fonts/` 路径。在 OPF manifest 登记 CSS 和字体，例如（相对于 OPF）：

```xml
<item id="font_wenkai" href="Fonts/LXGWWenKai.woff2" media-type="font/woff2"/>
<item id="font_wenkai_mono" href="Fonts/LXGWWenKaiMono.woff2" media-type="font/woff2"/>
```

只登记实际存在的文件。不需要嵌入字体时使用通用模板与系统回退即可；字体子集体积取决于实际字符集，不承诺固定压缩比例。再次运行优化器会重新注入通用模板，因此应在基础优化后完成最终字体定制，或将可重复使用的 CSS 定制加入源兼容层。

```powershell
python scripts/build_epub.py EXTRACT_DIR final.epub
python -c "import sys; from epubcheck import EpubCheck; result = EpubCheck(sys.argv[1]); print(result.valid); sys.exit(0 if result.valid else 1)" final.epub
```

将打包输出放在解包目录之外，并另存新文件。`build_epub.py` 会覆盖已有输出，只检查 `mimetype` 首项、STORED 和内容，不运行 EPUBCheck，也不提供优化入口的内容比较与候选替换保护。用 Python `zipfile` 打包，不用 PowerShell `Compress-Archive`。完成字体定制后重新检查实际阅读效果。

## 验证与交付

运行 `python -m unittest discover -s tests -v`；没有 Java/EPUBCheck 时规范集成测试会跳过，没有设置 `EPUB_REVIEW_BROWSER` 时浏览器测试会跳过。完整检查需安装审阅依赖并设置 Chrome/Edge 路径，见 [README.md](README.md)。文档校验或测试跳过不能表述为完整 EPUB 验收。

保留用户原始文件，将临时解包文件放在临时工作目录；交付最终 EPUB、必要报告和可点击链接，简述修改、检查结果及尚未验证的真实阅读器行为。
