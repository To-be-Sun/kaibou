#!/usr/bin/env python3
"""
記号問題頻度順.md の全問題に、試験問題フォルダから問題文・選択肢を付与する。
実行: .venv の python で python scripts/add_problem_text_to_frequency.py
"""

import re
from pathlib import Path


def exam_id_from_filename(name: str) -> str:
    """2022本試験 -> 2022本試, 2022再試験 -> 2022再試"""
    m = re.match(r"(\d{4})(本|再)試験", name)
    if m:
        return f"{m.group(1)}{m.group(2)}試"
    return ""


def parse_question_numbers(heading: str) -> list[int]:
    """## 問1, ## 問36・問38, ## 問35・36・37 などから番号リストを抽出"""
    nums = []
    for part in re.split(r"[・、]", heading):
        m = re.search(r"問(\d+)", part)
        if m:
            nums.append(int(m.group(1)))
    return nums


def extract_problem_choices_answer(text: str, start: int, end: int) -> tuple[str, str, str]:
    """ブロックから問題文・選択肢・正解を抽出"""
    block = text[start:end]
    problem = ""
    choices_lines = []
    answer = ""

    # 問題文: ### 問題文 または #### 問題文 の次
    for pattern in [
        r"#{3,4}\s*問題文[（(]全文[）)]\s*\n+(.+?)(?=\n#{2,4}\s|\n---|\Z)",
        r"#{3,4}\s*問題文[（(]要旨[）)]\s*\n+(.+?)(?=\n#{2,4}\s|\n---|\Z)",
        r"#{3,4}\s*問題文\s*\n+(.+?)(?=\n#{2,4}\s|\n---|\Z)",
    ]:
        prob_match = re.search(pattern, block, re.DOTALL)
        if prob_match:
            problem = prob_match.group(1).strip().replace("\n", " ")
            break

    # 選択肢: ### 選択肢 の次の - **a.** ... 形式（①②③④⑤なども対応）
    choice_match = re.search(
        r"#{3,4}\s*選択肢\s*\n+((?:-\s*\*\*[a-e①②③④⑤⑥⑦⑧⑨⑩][.．、:：]?\*\*[^\n]*\n?)+)",
        block,
    )
    if choice_match:
        raw = choice_match.group(1).strip()
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                choices_lines.append(line[2:].strip())

    # 正解: ### 正解 の次の行（**d.** 手掌を内側に向ける 形式）
    ans_match = re.search(
        r"#{3,4}\s*正解\s*\n+(.+?)(?=\n#{2,4}\s|\n---|\Z)",
        block,
        re.DOTALL,
    )
    if ans_match:
        raw = ans_match.group(1).strip().replace("**", "")
        answer = re.sub(r"\s+", " ", raw.strip())

    choices = " / ".join(choices_lines) if choices_lines else ""
    return problem, choices, answer


def normalize_answer_for_match(s: str) -> str:
    """正解文言の比較用に正規化（選択肢記号を除いたキーワード部分）"""
    s = re.sub(r"^\s*[a-e①②③④⑤⑥⑦⑧⑨⑩]\s*[\.．、:：\s]*", "", s)
    s = s.strip()
    # （xxx）や(xxx)の内容を抽出（④（左大脳半球の下前頭回）→ 左大脳半球の下前頭回）
    s = re.sub(r"[（(]([^）)]*)[）)]", r"\1", s)
    return re.sub(r"\s+", "", s)


def answers_match(row_ans: str, cand_ans: str) -> bool:
    """正解の意味的一致を判定（問番号がずれていても同一問題を検出）"""
    r = normalize_answer_for_match(row_ans)
    c = normalize_answer_for_match(cand_ans)
    if not r or not c:
        return False
    if r == c:
        return True
    # 一方が他方に含まれる場合、短い方が長い方の50%以上であることを要求
    # （「上腕二頭筋」が「上腕動脈…上腕二頭筋腱…」に誤マッチするのを防ぐ）
    if r in c:
        return len(r) >= 0.5 * len(c)
    if c in r:
        return len(c) >= 0.5 * len(r)
    # 主要な文字が含まれるか（手掌・内側など2文字以上）
    r_chars = set(re.findall(r"[一-龥]{2,}|[a-zA-Z]{2,}", r))
    c_chars = set(re.findall(r"[一-龥]{2,}|[a-zA-Z]{2,}", c))
    return bool(r_chars & c_chars)


