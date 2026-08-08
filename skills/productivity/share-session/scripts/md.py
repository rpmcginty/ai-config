#!/usr/bin/env python3
"""Minimal, dependency-free Markdown -> HTML converter sized for transcript prose."""
import re, html

_CODE_TOKEN = "\x00CODE%d\x00"


def _esc(s):
    return html.escape(s, quote=False)


def _inline(text):
    spans = []

    def stash(m):
        spans.append(m.group(1))
        return _CODE_TOKEN % (len(spans) - 1)

    # protect inline code first (longest fence run wins)
    text = re.sub(r"``(.+?)``", stash, text, flags=re.S)
    text = re.sub(r"`([^`]+?)`", stash, text)

    text = _esc(text)

    # links [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}" target="_blank" rel="noopener">{m.group(1)}</a>',
        text,
    )
    # bare urls not already inside an href
    text = re.sub(
        r"(?<!\")(?<!>)\b(https?://[^\s<>\"')\]]+)",
        lambda m: f'<a href="{html.escape(m.group(1), quote=True)}" target="_blank" rel="noopener">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text, flags=re.S)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text, flags=re.S)
    text = re.sub(r"(?<!\w)\*([^*\n]+?)\*(?!\w)", r"<em>\1</em>", text)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text, flags=re.S)

    for i, c in enumerate(spans):
        text = text.replace(_CODE_TOKEN % i, f"<code>{_esc(c)}</code>")
    return text


def _table(rows):
    if len(rows) < 2:
        return ""
    head = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    body = rows[2:]
    out = ['<div class="tbl-wrap"><table><thead><tr>']
    out += [f"<th>{_inline(c)}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def render(src):
    if not src:
        return ""
    src = src.replace("\r\n", "\n").replace("\r", "\n")
    lines = src.split("\n")
    out = []
    i = 0
    para = []
    list_stack = []  # list of (tag, indent)

    def flush_para():
        if para:
            out.append(f"<p>{_inline(' '.join(para).strip())}</p>")
            para.clear()

    def close_lists(to_indent=-1):
        while list_stack and list_stack[-1][1] > to_indent:
            out.append(f"</{list_stack.pop()[0]}>")

    while i < len(lines):
        ln = lines[i]
        stripped = ln.strip()

        # fenced code
        m = re.match(r"^\s*(`{3,}|~{3,})\s*([\w+-]*)\s*$", ln)
        if m:
            fence, lang = m.group(1)[0] * 3, m.group(2)
            flush_para(); close_lists()
            buf = []
            i += 1
            while i < len(lines) and not re.match(r"^\s*(`{3,}|~{3,})\s*$", lines[i]):
                buf.append(lines[i]); i += 1
            i += 1
            cls = f' class="lang-{_esc(lang)}"' if lang else ""
            label = f'<span class="code-lang">{_esc(lang)}</span>' if lang else ""
            out.append(f'<div class="code-block">{label}<pre><code{cls}>{_esc(chr(10).join(buf))}</code></pre></div>')
            continue

        if not stripped:
            flush_para(); close_lists()
            i += 1
            continue

        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para(); close_lists()
            lvl = min(len(m.group(1)) + 2, 6)
            out.append(f"<h{lvl}>{_inline(m.group(2).strip())}</h{lvl}>")
            i += 1
            continue

        # hr
        if re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", ln):
            flush_para(); close_lists()
            out.append("<hr>")
            i += 1
            continue

        # table
        if "|" in stripped and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1]):
            flush_para(); close_lists()
            rows = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(lines[i]); i += 1
            out.append(_table(rows))
            continue

        # blockquote
        if stripped.startswith(">"):
            flush_para(); close_lists()
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append(f"<blockquote>{render(chr(10).join(buf))}</blockquote>")
            continue

        # list item
        m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", ln)
        if m:
            indent = len(m.group(1).expandtabs(4))
            ordered = not m.group(2) in ("-", "*", "+")
            tag = "ol" if ordered else "ul"
            flush_para()
            close_lists(indent)
            if not list_stack or list_stack[-1][1] < indent:
                list_stack.append((tag, indent))
                out.append(f"<{tag}>")
            elif list_stack[-1][0] != tag:
                out.append(f"</{list_stack.pop()[0]}>")
                list_stack.append((tag, indent))
                out.append(f"<{tag}>")
            # gather continuation lines
            content = [m.group(3)]
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    break
                if re.match(r"^(\s*)([-*+]|\d+[.)])\s+", nxt):
                    break
                if re.match(r"^\s*(#{1,6})\s+", nxt) or re.match(r"^\s*(`{3,})", nxt):
                    break
                content.append(nxt.strip())
                i += 1
            out.append(f"<li>{_inline(' '.join(content))}</li>")
            continue

        para.append(stripped)
        i += 1

    flush_para(); close_lists()
    return "".join(out)
