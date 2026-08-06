from ai_core import analyze_message
from safety_engine import analyze_safety
from privacy_filter import BLOCKED_RESPONSE, is_internal_info_request
from personal_memory import format_memory_for_ai, get_relevant_memory

try:
    from ai_engine import ask_ai
    AI_AVAILABLE = True
except Exception:
    AI_AVAILABLE = False


def get_response(user_id, history, text):

    # This check is deliberately before any model call. The handler in main.py
    # also checks it before saving the message, so blocked content is not later
    # re-sent as part of the conversation history.
    if is_internal_info_request(text):
        return BLOCKED_RESPONSE

    # Проверка опасных сообщений
    safety = analyze_safety(text)

    if safety.get("level") in ["critical", "high"]:
        return safety["response"]

    # GPT
    if AI_AVAILABLE:
        try:
            personal_memory = format_memory_for_ai(
                get_relevant_memory(user_id, text)
            )
            answer = ask_ai(history, personal_memory)

            print("\n========== GPT ==========")
            print(answer)
            print("=========================\n")

            return answer

        except Exception as e:

            print("\n========== AI ERROR ==========")
            print(e)
            print("==============================\n")

    # Если GPT недоступен — запасной ответ
    result = analyze_message(text)

    return result["response"]
