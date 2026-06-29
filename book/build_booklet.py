#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يبني «كتيبًا صغيرًا لرويدا» — مختارات القلب بقطع A6 جيب.

مُنتقى ليكون هديّةً حميمة قصيرة: الإهداء + اللي أحبّه فيكِ + وعود وأحلام + الخاتمة.
يعيد استخدام محوّل الماركداون من build_pdf.py.
"""
from pathlib import Path
from build_pdf import md_to_html  # نفس المحوّل

BOOK = Path(__file__).resolve().parent
# مختارات موجّهة لها وحدها (لا فصول الرحلة)
ORDER = ["00-dedication.md", "ch04.md", "ch10.md", "99-closing.md"]

TITLE = "إلى رويدا"
SUBTITLE = "كتيبٌ صغير… من قلب عبدالرحمن"

CSS = """
@page { size: A6; margin: 14mm 13mm; }
* { box-sizing: border-box; }
body { font-family: 'FreeSerif', serif; direction: rtl; text-align: right;
       color: #1a1a1a; line-height: 1.95; font-size: 11.5pt; margin: 0; }
.chapter { page-break-before: always; }
h1 { font-size: 16pt; text-align: center; margin: 0 0 3pt; color: #6b3f2b; }
h2 { font-size: 11.5pt; text-align: center; font-weight: normal;
     color: #9a6a4f; margin: 0 0 18pt; letter-spacing: .5px; }
h3 { font-size: 11.5pt; color: #6b3f2b; margin: 16pt 0 5pt; }
p { margin: 0 0 9pt; text-align: justify; }
blockquote { margin: 10pt 4pt; padding: 6pt 12pt; border-right: 2px solid #c9a18a;
             background: #faf5f0; color: #4a3326; font-style: italic; }
strong { color: #6b3f2b; }
.cover { display: flex; flex-direction: column; justify-content: center;
         align-items: center; height: 118mm; text-align: center;
         page-break-after: always; }
.cover .t { font-size: 26pt; color: #6b3f2b; margin-bottom: 14pt; }
.cover .ornament { font-size: 17pt; color: #c9a18a; margin: 18pt 0; }
.cover .s { font-size: 11.5pt; color: #9a6a4f; max-width: 85%; line-height: 1.7; }
"""


def main():
    import html
    parts = ['<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">',
             f"<style>{CSS}</style></head><body>",
             f'<div class="cover"><div class="t">{html.escape(TITLE)}</div>'
             f'<div class="ornament">❀</div>'
             f'<div class="s">{html.escape(SUBTITLE)}</div></div>']
    for name in ORDER:
        f = BOOK / name
        if f.exists():
            parts.append(f'<div class="chapter">{md_to_html(f.read_text(encoding="utf-8"))}</div>')
    parts.append("</body></html>")
    (BOOK / "booklet.html").write_text("\n".join(parts), encoding="utf-8")
    print(f"تم إنشاء {BOOK / 'booklet.html'}")


if __name__ == "__main__":
    main()
