# QuickPNG-Tinize4Web — Web公開用 高圧縮PNG クイック出力パッチ

## 目的

`input-IMG/` に置かれた**ファイル形式を問わない画像**を、次の要件で `output-TinyPNG/` へ
低サイズの高圧縮PNGとして出力する。

- **長辺（横または縦の長い方）が `MAX_EDGE`px（既定 1180）を超える場合のみ縮小**する
- **アスペクト比は常に維持**する
- **拡大処理は行わない**（元が `MAX_EDGE`px 以下ならそのままの寸法で出力）
- Web公開に不要な**メタデータ（EXIF / DPI / タイムスタンプ / コメント等）を削除**する
- **透過（アルファ）は保持**する

## 返答言語

チャットでの返答は必ず日本語。

## プライバシー方針（重要）

`input-IMG/` の中身（ファイル名・画像内容）は、CLAUDE.md や README 等の**設定・ドキュメント類に
一切含めない**。処理ログやチャット上の一時的な言及に留め、リポジトリへコミットしない。
画像アセットは `.gitignore` によりgit管理外。

## 設定（.env）

作業開始時に必ずリポジトリ直下の `.env` を読み、以下をパイプライン全体へ反映する。無い場合は既定値。

```
MAX_EDGE=1180        # 長辺の最大px。超過時のみ縮小、以下なら拡大せず維持
PALETTE_COLORS=256   # 高圧縮パレットの色数(2-256)
DITHER=1             # ディザリング(1=有効/0=無効)
OXIPNG_LEVEL=6       # oxipng最適化レベル(0-6)
QUANTIZE=1           # パレット量子化(1=行う/0=可逆最適化のみ)
```

## 出力要件（すべて必須）

- 寸法: `long=max(W,H)` が `MAX_EDGE` 超なら `scale=MAX_EDGE/long` で両辺を縮小、以下なら原寸維持（±1px許容）
- 拡大禁止: `scale` は決して 1.0 を超えない
- アルファ: 透過を保持（背景が白に合成されていたら失敗 → やり直し）
- メタデータ: EXIF/pHYs(DPI)/tIME/tEXt 等の付随チャンクを削除（描画に必須な tRNS 等は保持）
- 形式: PNG。ファイル名は元のベース名を維持（拡張子は `.png`）

## 推奨パイプライン: ローカル高圧縮（既定・最優先）

高圧縮とメタデータ削除の実処理は `scripts/tinize.py`（Pillow + pyoxipng）が担う。これが最も
確実に「低サイズの高圧縮PNG」を生成する。

```bash
python3 scripts/tinize.py
```

処理内容（1ファイルあたり）:

1. 画像を開き RGBA へ変換（マルチフレームは先頭フレームのみ）
2. `target_size()` で縮小後寸法を算出（長辺 > `MAX_EDGE` のときのみ、`LANCZOS` で縮小。拡大しない）
3. `QUANTIZE=1` なら `Image.quantize(method=FASTOCTREE, dither=…)` でパレット化（**透過を保持**）
4. `info` を空にしてから PNG 保存（元メタデータを持ち込まない）
5. `oxipng.optimize(strip=StripChunks.safe())` で可逆圧縮 + 補助チャンク（メタデータ）を全削除
6. 出力を開き直して寸法・モードを検証

依存が無い場合: `pip install pillow pyoxipng`

## 任意パイプライン: Adobeハイブリッド（縮小前処理にコネクタを使う場合）

Adobe for creativity コネクタ（MCP）を使って縮小だけをクラウドで行う運用も可能。
ただし高圧縮パレット化・メタデータ削除は行われないため、**最終段は必ず `scripts/tinize.py`
相当の処理（量子化 + oxipng strip）を通す**。

1. `adobe_mandatory_init` を呼び、`get_account_type` が `auth` であることを確認
2. `asset_initialize_file_upload` → transfer URL へ `curl -s -L -X PUT` → `asset_finalize_file_upload`
3. `image_crop_and_resize({imageURI, options:{fit:"pad", output:{width,height}}, outputFileType:"png"})`
   - width/height = 長辺基準で `MAX_EDGE` に合わせた縮小値（拡大にならないよう原寸を超えない）
4. 出力URLをダウンロードし、`scripts/tinize.py` の量子化 + strip 段を適用して `output-TinyPNG/` へ

> Adobeコネクタは認証（claude.ai → 設定 → コネクタ → Adobe for creativity）が必要。
> 未接続・不通時はローカル高圧縮パイプラインをそのまま使えばよい。

## フォールバック: ImageMagickのみ（Python/oxipng が無い環境）

`scripts/local_fallback.sh` を実行（`.env` を自動読込）。実質:

```bash
convert "input.ext[0]" -resize "${MAX_EDGE}x${MAX_EDGE}>" -strip \
  -colors ${PALETTE_COLORS} "PNG8:output.png"
```

`>` フラグにより縮小専用（拡大しない）、`-strip` でメタデータ削除、`PNG8` でパレット高圧縮。

## 検証チェックリスト（毎回・全件）

- PIL で `Image.open(f); im.load()` が通る（ダウンロード切断/破損の検出）
- 長辺が `MAX_EDGE` 以下。かつ**元が `MAX_EDGE` 以下なら原寸のまま**（拡大していない）
- アスペクト比が元と一致（±1pxの丸め差のみ）
- 元が透過なら出力も透過（角ピクセル alpha=0 等で確認）
- pHYs/EXIF/tEXt 等の不要メタデータが残っていない
- 出力サイズが入力より小さい（高圧縮できている）

## 既知の落とし穴

- `-flatten` や誤ったRGB変換は透過を壊す。RGBA→パレットは FASTOCTREE を使い透過を保つ
- パレット256色ではグラデーションにバンディングが出ることがある。気になる場合は `QUANTIZE=0`
  （可逆最適化のみ）または前段でリサイズ品質を上げる
- Coworkのマウント同期: サンドボックスが書いた出力をPC側で見る際、稀に旧内容が残る場合がある。
  出力名を変えて再取得してから差し替える

## ライセンス

このリポジトリの設定・スクリプト・ドキュメントは MIT（`LICENSE` 参照）。
`input-IMG/`・`output-TinyPNG/` の画像アセットは**ライセンス対象外かつgit管理外**。
