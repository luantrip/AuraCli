"""Duplicate code detection using token-based line hashing."""

import hashlib
import re


def detect_duplicates(
    source: str, filepath: str = "", min_lines: int = 6
) -> list[dict]:
    """Detect duplicate code blocks in source.

    Args:
        source: Python source code string.
        filepath: Optional filepath for context.
        min_lines: Minimum consecutive lines to consider a duplicate.

    Returns:
        List of finding dicts with duplicate location pairs.
    """
    lines = source.splitlines()
    if len(lines) < min_lines * 2:
        return []

    normalized = [_normalize(line) for line in lines]

    # Build hash -> list of start positions
    seen: dict[str, list[int]] = {}
    for i in range(len(normalized) - min_lines + 1):
        block = "\n".join(normalized[i : i + min_lines])
        if not block.strip():
            continue
        h = hashlib.md5(block.encode(), usedforsecurity=False).hexdigest()
        seen.setdefault(h, []).append(i)

    # Collect raw duplicate pairs
    pairs: list[tuple[int, int, int]] = []  # (start_a, start_b, length)
    for positions in seen.values():
        if len(positions) < 2:
            continue
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                a, b = positions[i], positions[j]
                # Skip overlapping blocks
                if abs(a - b) < min_lines:
                    continue
                pairs.append((a, b, min_lines))

    # Merge overlapping pairs
    merged = _merge_pairs(pairs, len(lines))

    findings: list[dict] = []
    for a_start, a_end, b_start, b_end in merged:
        num_lines = a_end - a_start + 1
        findings.append(
            {
                "type": "duplicate",
                "line_start_a": a_start + 1,
                "line_end_a": a_end + 1,
                "line_start_b": b_start + 1,
                "line_end_b": b_end + 1,
                "lines": num_lines,
                "message": f"Duplicate block of {num_lines} lines",
                "severity": "medium",
            }
        )

    return findings


def _normalize(line: str) -> str:
    """Normalize a line by stripping comments and collapsing whitespace."""
    line = re.sub(r"#.*$", "", line)
    return " ".join(line.split())


def _merge_pairs(
    pairs: list[tuple[int, int, int]], total_lines: int
) -> list[tuple[int, int, int, int]]:
    """Merge overlapping duplicate regions into consolidated pairs."""
    if not pairs:
        return []

    # Group by (a_start, b_start) proximity and extend
    # Sort by first position
    pairs.sort()

    merged: list[tuple[int, int, int, int]] = []
    used: set[int] = set()

    for idx, (a, b, length) in enumerate(pairs):
        if idx in used:
            continue
        a_end = a + length - 1
        b_end = b + length - 1
        # Try to extend with subsequent pairs
        for idx2 in range(idx + 1, len(pairs)):
            if idx2 in used:
                continue
            a2, b2, l2 = pairs[idx2]
            # Check if this pair extends the current one
            if a2 <= a_end + 1 and b2 <= b_end + 1 and a2 >= a and b2 >= b:
                a_end = max(a_end, a2 + l2 - 1)
                b_end = max(b_end, b2 + l2 - 1)
                used.add(idx2)

        merged.append((a, a_end, b, b_end))

    # Deduplicate (avoid reporting A,B and B,A)
    seen: set[tuple[int, int, int, int]] = set()
    result = []
    for item in merged:
        a_s, a_e, b_s, b_e = item
        key = (min(a_s, b_s), min(a_e, b_e), max(a_s, b_s), max(a_e, b_e))
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result