def build_lookup(
    root: Path,
) -> tuple[
    dict[tuple[str, int], list[tuple[str, str, str]]],
    dict[str, list[tuple[int, str, str, str]]],
]:
    """(試験ID,問番号) および 試験ID->[(問番号,問題文,選択肢,正解),...] を構築"""
    from collections import defaultdict

    by_qnum: dict[tuple[str, int], list[tuple[str, str, str]]] = defaultdict(list)
    by_exam: dict[str, list[tuple[int, str, str, str]]] = defaultdict(list)
    exam_dir = root / "試験問題"

    for md_path in sorted(exam_dir.rglob("*.md")):
        if md_path.name in ("図を含む問題一覧.md", "README.md", "記号問題頻度順.md"):
            continue
        if "問題解説" not in md_path.name:
            continue

        exam_id = exam_id_from_filename(md_path.stem)
        if not exam_id:
            continue

        text = md_path.read_text(encoding="utf-8")

        for m in re.finditer(
            r"^#{2,4}\s+(問\d+(?:[・、]問?\d+)*)\s*(?:[（(][^）)]*[）)])?\s*$",
            text,
            re.MULTILINE,
        ):
            q_nums = parse_question_numbers(m.group(1))
            if not q_nums:
                continue

            # 次の問題見出し（## 問N）または次の大見出しまでをブロックとする
            next_m = re.search(r"\n^#{2,4}\s+問\d", text[m.end() :], re.MULTILINE)
            if not next_m:
                next_m = re.search(r"\n^#{2,3}\s+", text[m.end() :], re.MULTILINE)
            block_end = m.end() + next_m.start() if next_m else len(text)

            problem, choices, answer = extract_problem_choices_answer(
                text, m.end(), block_end
            )

            for qn in q_nums:
                if problem or choices:
                    entry = (problem, choices, answer)
                    by_qnum[(exam_id, qn)].append(entry)
                    by_exam[exam_id].append((qn, problem, choices, answer))

    return dict(by_qnum), dict(by_exam)


def format_problem_block(problem: str, choices: str) -> str:
    """問題文・選択肢をMarkdownブロックとしてフォーマット"""
    lines = []
    if problem:
        lines.append(f"- **問題文** {problem}")
    if choices:
        lines.append(f"- **選択肢** {choices}")
    if not lines:
        return ""
    return "\n".join(lines)


def main():
    root = Path(__file__).resolve().parent.parent
    exam_dir = root / "試験問題"
    freq_path = exam_dir / "記号問題頻度順.md"

    content = freq_path.read_text(encoding="utf-8")
    # 既存の誤追加ブロックを削除（前回実行分）
    content = re.sub(r"\n- \*\*問題文\*\* [^\n]+", "", content)
    content = re.sub(r"\n- \*\*選択肢\*\* [^\n]+", "", content)

    by_qnum, by_exam = build_lookup(root)

    def replace_row(m: re.Match) -> str:
        full_line = m.group(0)
        exam = m.group(1).strip()
        q_part = m.group(2).strip()
        row_ans = m.group(3).strip()

        q_num_match = re.search(r"問(\d+)", q_part)
        if not q_num_match:
            return full_line

        q_num = int(q_num_match.group(1))
        candidates = by_qnum.get((exam, q_num), [])
        prob, choices = "", ""

        for p, c, a in candidates:
            if answers_match(row_ans, a):
                prob, choices = p, c
                break

        if not prob and exam in by_exam:
            for _qn, p, c, a in by_exam[exam]:
                if answers_match(row_ans, a):
                    prob, choices = p, c
                    break

        block = format_problem_block(prob, choices)
        if block:
            return f"{full_line}\n{block}"
        return full_line

    pattern = re.compile(
        r"^\|\s*(202\d(?:本|再)試)\s*\|\s*(問\d+)\s*\|\s*([^|]+)\s*\|$",
        re.MULTILINE,
    )
    new_content = pattern.sub(replace_row, content)

    freq_path.write_text(new_content, encoding="utf-8")
    print(f"Updated {freq_path}")


if __name__ == "__main__":
    main()
