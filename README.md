# QuickPNG-Tinize4Web

ファイル形式を問わない画像を、**長辺が最大 `MAX_EDGE`px（既定 1180）** になるまで縮小し、
Web公開に不要なメタデータを削除した**低サイズの高圧縮PNG**へクイック変換する、
Claude（Cowork / Claude Code）向けパイプライン設定。

- アスペクト比は常に維持し、**拡大は行わない**（元が基準px以下ならそのまま）
- 透過（アルファ）は保持
- EXIF・DPI・タイムスタンプ等の付随メタデータを削除

姉妹リポジトリ:

- [QuickPNG-To256Permill](https://github.com/radiann-kswg/QuickPNG-To256Permill) — PSDカンバスの256‰縮小PNG出力
- [QuickPNG-SmartObjectExport](https://github.com/radiann-kswg/QuickPNG-SmartObjectExport) — PSD埋め込みスマートオブジェクトの変形初期化PNG抽出

## 使い方

1. `input-IMG/` に変換したい画像を置く（PNG / JPEG / WebP / GIF / BMP / TIFF など形式は不問）
2. `.env.example` を `.env` にリネームコピーする（必要に応じてパラメータを変更）
3. Claude Desktop（Cowork）または Claude Code でこのフォルダを開く
4. 「input-IMG のファイルを output-TinyPNG へ変換して」と依頼する
   — Claude が `CLAUDE.md` の手順に従って処理する
5. 結果は `output-TinyPNG/` に出力される

## 直接実行（Claudeを介さず手元で回す場合）

```bash
pip install -r requirements.txt
# Cowork のサンドボックスなど PEP 668 管理環境では:
#   pip install -r requirements.txt --break-system-packages
python3 scripts/tinize.py
```

`.env`（無ければ既定値）を読み込み、`input-IMG/` 内の全画像を変換して `output-TinyPNG/` へ出力する。

macOS では venv を使う（姉妹リポジトリと並べた親フォルダに共有 `.venv` を作ると使い回せる）。
Python 3.14 では pyoxipng がソースビルドになるため、初回の導入に数分かかる。

```bash
python3 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt
../.venv/bin/python scripts/tinize.py
```

## 構成

```
CLAUDE.md            # Claude向けパイプライン定義（本体）
README.md            # 本ファイル
.env.example         # 変換パラメータのテンプレート
.env                 # 実際の変換パラメータ（git管理外・要作成）
requirements.txt     # Python依存（Pillow / pyoxipng）
scripts/tinize.py    # 変換本体（Pillow + oxipng）
scripts/local_fallback.sh  # ImageMagickベースの簡易フォールバック
input-IMG/           # 入力（git管理外）
output-TinyPNG/      # 出力（git管理外）
```

## 設定（.env）

| 変数              | 既定値  | 意味                                                     |
| --------------- | ---- | ------------------------------------------------------ |
| `MAX_EDGE`      | 1180 | 長辺の最大px。超過時のみ縮小、以下なら拡大せず維持。          |
| `PALETTE_COLORS`| 256  | 高圧縮のためのパレット色数(2-256)。0 = 量子化しない（`QUANTIZE=0` と同じ）。 |
| `DITHER`        | 1    | ディザリング(1=有効/0=無効)。                             |
| `OXIPNG_LEVEL`  | 6    | oxipngの最適化レベル(0-6)。                               |
| `QUANTIZE`      | 1    | パレット量子化(1=行う/0=可逆最適化のみ)。                   |
| `COLOR_BITS`    | 0    | truecolor維持でchビット深度を削減(0/8=無効、5/6/7)。`QUANTIZE=1` 時は無視。 |

### 圧縮モードの選び方（画質 vs サイズ）

| 設定                            | 画質                          | サイズ |
| ------------------------------- | ----------------------------- | ------ |
| `QUANTIZE=1`                    | 256色パレット。グラデーションにバンディングが出やすい | 最小   |
| `QUANTIZE=0` + `COLOR_BITS=6`   | **推奨**。truecolor維持で高品質（PSNR≈47dB）        | 可逆の約6割 |
| `QUANTIZE=0` + `COLOR_BITS=0`   | 完全可逆（無劣化）                                  | 最大   |

`COLOR_BITS` は `7`=ほぼ無劣化 / `6`=高品質バランス / `5`=やや軽量。

## 前提

- Python 3 と Pillow / pyoxipng（`pip install -r requirements.txt`）
- 縮小前処理に Adobe for creativity コネクタを使う運用も可能（`CLAUDE.md` 参照）。
  高圧縮・メタデータ削除の実処理は `scripts/tinize.py` が担う。
- Python/oxipng が無い環境向けに ImageMagick のみのフォールバック（`scripts/local_fallback.sh`）あり。
  macOS では `brew install imagemagick` の上で `bash scripts/local_fallback.sh` で実行する。

## 出力の検証

変換後、全件について次を確認する（詳細は `CLAUDE.md`）。

- PILで開けること（破損の検出）
- 長辺が `MAX_EDGE` 以下。かつ**元が `MAX_EDGE` 以下なら原寸のまま**（拡大していない）
- アスペクト比が元と一致（±1pxの丸め差のみ）
- 元が透過なら出力も透過
- pHYs/EXIF/tEXt 等の不要メタデータが残っていない
- 出力サイズが入力より小さい

## ライセンス

設定・スクリプト・ドキュメントは [MIT License](LICENSE)。
`input-IMG/`・`output-TinyPNG/` の画像アセットは**ライセンス対象外かつgit管理外**。
