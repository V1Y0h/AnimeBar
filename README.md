# AnimeBar

macOS 菜单栏看番工具：本周新番、剧场版、以及日本正在上映的动画电影，点一下菜单栏图标就能看。

[中文](#中文) · [English](#english)

---

## 中文

### 功能

菜单栏点开是一个弹窗，四个标签：

- **新番** — 本周在播的全部作品，可按星期、评分筛选
- **剧场版** — 剧场版动画，可按评分或上映日排序
- **上映中** — 日本影院正在上映的动画电影，带「リバイバル」（重映）标记
- **档案** — 1969–1995 年的影像软件（OVA / LD / VHS 时代），三语标题、封面、一键复制日文原名
- **记录** — 捕获与手记混排的列表：捕获来自 IINA 的 ⌃⌥K（见下），手记是自己写的；
  每张卡片可补集数、现象/推测标签、维度与反思，支持清空复盘、删除、导出草稿

新番页会**自动过滤已完结与一次性放出的作品**（Bangumi 的放送表不会自己摘掉，
每季大约有 1/5 是这种情况）。能匹配上 しょぼいカレンダー 的作品还会显示
「周四 00:00 · BSテレ東」这样的精确放送时间，匹配不上就不显示。

### 捕获（配合 IINA）

装上 [IINA 插件](integrations/iina/) 后，播放时按 **⌃⌥K**，App 会记下当前时间码，
并在屏幕右上角浮出一个非激活的确认面板（**全屏播放时也能看到，不打断播放、不抢焦点**）。

记录写入 `~/Library/Application Support/AnimeBar/creation-log.jsonl`，一行一条。
复盘内容写在同目录的 `triage-mac.jsonl`，与
[dsh-animebar](https://github.com/V1Y0h/dsh-animebar) 的 `triage.jsonl` 按时间戳合并。

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
app/main.m                  菜单栏 App + 捕获接收端 + 确认浮层（Objective-C）
app/Info.plist              bundle 信息（LSUIElement，纯菜单栏）
app/AppIcon.icon/           图标源（actool 编译）
app/MenuIcon.png            菜单栏图标
board/anime_board.py        生成弹窗里的 HTML
board/captures_tab.py       记录页（捕获 + 手记，卡片式）
board/notes_tab.py          标签词表加载
board/assets/               占位图、英文名缓存
integrations/iina/          IINA 插件（捕获）
spike/capture-panel/        浮层技术验证（历史，不参与构建）
build.sh                    构建入口（含图标编译、脚本检查、签名）
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

### Capture (with IINA)

Install the [IINA plugin](integrations/iina/). While playing, press **⌃⌥K**; the app records
the current timecode and shows a non-activating confirmation panel in the top-right corner
(visible over fullscreen video, without interrupting playback or stealing focus).

Captures are appended to `~/Library/Application Support/AnimeBar/creation-log.jsonl`.
Triage written on the Mac goes to `triage-mac.jsonl` and is merged by timestamp with
`triage.jsonl` from [dsh-animebar](https://github.com/V1Y0h/dsh-animebar).

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

---

## 日本語

macOS のメニューバーアニメツール。今期の新作・劇場版・上映中に加えて、
IINA から時間碼を記録して後から振り返る機能を持つ。

### 機能

- **新作** — 今週放送中の作品を Bangumi から取得。曜日・評価で絞り込み
- **劇場版** / **上映中** — 劇場アニメと日本公開中の作品
- **アーカイブ** — 1969〜1995 年の映像ソフト（OVA / LD / VHS 時代）。
  中国語・英語・日本語のタイトル、ジャケット、日本語題名のコピー
- **記録** — IINA の ⌃⌥K で記録した時間碼とメモを一覧で管理

放送済み・一括配信の作品は**自動的に除外**される。しょぼいカレンダーと
照合できた作品には「木 00:00 · BSテレ東」のような正確な放送時刻も表示する。

### 必要なもの

- macOS 12 以降、`clang`（`xcode-select --install`）、`python3`（標準ライブラリのみ）

### ビルド

```bash
./build.sh
open build/AnimeBar.app
```

### データの場所

`~/Library/Application Support/AnimeBar/` にすべてローカル保存。

### ライセンス

MIT
