#!/usr/bin/env python3
"""
図を含む問題を試験問題フォルダから抽出し、一覧Markdownを生成する。
実行: .venv の python で python scripts/extract_figure_questions.py
"""

import re
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    exam_dir = root / "試験問題"
    out_path = root / "試験問題" / "図を含む問題一覧.md"

    # 図問題セクション: ## 問N（図問題） または ### 問N・問M（図問題
    fig_heading = re.compile(
        r"^#{2,3}\s+(問\d+[・問\d]*)\s*[（(]図問題", re.MULTILINE
    )
    # 問題文内の図関連キーワード（要旨抽出用）
    fig_keywords = re.compile(r"図で選|図に示す|図示|模式図|図の番号|図の矢印|図の斜線")

    results = []  # (範囲, ファイル名, 問番号, 要旨)

    for md_path in sorted(exam_dir.rglob("*.md")):
        if md_path.name in ("図を含む問題一覧.md", "README.md"):
            continue
        rel = md_path.relative_to(exam_dir)
        scope = rel.parts[0] if len(rel.parts) > 1 else "ルート"
        text = md_path.read_text(encoding="utf-8")

        for m in fig_heading.finditer(text):
            qnum = m.group(1).strip()
            start = m.end()
            # 次の「## 」見出しまでをブロックとして取得（### は含める）
            next_h = re.search(r"\n##\s+", text[start:])
            end = start + next_h.start() if next_h else len(text)
            block = text[start:end].strip()
            # 要旨：問題文らしい行を優先（図・選・どれか・示す を含む）、次に見出し以外
            lines = []
            for line in block.split("\n"):
                s = line.strip().replace("#", "").replace("**", "").strip()
                if not s or len(s) < 3:
                    continue
                if s in ("）", "---", "（", "）", "正解", "解説", "選択肢"):
                    continue
                if re.match(r"^[・\-*]\s*$", s):
                    continue
                lines.append(s)
                if len(" ".join(lines)) >= 180:
                    break
                if len(lines) >= 6:
                    break
            summary = " ".join(lines[:6]).strip()
            if not summary:
                for line in block.split("\n"):
                    s = line.strip().replace("#", "").replace("**", "").strip()
                    if len(s) > 15 and ("図" in s or "選" in s or "示す" in s or "どれか" in s):
                        summary = s[:220] + ("..." if len(s) > 220 else "")
                        break
            if len(summary) > 250:
                summary = summary[:247] + "..."
            results.append((scope, md_path.name, qnum, summary))

    # 範囲・ファイル名・問番号で一意に
    seen = set()
    unique = []
    for scope, fname, qnum, summary in results:
        key = (scope, fname, qnum)
        if key not in seen:
            seen.add(key)
            unique.append((scope, fname, qnum, summary))

    # 範囲ごとにまとめてMarkdown生成
    by_scope = {}
    for scope, fname, qnum, summary in unique:
        by_scope.setdefault(scope, []).append((fname, qnum, summary))

    lines_out = [
        "# 図を含む問題 一覧",
        "",
        "過去問から「（図問題）」として記載されている問題を抽出した一覧です。",
        "実際の試験では図が配布されるため、本一覧では問題文・要旨のみ記載しています。",
        "",
        "---",
        "",
    ]
    for scope in sorted(by_scope.keys()):
        lines_out.append(f"## {scope}")
        lines_out.append("")
        for fname, qnum, summary in sorted(by_scope[scope], key=lambda x: (x[0], x[1])):
            lines_out.append(f"- **{qnum}**（{fname}）")
            if summary:
                lines_out.append(f"  {summary[:220]}{'...' if len(summary) > 220 else ''}")
            lines_out.append("")
        lines_out.append("---")
        lines_out.append("")

    out_path.write_text("\n".join(lines_out), encoding="utf-8")
    print(f"出力: {out_path}")
    print(f"図を含む問題: {len(unique)} 件")


if __name__ == "__main__":
    main()
