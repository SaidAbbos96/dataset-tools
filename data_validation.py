import hashlib
from typing import List, Dict, Any
from jsonschema import validate
import jsonschema
import orjson as json


def validate_conversation(data: List[Dict], schema: Dict) -> bool:
    """
    Qisqartirilgan nomlar bilan validatsiya
    """
    try:
        # Asosiy schema validatsiyasi
        validate(instance=data, schema=schema)

        # Qo'shimcha tekshirishlar
        for conv_obj in data:
            messages = conv_obj["c"]  # conversations->c

            for message in messages:
                # F (from) tekshiruvi
                # user->u, assistant->a
                if not isinstance(message["f"], str) or message["f"] not in ["u", "a"]:
                    raise ValueError(f"Invalid 'f' value: {message['f']}")

                # V (value) tekshiruvi
                if not isinstance(message["v"], str) or len(message["v"]) < 2:
                    raise ValueError(f"Invalid 'v': {message['v']}")

        return True

    except jsonschema.exceptions.ValidationError as err:
        print(f"Schema validation error: {err}")
        return False
    except KeyError as err:
        print(f"Missing required field: {err}")
        return False
    except ValueError as err:
        print(f"Data validation error: {err}")
        return False
    except Exception as err:
        print(f"Unexpected error during validation: {err}")
        return False


def hash_conv(obj: Dict[str, Any]) -> str:
    # Stable hash to deduplicate
    h = hashlib.sha256()
    h.update(json.dumps(obj, option=json.OPT_SORT_KEYS).encode("utf-8"))
    return h.hexdigest()


def expand_keys(data: List[Dict]) -> List[Dict]:
    """
    Qisqartirilgan JSON strukturasini asl nomlariga qaytaradi
    
    Args:
        data: [{"c": [{"f": "a", "v": "..."}, ...]}] formatidagi ma'lumot
        
    Returns:
        [{"conversations": [{"from": "assistant", "value": "..."}, ...]}]
    """
    expanded_data = []
    
    for item in data:
        if "c" not in item:
            continue
            
        conversations = []
        for message in item["c"]:
            if "f" not in message or "v" not in message:
                continue
                
            # "f" (from) ni kengaytiramiz
            role_map = {"u": "user", "a": "assistant"}
            from_value = role_map.get(message["f"], message["f"])
            
            conversations.append({
                "from": from_value,
                "value": message["v"]
            })
        
        expanded_data.append({
            "conversations": conversations
        })
    
    return expanded_data