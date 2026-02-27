#!/usr/bin/env python3
"""
Restructure 選択問題頻出順.md by:
1. Parse each theme block (### N. or #### N.)
2. Count exam refs: lines matching "- 20[0-9]{2}(本|再) 問" (exclude lines with ※)
3. Sort by frequency descending
4. Renumber themes sequentially
5. Output restructured markdown
"""

import re
from pathlib import Path

# Paths
INPUT = Path(__file__).parent.parent / "試験問題" / "選択問題頻出順.md"
OUTPUT = Path(__file__).parent.parent / "試験問題" / "選択問題頻出順.md"

# Pattern for exam references (exclude lines with ※)
REF_PATTERN = re.compile(r"^- 20\d{2}(?:本|再) 問\d+", re.MULTILINE)
EXCLUDE_PATTERN = re.compile(r"※")  # lines with ※ are "not this theme"

# Theme header patterns
H3_PATTERN = re.compile(r"^(### \d+\. .+)$", re.MULTILINE)
H4_PATTERN = re.compile(r"^(#### \d+\. .+)$", re.MULTILINE)
SECTION_PATTERN = re.compile(r"^(## .+)$", re.MULTILINE)


def count_references(text: str) -> int:
    """Count exam references in block, excluding lines with ※."""
    count = 0
    for line in text.splitlines():
        if EXCLUDE_PATTERN.search(line):
            continue
        if REF_PATTERN.search(line):
            count += 1
    return count


def parse_themes(content: str) -> list[tuple[str, int, str]]:
    """Parse from line 18 to end. Return list of (theme_block, count, header_line)."""
    lines = content.splitlines()
    # Find start (line 18, 0-indexed: 17)
    start = 17
    rest = "\n".join(lines[start:])

    themes: list[tuple[str, int, str]] = []

    # Split by ### or #### or ##
    parts = re.split(r"^(### |#### |## )", rest, flags=re.MULTILINE)
    # parts[0] may be empty or intro; then alternating delimiter + content
    i = 1
    current_header = None
    current_content = []
    pending_section_header = None

    while i < len(parts):
        delim = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        i += 2

        full_line = delim + body.split("\n")[0] if body else delim
        rest_of_block = "\n".join(body.split("\n")[1:]) if "\n" in body else ""

        if delim == "## ":
            # Section header (e.g. ## ★★★ 6回出題)
            if current_header is not None and current_content:
                block = "\n".join(current_content)
                cnt = count_references(block)
                themes.append((block, cnt, current_header))
            pending_section_header = full_line
            current_header = None
            current_content = [full_line]
        elif delim in ("### ", "#### "):
            if current_header is not None and current_content:
                block = "\n".join(current_content)
                cnt = count_references(block)
                themes.append((block, cnt, current_header))
            # New theme
            current_header = full_line
            current_content = [full_line]
            if rest_of_block:
                current_content.append(rest_of_block)
        else:
            if current_content is not None:
                current_content.append(delim + (body if not rest_of_block else body))

    if current_header is not None and current_content:
        block = "\n".join(current_content)
        cnt = count_references(block)
        themes.append((block, cnt, current_header))

    return themes


def parse_themes_v2(content: str) -> tuple[str, list[tuple[str, int]]]:
    """Parse file. Return (intro_text, list of (block_content, count))."""
    lines = content.splitlines()
    intro_end = 17  # lines 1-17 are intro (0-indexed: 0-16)
    intro = "\n".join(lines[: intro_end + 1])  # include line 17 (---) or similar

    rest = "\n".join(lines[intro_end:])
    themes: list[tuple[str, int]] = []

    # Find all ### N. or #### N. starts
    theme_matches = list(re.finditer(r"^(#{3,4}) (\d+)\. (.+)$", rest, re.MULTILINE))
    section_matches = list(re.finditer(r"^(## )", rest, re.MULTILINE))

    # Build list of (start_pos, end_pos, level) for each theme
    for idx, m in enumerate(theme_matches):
        start = m.start()
        next_match = theme_matches[idx + 1] if idx + 1 < len(theme_matches) else None
        next_section = None
        for sm in section_matches:
            if sm.start() > start:
                next_section = sm
                break
        if next_match and next_section:
            end = min(next_match.start(), next_section.start())
        elif next_match:
            end = next_match.start()
        elif next_section:
            end = next_section.start()
        else:
            end = len(rest)
        block = rest[start:end].rstrip()
        cnt = count_references(block)
        themes.append((block, cnt))

    return intro, themes


