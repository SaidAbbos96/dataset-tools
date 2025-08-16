import re
import unicodedata

# sozlanma: 'safe' yoki 'aggressive'
MINIFY_SAFE = 1
MINIFY_LEVEL = 'safe' if MINIFY_SAFE else 'aggressive'  # qilsa bo'ladi

# Uzbek apostrof va chiziqcha xaritalari (unifikatsiya)
_APOS = {"\u2019": "'", "\u2032": "'", "\u02BC": "'",
         "\u02BB": "'", "ʼ": "'", "ʻ": "'", "’": "'"}
_DASH = {"\u2013": "-", "\u2014": "-", "\u2212": "-", "−": "-"}

# Mantiqiy punktuatsiya "oq ro'yxati"
_SAFE_PUNCTS = set(list(".,;:!?()[]\"'%-/"))


# ------------------------ Matn tozalash pipeline ------------------------
_ZW = "".join(["\u200B", "\u200C", "\u200D", "\u2060"])  # zero-width belgilar

# --- Qoidalar ro‘yxati: istalgancha kengaytiring ---
REPL_RULES = [
    # Qator ajratgichlarni unifikatsiya
    {"sym": "\r\n", "to": "\n"},
    {"sym": "\r",   "to": "\n"},
    # {"sym": "§.",   "to": ""},

    # Soft hyphen / NBSP
    {"sym": "\u00AD", "to": ""},   # soft hyphen -> o‘chir
    {"sym": "\u00A0", "to": " "},  # NBSP -> space

    # Zero-width belgilar
    {"sym": r"[\u200B\u200C\u200D\u2060]", "to": "", "regex": True},

    # (ixtiyoriy) Smart quotes -> oddiy
    {"sym": r"[“”„«»]", "to": '"', "regex": True},
    {"sym": r"[‘’ʼʻ´`]", "to": "'", "regex": True},

    # (ixtiyoriy) Uzun tirelar -> oddiy minus
    {"sym": r"[–—−]", "to": "-", "regex": True},

    # (ixtiyoriy) Tab va ko‘p probelni qisqartirish (qatordan mustaqil)
    # Agar bu bosqichda kerak bo'lmasa, pastdagini o'chirib turing:
    # {"sym": r"[ \t]+", "to": " ", "regex": True},
]

# --- Oldindan kompilyatsiya (regex bo‘lsa) ---
_REPL_RULES_COMPILED = []
for rule in REPL_RULES:
    if rule.get("regex"):
        _REPL_RULES_COMPILED.append(
            {"pattern": re.compile(rule["sym"]),
             "to": rule["to"], "regex": True}
        )
    else:
        _REPL_RULES_COMPILED.append(rule)


def count_chars(s: str, mode: str = "total") -> int:
    """
    mode:
      - "total": barcha belgilar soni
      - "no_whitespace": bo'shliq (space, tab, newline, ...) larsiz
      - "visible": zero-width va control (Cc/Cf/Cs/Co/Cn) ni chiqarib tashlab sanaydi
    """
    if mode == "total":
        return len(s)

    if mode == "no_whitespace":
        return len(re.sub(r"\s+", "", s))

    if mode == "visible":
        # Zero-widthlarni va barcha 'Control' toifadagi belgilarni olib tashlaymiz
        ZERO_WIDTH = {"\u200B", "\u200C", "\u200D", "\u2060"}
        cleaned = []
        for ch in s:
            # masalan: 'Ll', 'Nd', 'Zs', 'Cc', 'Cf'
            cat = unicodedata.category(ch)
            if ch in ZERO_WIDTH:
                continue
            if cat.startswith("C"):  # Cc, Cf, Cs, Co, Cn
                continue
            cleaned.append(ch)
        return len("".join(cleaned))

    raise ValueError(
        "mode 'total' | 'no_whitespace' | 'visible' bo'lishi kerak")


def semantic_minify(s: str, level: str = 'safe') -> str:
    # 1) Unicode normalizatsiya (NFKC) — kombinatsiyalarni ixcham qiladi
    s = unicodedata.normalize("NFKC", s)

    # 2) Tipografik belgilarni unifikatsiya (apostrof/dash/qo‘shtirnoq)
    for k, v in _APOS.items():
        s = s.replace(k, v)
    for k, v in _DASH.items():
        s = s.replace(k, v)
    s = s.replace("“", '"').replace("”", '"').replace(
        "„", '"').replace("«", '"').replace("»", '"')

    # 3) Hech narsa ko‘rinmaydigan belgilarni tozalash
    s = s.replace("\u200B", "").replace("\u200C", "").replace(
        "\u200D", "").replace("\u2060", "")

    # 4) Bo‘shliqlarni normallashtirish
    s = s.replace("\xa0", " ")
    # qatordagi ko‘p space/tab -> 1 space
    s = "\n".join(" ".join(line.split()) for line in s.split("\n"))
    s = s.strip()

    if level == 'safe':
        # — SAFE: ma’noli punktuatsiyani saqlaymiz, tipografiya tozalangan
        # Chiziqcha atrofidagi bo‘sh joyni nazorat: " - " (qoida bo‘yicha)
        s = s.replace(" - ", " - ")
        # Punktuatsiya oldi/ketidan bo‘shliq oddiylashtirish
        s = re.sub(r"\s+([,;:!?])", r"\1", s)     # vergul, nuqtali vergul, !
        s = re.sub(r"\s+(\.)", r"\1", s)          # nuqta
        s = re.sub(r"([(\[])\s+", r"\1", s)       # ochiq qavsdan so‘ng
        s = re.sub(r"\s+([)\]])", r"\1", s)       # yopiq qavsdan oldin
        return s + "\n"

    # — AGGRESSIVE: faqat harflar/raqamlar va minimal punktuatsiya
    out = []
    for ch in s:
        if ch.isalnum() or ch.isspace() or ch in _SAFE_PUNCTS:
            out.append(ch)
        # aks holda tashlaymiz (masalan, §, “bezak” chiziqlar, uzun tirelar, maxsus belgilar)
    s = "".join(out)

    # 5) Footnote va izoh raqamlari (qo‘pol, ammo foydali) — ixtiyoriy olib tashlash
    # Misol: "fan” 2." yoki "Matematika fanlari 1." oxiridagi " 1." ni olib tashlash
    s = re.sub(r"(\S)\s+\d+(\.)", r"\1\2", s)

    # 6) Qolgan bo‘shliqlarni ixchamla
    s = "\n".join(" ".join(line.split()) for line in s.split("\n"))
    s = re.sub(r"\n{2,}", "\n", s).strip()
    return s + "\n"
