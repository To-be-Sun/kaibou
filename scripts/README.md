# scripts

## 図を含む問題の抽出

`.venv` の Python で実行します。

```bash
# プロジェクトルートで
.venv/bin/python scripts/extract_figure_questions.py
```

- **入力**: `試験問題/` 以下の各範囲の `*_問題解説.md`
- **出力**: `試験問題/図を含む問題一覧.md`（「（図問題）」として記載されている問題の一覧）

初回はプロジェクトルートで `.venv` を作成してください。

```bash
python3 -m venv .venv
```
