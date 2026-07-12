# QuickPNG-Tinize4Web

ファイル形式を問わない画像を、**長辺が最大 `MAX_EDGE`px（既定 1180）** になるまで縮小し、
Web公開に不要なメタデータを削除した**低サイズの高圧縮PNG**へクイック変換する、
Claude（Cowork / Claude Code）向けパイプライン設定。

- アスペクト比は常に維持し、**拡大は行わない**（元が基準px以下ならそのまま）
- 透過（アルファ）は保持
- EXIF・DPI・タイムスタンプ等の付随メタデータを削除

## 使い方

1. `input-IMG/` に変換したい画像を置く（PNG / JPEG / WebP / GIF / BMP / TIFF など形式は不問）
2. `.env.example` を `.env` にリネームコピーする（必要に応じてパラメータを変更）
3. Claude Desktop（Cowork）または Claude Code でこのフォルダを開く
4. 「input-IMG のファイルを output-TinyPNG へ変換して」と依頼する
   — Claude が `CLAUDE.md` の手順に従って処理する
5. 結果は `output-TinyPNG/` に出力される

## 直接実行（Claudeを介さず手元で回す場合）

```bash
python3 scripts/tinize.py
```

`.env`（無ければ既定値）を読み込み、`input-IMG/` 内の全画像を変換して `output-TinyPNG/` へ出力する。

## 構成

```
CLAUDE.md            # Claude向けパイプライン定義（本体）
README.md            # 本ファイル
.env.example         # 変換パラメータのテンプレート
scripts/tinize.py    # 変換本体（Pillow + oxipng）
scripts/local_fallback.sh  # ImageMagickベースの簡易フォールバック
input-IMG/           # 入力（git管理外）
output-TinyPNG/      # 出力（git管理外）
```

## 設定（.env）

| 変数              | 既定値  | 意味                                                     |
| --------------- | ---- | ------------------------------------------------------ |
| `MAX_EDGE`      | 1180 | 長辺の最大px。超過時のみ縮小、以下なら拡大せず維持。          |
| `PALETTE_COLORS`| 256  | 高圧縮のためのパレット色数(2-256)。                        |
| `DITHER`        | 1    | ディザリング(1=有効/0=無効)。                             |
| `OXIPNG_LEVEL`  | 6    | oxipngの最適化レベル(0-6)。                               |
| `QUANTIZE`      | 1    | パレット量子化(1=行う/0=可逆最適化のみ)。                   |

## 前提

- Python 3 と Pillow / pyoxipng（`pip install pillow pyoxipng`）
- 縮小前処理に Adobe for creativity コネクタを使う運用も可能（`CLAUDE.md` 参照）。
  高圧縮・メタデータ削除の実処理は `scripts/tinize.py` が担う。

## ライセンス

設定・スクリプト・ドキュメントは [MIT License](LICENSE)。
`input-IMG/`・`output-TinyPNG/` の画像アセットは**ライセンス対象外かつgit管理外**。
