#!/bin/bash
# 构建 AnimeBar.app：先抓数据生成页面，再编译并组装 App 包
set -e
cd "$(dirname "$0")"

mkdir -p build
echo "→ 抓取数据…"
ANIMEBAR_OUT="$PWD/build/anime_board.html" python3 board/anime_board.py

APP=build/AnimeBar.app
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp app/Info.plist "$APP/Contents/Info.plist"

echo "→ 编译…"
clang -fobjc-arc -O2 -framework Cocoa -framework WebKit \
  -o "$APP/Contents/MacOS/AnimeBar" app/main.m

cp build/anime_board.html board/anime_board.py "$APP/Contents/Resources/"
cp -R board/assets "$APP/Contents/Resources/assets"
codesign --force --deep -s - "$APP" >/dev/null 2>&1 || true

echo "✓ $APP"
