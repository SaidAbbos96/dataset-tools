import time
import config
from conversations import ConversationConfig, get_conversations, make_schema_for_count
import data_validation
from functools import partial
import signal
from config import MAX_CHARS_DEFAULT, MAX_LINES_DEFAULT, OUT_DIR, should_exit, processed_chunks
import utils
import time
import signal
from functools import partial


def request_conversations(group_text: str, conv_count: int, api_schema: dict, promt: str):
    return get_conversations(ConversationConfig(
        api_url=config.API_URL,
        api_key=config.OPENROUTER_API_KEYS[0],
        model_name=config.MODEL_NAMES[1],
        system_prompt=promt,
        resource=group_text,
        min_conversations=conv_count,
        max_conversations=conv_count,
        json_schema=api_schema
    ))


def process_files_with_ai(
    delimiter: str = "###",
    min_count: int = 1,
    max_count: int = 10,
    min_items: int = 2,
    max_items: int = 8,
    # YANGI parametrlar:
    max_lines_per_group: int = MAX_LINES_DEFAULT,
    max_chars_per_group: int = MAX_CHARS_DEFAULT
):
    global should_exit  # processed_chunks ni "global" demang
    ...
    results = []
    config.processed_chunks.clear()

    uniq_id = utils.generate_uuid()

    # Schema (min/max conversations sizning kiritingan parametrlar bilan hamohang bo‘lishi mumkin,
    # ammo biz guruh uzunligiga teng (conv_count) yuboramiz)
    API_SCHEMA = make_schema_for_count(
        min_count, max_count, min_items, max_items)

    # SIGINT
    signal.signal(signal.SIGINT, partial(utils.signal_handler, id=uniq_id))

    start_time = time.time()

    selected_file = utils.choose_source_file()
    if not selected_file:
        return

    output_name = input(
        "Natijalar uchun fayl nomini kiriting (`.json` kiritmang): ")
    output_file = OUT_DIR / f"{output_name}_{uniq_id}.json"

    content = utils.read_content_file(selected_file)
    if content is None:
        return

    chunks = utils.split_chunks(content, delimiter)
    if not chunks:
        return

    print(f"\n{len(chunks)} ta ma'lumot bo'lagi topildi. Jarayon boshlandi...")

    adaptive_groups = utils.batch_adaptive_by_chars(
        chunks,
        max_lines=max_lines_per_group,
        max_chars=max_chars_per_group
    )

    results = []

    for group_num, chunk_group in enumerate(adaptive_groups, 1):
        if should_exit:
            break

        conv_count = max(min(len(chunk_group), max_count), min_count)
        combined_content = "\n\n".join(chunk_group)
        promt = data_validation.strict_system_prompt(
            config.PROMTS["system-from-text"],
            min_count,  min_items, max_items)
        try:
            result = utils.run_with_loader(
                request_conversations,
                combined_content,
                conv_count,
                API_SCHEMA,
                promt

            )
            if result:
                start_idx = sum(len(g)
                                for g in adaptive_groups[:group_num-1]) + 1
                end_idx = start_idx + len(chunk_group) - 1
                print(
                    f"\rBo'laklar {start_idx}-{end_idx}/{len(chunks)}: {len(result)} ta conversation")

                result = data_validation.expand_keys(result)
                results.extend(result)
                # Eskidek rebind emas, in-place yig'amiz:
                config.processed_chunks.extend(result)

                if group_num % 5 == 0:
                    utils.save_partial_results(
                        uniq_id,
                        config.processed_chunks,
                        part_idx=group_num
                    )
            else:
                print(
                    f"\rGuruh {group_num} uchun conversation olish muvaffaqiyatsiz tugadi")
        except Exception as e:
            utils.save_partial_results(
                uniq_id,
                config.processed_chunks,
                part_idx=group_num
            )
            print(f"\rGuruh {group_num} ishlashda xato: {e}")
            continue

    # Yakuniy natijalar
    try:
        utils.save_data_as_json(output_file, results)
        print(f"\nNatijalar muvaffaqiyatli saqlandi: {output_file}")
        print(f"Jami {len(results)} ta conversation generatsiya qilindi")
        utils.print_time_info(start_time)
        utils.clear_partial_results(uniq_id)
    except Exception as e:
        print(
            f"Natijalarni saqlashda yoki temp filelarni o'chirishda xatolik: {e}")


if __name__ == "__main__":
    process_files_with_ai("\n", min_count=5, max_lines_per_group=10)
