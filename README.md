# AnimeBar

A macOS menu bar app for tracking anime: today's broadcast schedule, theatrical films, and what is actually showing in Japanese cinemas right now.

Click the menu bar icon for a popover with three tabs:

- **新番 / TV** — every show airing this week, filterable by weekday and rating
- **剧场版 / Films** — theatrical films, sortable by score or release date
- **上映中 / In cinemas** — anime currently screening in Japan

Toggle **EN / 中文** in the header. Choices persist.

## Requirements

- macOS 12 or newer
- Command Line Tools (`xcode-select --install`) for `clang`
- `python3` (standard library only)
- Network access

## Build

```sh
./build.sh
open build/AnimeBar.app
```

`build.sh` fetches the data, compiles `app/main.m`, and assembles `build/AnimeBar.app`.

Move the app to `/Applications` if you want it around; add it to Login Items to start it at login.

## Data sources

| Source | Used for |
| --- | --- |
| [Bangumi](https://bgm.tv) `api.bgm.tv/calendar` | weekly TV schedule, scores, covers |
| Bangumi `v0/search/subjects` | theatrical films, English-adjacent metadata |
| [映画.com](https://eiga.com/now/アニメ/) | anime currently in Japanese cinemas |
| [AniList](https://anilist.co) GraphQL | official English titles (cached) |

English titles are cached in `board/assets/titles-en.json`; the first build of a new season fills in the misses. Delete the file to re-resolve everything.

## Layout

```
app/main.m            menu bar app (Objective-C, Cocoa + WebKit)
app/Info.plist        bundle metadata (LSUIElement = menu bar only)
board/anime_board.py  generates the HTML popover content
board/assets/         placeholder image, English title cache
build.sh              build entry point
```

The generated page is plain HTML/CSS/JS with no build step and no framework.

## Notes

- The page is regenerated at build time; the app reads the bundled copy, or `~/Library/Application Support/AnimeBar/anime_board.html` after **更新数据**.
- Scores come from Bangumi; a title with few ratings will look wrong. That is the data, not a bug.
- 上映中 includes revival screenings (リバイバル), marked as such.

## License

MIT.
