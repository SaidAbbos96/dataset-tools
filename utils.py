from pathlib import Path
import re
import unicodedata
import fitz

# sozlanma: 'safe' yoki 'aggressive'
MINIFY_SAFE = 1
MINIFY_LEVEL = 'safe' if MINIFY_SAFE else 'aggressive'

# Uzbek apostrof va chiziqcha xaritalari (unifikatsiya)
_APOS = {"\u2019": "'", "\u2032": "'", "\u02BC": "'",
         "\u02BB": "'", "ʼ": "'", "ʻ": "'", "’": "'"}
_DASH = {"\u2013": "-", "\u2014": "-", "\u2212": "-", "−": "-"}

# Mantiqiy punktuatsiya "oq ro'yxati"
_SAFE_PUNCTS = set(".,;:!?()[]\"'%-/")

# Zero-width belgilar
_ZW = "".join(["\u200B", "\u200C", "\u200D", "\u2060"])

# ------------------------ REPLACEMENT RULES ------------------------

REPL_RULES = [
    # Qator ajratgichlarni normallashtirish
    {"sym": "\r\n", "to": "\n"},
    {"sym": "\r",   "to": "\n"},

    # Soft hyphen / NBSP
    {"sym": "\u00AD", "to": ""},
    {"sym": "\u00A0", "to": " "},
    {"sym": "|", "to": " "},

    # Zero-width belgilar
    {"sym": r"[\u200B\u200C\u200D\u2060]", "to": "", "regex": True},

    # Apostrofli harflarni birlashtirish (masalan: 0 ’ → O')
    {"sym": r"[0OoGg]\s*[‘’ʼʻ´`']",
     "to": lambda m: m.group(0)[0] + "'", "regex": True},

    # So‘zlar orasidagi defis atrofidagi bo‘sh joylarni olib tashlash
    {"sym": r"(?<=\S)\s*-\s*(?=\S)", "to": "-", "regex": True},

    # Smart quotes → oddiy
    {"sym": r"[“”„«»]", "to": '"', "regex": True},
    {"sym": r"[‘’ʼʻ´`]", "to": "'", "regex": True},
    {"sym": r"\b0\s*'", "to": "O'", "regex": True},

    # Uzun tirelar → minus
    {"sym": r"[–—−]", "to": "-", "regex": True},

    # Ko‘p probel/tab → 1 probel
    {"sym": r"[ \t]+", "to": " ", "regex": True},
]

# Kompilyatsiya qilingan qoidalar
_REPL_RULES_COMPILED = []
for rule in REPL_RULES:
    if rule.get("regex"):
        _REPL_RULES_COMPILED.append({
            "pattern": re.compile(rule["sym"]),
            "to": rule["to"],
            "regex": True
        })
    else:
        _REPL_RULES_COMPILED.append(rule)

# ------------------------ FUNKSIYALAR ------------------------


def pre_clean(s: str) -> str:
    """Qoidalarga asoslangan tozalash"""
    for rule in _REPL_RULES_COMPILED:
        if rule.get("regex"):
            s = rule["pattern"].sub(rule["to"], s)
        else:
            s = s.replace(rule["sym"], rule["to"])
    return s


def count_chars(s: str, mode: str = "total") -> int:
    if mode == "total":
        return len(s)
    if mode == "no_whitespace":
        return len(re.sub(r"\s+", "", s))
    if mode == "visible":
        ZERO_WIDTH = {"\u200B", "\u200C", "\u200D", "\u2060"}
        return sum(
            1 for ch in s
            if ch not in ZERO_WIDTH and not unicodedata.category(ch).startswith("C")
        )
    raise ValueError(
        "mode 'total' | 'no_whitespace' | 'visible' bo'lishi kerak")


