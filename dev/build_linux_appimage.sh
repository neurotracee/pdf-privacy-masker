#!/usr/bin/env bash
# 构建 Linux AppImage。只能在 Linux 上跑（CI 的 ubuntu runner，或本机 Linux）。
#
#   bash dev/build_linux_appimage.sh               # 只构建
#   bash dev/build_linux_appimage.sh --smoke       # 构建 + 冒烟
#   bash dev/build_linux_appimage.sh --smoke-only  # 不构建，只对已有产物冒烟
#
# 依赖：python3 + requirements.txt + pyinstaller，联网下载 appimagetool（约 10 MB）。
# 产物：dist/PDFPrivacyMasker-<版本>-x86_64.AppImage
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="build"
case "${1:-}" in
  --smoke)      MODE="build-smoke" ;;
  --smoke-only) MODE="smoke" ;;
  "")           MODE="build" ;;
  *) echo "未知参数：$1"; exit 2 ;;
esac

PY="${PYTHON:-python3}"

VER="$("$PY" - <<'EOF'
import io, re
s = io.open("pdfmask.py", encoding="utf-8").read()
print(re.search(r'VERSION\s*=\s*"([^"]+)"', s).group(1))
EOF
)"
OUT="dist/PDFPrivacyMasker-${VER}-x86_64.AppImage"

# ------------------------------------------------------------------ 冒烟
smoke() {
  local img="$1"
  echo "== 冒烟 $img =="
  # 不要写成 `... | head -3`：head 提前关掉管道会让程序收到 SIGPIPE 并报
  # BrokenPipeError，在 set -e 下被当成冒烟失败。先落盘再取前几行。
  "$img" --appimage-extract-and-run --about > build/about.txt 2>&1 || {
    echo "冒烟失败：--about 退出码非 0"; cat build/about.txt; return 1; }
  head -3 build/about.txt
  "$img" --appimage-extract-and-run --ocr-check > build/ocr.txt 2>&1 || {
    echo "冒烟失败：--ocr-check 退出码非 0"; cat build/ocr.txt; return 1; }
  head -3 build/ocr.txt

  PDFMASK_NO_OPEN=1 PYTHONUNBUFFERED=1 "$img" --appimage-extract-and-run > build/smoke.log 2>&1 &
  local pid=$!
  local url=""
  for _ in $(seq 1 40); do
    url="$(grep -oE 'http://127\.0\.0\.1:[0-9]+' build/smoke.log | head -1 || true)"
    if [ -z "$url" ]; then
      # 老版本的程序没有 flush，地址可能还卡在缓冲区里；直接从监听端口反查，
      # 这样冒烟不依赖被测程序把话打出来。
      port="$(ss -ltnp 2>/dev/null | awk '/pdfmask/ {print $4}' | head -1 | sed 's/.*://')"
      [ -n "${port:-}" ] && url="http://127.0.0.1:$port"
    fi
    [ -n "$url" ] && break
    sleep 1
  done
  if [ -z "$url" ]; then
    echo "冒烟失败：本地服务没起来"
    cat build/smoke.log
    kill $pid 2>/dev/null || true
    return 1
  fi
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' "$url/")"
  echo "  首页 HTTP $code  $url"
  kill $pid 2>/dev/null || true
  wait $pid 2>/dev/null || true
  [ "$code" = "200" ] || { echo "冒烟失败：首页不是 200"; return 1; }
  echo "== 冒烟通过 =="
}

if [ "$MODE" = "smoke" ]; then
  test -f "$OUT" || { echo "没有 $OUT，先构建"; exit 1; }
  smoke "$OUT"
  exit 0
fi

echo "== 版本 $VER =="

# 1) 图标：从 app.ico 转 PNG（.desktop / AppImage 不认 ico）
"$PY" dev/make_linux_icon.py

# 2) PyInstaller onedir
"$PY" -m PyInstaller pdfmask-linux.spec --noconfirm \
      --distpath build/pyi --workpath build/work

test -x "build/pyi/pdfmask/pdfmask" || {
  echo "打包失败：build/pyi/pdfmask/pdfmask 不存在"; exit 1; }

# 3) 组装 AppDir（AppImage 的目录树规范）
APPDIR="build/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" \
         "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
         "$APPDIR/usr/share/applications"
cp -a build/pyi/pdfmask "$APPDIR/usr/bin/pdfmask"
cp build/appimage/pdfmask.png "$APPDIR/pdfmask.png"
cp build/appimage/pdfmask.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/pdfmask.png"
cp dev/appimage/pdfmask.desktop "$APPDIR/pdfmask.desktop"
cp dev/appimage/pdfmask.desktop "$APPDIR/usr/share/applications/pdfmask.desktop"
cp dev/appimage/AppRun "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"

# 4) appimagetool（本身也是 AppImage，无 FUSE 时用 --appimage-extract-and-run）
TOOL="${APPIMAGETOOL:-build/appimagetool-x86_64.AppImage}"
if [ ! -x "$TOOL" ]; then
  echo "下载 appimagetool ..."
  curl -fL --retry 3 --connect-timeout 20 -o "$TOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "$TOOL"
fi

rm -f "$OUT"
mkdir -p dist
ARCH=x86_64 VERSION="$VER" "$TOOL" --appimage-extract-and-run "$APPDIR" "$OUT"
test -f "$OUT" || { echo "appimagetool 没产出 $OUT"; exit 1; }
chmod +x "$OUT"
echo "== 产物 $OUT（$(du -h "$OUT" | cut -f1)）=="

sha256sum "$OUT" | tee "dist/SHA256SUMS-linux.txt"

if [ "$MODE" = "build-smoke" ]; then
  smoke "$OUT"
fi
