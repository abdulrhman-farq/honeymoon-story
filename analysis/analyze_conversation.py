#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محلّل المحادثة الكمّي — مشروع كتاب «من عبدالرحمن إلى رويدا»
================================================================
الهدف: تحويل تفريغ التسجيل الصوتي (Jalan_Cempaka_ara.txt) إلى بياناتٍ
قابلة للقياس، بحيث يكون كل استنتاج في وثائق المشروع مبنيًّا على دليل
لا على انطباع.

يقيس:
  - عدد المقاطع (الخام = كل بلوك توقيت، والمنطوقة = أدوار المتحدث)
  - عدد الكلمات لكل متحدث ونسبة الكلام
  - متوسط طول المقطع
  - الأسئلة (؟ / ?)
  - الضحك (إشارات نصية)
  - الكلمات الإنجليزية
  - الكلمات الأكثر تكرارًا (بعد إزالة كلمات الوقف)
  - الموضوعات الأكثر ذكرًا (مجموعات مفاتيح)
  - تطوّر الحوار زمنيًّا (تقسيم على أرباع المدة)
  - ملفات شخصية مبدئية لكل متحدث
  - مصفوفة أدلة + درجات ثقة لكل استنتاج

الاستخدام:
    python3 analysis/analyze_conversation.py [مسار_التفريغ]
