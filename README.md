# epub-reader-optimizer

优化 EPUB 文件的中文阅读体验：重写 CSS、统一中英文双语段落排版、强制字体（如 LXGW WenKai）、美化代码块与表格、修复阅读器白底白字问题。

核心思路：**不改动 EPUB 的章节结构、HTML 正文与图片资源**，只通过重写 CSS 与必要的元数据来提升阅读体验、修复渲染缺陷。

## 何时使用

- EPUB 在某个阅读器/编辑器里文字看不见（白底白字、黑底黑字）。
- 字体丑、行距太挤、图表错位、代码块乱、表格挤成一团。
- 双语 EPUB 需要调整为「中文为主、英文为辅」或「英文在上、中文在下」的对照排版。
- 给 EPUB 强制指定中文字体（LXGW WenKai 系列）。
- 「公式即图片」型 EPUB：单个字符的行内公式 `x` / `y` 被强制独占一行居中。

## 目录结构（遵循 SkillHub 推荐 Skill 格式）

```
epub-reader-optimizer/
├── SKILL.md                      # Skill 唯一必需文件：YAML 元数据 + Markdown 指令
├── README.md / README.en.md      # 中英文说明
├── scripts/                      # 可执行脚本
│   ├── build_epub.py             # 把目录打包为合规 EPUB（mimetype STORED 优先）
│   ├── optimize_formula_images.py# 公式即图片型 EPUB 的 HTML 标签结构修复
│   └── subset_fonts.py          # LXGW WenKai TTF → 子集 WOFF2
└── assets/                       # 模板 / 资源文件
    ├── stylesheet.template.css       # 双语 EPUB 基础 CSS 模板
    └── stylesheet.formula-image.css  # 公式即图片型 EPUB 专用 CSS（行内/块级双轨）
```

## 环境与依赖

- Python 3（用于 `zipfile` 重新打包）
- 7-Zip 或系统解压（解 EPUB，EPUB 即 zip）
- 公式即图片型场景额外依赖：`pip install fonttools brotli`
- 可选：`epubcheck`（更严格的 EPUB 合规性检查，没装也不阻塞）

> ⚠️ **打包 EPUB 必须用 Python `zipfile`**，不要用 PowerShell 的 `Compress-Archive`——
> 它生成的 zip 不满足 EPUB 规范（mimetype 顺序与压缩方式都不对）。`scripts/build_epub.py` 已替你处理。

## 用法概览

```
1. 解包 EPUB（7z x book.epub -oepub_extract -y）
2. 探查 content.opf / toc.ncx / 章节 XHTML 抽样，决定要重写的选择器
3. 按 assets/ 下的模板重写 stylesheet.css（必要时改 page_styles.css）
4. 公式即图片型 EPUB：先跑 scripts/optimize_formula_images.py 处理 xhtml，
   再用 scripts/subset_fonts.py 子集化嵌入 LXGW WenKai
5. 用 scripts/build_epub.py 重新打包为合规 EPUB
6. 自检：用 Python 验证 mimetype 为第一个条目且 STORED
```

完整可调用流程、CSS 重写要点（白字修复、强制字体、双语段落、代码块、表格、图片公式、标题层级）、字体子集化细节、常见问题速查表均见 [SKILL.md](SKILL.md)。

## 配套 Skill

`epub-translator`（英→中双语对照翻译）翻译完成后，应调用本 skill 对成品做最终样式美化。

## 许可与免责

本 skill 只重写样式与必要元数据，不修改受版权保护的 EPUB 正文文本。请在自己拥有合法使用权的电子书上使用。