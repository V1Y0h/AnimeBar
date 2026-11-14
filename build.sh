#!/bin/bash
# 构建 AnimeBar.app：先抓数据生成页面，再编译并组装 App 包
#
# 组装和签名都在临时目录里做：这个仓库位于 ~/Documents（iCloud 同步），
# iCloud 会在写入后异步追加 com.apple.provenance / com.apple.fileprovider 等属性，
# 撞上 codesign 就会报 "resource fork, Finder information, or similar detritus not allowed"。
# 临时目录不受影响，签完再拷回来。
set -e
cd "$(dirname "$0")"

mkdir -p build
echo "→ 抓取数据…"
ANIMEBAR_OUT="$PWD/build/anime_board.html" python3 board/anime_board.py

echo "→ 检查页面脚本…"
python3 - <<'EOF'
import re
html = open('build/anime_board.html', encoding='utf-8').read()
blocks = re.findall(r'<script>(.*?)</script>', html, re.S)
open('/tmp/animebar-page.js', 'w', encoding='utf-8').write('\n;\n'.join(blocks))
print(f"   提取 {len(blocks)} 段脚本")
EOF
node --check /tmp/animebar-page.js || { echo "! 页面脚本有语法错误"; exit 1; }

echo "→ 编译图标…"
mkdir -p build/icon
xcrun actool --compile build/icon --platform macosx --minimum-deployment-target 12.0 \
  --app-icon AppIcon --output-partial-info-plist build/icon/partial.plist \
  app/AppIcon.icon >/dev/null

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
APP="$STAGE/AnimeBar.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp app/Info.plist "$APP/Contents/Info.plist"
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

xattr -cr "$APP"
if codesign --force -s - "$APP"; then
  echo "✓ 已签名（ad-hoc）"
else
  echo "! 签名失败：本机能跑，但 TCC 权限会随每次重装重新询问"
fi

rm -rf build/AnimeBar.app
ditto "$APP" build/AnimeBar.app
echo "✓ build/AnimeBar.app"