def main():
    content = INPUT.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Intro: lines 1-17 (0-indexed 0-16)
    intro_lines = lines[:17]
    intro = "\n".join(intro_lines)

    # Content to parse: from line 18 (index 17) to end
    rest_lines = lines[17:]
    rest = "\n".join(rest_lines)

    themes: list[tuple[str, int]] = []
    theme_positions: list[tuple[int, int]] = []  # (start, end) in rest

    for i, line in enumerate(rest_lines):
        if re.match(r"^### \d+\. ", line) or re.match(r"^#### \d+\. ", line):
            theme_positions.append((i, -1))
        elif theme_positions and re.match(r"^## ", line):
            # End previous theme before section
            theme_positions[-1] = (theme_positions[-1][0], i)

    # Close last theme
    if theme_positions and theme_positions[-1][1] == -1:
        theme_positions[-1] = (theme_positions[-1][0], len(rest_lines))

    # Also need to split when next theme starts
    theme_starts = []
    for i, line in enumerate(rest_lines):
        if re.match(r"^(###|####) \d+\. ", line):
            theme_starts.append(i)

    prev_end = 0
    for idx, start in enumerate(theme_starts):
        end = theme_starts[idx + 1] if idx + 1 < len(theme_starts) else len(rest_lines)
        # Don't go past next ## section (but content between ## and next theme belongs to next theme)
        for j in range(start + 1, end):
            if rest_lines[j].startswith("## ") and not rest_lines[j].startswith("###"):
                end = j
                break
        block_lines = rest_lines[start:end]
        # If there's orphaned content between prev block and this theme (e.g. ※, ### 【X】), prepend it
        # Skip ## lines since we output those via freq_to_header
        if idx > 0 and prev_end < start:
            gap = rest_lines[prev_end:start]
            for g, line in enumerate(gap):
                if line.startswith("## ") and not line.startswith("###"):
                    block_lines = gap[g + 1 :] + block_lines
                    break
        block = "\n".join(block_lines)
        cnt = count_references(block)
        themes.append((block, cnt))
        prev_end = end

    # Sort by frequency descending; within same frequency, keep original order
    # Use stable sort: first enumerate to keep order, then sort by -count
    indexed = [(i, blk, cnt) for i, (blk, cnt) in enumerate(themes)]
    indexed.sort(key=lambda x: (-x[2], x[0]))

    # Build output: intro + restructured themes
    freq_to_header = {
        6: "## ★★★ 6回出題",
        5: "## ★★★ 5回出題",
        4: "## ★★★ 4回出題",
        3: "## ★★ 3回出題",
        2: "## ★★ 2回出題",
        1: "## ★ 1回のみ出題",
    }

    out_parts = [intro, ""]
    current_freq = None
    theme_num = 1

    for _, block, cnt in indexed:
        if cnt != current_freq:
            current_freq = cnt
            if current_freq in freq_to_header:
                out_parts.append(freq_to_header[current_freq])
                out_parts.append("")
        # Renumber theme: ### 1. -> ### N. or #### 57. -> #### N.
        new_block = re.sub(r"^(#{3,4}) \d+\. ", lambda m: f"{m.group(1)} {theme_num}. ", block, count=1)
        # Remove leading ## section header if block starts with it (avoid duplicate)
        sh = freq_to_header.get(current_freq, "")
        if sh and new_block.strip().startswith(sh):
            new_block = new_block.strip()[len(sh):].lstrip("\n")
        out_parts.append(new_block)
        out_parts.append("")
        theme_num += 1

    output_text = "\n".join(out_parts).rstrip() + "\n"
    OUTPUT.write_text(output_text, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"Themes: {len(themes)}, sorted by frequency (desc), renumbered 1..{theme_num-1}")


if __name__ == "__main__":
    main()
