"""Private, rule-based long-term memory for one SafeAI user."""

import re

from database import get_user_memories, save_user_memory


MEMORY_LABELS = {
    "name": "Имя",
    "location": "Где живёт",
    "calming": "Помогает успокоиться",
    "trigger": "Вызывает тревогу",
    "communication": "Предпочтение в общении",
    "close_person": "Близкий человек",
}

_PATTERNS = (
    ("name", r"\bменя зовут\s+([^.!?\n]{2,60})"),
    ("location", r"\bя живу\s+(?:в|на)\s+([^.!?\n]{2,120})"),
    ("calming", r"\bменя\s+(?:очень\s+)?успокаивает\s+([^.!?\n]{2,160})"),
    ("calming", r"\bмне помогает\s+([^.!?\n]{2,160})"),
    ("calming", r"\bмне легче(?: становится)?\s+когда\s+([^.!?\n]{2,160})"),
    ("trigger", r"\bменя тревожит\s+([^.!?\n]{2,160})"),
    ("trigger", r"\b(?:мне страшно|я боюсь)\s+(?:из-за\s+)?([^.!?\n]{2,160})"),
    ("communication", r"\bя предпочитаю\s+([^.!?\n]{2,160})"),
    ("communication", r"\bя люблю\s+когда\s+([^.!?\n]{2,160})"),
    ("close_person", r"\bмой близкий человек\s*[—:-]?\s*([^.!?\n]{2,100})"),
)

_DISTRESS_WORDS = (
    "плохо", "тяжело", "тревожно", "тревога", "страшно", "боюсь",
    "паника", "одиноко", "не справляюсь", "отчаяние",
)


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" ,;:-")


def learn_from_message(user_id: int, text: str) -> list[tuple[str, str]]:
    """Extract only explicit, durable facts; return newly observed entries."""
    learned = []
    for category, pattern in _PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = _clean_value(match.group(1))
        if value:
            save_user_memory(user_id, category, value)
            learned.append((category, value))
    return learned


def get_relevant_memory(user_id: int, current_text: str, limit: int = 6) -> list[tuple[str, str]]:
    """Choose memories useful for the current support message."""
    memories = get_user_memories(user_id)
    text = current_text.lower()
    is_distressed = any(word in text for word in _DISTRESS_WORDS)
    selected = []

    for category, value in memories:
        value_words = [word for word in re.findall(r"\w+", value.lower()) if len(word) > 3]
        overlaps = any(word in text for word in value_words)
        if overlaps or (is_distressed and category in {"calming", "trigger", "communication"}):
            selected.append((category, value))
        if len(selected) >= limit:
            break

    return selected


def format_memory_for_ai(memories: list[tuple[str, str]]) -> str:
    if not memories:
        return ""

    lines = [f"- {MEMORY_LABELS[category]}: {value}" for category, value in memories]
    return "\n".join(lines)
