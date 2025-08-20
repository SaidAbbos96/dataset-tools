import json
import os
from pathlib import Path
import sys
import threading
import time
from typing import Dict, List, Literal, Optional, Union, Any

import uuid

from config import SRC_DIR, TEMP_DIR, processed_chunks
import config


def get_list_from_json_file(filepath: str) -> List[Any] | None:
    """
    Berilgan fayl yo'li (filepath) bo'yicha JSON faylni ochadi,
    uning ichidagi ro'yxatni o'qib qaytaradi.

    Args:
        filepath: JSON faylning yo'li (string).

    Returns:
        JSON fayl ichidagi ro'yxatni (List) qaytaradi.
        Agar fayl topilmasa, JSON xato bo'lsa yoki ichidagi ma'lumot
        ro'yxat bo'lmasa, None qaytaradi.
    """
    file_path = Path(filepath)

    if not file_path.exists():
        print(f"Xato: '{filepath}' fayli topilmadi.")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                print(f"Xato: JSON fayl ichidagi ma'lumot ro'yxat emas.")
                return None
    except json.JSONDecodeError:
        print(f"Xato: '{filepath}' fayli yaroqsiz JSON formatida.")
        return None
    except Exception as e:
        print(f"Kutilmagan xato: {e}")
        return None


def generate_uuid(compact: bool = False) -> str:
    """
    UUID (Universally Unique Identifier) generatsiya qiladi

    Returns:
        str: 36 belgili UUID (format: 550e8400-e29b-41d4-a716-446655440000)
    """
    return str(uuid.uuid4()).replace("-", "") if compact else str(uuid.uuid4())


