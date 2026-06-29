#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يبني نسخة HTML من فصول الكتاب (RTL) تمهيدًا لطباعتها PDF عبر Chromium.

الاستخدام:
    python3 book/build_pdf.py          # يكتب book/book.html
ثم يُطبع PDF بـ Chromium (انظر الأوامر في نهاية الجلسة).
"""
import html
import re
from pathlib import Path

BOOK = Path(__file__).resolve().parent
ORDER = [
    "00-dedication.md", "ch01.md", "ch02.md", "ch03.md", "ch04.md",
    "ch05.md", "ch06.md", "ch07.md", "ch08.md", "ch09.md", "ch10.md",
    "99-closing.md",
]

TITLE = "من عبدالرحمن إلى رويدا"
SUBTITLE = "حكاية شهر عسلٍ في بالي — ومذكّرة حبٍّ إلى من اخترتها"


def inline(text: str) -> str:
    """تحويل **غامق** مع تهريب HTML."""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def md_to_html(md: str) -> str:
    out = []
    para = []

    def flush():
        if para:
            out.append("<p>" + " ".join(para).strip() + "</p>")
            para.clear()

    for line in md.splitlines():
        s = line.strip()
        if not s:
            flush()
            continue
        if s.startswith("# "):
            flush(); out.append(f"<h1>{inline(s[2:])}</h1>")
        elif s.startswith("## "):
            flush(); out.append(f"<h2>{inline(s[3:])}</h2>")
        elif s.startswith("### "):
            flush(); out.append(f"<h3>{inline(s[4:])}</h3>")
        elif s.startswith(">"):
            flush(); out.append(f"<blockquote>{inline(s.lstrip('> ').strip())}</blockquote>")
        elif s.startswith("---") or s.startswith("***"):
            flush()  # فاصل بصريّ نتجاهله (الفواصل بين الفصول صفحات)
        else:
            para.append(inline(s))
    flush()
    return "\n".join(out)


CSS = """
@page { size: A5; margin: 20mm 18mm; }
* { box-sizing: border-box; }
body {
  font-family: 'FreeSerif', serif;
  direction: rtl; text-align: right;
  color: #1a1a1a; line-height: 2.0; font-size: 13.5pt;
  margin: 0;
}
.chapter { page-break-before: always; }
h1 { font-size: 21pt; text-align: center; margin: 0 0 4pt; color: #6b3f2b; }
h2 { font-size: 15pt; text-align: center; font-weight: normal;
     color: #9a6a4f; margin: 0 0 26pt; letter-spacing: 1px; }
h3 { font-size: 13.5pt; color: #6b3f2b; margin: 22pt 0 6pt; }
p { margin: 0 0 12pt; text-align: justify; text-justify: inter-word; }
blockquote {
  margin: 14pt 6pt; padding: 8pt 16pt; border-right: 3px solid #c9a18a;
  background: #faf5f0; color: #4a3326; font-style: italic;
}
strong { color: #6b3f2b; }
.cover {
  display: flex; flex-direction: column; justify-content: center;
  align-items: center; height: 160mm; text-align: center;
  page-break-after: always;
}
.cover .t { font-size: 30pt; color: #6b3f2b; margin-bottom: 18pt; }
.cover .s { font-size: 14pt; color: #9a6a4f; line-height: 1.8; max-width: 80%; }
.cover .ornament { font-size: 22pt; color: #c9a18a; margin: 26pt 0; }
"""


def main():
    parts = [
        '<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">',
        f"<style>{CSS}</style></head><body>",
        f'<div class="cover"><div class="t">{html.escape(TITLE)}</div>'
        f'<div class="ornament">✦ ❀ ✦</div>'
        f'<div class="s">{html.escape(SUBTITLE)}</div></div>',
    ]
    for name in ORDER:
        f = BOOK / name
        if not f.exists():
            continue
        parts.append(f'<div class="chapter">{md_to_html(f.read_text(encoding="utf-8"))}</div>')
    parts.append("</body></html>")
    (BOOK / "book.html").write_text("\n".join(parts), encoding="utf-8")
    print(f"تم إنشاء {BOOK / 'book.html'}")


if __name__ == "__main__":
    main()
