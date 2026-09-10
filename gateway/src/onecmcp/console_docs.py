from __future__ import annotations

import html
import re
from pathlib import Path


def docs_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "docs",
        here.parents[2] / "docs",
        Path("/app/docs"),
        Path.cwd() / "docs",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]


def resolve_doc(file_name: str) -> Path | None:
    root = docs_root()
    relative = file_name.replace("\\", "/").lstrip("/")
    if ".." in Path(relative).parts:
        return None
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    if path.is_file():
        return path
    return None


def markdown_to_html(source: str) -> str:
    text = source.replace("\r\n", "\n")
    fences: list[str] = []

    def _fence(match: re.Match[str]) -> str:
        lang = html.escape(match.group(1) or "")
        body = html.escape(match.group(2))
        fences.append(f'<pre class="code" data-lang="{lang}"><code>{body}</code></pre>')
        return f"\x00FENCE{len(fences) - 1}\x00"

    text = re.sub(r"```(\w*)\n(.*?)```", _fence, text, flags=re.S)
    chunks: list[str] = []
    for raw_block in re.split(r"\n{2,}", text.strip()):
        block = raw_block.strip()
        if not block:
            continue
        if block.startswith("\x00FENCE"):
            chunks.append(block)
            continue
        if block.startswith("!!!"):
            first, _, rest = block.partition("\n")
            kind = first[3:].strip().split(" ", 1)[0] or "note"
            chunks.append(
                f'<aside class="admonition {html.escape(kind)}">{_inline(rest or first)}</aside>'
            )
            continue
        if block.startswith("|") and "\n|" in block:
            chunks.append(_table(block))
            continue
        if re.match(r"^#{1,6} ", block):
            hashes, title = block.split(" ", 1)
            level = min(6, len(hashes))
            chunks.append(f"<h{level}>{_inline(title)}</h{level}>")
            continue
        if all(line.strip().startswith(("- ", "* ")) for line in block.splitlines()):
            items = "".join(f"<li>{_inline(line.strip()[2:])}</li>" for line in block.splitlines())
            chunks.append(f"<ul>{items}</ul>")
            continue
        if all(re.match(r"^\d+\. ", line.strip()) for line in block.splitlines()):
            items = "".join(
                f"<li>{_inline(re.sub(r'^\d+\.\s+', '', line.strip()))}</li>"
                for line in block.splitlines()
            )
            chunks.append(f"<ol>{items}</ol>")
            continue
        chunks.append("<p>" + "<br>".join(_inline(line) for line in block.splitlines()) + "</p>")
    html_out = "\n".join(chunks)
    for index, fence in enumerate(fences):
        html_out = html_out.replace(f"\x00FENCE{index}\x00", fence)
    return html_out


def _table(block: str) -> str:
    rows = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    if len(rows) < 2:
        return f"<p>{_inline(block)}</p>"
    def cells(line: str) -> list[str]:
        return [part.strip() for part in line.strip("|").split("|")]

    head = cells(rows[0])
    body_rows = rows[2:] if re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$", rows[1]) else rows[1:]
    thead = "<tr>" + "".join(f"<th>{_inline(cell)}</th>" for cell in head) + "</tr>"
    tbody = "".join(
        "<tr>" + "".join(f"<td>{_inline(cell)}</td>" for cell in cells(row)) + "</tr>"
        for row in body_rows
    )
    return f"<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>"


def _inline(text: str) -> str:
    escaped = html.escape(text)

    def link(match: re.Match[str]) -> str:
        label = match.group(1)
        href = match.group(2)
        if href.endswith(".md") or "/" in href or href.endswith(".md)"):
            target = href
        else:
            target = href
        return f'<a href="{html.escape(target)}">{label}</a>'

    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped
