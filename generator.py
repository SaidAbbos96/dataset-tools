import time

from api import call_llm_api, get_ai_api_client
import config
import data_validation
from functools import partial
import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import threading
import sys
import signal
from config import OUT_DIR, SRC_DIR, TEMP_DIR
import utils

# Global o'zgaruvchilar va flaglar
should_exit = False
processed_chunks = []


@dataclass
class ConversationConfig:
    api_url: str
    api_key: str
    model_name: str
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    resource: Optional[str] = None
    min_conversations: int = 1
    max_conversations: int = 10
    min_messages: int = 4
    max_messages: int = 12
    json_schema: Optional[dict] = None


def get_conversations(params: ConversationConfig) -> Union[List[Dict], bool]:
    client = get_ai_api_client(params.api_url, params.api_key)
    messages = [
        {"role": "system", "content": params.system_prompt}
    ]
    if params.user_prompt:
        messages.append({"role": "user", "content": params.user_prompt})
    if params.resource:
        messages.append(
            {"role": "user", "content": f"info: {params.resource}"})

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = call_llm_api(
                client=client,
                model=params.model_name,
                messages=messages,
                response_format_type="json_schema",
                json_schema=params.json_schema,
                max_tokens=2000,
                top_p=0.95,
                frequency_penalty=0.2,
                presence_penalty=0.2
            )

            # Parse response if needed
            if isinstance(response, str):
                response = json.loads(response)

            # Validate the response
            if data_validation.validate_conversation(response, params.json_schema["schema"]):
                return response

            print(f"Validation failed on attempt {attempt + 1}/{max_attempts}")

        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}")

            # Don't wait on the last attempt
            if attempt < max_attempts - 1:
                # Exponential backoff (1, 2, 4 seconds)
                wait_time = 2 ** attempt
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    print(f"All {max_attempts} attempts failed")
    return False


def signal_handler(sig, frame, id: str = "1"):
    global should_exit
    print("\nTizim to'xtatilmoqda... Joriy natijalarni saqlab olaman")
    should_exit = True
    save_partial_results(id)


def animate_loading():
    chars = "/—\\|"
    while not loading_complete:
        for char in chars:
            sys.stdout.write(f"\rYuklanmoqda {char}")
            sys.stdout.flush()
            time.sleep(0.1)
            if loading_complete:
                break


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
        utils.save_data_as_json(temp_file, processed_chunks)
        print(f"\nVaqtincha saqlangan natijalar: {temp_file}")
    except Exception as e:
        print(f"\nVaqtincha saqlashda xato: {e}")


