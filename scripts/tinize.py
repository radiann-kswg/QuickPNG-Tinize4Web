#!/usr/bin/env python3
"""QuickPNG-Tinize4Web 変換本体。

input-IMG/ 内のファイル形式を問わない画像を:
  1. 長辺が MAX_EDGE px を超える場合のみ、アスペクト比を維持して縮小（拡大はしない）
  2. Web公開に不要なメタデータ（EXIF/DPI/タイムスタンプ等）を削除
  3. パレット量子化 + oxipng で低サイズの高圧縮PNGへ変換
して output-TinyPNG/ へ出力する。透過（アルファ）は保持する。

設定はリポジトリ直下の .env（無ければ既定値）から読み込む。
依存: Pillow, pyoxipng
"""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

from PIL import Image

try:
    import oxipng
except ImportError:
    oxipng = None

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input-IMG"
OUTPUT_DIR = ROOT / "output-TinyPNG"

DEFAULTS = {
    "MAX_EDGE": 1180,
    "PALETTE_COLORS": 256,
    "DITHER": 1,
    "OXIPNG_LEVEL": 6,
    "QUANTIZE": 1,
    # 中間設定: truecolorを保ったままチャンネルのビット深度を落として高圧縮する。
    # 0 または 8 = 無効(フル8bit)。5/6/7 を指定するとそのビット数へ量子化(6が画質/サイズの良バランス)。
    # QUANTIZE=1 が優先される。色を保ちたい場合は QUANTIZE=0 かつ COLOR_BITS=6 を推奨。
    "COLOR_BITS": 0,
}

# Pillow が扱える一般的な入力拡張子（形式は問わない方針だが明らかな非画像は除外）
IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff",
    ".ppm", ".pgm", ".tga", ".ico", ".jfif", ".psd",
}


def load_env() -> dict:
    cfg = dict(DEFAULTS)
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k in cfg:
                try:
                    cfg[k] = int(v)
                except ValueError:
                    pass
    return cfg


def _posterize_rgb(im: "Image.Image", bits: int) -> "Image.Image":
    """RGB各チャンネルを bits ビットへ量子化（truecolor維持・アルファは温存）。numpy不要。"""
    shift = 8 - bits
    step = 1 << shift
    lut = [min(((i >> shift) << shift) + step // 2, 255) for i in range(256)]
    r, g, b, a = im.split()
    r, g, b = r.point(lut), g.point(lut), b.point(lut)
    return Image.merge("RGBA", (r, g, b, a))


def target_size(w: int, h: int, max_edge: int) -> tuple[int, int]:
    """長辺が max_edge を超える場合のみ縮小。拡大はしない。アスペクト比維持。"""
    long_edge = max(w, h)
    if long_edge <= max_edge:
        return w, h
    scale = max_edge / long_edge
    return max(1, round(w * scale)), max(1, round(h * scale))


def convert_one(src: Path, cfg: dict) -> dict:
    with Image.open(src) as im:
        im.seek(0)  # マルチフレームは先頭のみ
        im = im.convert("RGBA")
        ow, oh = im.size

        tw, th = target_size(ow, oh, cfg["MAX_EDGE"])
        resized = ow != tw or oh != th
        if resized:
            im = im.resize((tw, th), Image.LANCZOS)

        bits = cfg["COLOR_BITS"]
        if cfg["QUANTIZE"]:
            dither = Image.Dither.FLOYDSTEINBERG if cfg["DITHER"] else Image.Dither.NONE
            colors = max(2, min(256, cfg["PALETTE_COLORS"]))
            # FASTOCTREE はRGBAの透過を保持したままパレット化できる（最大圧縮・256色上限）
            out_im = im.quantize(colors=colors, method=Image.Quantize.FASTOCTREE, dither=dither)
        elif 1 <= bits <= 7:
            # 中間設定: truecolorを維持したままRGB各chをbitsビットへ量子化（透過は保持）
            out_im = _posterize_rgb(im, bits)
        else:
            out_im = im

    dst = OUTPUT_DIR / (src.stem + ".png")
    # 新規Imageに描き直し、元画像由来のinfo（メタデータ）を持ち込まない
    out_im.info = {}
    out_im.save(dst, format="PNG", optimize=True)

    # oxipng: 可逆で更に圧縮しつつ、描画に不要な補助チャンク（メタデータ）を全削除
    if oxipng is not None:
        level = max(0, min(6, cfg["OXIPNG_LEVEL"]))
        oxipng.optimize(str(dst), level=level, strip=oxipng.StripChunks.safe())

    # 検証用に読み直す
    with Image.open(dst) as chk:
        chk.load()
        cmode, csize = chk.mode, chk.size

    return {
        "name": src.name,
        "out": dst.name,
        "orig_px": (ow, oh),
        "out_px": csize,
        "resized": resized,
        "mode": cmode,
        "orig_kb": src.stat().st_size / 1024,
        "out_kb": dst.stat().st_size / 1024,
    }


def main() -> int:
    cfg = load_env()
    if oxipng is None:
        print("warn: pyoxipng 未導入。可逆最適化とメタデータ全削除はスキップされます "
              "(`pip install pyoxipng`)", file=sys.stderr)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        p for p in INPUT_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )
    if not files:
        print(f"input-IMG に変換対象の画像がありません: {INPUT_DIR}")
        return 0

    print(f"settings: MAX_EDGE={cfg['MAX_EDGE']} PALETTE_COLORS={cfg['PALETTE_COLORS']} "
          f"DITHER={cfg['DITHER']} OXIPNG_LEVEL={cfg['OXIPNG_LEVEL']} QUANTIZE={cfg['QUANTIZE']} "
          f"COLOR_BITS={cfg['COLOR_BITS']}")

    total_in = total_out = 0.0
    ok = 0
    for f in files:
        try:
            r = convert_one(f, cfg)
        except Exception as e:  # noqa: BLE001
            print(f"  ERR  {f.name}: {e}", file=sys.stderr)
            continue
        total_in += r["orig_kb"]
        total_out += r["out_kb"]
        ok += 1
        flag = "resize" if r["resized"] else "keep  "
        print(f"  OK  {flag} {r['orig_px'][0]}x{r['orig_px'][1]} -> "
              f"{r['out_px'][0]}x{r['out_px'][1]}  "
              f"{r['orig_kb']:7.1f}KB -> {r['out_kb']:6.1f}KB  [{r['mode']}]  {r['out']}")

    if ok:
        ratio = 100 * total_out / total_in if total_in else 0
        print(f"done: {ok}/{len(files)} 件  合計 {total_in/1024:.2f}MB -> "
              f"{total_out/1024:.2f}MB ({ratio:.1f}%)")
    subprocess.run([sys.executable, str(Path(__file__).with_name("iloveapi_compress.py"))])  # 後段: iLoveAPI 圧縮（.env で有効時のみ）
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