def save_data_as_json(filename_full_path: str, data: List[Dict]):
    try:
        with open(filename_full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Natijalarni saqlashda xato: {e}")
        return


def get_data_from_file(filename_full_path: str):
    try:
        with open(filename_full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return content
    except Exception as e:
        print(f"Faylni o'qishda xatolik: {e}")
        return


def print_time_info(start_time: float):
    # Vaqt hisobi
    end_time = time.time()
    total_time = end_time - start_time
    hours, rem = divmod(total_time, 3600)
    minutes, seconds = divmod(rem, 60)
    print(
        f"Jami vaqt: {int(hours)} soat {int(minutes)} daqiqa {int(seconds)} soniya")


def signal_handler(sig, frame, id: str = "1"):
    # Birinchi signalda ishlaydi, keyingilarini e'tiborsiz qoldirish uchun simple guard qo‘yish mumkin
    print("\nTizim to'xtatilmoqda... Joriy natijalarni saqlab olaman")
    # loaderni to'xtatamiz
    try:
        if config.current_loader_event is not None:
            config.current_loader_event.set()
    except Exception:
        pass

    # faqat SAQLANMAGAN qismini yozamiz: buffer[saved_index:]
    try:
        buf = config.processed_chunks
        start = getattr(config, "saved_index", 0)
        if start < len(buf):
            new_slice = buf[start:]
            if new_slice:
                save_partial_results(id, new_slice, part_idx="SIGINT")
                config.saved_index = len(buf)
                print(f"[SIGINT] {len(new_slice)} ta yangi bo'lak saqlandi.")
        else:
            print("[SIGINT] Yangi saqlanadigan bo‘lak yo‘q.")
    except Exception as e:
        print(f"[SIGINT] Saqlashda xato: {e}")

    # asosiy siklga chiqish signali
    try:
        # bu flagni asosiy sikl tekshiradi
        import builtins
        builtins.should_exit = True  # yoki config.should_exit = True
    except Exception:
        pass

    # Jarayonni toza yopish (bloklangan joy bo‘lsa ham 130 exit code)
    try:
        sys.exit(130)
    except SystemExit:
        raise


def animate_loading(stop_event: threading.Event):
    chars = "/—\\|"
    while not stop_event.is_set():
        for ch in chars:
            if stop_event.is_set():
                break
            sys.stdout.write(f"\rYuklanmoqda {ch}")
            sys.stdout.flush()
            time.sleep(0.1)
    # chiziqni tozalab qo'yamiz
    sys.stdout.write("\r" + " " * 40 + "\r")
    sys.stdout.flush()


def run_with_loader(fn, *args, **kwargs):
    stop_event = threading.Event()
    config.current_loader_event = stop_event
    t = threading.Thread(target=animate_loading,
                         args=(stop_event,), daemon=True)
    t.start()
    try:
        return fn(*args, **kwargs)
    finally:
        stop_event.set()
        t.join()
        config.current_loader_event = None
        # konsolni tozalash ixtiyoriy
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()


def clear_partial_results(id: str = "1"):
    for temp_file in TEMP_DIR.glob(f"partial_{id}*.json"):
        try:
            temp_file.unlink()
        except:
            pass


def save_partial_results(uniq_id: str,
                         buffer: list,
                         part_idx: int | None = None,
                         temp_dir: Path = TEMP_DIR) -> None:
    """
    Vaqtinchalik natijalarni diskka yozadi.
    - buffer: ayni paytdagi natijalar ro'yxati (aniq uzatiladi)
    - part_idx: qaysi guruhgacha snapshot (ixtiyoriy)
    - atomar yozish: .part -> final rename
    """
    if not buffer:
        return

    # Katalogni yaratib qo'yamiz
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Mutatsiyadan saqlanish uchun snapshot olamiz
    snapshot = list(buffer)

    ts = int(time.time())
    suffix = f"_part-{part_idx}" if part_idx is not None else ""
    file_name = f"partial_{uniq_id}{suffix}_c_{len(snapshot)}_{ts}.json"
    final_path = temp_dir / file_name
    part_path = final_path.with_suffix(final_path.suffix + ".part")

    try:
        # Atomar yozish ketma-ketligi
        with part_path.open("w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        part_path.replace(final_path)

        print(
            f"\nVaqtincha saqlangan natijalar ({len(snapshot)}) ta: {file_name}")
    except Exception as e:
        print(f"\nVaqtincha saqlashda xato: {e}")


def choose_source_file() -> Path | None:
    src_files = list(SRC_DIR.glob("*.txt"))
    if not src_files:
        print(f"SRC_DIR ({SRC_DIR}) da hech qanday .txt fayl topilmadi")
        return None

    print("\nMavjud fayllar:")
    for i, file in enumerate(src_files, 1):
        print(f"{i}. {file.name}")

    try:
        file_num = int(input("\nIshlamoqchi bo'lgan fayl raqamini kiriting: "))
        return src_files[file_num - 1]
    except (ValueError, IndexError):
        print("Noto'g'ri raqam kiritildi")
        return None


def read_content_file(file_path: Path) -> str | None:
    try:
        return get_data_from_file(file_path)
    except Exception as e:
        print(f"Faylni o'qishda xato: {e}")
        return None


def split_chunks(content: str, delimiter: str) -> list[str]:
    chunks = [c.strip() for c in content.split(delimiter) if c.strip()]
    if not chunks:
        print(
            f"Faylda hech qanday ma'lumot topilmadi ('{delimiter}' bilan ajratilgan bo'laklar)")
        return []
    return chunks


def batch_adaptive_by_chars(chunks: list[str],
                            max_lines: int = config.MAX_LINES_DEFAULT,
                            max_chars: int = config.MAX_CHARS_DEFAULT) -> list[list[str]]:
    """
    1) Har iteratsiyada  max_lines dan boshlaydi
    2) "\n\n".join(group) uzunligi max_chars dan oshsa, lines-- qilib tekshiradi
    3) Mos kelganda group => natijaga qo'shadi va ko'rsatkichni oldinga suradi
    """
    groups = []
    i = 0
    n = len(chunks)
    while i < n:
        lines = min(max_lines, n - i)
        # kamida 1 qatorda bo'lsin
        while lines > 0:
            candidate = chunks[i:i + lines]
            combined = "\n\n".join(candidate)
            if len(combined) <= max_chars:
                groups.append(candidate)
                i += lines
                break
            lines -= 1

        if lines == 0:
            # Juda uzun bitta chunk bo'lsa, uni kesish (yoki log)
            # Bu fallback: bitta chunk 2000+ bo‘lsa, minimal ishlash uchun trunc qilish yoki skip
            # Bu yerda xavfsiz variant — trunc:
            over = chunks[i]
            safe = over[:max_chars]
            groups.append([safe])
            i += 1

    return groups




# Literal yordamida mumkin bo'lgan qiymatlarni belgilaymiz
SortBy = Literal['name', 'date', 'size', 'none']
FilterBy = Literal['none', 'name', 'size_range']

def find_files_by_pattern(
    path: Path,
    pattern: str,
    sort_by: SortBy = 'name',
    reverse_sort: bool = False,
    min_size_kb: Optional[int] = None,
    max_size_kb: Optional[int] = None,
    filter_by_name: Optional[str] = None
) -> List[Path]:
    """
    Berilgan yo'l (path) ichida, berilgan naqsh (pattern) bo'yicha fayllarni qidiradi
    va ularni sortlash hamda filterlash imkoniyatini taqdim etadi.

    Args:
        path (Path): Fayllar qidiriladigan papkaning yo'li.
        pattern (str): Qidirish naqshi (masalan, '*.json' yoki 'report_*.txt').
        sort_by (SortBy): Fayllarni saralash mezoni ('name', 'date', 'size' yoki 'none').
                          Default 'name'.
        reverse_sort (bool): Saralash tartibini teskari qilish. Default False.
        min_size_kb (Optional[int]): Minimal fayl hajmi (KB). None bo'lsa, hajm bo'yicha filterlanmaydi.
        max_size_kb (Optional[int]): Maksimal fayl hajmi (KB). None bo'lsa, hajm bo'yicha filterlanmaydi.
        filter_by_name (Optional[str]): Fayl nomida mavjud bo'lishi kerak bo'lgan matn.

    Returns:
        List[Path]: Filterdan o'tgan va saralangan fayllarning ro'yxati.
    """
    # 1. Pattern bo'yicha dastlabki fayllarni topish
    found_files = list(path.glob(pattern))

    if not found_files:
        return []

    # 2. Fayllarni filterlash
    filtered_files = found_files
    # Nom bo'yicha filter
    if filter_by_name:
        filtered_files = [
            f for f in filtered_files if filter_by_name in f.name]

    # Hajm bo'yicha filter
    if min_size_kb is not None or max_size_kb is not None:
        min_bytes = min_size_kb * 1024 if min_size_kb is not None else 0
        max_bytes = max_size_kb * \
            1024 if max_size_kb is not None else float('inf')
        filtered_files = [
            f for f in filtered_files if min_bytes <= os.path.getsize(f) <= max_bytes]

    # 3. Fayllarni sortlash
    if sort_by == 'date':
        # Eng oxirgi o'zgartirilgan fayllar boshida bo'lishi uchun 'reverse=True' default bo'lishi mumkin
        filtered_files.sort(key=os.path.getmtime, reverse=reverse_sort)
    elif sort_by == 'size':
        filtered_files.sort(key=os.path.getsize, reverse=reverse_sort)
    elif sort_by == 'name':
        # Nomi bo'yicha alifbo tartibida sort
        filtered_files.sort(reverse=reverse_sort)
    # 'none' bo'lsa, saralanmaydi

    return filtered_files