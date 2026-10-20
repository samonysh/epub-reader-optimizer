# 上游样式同步记录

同步日期：2026-10-20。来源：[samonysh/epub-translator v1.4.0](https://github.com/samonysh/epub-translator/tree/817c210af90555764a2f56a292c3cb007b7c3bb1)，提交 `817c210af90555764a2f56a292c3cb007b7c3bb1`（2026-10-19）。此记录固定本次导入版本；运行优化器不会自动拉取上游更新。

## 引入内容

- `assets/translated.css`：上游原样快照，可直接与指定提交对比。
- `scripts/reading_layout.py`：从上游 `translate_epub.py` 提取排版、图片识别、XML 解析、CSS 注入、EPUB 打包与检查函数；不引入翻译、API 配置或 OpenAI SDK。
- `scripts/optimize_epub.py`、`scripts/review_epub.py`：已有 EPUB 的样式优化和宽窄屏截图流程，导入改为本地共享模块。
- `tests/test_image_sizing.py`、`tests/test_style_review.py`：与排版相关的上游回归测试，模块名和图片保留预期适配本项目。

## 当前默认方案

正文采用 Georgia 与中文衬线字体回退，标题使用无衬线字体，代码采用 Cascadia Mono/Consolas。正文行距 1.7，中文译文 1.78；英文段后间隔 0.28em、译文后间隔 1.05em。中文无色块与竖线，标题保持层级。代码保留缩进和空行，只有最外层有浅色背景、细边框和滚动区域；长代码不强制折行。

插图按结构、alt 与真实像素大小区分照片、普通图、超宽图、公式与图标。当前基线以正文宽度 100%、通常 80vh 为上限；超宽示意图可局部滚动，小插图和人物照片分别控制大小。旧的 85% / 96vh 方案是上游 `legacy-image-sizing.css` 中的专项修复策略，不是 v1.4.0 默认方案，未作为新默认引入。

宽表与独立公式有各自的滚动容器，保留 MathML、SVG 属性大小写以及公式编号。截图报告包含宽窄屏、可滚动区域右端、资源哈希和反馈记录；自动布局指标不能替代人工看图。

## 本地适配

1. 图片默认不去重，优化已有书时保留重复出现的同一资源。
2. `reader-compat.css` 补齐旧 `.para*`、小写代码类、Sigil 公式段和 `lang`/`xml:lang` 中文段落；修正块公式受到行内公式高度限制的问题。
3. 通过 `python scripts/sync_styles.py` 生成两个可独立复制的模板，避免 EPUB 阅读器对 `@import` 的差异。优化器注入的是生成的通用模板，归档中的名字仍为 `translated.css`，便于更新已有产物。
4. `stylesheet.formula-image.css` 额外声明可选的文楷字体；字体文件需要单独子集化与登记，字体不随仓库分发。
5. 原 `optimize_formula_images.py` 使用共享分类器，保留图片属性，支持单引号属性，重复处理不再嵌套公式包装。命令行处理的 XHTML/HTML 仍须是格式正确的 XML。

后续同步先更新原样 CSS 快照和共享逻辑，再审查本地兼容层，重建模板并运行回归与截图检查。

## 本次验证

- 39 项回归全部通过，无跳过项；包括图片分类、旧版标记兼容、重复运行、正文/代码/资源保留以及检查失败时保护已有输出。
- 使用 Java 和 EPUBCheck 5.3.0 检查有效/无效样本，并确认优化后的有效 EPUB 通过检查。
- 本机 Chrome 在 1050px、420px 视口下运行样书回归，生成 48 张截图，布局扫描问题数为 0；另保留样书截图并实际目视复核。
- 四份 CSS 通过语法解析，Python 脚本通过编译检查。

上述检查使用合成样书，图片是用于检验几何尺寸的色块；没有用户真实书籍或真实阅读器的验收结果。
