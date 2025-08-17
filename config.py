from pathlib import Path
from dotenv import load_dotenv
import os

# .env faylni avtomatik topib yuklaydi (agar u project rootda bo‘lsa)
load_dotenv()

OPENROUTER_API_KEYS = os.getenv("OPENROUTER_API_KEYS").split(",")
API_URL = "https://openrouter.ai/api/v1"

MODEL_AUTO = False
DEFAULT_API_KEY_INDEX = 0
MODEL_NAMES = [
    "openrouter/auto",
    "deepseek/deepseek-chat-v3-0324",
    "meta-llama/llama-3.2-1b-instruct",
    "google/gemma-2-9b-it",
    # "openai/gpt-oss-20b:free",
    "liquid/lfm-7b",
    "google/gemma-2-9b-it",
    "deepseek/deepseek-r1-0528-qwen3-8b",
    "cognitivecomputations/dolphin3.0-r1-mistral-24b",
]


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "files" / "source"
OUT_DIR = ROOT / "files" / "finish"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SRC_DIR.mkdir(parents=True, exist_ok=True)

TEMP_DIR = ROOT / "files" / "finish" / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# Global o'zgaruvchilar va flaglar
should_exit = False
processed_chunks = []
saved_index = 0
current_loader_event = None  # signal_handler ko‘radi
MAX_LINES_DEFAULT = 10
MAX_CHARS_DEFAULT = 2000

PROMTS = {
    "system": """You are generating high-quality TRAINING DATA for a national Uzbek AI assistant.
        OUTPUT RULES (must follow strictly):
        - Output MUST be valid JSON that conforms to the provided JSON schema.
        - Language: 100% Uzbek (Latin script only; no Cyrillic).
        - Topics must be deep, educational, and culturally relevant. Cover diverse fields:
        Science (physics, chemistry, biology, CS, astronomy), engineering, mathematics,
        history (world + Uzbekistan), biographies, arts & culture (Uzbek literature, music,
        cinema, crafts), Uzbek language and grammar, geography (regions, climate, nature),
        education/study skills, logic and problem solving, practical life knowledge in Uzbekistan.
        - Avoid religion, politics, or any sensitive/controversial content.
        - Each conversation should feel natural, helpful, respectful, and informative.
        - 4–8 turns is ideal; start with a realistic user question, then alternate user/assistant.
        - No trivia-level small talk; prioritize meaningful facts, explanations, and reasoning.
        - Never repeat earlier generated content; ensure uniqueness and non-redundancy.
        - Do NOT include references or links. No source citations.
        - Keep responses concise but substantial; avoid fluff.
    """,
    "user": """Generate 2 independent JSON objects. 
        Each object must match the given schema and represent a single Uzbek conversation with a unique `"id"`.
        Quality constraints:
        - Rich, accurate, Uzbekistan-relevant knowledge where appropriate.
        - No religion/politics/sensitive topics.
        - Latin Uzbek only.
        - 4–8 turns per conversation, alternating user/assistant naturally.
        - Completely unique samples (no overlap with each other).
        Return them as a JSON array (list) of objects, WITHOUT any extra text.
    """,
    "topics": [
        "O‘zbekiston tarixidagi islohotlar va madaniy meros",
        "Markaziy Osiyo geologiyasi va iqlim xususiyatlari",
        "Al-Xorazmiy, Beruniy, Ibn Sino ilmiy merosi",
        "Zamonaviy dasturlash: algoritmlar va ma’lumot tuzilmalari",
        "Fizika: mexanika, termodinamika, elektromagnitlik asoslari",
        "Kimyo: organik reaksiyalar va laboratoriya xavfsizligi",
        "Biologiya: evolyutsiya, genetika, ekologiya",
        "Astronomiya: Quyosh tizimi, yulduzlar, teleskoplar",
        "Adabiyot: o‘zbek she’riyati, proza, janrlar tahlili",
        "Tilshunoslik: o‘zbek grammatikasi va imlo me’yorlari",
        "Matematika: ehtimollar, chiziqli algebra, hisoblash usullari",
        "Ta’lim: samarali o‘qish strategiyalari, konspekt tuzish",
        "San’at: amaliy san’at, maketlash, dizayn tamoyillari",
        "Texnologiya: kompyuter arxitekturasi, tarmoqlar, xavfsizlik",
    ],
    "system-from-text": """Input: raw text.  
    Task: extract only real facts/rules/numbers/knowledge from content. 
    Then generate multiple unique conversations in Uzbek (Latin only).  
    Rules: accurate, Uzbekistan-relevant if possible, no religion/politics, 4–8 turns, alternate user/assistant""",

    "system-from-facts": """Given a list of prepared facts (one fact per line), create at least 1 unique, high-quality conversation in perfect Uzbek (Latin script) for each fact.  
    Constraints: accurate, Uzbekistan-relevant if possible, no religion/politics, 4–8 turns, alternating u/a.  
    Schema: JSON array of objects, each { "c": [ { "u": "...", "v": "..." }, { "a": "...", "v": "..." }, ... ] }.  
    No extra text, only valid JSON.""",

    "system-summarize": """I will send you large texts. Your task is to summarize the facts, important information, dates, historical figures, rules, and similar key details from them. Present this summary as a concise but informative list."""
}
