import json
import sys
import threading
import time
from typing import Dict, List, Union

import uuid

from config import TEMP_DIR, processed_chunks


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
    global should_exit
    print("\nTizim to'xtatilmoqda... Joriy natijalarni saqlab olaman")
    should_exit = True
    save_partial_results(id)


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


def clear_partial_results(id: str = "1"):
    for temp_file in TEMP_DIR.glob(f"partial_{id}*.json"):
        try:
            temp_file.unlink()
        except:
            pass


def save_partial_results(id: str = "1"):
    if not processed_chunks:
        return

    timestamp = int(time.time())
    temp_file = TEMP_DIR / f"partial_{id}_{timestamp}.json"

    try:
        save_data_as_json(temp_file, processed_chunks)
        print(f"\nVaqtincha saqlangan natijalar: {temp_file}")
    except Exception as e:
        print(f"\nVaqtincha saqlashda xato: {e}")