يكتب تقريرًا إلى analysis/analysis_report.md ويطبع ملخّصًا.
"""

import re
import sys
import json
from collections import Counter, defaultdict
from pathlib import Path

# ----------------------------------------------------------------------------
# الإعدادات
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRANSCRIPT = ROOT / "Jalan_Cempaka_ara.txt"
REPORT_MD = ROOT / "analysis" / "analysis_report.md"
REPORT_JSON = ROOT / "analysis" / "analysis_report.json"

SPEAKER_NAMES = {"0": "عبدالرحمن", "1": "رويدا"}

# نمط سطر التوقيت + المتحدث، مثال:
# 00:00:14,100 --> 00:00:16,020 [Speaker 1]
HEADER_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*"
    r"(?P<end>\d{2}:\d{2}:\d{2},\d{3})\s*\[Speaker\s*(?P<sp>\d+)\]"
)

ENGLISH_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
ARABIC_TOKEN_RE = re.compile(r"[ء-ي]+")
LAUGH_RE = re.compile(r"هه+|haha+|lol|😂|🤣|\[laugh", re.IGNORECASE)

# كلمات وقف عربية شائعة (لتنظيف قائمة التكرار)
AR_STOPWORDS = set("""
في من على إلى عن مع هذا هذه ذلك تلك الذي التي و او أو ثم بس يعني
أنا انا انت أنت هو هي نحن احنا هم هي كان كانت يكون نكون ما لا لم لن
قد كل بعض غير عند لكن لأن لان إن ان أن إنه انه له لها لنا لي بك بها به
يا اي أي كذا كذه شي شيء كده هيك هنا هناك الحين الان الآن طيب خلاص
صح اه آه ايه أيوه نعم لا والله الله ثم وش وشو كيف ليش ليه متى وين فين
زي مثل برضو برضه عشان علشان حق حقت بعد قبل فوق تحت جوا برا
""".split())

EN_STOPWORDS = set("""
the a an and or of to in on at is are was were be been i you he she it we they
this that these those my your our for so but not no yes ok okay we'll i'm it's
""".split())

# مجموعات الموضوعات (مفاتيح عربية + إنجليزية) — تُعدّ بعدد المقاطع التي تذكرها
TOPICS = {
    "الأماكن والسفر": ["بالي", "أوبود", "اوبود", "نوسا", "دوا", "الدوحة", "بانكوك",
                       "الرياض", "المطار", "فندق", "resort", "hotel", "ريتز",
                       "كارلتون", "destination", "نهر", "river", "شلال", "مزرعة"],
    "الطعام والشراب": ["أكل", "اكل", "نأكل", "ناكل", "فطور", "عشاء", "غداء", "برغر",
                      "ستيك", "stake", "steak", "باييلا", "سلمون", "ماتشا", "قهوة",
                      "coffee", "عصير", "أومليت", "كرواسون", "organic", "تاكو",
                      "أفوكادو", "مشروم", "mushroom", "جوز", "موز", "banana"],
    "الحب والمشاعر": ["أحب", "احب", "حب", "أحبك", "احبك", "love", "قلب", "حبيبي",
                     "حبيبتي", "أدلعك", "ادلعك", "دلع", "اشتاق", "غالي", "قدرك"],
    "العائلة والأطفال": ["أولاد", "اولاد", "أطفال", "اطفال", "ولد", "بنت", "أمكم",
                        "امكم", "أبوكم", "ابوكم", "جدكم", "جدّكم", "عمي", "عمك",
                        "محمد", "والد", "والدي", "أهل", "اهل", "عائلة", "حمولة"],
    # ملاحظة: استُبعدت «الله»/«والله» عمدًا لأنها تُستعمل غالبًا حشوًا لفظيًّا
    # («والله»، «الله يسعدك») لا ذكرًا دينيًّا، فتُضخّم الموضوع زيفًا. يُقتصر هنا
    # على الإشارات الدينية الصريحة. (انظر مقياس الحشو اللفظي في القسم المنفصل.)
    "الإيمان والدين": ["اللهم", "سبحان", "القرآن", "قرآن", "قرأتي", "صل وسلم",
                      "أقسم بالله", "اقسم بالله", "بركة", "بركات", "دعاء",
                      "إن شاء الله", "ان شاء الله", "ربي بارك", "رب بارك"],
    # ملاحظة: استُبعدت «بعدين» لأنها رابط سردي («ثم») لا دلالة مستقبل.
    "المستقبل والأحلام": ["مستقبل", "حلم", "نحلم", "بنبني", "نبني", "بيت",
                         "مزرعة", "بئر", "بحيرة", "عشر سن", "سنين", "سنوات",
                         "بنسمي", "نربي", "أساس", "اساس", "متين"],
    "اللعب والمرح": ["نلعب", "لعب", "ضحك", "نضحك", "رقص", "رقصنا", "مزح", "نكتة",
                    "gangster", "gangsters", "خصيو", "زبيو"],
    "الطبيعة": ["طبيعة", "nature", "جبل", "أرز", "rice", "بحر", "شمس", "قمر",
               "خضرة", "أخضر", "اخضر", "بط", "حيوان"],
}


def parse_timestamp(ts: str) -> float:
    """يحوّل HH:MM:SS,mmm إلى ثوانٍ (float)."""
    hh, mm, rest = ts.split(":")
    ss, ms = rest.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0


def parse_blocks(text: str):
    """يقسّم التفريغ إلى بلوكات: (المتحدث، البداية، النهاية، النص)."""
    lines = text.splitlines()
    blocks = []
    current = None
    for line in lines:
        m = HEADER_RE.search(line)
        if m:
            if current:
                blocks.append(current)
            current = {
                "speaker": m.group("sp"),
                "start": parse_timestamp(m.group("start")),
                "end": parse_timestamp(m.group("end")),
                "text_parts": [],
            }
        elif current is not None:
            stripped = line.strip()
            if stripped:
                current["text_parts"].append(stripped)
    if current:
        blocks.append(current)
    for b in blocks:
        b["text"] = " ".join(b["text_parts"]).strip()
    return [b for b in blocks if b["text"]]


def count_words(s: str) -> int:
    """عدد الكلمات (عربية + إنجليزية + أرقام) بالفصل على المسافات."""
    return len([t for t in re.split(r"\s+", s.strip()) if t])


def merge_turns(blocks):
    """دمج البلوكات المتتالية لنفس المتحدث في 'دور' واحد."""
    turns = []
    for b in blocks:
        if turns and turns[-1]["speaker"] == b["speaker"]:
            turns[-1]["text"] += " " + b["text"]
            turns[-1]["end"] = b["end"]
        else:
            turns.append({"speaker": b["speaker"], "start": b["start"],
                          "end": b["end"], "text": b["text"]})
    return turns


def analyze(transcript_path: Path):
    text = transcript_path.read_text(encoding="utf-8")
    blocks = parse_blocks(text)
    turns = merge_turns(blocks)

    total_duration = max((b["end"] for b in blocks), default=0)

    # ---- إحصاءات لكل متحدث ----
    per_speaker = {}
    for sp, name in SPEAKER_NAMES.items():
        sp_blocks = [b for b in blocks if b["speaker"] == sp]
        sp_turns = [t for t in turns if t["speaker"] == sp]
        joined = " ".join(b["text"] for b in sp_blocks)
        words = count_words(joined)
        questions = sum(1 for b in sp_blocks if ("؟" in b["text"] or "?" in b["text"]))
        laughs = len(LAUGH_RE.findall(joined))
        english = ENGLISH_RE.findall(joined)
        per_speaker[sp] = {
            "name": name,
            "blocks": len(sp_blocks),
            "turns": len(sp_turns),
            "words": words,
            "questions": questions,
            "laughs": laughs,
            "english_tokens": len(english),
            "avg_words_per_block": round(words / len(sp_blocks), 1) if sp_blocks else 0,
            "avg_words_per_turn": round(words / len(sp_turns), 1) if sp_turns else 0,
        }

    total_words = sum(s["words"] for s in per_speaker.values())
    for sp in per_speaker:
        per_speaker[sp]["talk_ratio"] = (
            round(100 * per_speaker[sp]["words"] / total_words, 1) if total_words else 0
        )

    # ---- الكلمات الأكثر تكرارًا ----
    all_text = " ".join(b["text"] for b in blocks)
    ar_freq = Counter(
        w for w in ARABIC_TOKEN_RE.findall(all_text)
        if w not in AR_STOPWORDS and len(w) > 1
    )
    en_freq = Counter(
        w.lower() for w in ENGLISH_RE.findall(all_text)
        if w.lower() not in EN_STOPWORDS and len(w) > 1
    )

    # ---- الموضوعات ----
    topic_counts = {}
    for topic, keys in TOPICS.items():
        keyset = [k for k in keys]
        c = 0
        for b in blocks:
            low = b["text"].lower()
            if any(k.lower() in low for k in keyset):
                c += 1
        topic_counts[topic] = c

    # ---- الحشو اللفظي / التعابير المتكرّرة (نمط كلام، لا موضوع) ----
    FILLERS = ["والله", "يعني", "المهم", "طبعًا", "طبعا", "إن شاء الله",
               "ان شاء الله", "الحين", "بعدين", "خلاص", "عادي", "صح"]
    filler_counts = {f: all_text.count(f) for f in FILLERS}
    filler_counts = dict(sorted(filler_counts.items(), key=lambda x: -x[1]))

    # ---- التطوّر الزمني (أرباع) ----
    quarters = [{"label": f"الربع {i+1}", "0_words": 0, "1_words": 0,
                 "blocks": 0} for i in range(4)]
    for b in blocks:
        idx = min(3, int((b["start"] / total_duration) * 4)) if total_duration else 0
        quarters[idx]["blocks"] += 1
        quarters[idx][f"{b['speaker']}_words"] += count_words(b["text"])

    # ---- المصفوفة ودرجات الثقة ----
    a, r = per_speaker["0"], per_speaker["1"]
    evidence = build_evidence_matrix(per_speaker, topic_counts, total_words)

    return {
        "total_duration_sec": round(total_duration, 1),
        "total_blocks": len(blocks),
        "total_turns": len(turns),
        "total_words": total_words,
        "per_speaker": per_speaker,
        "top_arabic": ar_freq.most_common(25),
        "top_english": en_freq.most_common(20),
        "topics": dict(sorted(topic_counts.items(), key=lambda x: -x[1])),
        "fillers": filler_counts,
        "quarters": quarters,
        "evidence_matrix": evidence,
    }


def build_evidence_matrix(per_speaker, topics, total_words):
    """يبني استنتاجات موسومة بدرجة ثقة بناءً على فجوة البيانات."""
    a, r = per_speaker["0"], per_speaker["1"]

    def confidence(margin_ratio):
        # margin_ratio: حجم الفارق النسبي بين الطرفين (0..1)
        if margin_ratio >= 0.30:
            return "عالية"
        if margin_ratio >= 0.12:
            return "متوسطة"
        return "منخفضة"

    talk_margin = abs(a["talk_ratio"] - r["talk_ratio"]) / 100
    q_total = a["questions"] + r["questions"]
    q_margin = abs(a["questions"] - r["questions"]) / q_total if q_total else 0
    len_margin = (abs(a["avg_words_per_block"] - r["avg_words_per_block"]) /
                  max(a["avg_words_per_block"], r["avg_words_per_block"], 1))

    rows = [
        {
            "claim": "عبدالرحمن يقود السرد (حصة الكلام الأكبر)",
            "evidence": f"{a['talk_ratio']}% مقابل {r['talk_ratio']}% "
                        f"({a['words']} مقابل {r['words']} كلمة)",
            "confidence": confidence(talk_margin),
        },
        {
            "claim": "عبدالرحمن يتكلم بمقاطع أطول",
            "evidence": f"{a['avg_words_per_block']} مقابل "
                        f"{r['avg_words_per_block']} كلمة/مقطع",
            "confidence": confidence(len_margin),
        },
        {
            "claim": "عبدالرحمن يطرح أسئلة أكثر",
            "evidence": f"{a['questions']} مقابل {r['questions']} سؤال",
            "confidence": confidence(q_margin),
        },
        {
            "claim": "الحوار متبادل (كلاهما حاضر بقوة)",
            "evidence": f"{a['turns']} مقابل {r['turns']} دور كلامي",
            "confidence": "عالية" if min(a["turns"], r["turns"]) /
                          max(a["turns"], r["turns"], 1) > 0.5 else "متوسطة",
        },
        {
            "claim": f"الموضوع الأبرز: {max(topics, key=topics.get)}",
            "evidence": f"{topics[max(topics, key=topics.get)]} مقطعًا يذكره",
            "confidence": "متوسطة",
        },
    ]
    return rows


# ----------------------------------------------------------------------------
# توليد التقرير
# ----------------------------------------------------------------------------
def fmt_duration(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m} دقيقة و{s} ثانية"


def render_markdown(d) -> str:
    a = d["per_speaker"]["0"]
    r = d["per_speaker"]["1"]
    lines = []
    out = lines.append

    out("# تقرير التحليل الكمّي للمحادثة")
    out("> مُولَّد آليًّا بواسطة `analysis/analyze_conversation.py` من "
        "`Jalan_Cempaka_ara.txt`. لا يُحرَّر يدويًّا — أعد تشغيل السكربت لتحديثه.\n")

    out("## ١. أرقام عامة")
    out(f"- مدة التسجيل: **{fmt_duration(d['total_duration_sec'])}**")
    out(f"- المقاطع الخام (بلوكات التوقيت): **{d['total_blocks']}**")
    out(f"- الأدوار الكلامية (بعد دمج المتتالي لنفس المتحدث): **{d['total_turns']}**")
    out(f"- إجمالي الكلمات: **{d['total_words']}**\n")

    out("## ٢. لكل متحدث")
    out("| المقياس | عبدالرحمن | رويدا |")
    out("|---|---|---|")
    out(f"| الكلمات | {a['words']} | {r['words']} |")
    out(f"| نسبة الكلام | **{a['talk_ratio']}%** | **{r['talk_ratio']}%** |")
    out(f"| المقاطع الخام | {a['blocks']} | {r['blocks']} |")
    out(f"| الأدوار الكلامية | {a['turns']} | {r['turns']} |")
    out(f"| متوسط الكلمات/مقطع | {a['avg_words_per_block']} | {r['avg_words_per_block']} |")
    out(f"| متوسط الكلمات/دور | {a['avg_words_per_turn']} | {r['avg_words_per_turn']} |")
    out(f"| الأسئلة | {a['questions']} | {r['questions']} |")
    out(f"| كلمات إنجليزية | {a['english_tokens']} | {r['english_tokens']} |")
    out(f"| إشارات ضحك نصية | {a['laughs']} | {r['laughs']} |\n")

    out("## ٣. الموضوعات الأكثر ذكرًا (عدد المقاطع)")
    out("| الموضوع | المقاطع |")
    out("|---|---|")
    for topic, c in d["topics"].items():
        out(f"| {topic} | {c} |")
    out("")

    out("## ٤. الكلمات العربية الأكثر تكرارًا")
    out("| الكلمة | التكرار |")
    out("|---|---|")
    for w, c in d["top_arabic"]:
        out(f"| {w} | {c} |")
    out("")

    out("## ٥. الكلمات الإنجليزية الأكثر تكرارًا")
    out("| الكلمة | التكرار |")
    out("|---|---|")
    for w, c in d["top_english"]:
        out(f"| {w} | {c} |")
    out("")

    out("## ٦. الحشو اللفظي / التعابير المتكرّرة (نمط كلام)")
    out("> هذه تعابير لفظية متكرّرة، تُرصد كنمط كلام لا كموضوع. كلمة «والله» "
        "خصوصًا تُستعمل حشوًا غالبًا، ولذلك أُخرجت من تصنيف «الإيمان والدين».")
    out("| التعبير | التكرار |")
    out("|---|---|")
    for w, c in d["fillers"].items():
        out(f"| {w} | {c} |")
    out("")

    out("## ٧. تطوّر الحوار زمنيًّا (أرباع المدة)")
    out("| المقطع الزمني | كلمات عبدالرحمن | كلمات رويدا | بلوكات |")
    out("|---|---|---|---|")
    for q in d["quarters"]:
        out(f"| {q['label']} | {q['0_words']} | {q['1_words']} | {q['blocks']} |")
    out("")

    out("## ٨. مصفوفة الأدلة ودرجات الثقة")
    out("| الاستنتاج | الدليل (بيانات) | الثقة |")
    out("|---|---|---|")
    for row in d["evidence_matrix"]:
        out(f"| {row['claim']} | {row['evidence']} | {row['confidence']} |")
    out("")

    out("## ٩. ملاحظات منهجية")
    out("- **الضحك:** التفريغ النصي لا يوسم الضحك إلا نادرًا، فعدد إشارات "
        "الضحك أدنى من الواقع الفعلي ولا يُبنى عليه استنتاج.")
    out("- **المقاطع:** «المقاطع الخام» = كل بلوك توقيت في التفريغ؛ بينما "
        "«الأدوار الكلامية» تدمج البلوكات المتتالية لنفس المتحدث. الرقمان "
        "مختلفان عمدًا، واستُخدم كلٌّ منهما حيث يناسب.")
    out("- **الموضوعات:** تُحسب بمطابقة كلمات مفتاحية؛ المقطع الذي يمسّ أكثر "
        "من موضوع يُحسب في كلٍّ منها.")
    out("- كل الأرقام أعلاه مُعاد إنتاجها بتشغيل السكربت على التفريغ الحالي.")

    return "\n".join(lines)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TRANSCRIPT
    if not path.exists():
        print(f"خطأ: لم يُعثر على التفريغ: {path}", file=sys.stderr)
        sys.exit(1)

    data = analyze(path)
    REPORT_MD.write_text(render_markdown(data), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                           encoding="utf-8")

    a = data["per_speaker"]["0"]
    r = data["per_speaker"]["1"]
    print("=" * 56)
    print("ملخّص التحليل الكمّي")
    print("=" * 56)
    print(f"المدة: {fmt_duration(data['total_duration_sec'])}")
    print(f"المقاطع الخام: {data['total_blocks']} | الأدوار: {data['total_turns']}")
    print(f"إجمالي الكلمات: {data['total_words']}")
    print(f"عبدالرحمن: {a['talk_ratio']}% ({a['words']} كلمة) | "
          f"أسئلة {a['questions']} | متوسط/مقطع {a['avg_words_per_block']}")
    print(f"رويدا:     {r['talk_ratio']}% ({r['words']} كلمة) | "
          f"أسئلة {r['questions']} | متوسط/مقطع {r['avg_words_per_block']}")
    print(f"الموضوع الأبرز: {max(data['topics'], key=data['topics'].get)}")
    print("-" * 56)
    print(f"كُتب التقرير إلى: {REPORT_MD.relative_to(ROOT)}")
    print(f"وبيانات JSON إلى: {REPORT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
