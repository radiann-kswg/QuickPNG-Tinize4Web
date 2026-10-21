#!/usr/bin/env bash
# QuickPNG-Tinize4Web フォールバック（ImageMagickのみ）
#
# scripts/tinize.py（Pillow+oxipng）が使えない環境向けの簡易版。
# input-IMG/ の画像を:
#   - 長辺が MAX_EDGE px を超える場合のみ縮小（"...>" フラグ = 縮小専用・拡大しない）
#   - -strip で付随メタデータ（EXIF/DPI/コメント等）を削除
#   - PNG8 パレット + 最大圧縮で高圧縮PNG化（透過は保持）
# して output-TinyPNG/ へ出力する。設定はリポジトリ直下の .env から読み込む。
set -euo pipefail
cd "$(dirname "$0")/.."

# 既定値
MAX_EDGE=1180
PALETTE_COLORS=256
QUANTIZE=1

# .env 読み込み（KEY=VALUE のみ。コメント・空行・未知キーは無視）
if [ -f .env ]; then
  while IFS='=' read -r k v; do
    v=${v%%#*}
    v=${v//[[:space:]]/}
    case "$k" in
      MAX_EDGE | PALETTE_COLORS | QUANTIZE) printf -v "$k" '%s' "$v" ;;
    esac
  done < <(grep -E '^[A-Z_]+=' .env)
fi

echo "settings: MAX_EDGE=${MAX_EDGE} PALETTE_COLORS=${PALETTE_COLORS} QUANTIZE=${QUANTIZE}"
mkdir -p output-TinyPNG
shopt -s nullglob nocaseglob
count=0
for f in input-IMG/*.png input-IMG/*.jpg input-IMG/*.jpeg input-IMG/*.webp \
         input-IMG/*.gif input-IMG/*.bmp input-IMG/*.tif input-IMG/*.tiff; do
  [ -e "$f" ] || continue
  base=$(basename "$f"); base=${base%.*}
  out="output-TinyPNG/${base}.png"
  if [ "${QUANTIZE}" = "1" ]; then
    convert "${f}[0]" -resize "${MAX_EDGE}x${MAX_EDGE}>" -strip \
      -quality 95 -define png:compression-level=9 \
      "PNG8:${out}"
    # PNG8 だけでは色数固定なので、必要なら明示量子化
    convert "${out}" -colors "${PALETTE_COLORS}" "PNG8:${out}"
  else
    convert "${f}[0]" -resize "${MAX_EDGE}x${MAX_EDGE}>" -strip \
      -define png:compression-level=9 "PNG32:${out}"
  fi
  identify -format "%f | %wx%h | alpha=%A | %b\n" "${out}"
  count=$((count + 1))
done
# 後段: iLoveAPI 圧縮（.env で有効時のみ。python3 が無ければ python）
(command -v python3 >/dev/null && python3 scripts/iloveapi_compress.py) || python scripts/iloveapi_compress.py || true
echo "done: ${count} file(s)"