def semantic_minify(s: str, level: str = 'safe') -> str:
    s = unicodedata.normalize("NFKC", s)

    # Apostrof va chiziqcha belgilarni normallashtirish
    for k, v in _APOS.items():
        s = s.replace(k, v)
    for k, v in _DASH.items():
        s = s.replace(k, v)

    s = s.replace("\xa0", " ")  # NBSP
    s = "".join(ch for ch in s if ch not in _ZW)  # Zero-width

    # Qator ichida ko‘p bo‘shliqni bitta probelga tushurish
    s = "\n".join(" ".join(line.split()) for line in s.split("\n")).strip()

    if level == 'safe':
        # Punktuatsiya atrofidagi bo‘shliqlarni ixchamlash
        s = s.replace(" - ", " - ")
        s = re.sub(r"\s+([,;:!?])", r"\1", s)
        s = re.sub(r"\s+(\.)", r"\1", s)
        s = re.sub(r"([(\[])\s+", r"\1", s)
        s = re.sub(r"\s+([)\]])", r"\1", s)
        return s + "\n"

    # AGGRESSIVE: faqat harf/raqam/punktuatsiya qoldirish
    s = "".join(ch for ch in s if ch.isalnum()
                or ch.isspace() or ch in _SAFE_PUNCTS)
    s = re.sub(r"(\S)\s+\d+(\.)", r"\1\2", s)
    s = "\n".join(" ".join(line.split()) for line in s.split("\n"))
    s = re.sub(r"\n{2,}", "\n", s).strip()
    return s + "\n"


def list_pdfs(folder: Path):
    return sorted([p for p in folder.glob("*.pdf") if p.is_file()])


def prompt_choice(items):
    for i, p in enumerate(items, 1):
        print(f"{i}. {p.name}")
    while True:
        s = input("-> Qaysi fayl? (raqam kiriting): ").strip()
        if s.isdigit():
            i = int(s)
            if 1 <= i <= len(items):
                return items[i-1]
        print("Noto‘g‘ri tanlov. Qayta urinib ko‘ring.")


def parse_pages(spec: str, total_pages: int):
    """
    '2,5,7-9' -> 0-based indexlar
    """
    pages = set()
    tokens = [t.strip() for t in spec.split(",") if t.strip()]
    rng = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")
    for t in tokens:
        if t.isdigit():
            n = int(t)
            if 1 <= n <= total_pages:
                pages.add(n-1)
        else:
            m = rng.match(t)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                if a > b:
                    a, b = b, a
                a = max(1, a)
                b = min(total_pages, b)
                for n in range(a, b+1):
                    pages.add(n-1)
    return sorted(pages)


def pre_clean(s: str) -> str:
    """Qoidalarga asoslangan old-tozalash (yengil va kengaytiriladigan)."""
    for rule in _REPL_RULES_COMPILED:
        if rule.get("regex"):
            s = rule["pattern"].sub(rule["to"], s)
        else:
            s = s.replace(rule["sym"], rule["to"])
    return s


def join_wrapped_lines(s: str, wrap_threshold: int = 80) -> str:
    lines = s.split("\n")
    out, buf = [], ""

    strong_end = re.compile(r"[.!?;:…»)\]]$")
    is_list_head = re.compile(r"^\s*\d+\)\s*")  # masalan: "1) "
    # lotin/kiril kichik harf
    starts_lower = re.compile(r"^[a-zа-яёўғқҳıöüçşñʼ’ʻ-]")

    prev_was_list = False

    for line in lines:
        t = re.sub(r"[ \t]+", " ", line.strip())
        if t == "":
            if buf:
                out.append(buf.strip())
                buf = ""
            prev_was_list = False
            continue

        # List band boshimi?
        if is_list_head.match(t):
            if buf:
                out.append(buf.strip())
                buf = ""
            buf = t
            prev_was_list = True
            continue

        if buf:
            # Agar avvalgi qator list bandi bo‘lgan bo‘lsa va bu qator kichik harf bilan boshlangan bo‘lsa,
            # yangi abzats emas — bandning davomi: bo‘shliq bilan ulaymiz
            if prev_was_list and starts_lower.search(t):
                buf = (buf + " " + t).strip()
                continue

        # ✅ KICHIK HARF bilan boshlangan VA 30 belgidan KICHIK bo‘lsa — avvalgi qator bilan birlashtiramiz
        if starts_lower.match(t) and len(t) < 30:
            buf = (buf + " " + t).strip() if buf else t
            continue

        # Qisqa satr va kuchli tinishsiz tugasa — davom deb birlashtiramiz
        if len(t) < wrap_threshold and not strong_end.search(t):
            buf = (buf + " " + t).strip() if buf else t
        else:
            if buf:
                buf = (buf + " " + t).strip()
                out.append(buf)
                buf = ""
            else:
                out.append(t)
            # Qator kuchli tinish bilan tugagan — endi list konteksti tugashi mumkin
            prev_was_list = False

    if buf:
        out.append(buf.strip())

    return "\n".join(out)


