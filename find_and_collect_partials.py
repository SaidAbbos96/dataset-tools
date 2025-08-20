from pathlib import Path
from typing import Any, List, Optional
import utils
import config


def find_and_collect_partials(id: str, path: str) -> Optional[List[Any]]:
    """
    Berilgan ID va yo'l bo'yicha mos JSON fayllarni topadi,
    ularni sanasi bo'yicha saralaydi va ichidagi ma'lumotlarni yig'ib qaytaradi.

    Args:
        id (str): Fayl nomida qidirilayotgan ID.
        path (str): Fayllar joylashgan papkaning yo'li.

    Returns:
        List[Any]: Barcha fayllardagi ma'lumotlardan tashkil topgan
                   yagona ro'yxatni qaytaradi.
        None: Agar fayllar topilmasa yoki birorta fayl ham
              to'g'ri o'qilmasa, None qaytaradi.
    """
    # Path ob'ektidan foydalanish amaliyotini yaxshilaydi
    try:
        path_obj = Path(path)
    except Exception as e:
        print(f"Xato: Berilgan yo'l yaroqsiz - {e}")
        return None

    if not path_obj.exists() or not path_obj.is_dir():
        print(f"Xato: '{path}' papkasi topilmadi yoki u papka emas.")
        return None

    # Fayllarni topish va sortlash
    found_files = utils.find_files_by_pattern(
        # utils funksiyasi string path talab qilishi mumkin
        path=path_obj,
        pattern=f"*{id}*.json",
        sort_by="date",
        reverse_sort=False
    )

    if not found_files:
        print("Filelar topilmadi.")
        return None

    print(
        f"Filelar topildi ({len(found_files)} ta), ma'lumotlarni yig'ish boshlandi.")

    all_data = []
    successful_files_count = 0

    for file in found_files:
        # Har bir fayl uchun alohida try-except blokidan foydalanish
        # bir fayldagi xato butun funksiyani to'xtatib qo'yishini oldini oladi.
        try:
            data = utils.get_list_from_json_file(file)
            if data:
                all_data.extend(data)
                successful_files_count += 1
        except Exception as e:
            print(
                f"Ogohlantirish: '{file}' faylida ma'lumotlarni yuklashda xato yuz berdi: {e}")
            continue

    if not all_data:
        print("Barcha topilgan fayllar bo'sh yoki xato tufayli o'qilmadi.")
        return None

    print(
        f"Ma'lumotlar {successful_files_count} ta fayldan muvaffaqiyatli yig'ildi.")

    return all_data


def main(id: str = None, to_path: str = None):
    path: str = config.TEMP_DIR
    if to_path:
        path = path / to_path

    print(f"Dastur ishga tushdi, workdir: {path}")
    if not id:
        id: str = input("ID ni kiriting: ")

    partials_data = find_and_collect_partials(id, path)
    final_file_name: str = input("File nomini qanday saqlaymiz *.json: ")
    final_file_path: Path = config.OUT_DIR / \
        f"{final_file_name}_c_{len(partials_data)}_{id}.json"
    if utils.save_data_as_json(final_file_path, partials_data):
        clear_tmp_files = input(
            "File yaratildi, tmp filelar tozalansinmi ? (y/n)")
        if clear_tmp_files == "y":
            utils.clear_partial_results(id)
            print("tmp filelar tozalandi.")
        else:
            print("Jarayon yaklunlandi.")


if __name__ == "__main__":
    id = "bee4ee4e-126c-4545-9b28-3fce50cc953b"
    main(id)
