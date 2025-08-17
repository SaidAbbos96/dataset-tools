
from api import call_llm_api, get_ai_api_client
from config import OPENROUTER_API_KEYS, MODEL_NAMES, API_URL
import config
import data_validation

client = get_ai_api_client(config.API_URL, config.OPENROUTER_API_KEYS[config.DEFAULT_API_KEY_INDEX])
messages = [
    {"role": "system", "content": "Sen ushbu foydalanuvchi bilan positive gaplashishing kerak !"},
    {"role": "user",   "content": "Salom, menga yordam kerak"}
]
res = call_llm_api(client, config.MODEL_NAMES[1], messages)
print(res)
