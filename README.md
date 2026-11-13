# AnimeBar

macOS 菜单栏看番工具：本周新番、剧场版、以及日本正在上映的动画电影，点一下菜单栏图标就能看。

[中文](#中文) · [English](#english)

---

## 中文

### 功能

菜单栏点开是一个弹窗，三个标签：

- **新番** — 本周在播的全部作品，可按星期、评分筛选
- **剧场版** — 剧场版动画，可按评分或上映日排序
- **上映中** — 日本影院正在上映的动画电影，带「リバイバル」（重映）标记

右上角 **EN / 中文** 切换界面语言，选择会记住。

### 环境要求

- macOS 12 或更新
- 命令行工具（`xcode-select --install`），提供 `clang`
- `python3`（只用标准库，无需 pip 安装任何东西）
- 能联网

### 构建

```sh
./build.sh
open build/AnimeBar.app
```

`build.sh` 会先抓数据生成页面，再编译 `app/main.m`，最后组装成 `build/AnimeBar.app`。

想常驻的话，把 App 拖进 `/Applications`，再加到「登录项」。

### 数据来源

| 来源 | 用途 |
| --- | --- |
| [Bangumi](https://bgm.tv) `api.bgm.tv/calendar` | 每周放送表、评分、封面 |
| Bangumi `v0/search/subjects` | 剧场版检索 |
| [映画.com](https://eiga.com/now/アニメ/) | 日本正在上映的动画电影 |
| [AniList](https://anilist.co) GraphQL | 官方英文名（本地缓存） |

英文名缓存在 `board/assets/titles-en.json`。新一季第一次构建会补上缺的部分；想全部重新解析，删掉这个文件重跑即可。

### 目录结构

```
app/main.m            菜单栏 App（Objective-C，Cocoa + WebKit）
app/Info.plist        bundle 信息（LSUIElement，纯菜单栏）
board/anime_board.py  生成弹窗里的 HTML
board/assets/         占位图、英文名缓存
build.sh              构建入口
```

生成的页面就是普通 HTML/CSS/JS，没有构建步骤，也没有框架。

### 说明

- 页面在构建时生成；App 读 bundle 里的副本，点「更新数据」后读 `~/Library/Application Support/AnimeBar/anime_board.html`。
- 评分来自 Bangumi，打分数少的作品分数会失真，那是数据本身的问题。
- 上映中里带「リバイバル」的是重映老片，不是数据错了。

### 许可

MIT。

---

## English

A macOS menu bar app for tracking anime: this week's broadcast schedule, theatrical films, and what is actually screening in Japanese cinemas right now.

### Build

```sh
./build.sh
open build/AnimeBar.app
```

Requires macOS 12+, Command Line Tools, and `python3` (standard library only).

### Data sources

Bangumi for the TV schedule and scores, 映画.com for current cinema listings, AniList for official English titles (cached in `board/assets/titles-en.json`).

### Layout

```
app/main.m            menu bar app (Objective-C, Cocoa + WebKit)
app/Info.plist        bundle metadata (LSUIElement)
board/anime_board.py  generates the popover HTML
board/assets/         placeholder image, English title cache
build.sh              build entry point
```

### License

MIT.
