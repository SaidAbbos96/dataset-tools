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
        api_key=config.OPENROUTER_API_KEYS[config.DEFAULT_API_KEY_INDEX],
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
    # --- Boshlanish: state/init ---
    results: list = []
    config.processed_chunks.clear()     # in-place
    # diskka yozilgan elementlar SONI (count)
    config.saved_index = 0

    uniq_id = utils.generate_uuid()

    # SIGINT (Ctrl+C) – signal handler ichida delta saqlash va loaderni to'xtatish
    signal.signal(signal.SIGINT, partial(utils.signal_handler, id=uniq_id))

    start_time = time.time()

    # --- Fayl tanlash va o‘qish ---
    selected_file = utils.choose_source_file()
    if not selected_file:
        return

    output_name = input(
        "Natijalar uchun fayl nomini kiriting (`.json` kiritmang): ")

    content = utils.read_content_file(selected_file)
    if content is None:
        return

    chunks = utils.split_chunks(content, delimiter)
    if not chunks:
        return

    print(f"\n{len(chunks)} ta ma'lumot bo'lagi topildi. Jarayon boshlandi...")

    # --- Adaptiv batching: 10 qatorgacha, ≤2000 belgi ---
    adaptive_groups = utils.batch_adaptive_by_chars(
        chunks,
        max_lines=max_lines_per_group,
        max_chars=max_chars_per_group
    )

    # --- Asosiy sikl ---
    for group_num, chunk_group in enumerate(adaptive_groups, 1):
        if config.should_exit:  # flag configdan
            break

        # Guruhga mos aniq son
        conv_count = min(len(chunk_group), min_count)
        combined_content = "\n\n".join(chunk_group)

        # HAR GURUH uchun EXACT schema (min=max=conv_count)
        API_SCHEMA = make_schema_for_count(
            conv_count, max_count, min_items, max_items)

        # Strict JSON-only prompt – aynan shu conv_count bilan
        prompt = data_validation.strict_system_prompt(
            config.PROMTS["system-from-text"], conv_count, max_count, min_items, max_items
        )
        # print(prompt)

        try:
            # Loader bilan ishga tushirish
            result = utils.run_with_loader(
                request_conversations,
                combined_content,
                conv_count,
                API_SCHEMA,
                prompt
            )

            if result:
                # Log uchun ko‘rsatkichlar
                start_idx = sum(len(g)
                                for g in adaptive_groups[:group_num-1]) + 1
                end_idx = start_idx + len(chunk_group) - 1
                print(
                    f"\rBo'laklar {start_idx}-{end_idx}/{len(chunks)}: {len(result)} ta conversation")

                # JSONni kengaytirish va yig‘ish
                result = data_validation.expand_keys(result)
                results.extend(result)
                config.processed_chunks.extend(result)

                # Har 2 guruhda faqat yangi bo‘laklarni saqlaymiz (delta)
                if group_num % 2 == 0:
                    new_slice = config.processed_chunks[config.saved_index:]
                    if new_slice:
                        utils.save_partial_results(
                            uniq_id,
                            new_slice,
                            part_idx=group_num
                        )
                        # Endi saqlangan sonni yangilaymiz
                        config.saved_index = len(config.processed_chunks)

            else:
                print(
                    f"\rGuruh {group_num} uchun conversation olish muvaffaqiyatsiz tugadi")

        except Exception as e:
            # Xatoda ham delta saqlaymiz
            new_slice = config.processed_chunks[config.saved_index:]
            if new_slice:
                utils.save_partial_results(
                    uniq_id, new_slice, part_idx=group_num)
                config.saved_index = len(config.processed_chunks)
            print(f"\rGuruh {group_num} ishlashda xato: {e}")
            continue

        # CTRL+C bosilgandan keyin handler flagni ko‘targan bo‘lsa — toza chiqish
        if config.should_exit:
            # ehtiyot uchun yana delta saqlash
            new_slice = config.processed_chunks[config.saved_index:]
            if new_slice:
                utils.save_partial_results(
                    uniq_id, new_slice, part_idx="EARLY_EXIT")
                config.saved_index = len(config.processed_chunks)
            break

        results_len = len(results)
        # Debug
        print(
            f"Jami natijalar: {results_len} ta, Diskka saqlangan: {config.saved_index} ta")

    # --- Yakuniy natijalar ---
    try:
        output_file_name = f"{output_name}_c_{results_len}_{uniq_id}.json"
        output_file = OUT_DIR / output_file_name
        if utils.save_data_as_json(output_file, results):
            print(f"\nNatijalar muvaffaqiyatli saqlandi: {output_file_name}")
            print(f"Jami {results_len} ta conversation generatsiya qilindi")
            utils.print_time_info(start_time)
            # tmp fayllarni tozalash (ixtiyoriy)
            # utils.clear_partial_results(uniq_id)

    except Exception as e:
        print(
            f"Natijalarni saqlashda yoki temp filelarni o'chirishda xatolik: {e}")


if __name__ == "__main__":
    process_files_with_ai("\n", min_count=5, max_lines_per_group=10)
    
