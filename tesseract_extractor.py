import os
import tempfile
from typing import List
from PIL import Image
import pytesseract
import fitz

from utils import clean_text  # PyMuPDF


def extract_text_from_pdf_pages(
    pdf_path: str,
    page_numbers: List[int],
    language: str = 'uzb+eng+rus'
) -> str:
    """
    PDF faylning berilgan sahifalaridan matnni ajratib olish

    Args:
        pdf_path: PDF fayl yo'li
        page_numbers: Sahifalar ro'yxati (0-indexed)
        language: OCR uchun til (uzb, eng, rus, uzb+eng, ...)

    Returns:
        Ajratilgan matnlar birlashtirilgan holda
    """
    # PDF fayl mavjudligini tekshirish
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF fayl topilmadi: {pdf_path}")
    print(f"Sahifa suratlaridan matnlarni olish boshlandi...")
    # Vaqtinchalik papka yaratish
    with tempfile.TemporaryDirectory() as temp_dir:
        extracted_texts = []

        try:
            # PDF ni ochish
            pdf_document = fitz.open(pdf_path)

            # Har bir sahifani qayta ishlash
            for page_num in page_numbers:
                print(f"Sahifa {page_num+1}, ustida ishlaymiz...")
                # Sahifa indeksini tekshirish
                if page_num < 0 or page_num >= len(pdf_document):
                    print(
                        f"Ogohlantirish: {page_num}-sahifa mavjud emas, o'tkazib yuborildi")
                    continue
                
                # Sahifani olish
                page = pdf_document[page_num]

                # Sahifani rasmga aylantirish (yuqori sifat bilan)
                mat = page.get_pixmap(
                    matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
                img_path = os.path.join(temp_dir, f"page_{page_num}.png")
                mat.save(img_path)

                # Rasmni OCR orqali matnga aylantirish
                text = extract_text_from_image(img_path, language)
                # extracted_texts.append(f"--- [Sahifa {page_num + 1}] ---\n{text}\n")
                extracted_texts.append(clean_text(text))

            # PDF ni yopish
            pdf_document.close()

            # Barcha matnlarni birlashtirish
            raw_all = "\n".join(extracted_texts)
            return clean_text(raw_all) or None

        except Exception as e:
            raise Exception(f"PDF qayta ishlashda xato: {str(e)}")


def extract_text_from_image(image_path: str, language: str = 'uzb+eng+rus') -> str:
    """
    Rasm fayldan matnni ajratib olish (OCR)
    """
    try:
        # Rasmni ochish va OCR qilish
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang=language)
        return text.strip()
    except Exception as e:
        raise Exception(f"OCR qilishda xato: {str(e)}")


# Funksiyani ishlatish misoli
if __name__ == "__main__":
    try:
        # PDF yo'li
        pdf_path = "/home/aicoder/coding/dataset-tools/tools/pdf-extractor/files/src/safayeva_s_r_turizm_va_ozbekiston_milliy_merosi_o_q_2017-2.pdf"

        # Qayta ishlash kerak bo'lgan sahifalar (0 dan boshlanadi)
        page_numbers = [0, 2, 4]  # 1, 3 va 5-sahifalar

        # Til (uzb, eng, rus, uzb+eng, hokazo)
        language = "uzb+eng"

        # Matnni ajratib olish
        result_text = extract_text_from_pdf_pages(
            pdf_path, page_numbers, language)

        # Natijani ko'rsatish
        print(result_text)

        # Natijani faylga saqlash (ixtiyoriy)
        with open("ajratilgan_matn.txt", "w", encoding="utf-8") as f:
            f.write(result_text)

    except Exception as e:
        print(f"Xato: {e}")
