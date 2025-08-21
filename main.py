#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import fitz
from config import OUT_DIR, SRC_DIR
from tesseract_extractor import extract_text_from_pdf_pages
from times import get_formatted_datetime
from utils import count_chars, extract_text, list_pdfs, parse_pages, prompt_choice


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
    new_file_name = input(
        "yangi fileni qanday nom bilan saqlaymiz: ") or pdf_path.stem
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

    if len(text) < 2:
        print("Matn topilmadi rasmlardan qidiramiz !")
        text = extract_text_from_pdf_pages(pdf_path, pages, "uzb")

    if text:
        print(
            f"Matnlar ajratib olindi, belgilar soni jami {count_chars(text)} ta. filega saqlaymiz !")
        out_file_name = f"{new_file_name}_{count_chars(text)}_{get_formatted_datetime()}.txt"
        out_path = OUT_DIR / out_file_name
        out_path.write_text(text, encoding="utf-8")
        print(
            f"✅ Saqlandi: {out_file_name} INFO: ~{count_chars(text)} ta belgilar, (~{out_path.stat().st_size/1024:.1f} KB)")
    else:
        print(f"Xatolik, belgilar soni jami {count_chars(text)}ta.")


if __name__ == "__main__":
    main()
