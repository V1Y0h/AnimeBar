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

# ~/Documents 若被 iCloud 同步，文件会带 com.apple.provenance 等扩展属性。
# --deep 会递归签名、撞上这些属性后报 "detritus not allowed"；单层签名不受影响。
xattr -cr "$APP"
if codesign --force -s - "$APP"; then
  echo "✓ 已签名（ad-hoc）"
else
  echo "! 签名失败：本机能跑，但 TCC 权限会随每次重装重新询问"
fi

echo "✓ $APP"
