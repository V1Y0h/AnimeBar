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

echo "→ 编译图标…"
mkdir -p build/icon
xcrun actool --compile build/icon --platform macosx --minimum-deployment-target 12.0 \
  --app-icon AppIcon --output-partial-info-plist build/icon/partial.plist \
  app/AppIcon.icon >/dev/null
cp build/icon/AppIcon.icns build/icon/Assets.car "$APP/Contents/Resources/"
cp app/MenuIcon.png "$APP/Contents/Resources/"

echo "→ 编译…"
clang -fobjc-arc -O2 -framework Cocoa -framework WebKit \
  -o "$APP/Contents/MacOS/AnimeBar" app/main.m

cp build/anime_board.html board/anime_board.py "$APP/Contents/Resources/"
cp -R board/assets "$APP/Contents/Resources/assets"

# 图标资源曾经在很长一段时间里根本没被打进包里，菜单栏因此退回文字兜底「番」
for f in MenuIcon.png AppIcon.icns Assets.car; do
  if [ ! -f "$APP/Contents/Resources/$f" ]; then
    echo "! 缺少图标资源：$f"
    exit 1
  fi
done

# ~/Documents 若被 iCloud 同步，文件会带 com.apple.provenance 等扩展属性。
# --deep 会递归签名、撞上这些属性后报 "detritus not allowed"；单层签名不受影响。
xattr -cr "$APP"
if codesign --force -s - "$APP"; then
  echo "✓ 已签名（ad-hoc）"
else
  echo "! 签名失败：本机能跑，但 TCC 权限会随每次重装重新询问"
fi

echo "✓ $APP"