def post_normalize(s: str) -> str:
    # Qator ichida ko‘p probel/tab -> 1 probel
    s = "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n"))

    # Raqamdan keyingi ;, ), . oldidagi ortiqcha bo‘shliq
    s = re.sub(r"(\d+)\s*;", r"\1;", s)
    s = re.sub(r"(\d+)\s+\)", r"\1)", s)
    s = re.sub(r"(\d+)\s+\.", r"\1.", s)

    # Izoh raqamlari so‘zga yopishmasin: fanlari1. -> fanlari 1.
    s = re.sub(r"([A-Za-zÀ-ÖØ-öø-ÿ\u0400-\u04FF”»])(\d)([.)])?", r"\1 \2\3", s)

    # Oddiy so‘zlar orasidagi defis atrofidagi bo‘shliqni ixchamla: " - " -> " - "
    s = re.sub(r"\s*-\s*", " - ", s)
    s = re.sub(r"\s{2,}", " ", s)  # ikki va ko‘p probel -> 1

    # SO‘Z ICHIDA tasodifiy bo‘lingan holatlar:
    # 1) bitta harf - keyingi so‘z boshlanishi (t a-biati, guma nitar)
    #    chapda 1 harf + '-' + pastki harf => defisni olib tashlab qo‘shib yuboramiz
    s = re.sub(
        r"(?<=\b[A-Za-zÀ-ÖØ-öø-ÿ\u0400-\u04FF])-\s*(?=[a-zà-öø-ÿ\u0400-\u04FF])", "", s)

    # 2) So‘z o‘rtasida tasodifiy bo‘shliq: "guma nitar" -> "gumanitar"
    s = re.sub(r"(\b[A-Za-zÀ-ÖØ-öø-ÿ\u0400-\u04FF]{2,})\s+([a-zà-öø-ÿ\u0400-\u04FF]{2,}\b)", lambda m:
               (m.group(1) + m.group(2)) if len(m.group(1)) <= 4 and len(m.group(2)) <= 5 else m.group(0), s)

    # Bir nechta bo‘sh qatorni bitta qilish
    s = re.sub(r"\n{2,}", "\n", s)

    return s.strip() + "\n"


def clean_text(full_text: str, wrap_threshold: int = 80) -> str:
    s = pre_clean(full_text)             # REPL_RULES ishlatiladi
    s = join_wrapped_lines(s, wrap_threshold=wrap_threshold)
    s = post_normalize(s)
    # eng ohirida chaqirilishi kerak
    s = semantic_minify(s, level=MINIFY_LEVEL)
    return s


def extract_text(pdf_path: Path, pages_idx):
    doc = fitz.open(pdf_path)
    try:
        parts = []
        PRESERVE_WS = getattr(fitz, "TEXT_PRESERVE_WHITESPACE", 0)
        PRESERVE_LIG = getattr(fitz, "TEXT_PRESERVE_LIGATURES", 0)
        flags = PRESERVE_WS | PRESERVE_LIG

        for i in pages_idx:
            page = doc.load_page(i)
            try:
                raw = page.get_text("text", flags=flags)
            except TypeError:
                raw = page.get_text("text")
            parts.append(raw)
        raw_all = "\n".join(parts)
        return clean_text(raw_all, wrap_threshold=80) or None
    finally:
        doc.close()
