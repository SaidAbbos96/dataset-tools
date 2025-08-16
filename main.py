#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF -> toza va yengil .txt
- files/src/ ichidan PDF tanlanadi
- Sahifa spetsifikatori: "2,5,7-9" yoki "*" (hammasi)
- Matn tozalanadi: soft-hyphen, zero-width, NBSP, ko'p probel/tab, noto'g'ri bo'linishlar
- Qatorlarni wrap_threshold asosida aqlli birlashtirish
- Abzatslar orasida faqat bitta \n
- Chiqarish: files/finish/<pdfnomi>.txt
"""
import os
import re
import sys
from pathlib import Path

from utils import _REPL_RULES_COMPILED, MINIFY_LEVEL, count_chars, semantic_minify

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF topilmadi. O'rnating: pip install pymupdf")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "files" / "src"
OUT_DIR = ROOT / "files" / "finish"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SRC_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------ FS yordamchi ------------------------


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
    s = pre_clean(full_text)
    s = join_wrapped_lines(s, wrap_threshold=wrap_threshold)
    s = post_normalize(s)
    s = semantic_minify(s, level=MINIFY_LEVEL)   # << qo'shildi
    return s

# ------------------------ Ekstraksya ------------------------


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
        return clean_text(raw_all, wrap_threshold=80)
    finally:
        doc.close()

# ------------------------ Main ------------------------


def main():
    pdfs = list_pdfs(SRC_DIR)
    if not pdfs:
        print(
            f"{SRC_DIR} ichida .pdf topilmadi. Avval PDF fayllarni shu papkaga qo‘ying.")
        return

    print("PDF fayllar ro‘yxati:")
    pdf_path = prompt_choice(pdfs)

    with fitz.open(pdf_path) as d:
        total = d.page_count
    print(f"Tanlangan: {pdf_path.name} (jami sahifa: {total})")

    spec = input("-> Sahifalar (masalan: 2,5,7-9) yoki * (hammasi): ").strip()
    if spec and spec != "*":
        pages = parse_pages(spec, total)
        if not pages:
            print("Sahifa tanlovi bo‘yicha mos sahifa topilmadi.")
            return
    else:
        pages = list(range(total))

    print(
        f"Ajratiladigan sahifalar (1-based): {', '.join(str(i+1) for i in pages)}")

    text = extract_text(pdf_path, pages)

    out_file_name = f"{pdf_path.stem}.txt"
    out_path = OUT_DIR / out_file_name
    out_path.write_text(text, encoding="utf-8")
    print(f"✅ Saqlandi: {out_file_name} INFO: ~{count_chars(text)} ta belgilar, (~{out_path.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
