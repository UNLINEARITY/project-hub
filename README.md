# Project hub

A static directory of apps by unlinearity, with product overviews, support pages, and privacy policies in English and Simplified Chinese. Includes Event Horizon Timer for macOS.

unlinearity 的应用网站，提供中英文产品介绍、使用支持和隐私政策，包含 macOS 应用 Event Horizon Timer。

## Build / 构建

Requires Python 3.9 or later. The generator uses the Python standard library; no packages or font CDN are needed.

需要 Python 3.9 或更新版本。生成器使用 Python 标准库，无需安装第三方包或加载在线字体。

```sh
python3 scripts/build.py
python3 scripts/check.py
python3 -m http.server 8000 --bind 127.0.0.1 --directory site
```

Visit `http://127.0.0.1:8000/` or `http://127.0.0.1:8000/index-zh-hans.html`. Pages also work directly from disk. Relative links support hosting at a domain root or repository subpath.

访问以上地址可预览英文或中文首页，页面也可直接从磁盘打开。相对链接支持独立域名和仓库子路径部署。

## Source layout / 源码结构

| Path | Content / 内容 |
|---|---|
| `projects.json` | App names, categories, summaries, and availability / 应用名称、分类、摘要与发布状态 |
| `projects/<slug>/pages/` | Six bilingual overview, support, and privacy fragments / 中英文介绍、支持和隐私正文 |
| `projects/<slug>/assets/` | Product icons and images / 产品图标与图片 |
| `shared/` | Shared styles and theme controls / 共用样式与主题控件 |
| `scripts/` | Build and validation tools / 构建与检查工具 |
| `tests/` | Generator and deployment regression tests / 生成器与部署回归测试 |
| `site/` | Generated static website / 生成的静态网站 |

Edit source files, then rebuild. Each project provides `index.html`, `support.html`, `privacy.html`, and their `-zh-hans.html` equivalents. The generator supplies navigation, language switching, and footers. Keep both languages consistent with the product’s behavior.

修改源文件后重新构建。每个项目包含介绍、支持、隐私三类正文，各提供中英文版本。生成器统一添加导航、语言切换和页脚，两种语言应与产品实际行为保持一致。

## Checks / 检查

The complete gate requires Python 3.9+ and Node.js 24:

完整检查需要 Python 3.9+ 和 Node.js 24：

```sh
python3 scripts/ci.py
actionlint
```

The checks cover JavaScript syntax, nine regression tests, deterministic builds, bilingual routes, local links, image attributes, and deployment artifacts. Install actionlint separately to validate the GitHub Actions workflow.

检查覆盖 JavaScript 语法、9 项回归测试、可重复构建、双语路由、本地链接、图片属性和部署产物。工作流语法使用单独安装的 actionlint 检查。

## GitHub Pages

The workflow validates pull requests and publishes `site/` on pushes to `main`. Configure Pages to use GitHub Actions, and restrict the `github-pages` environment to `main`. Only the deployment job has Pages and OIDC write permissions. Actions use pinned versions; Dependabot proposes updates.

工作流检查拉取请求，并在推送到 `main` 时发布 `site/`。在 Pages 设置中选择 GitHub Actions，将 `github-pages` 环境的部署分支限制为 `main`。仅部署任务具有 Pages 和 OIDC 写权限，依赖版本固定，由 Dependabot 提出更新。

After deployment, the workflow reads back each page and asset and compares its SHA-256 with the build. To verify an existing deployment manually:

部署后，工作流逐一读取线上页面和资源，与构建产物核对 SHA-256。也可手动检查已部署的网站：

```sh
python3 scripts/verify-deployment.py 'https://YOUR-OWNER.github.io/project-hub/'
```

Use the actual website URL, including its repository subpath. Revert a source commit to roll back through the same build and deployment checks. Keep published support and privacy URLs stable.

将示例替换为真实网址，并保留仓库子路径。回退时还原源文件提交，经过同一套构建和部署检查。已发布的支持与隐私页面应保持地址稳定。
