def analyze_safety(text):

    danger_words = [
        "умереть",
        "не хочу жить",
        "убью себя",
        "покончу",
        "суицид",
        "таблетки",
        "уснуть навсегда"
    ]

    text = text.lower()


    for word in danger_words:

        if word in text:

            return {
                "level": "critical",
                "score": 10,
                "response":
                    "Я рядом.\n\n"
                    "Мне важно понять:\n"
                    "Ты сейчас в безопасности?\n"
                    "Ты один?\n"
                    "Есть ли рядом человек, которому можно написать?"
            }


    return {
        "level": "normal",
        "score": 1,
        "response": None
    }
