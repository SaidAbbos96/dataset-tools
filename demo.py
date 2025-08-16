
from api import call_llm_api, get_ai_api_client
from config import OPENROUTER_API_KEYS, MODEL_NAMES, API_URL
import config
import data_validation

client = get_ai_api_client(config.API_URL, config.OPENROUTER_API_KEYS[0])
messages = [
    {"role": "system", "content": config.PROMTS['system']},
    {"role": "user",   "content": config.PROMTS['user']}
]
res = call_llm_api(client, config.MODEL_NAMES[1], messages,
                    response_format_type="json_schema", json_schema=data_validation.API_SCHEMA)
print(res)
