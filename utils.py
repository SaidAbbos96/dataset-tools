import json
import time
from typing import Dict, List, Union

import uuid


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
        print(f"Faylni o'qishda xato: {e}")
        return


def print_time_info(start_time: float):
    # Vaqt hisobi
    end_time = time.time()
    total_time = end_time - start_time
    hours, rem = divmod(total_time, 3600)
    minutes, seconds = divmod(rem, 60)
    print(
        f"Jami vaqt: {int(hours)} soat {int(minutes)} daqiqa {int(seconds)} soniya")
