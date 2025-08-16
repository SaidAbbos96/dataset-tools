import time

from api import call_llm_api, get_ai_api_client
import data_validation
import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass


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
            {"role": "user", "content": f"Text: {params.resource}"})

    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            response = call_llm_api(
                client=client,
                model=params.model_name,
                messages=messages,
                response_format_type="json_schema",
                json_schema=params.json_schema,
                max_tokens=5000,
                top_p=0.95,
                frequency_penalty=0.2,
                presence_penalty=0.2,
                temperature=0
            )
            # print(response)
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


def make_schema_for_count(min_count: int, max_count: int, min_items: int, max_items: int) -> dict:
    # top-level array EXACT count
        # Schema (min/max conversations sizning kiritingan parametrlar bilan hamohang bo‘lishi mumkin,
    # ammo biz guruh uzunligiga teng (conv_count) yuboramiz)
    return {
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