def process_files_with_ai(delimiter: str = "###", min_count: int = 1,
                          max_count: int = 10, min_items: int = 2, max_items: int = 8):
    global should_exit, loading_complete, processed_chunks
    uniq_id = utils.generate_uuid()
    # print(uniq_id)

    API_SCHEMA = {
        "name": "conversation_samples",
        "schema": {
            "type": "array",
            "minItems": min_count,
            "maxItems": max_count,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    # "id": {"type": "string"},
                    "c": {
                        "type": "array",
                        "minItems": min_items,
                        "maxItems": max_items,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "f": {"type": "string", "enum": ["u", "a"]},
                                "v": {"type": "string", "minLength": 2}
                            },
                            "required": ["f", "v"]
                        }
                    }
                },
                "required": ["c"]
            }
        }
    }

    # Signalni sozlash
    signal.signal(signal.SIGINT, partial(signal_handler, id=uniq_id))
    # Vaqt hisobi boshlanishi
    start_time = time.time()
    # Fayllar ro'yxatini olish
    src_files = list(SRC_DIR.glob("*.txt"))
    if not src_files:
        print(f"SRC_DIR ({SRC_DIR}) da hech qanday .txt fayl topilmadi")
        return

    # Fayllarni tanlash
    print("\nMavjud fayllar:")
    for i, file in enumerate(src_files, 1):
        print(f"{i}. {file.name}")

    try:
        file_num = int(input("\nIshlamoqchi bo'lgan fayl raqamini kiriting: "))
        selected_file = src_files[file_num-1]
    except (ValueError, IndexError):
        print("Noto'g'ri raqam kiritildi")
        return

    # Saqlash uchun fayl nomi
    output_name = input(
        "Natijalar uchun fayl nomini kiriting (`.json` kiritmang): ")
    output_file = OUT_DIR / f"{output_name}_{uniq_id}.json"

    # Fayldagi ma'lumotlarni o'qish
    try:
        content = utils.get_data_from_file(selected_file)
    except Exception as e:
        print(f"Faylni o'qishda xato: {e}")
        return

    # Ma'lumotlarni bo'laklarga ajratish
    chunks = [chunk.strip()
              for chunk in content.split(delimiter) if chunk.strip()]
    if not chunks:
        print(
            f"Faylda hech qanday ma'lumot topilmadi ('{delimiter}' bilan ajratilgan bo'laklar)")
        return

    print(f"\n{len(chunks)} ta ma'lumot bo'lagi topildi. Jarayon boshlandi...")

    results = []
    processed_chunks = []

    # Bo'laklarni min_count miqdorida guruhlash
    chunk_groups = [chunks[i:i + min_count]
                    for i in range(0, len(chunks), min_count)]

    for group_num, chunk_group in enumerate(chunk_groups, 1):
        if should_exit:
            break

        # Loading animatsiyasi
        loading_complete = False
        loading_thread = threading.Thread(target=animate_loading)
        loading_thread.start()

        try:
            # Gruppadagi barcha bo'laklarni birlashtirish
            combined_content = "\n\n".join(chunk_group)

            # Conversationlarni olish
            # if config.MODEL_AUTO:
            #     model_name = config.MODEL_NAMES[0]
            #     models = config.MODEL_NAMES[1:]
            # else:
            #     model_name = config.MODEL_NAMES[1]
            #     models = None

            result = get_conversations(ConversationConfig(
                api_url=config.API_URL,
                api_key=config.OPENROUTER_API_KEYS[0],
                model_name=config.MODEL_NAMES[1],
                system_prompt=config.PROMTS['system-from-facts'] +
                f" generate exactly {min_count} conversations per request.",
                resource=combined_content,
                min_conversations=min_count,
                max_conversations=max_count,
                json_schema=API_SCHEMA
            ))

            loading_complete = True
            loading_thread.join()

            if result:
                start_idx = (group_num - 1) * min_count + 1
                end_idx = min(
                    group_num * min_count, len(chunks))
                print(
                    f"\rBo'laklar {start_idx}-{end_idx}/{len(chunks)}: {len(result)} ta conversation")
                result = data_validation.expand_keys(result)
                results.extend(result)
                processed_chunks.extend(result)

                # Har 5 guruhdan keyin vaqtinchalik saqlash
                if group_num % 5 == 0:
                    save_partial_results(uniq_id)
            else:
                print(
                    f"\rGuruh {group_num} uchun conversation olish muvaffaqiyatsiz tugadi")

        except Exception as e:
            loading_complete = True
            loading_thread.join()
            print(f"\rGuruh {group_num} ishlashda xato: {e}")
            continue

    # Yakuniy natijalarni saqlash
    try:
        utils.save_data_as_json(output_file, results)
        print(f"\nNatijalar muvaffaqiyatli saqlandi: {output_file}")
        print(f"Jami {len(results)} ta conversation generatsiya qilindi")
        # vaqt hisobini chiqaramiz
        utils.print_time_info(start_time)
        # Vaqtincha fayllarni o'chirish
        clear_partial_results(uniq_id)

    except Exception as e:
        print(
            f"Natijalarni saqlashda yoki temp filelarni o'chirishda xatolik: {e}")


if __name__ == "__main__":
    process_files_with_ai("\n", min_count=5)


# if __name__ == "__main__":
    # resource = "test"
    # # Conversationlarni olish
    # result = get_conversations(ConversationConfig(
    #     api_url=config.API_URL,
    #     api_key=config.OPENROUTER_API_KEYS[0],
    #     =config.MODEL_NAMES[0],
    #     system_prompt=config.PROMTS['system-from-text'],
    #     resource=resource
    # ))
    # print(result)
    # if result:
    #     print(f"Successfully got {len(result)} conversations")
    # else:
    #     print("Failed to get valid conversations")
