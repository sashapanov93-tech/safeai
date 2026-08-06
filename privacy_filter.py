"""Local filter for requests about SafeAI's internal implementation.

Messages rejected here are never sent to the language model or placed in
the conversation history.
"""

import re
import unicodedata


BLOCKED_RESPONSE = (
    "Я не раскрываю внутреннее устройство и технические детали своей работы. "
    "Могу помочь с вопросом, который касается вас и вашей ситуации."
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("ё", "е")
    return re.sub(r"[^\w\s]", " ", text)


def is_internal_info_request(text: str) -> bool:
    """Return True for attempts to obtain service implementation details."""
    normalized = _normalize(text)

    # These phrases are specific enough not to interfere with normal support
    # conversations, while covering Russian and common English formulations.
    patterns = (
        r"\b(кто|кем)\s+тебя\s+(создал|сделал|разработал|владеет|принадлежит)\b",
        r"\b(кто|кем)\s+тебя\s+(создан|разработан)\b",
        r"\b(кто|кем)\s+(создал|сделал|разработал|владеет|принадлежит|создан|разработан)\s+"
        r"(этот\s+)?(бот|чат|сервис|safeai|ии|ai)\b",
        r"\bкто\s+(твой|у\s+тебя)\s+(владелец|создатель|разработчик)\b",
        r"\bкто\s+владелец\b",
        r"\b(владелец|создатель|разработчик|автор)\s+(бота|чата|сервиса|safeai)\b",
        r"\b(как|на чем|на какой базе|с помощью чего)\s+(создан|сделан|работает|построен)\s+"
        r"(этот\s+)?(бот|чат|сервис|safeai|ты|ии|ai)\b",
        r"\b(как|на чем|на какой базе|с помощью чего)\s+(бот|чат|сервис|safeai|ты|ии|ai)\s+"
        r"(создан|сделан|работает|построен)\b",
        r"\b(исходн(ый|ики)|код|архитектур[аы]|база данных|database)\b",
        r"\b(system prompt|системн(ый|ые) промпт|промпт|инструкци[яи] (бота|ии))\b",
        r"\b(api[ -]?ключ|токен|парол[ья]|секрет|настройк[аи] сервера)\b",
        r"\b(какая|какие|какую)\s+(модель|модели|технологи[яи]|инфраструктур[аы])\b",
        r"\b(как|где)\s+(обучали|обучена|работает)\s+(модель|ии|ai|бот)\b",
        r"\b(сервер\w*|хостинг|внутренн(яя|ие) логик[аи]|принятие решений)\b",
        r"\b(who (made|created|owns)|how (was|is) .* (built|made)|source code)\b",
    )

    return any(re.search(pattern, normalized) for pattern in patterns)
