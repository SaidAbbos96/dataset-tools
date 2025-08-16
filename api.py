from openai import OpenAI
import json
import time
from dataclasses import dataclass
from typing import Union, Literal, Optional, Any, Dict, List


def get_ai_api_client(api_url: str, api_key: str) -> OpenAI:
    return OpenAI(base_url=api_url, api_key=api_key)


# Response format variantlari
ResponseFormatType = Literal["json_schema", "text", "json_object"]
ReasoningLevel = Literal["low", "medium", "high", "max"]


@dataclass
class APIConfig:
    model: str
    temperature: float = 0.6
    reasoning: Dict[str, str] = None
    response_format: Dict[str, Any] = None
    max_retries: int = 3
    retry_delay: float = 1.5


def call_llm_api(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.6,
    retries: int = 3,
    reasoning: Dict[str, str] = None,
    response_format_type: ResponseFormatType = "json_schema",
    json_schema: Optional[Dict] = None,
    stream: bool = False,
    max_tokens: Optional[int] = None,
    **kwargs
) -> Union[Dict, List[Dict], str]:
    """
    Universal LLM API chaqiruv funksiyasi (OpenAI va OpenRouter bilan ishlaydi)

    Args:
        client: OpenAI yoki OpenRouter client obyekti
        model: Ishlatiladigan model nomi
        messages: Xabarlar ro'yxati [{"role": "system/user", "content": "..."}]
        temperature: Model kreativligi (0.0 - 2.0)
        retries: Qayta urinishlar soni
        reasoning: Modelning fikrlash darajasi (GPT-5 uchun)
        response_format_type: Qaytish formati (json_schema, text, json_object)
        json_schema: Agar JSON schema kerak bo'lsa
        stream: Stream qilib olish
        max_tokens: Maksimal tokenlar soni
        **kwargs: Qo'shimcha parametrlar

    Returns:
        JSON object, JSON array yoki text (qaytish formatiga qarab)
    """

    # Default reasoning
    if reasoning is None:
        reasoning = {"effort": "medium"}

    # Response formatni sozlash
    response_format = {"type": response_format_type or "text"}
    if response_format_type == "json_schema" and json_schema:
        response_format["json_schema"] = json_schema
        response_format["strict"] = False

    # Asosiy API chaqiruv tsikli
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            params = {
                "model": model,
                "temperature": temperature,
                "messages": messages,
                "response_format": response_format if response_format_type != "text" else None,
                "stream": stream,
                **kwargs
            }
            # print(params)
            if max_tokens:
                params["max_tokens"] = max_tokens

            # GPT-5 uchun reasoning parametri
            if model.startswith("gpt-5") and reasoning:
                params["reasoning"] = reasoning
            response = client.chat.completions.create(**params)
            # print("create", response)
            if stream:
                return response

            content = response.choices[0].message.content

            if response_format_type == "text":
                return content

            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
                return data if isinstance(data, list) else [data]
            except json.JSONDecodeError:
                return content

        except Exception as e:
            last_error = e
            if attempt == retries:
                raise LLMAPIError(
                    f"API call failed after {retries} attempts") from last_error
            time.sleep(1.5 * attempt)

    raise LLMAPIError("Unexpected error in API call")


class LLMAPIError(Exception):
    """Maxsus API xatolari uchun exception"""
    pass

# Foydalanish misollari:

# 1. Oddiy text response
# result = call_llm_api(client, "gpt-4", messages, response_format_type="text")

# 2. JSON schema bilan
# schema = {"type": "object", "properties": {...}}
# result = call_llm_api(client, "gpt-4", messages, json_schema=schema)

# 3. Stream qilib olish
# for chunk in call_llm_api(client, "gpt-4", messages, stream=True):
#     print(chunk)
