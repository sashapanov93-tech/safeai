"""Manual OpenAI smoke check; run this file directly when network is available."""

from ai_engine import ask_ai


def main():
    history = [("user", "Мне сегодня тяжело и я хочу поговорить")]
    print("Отправляю запрос...")
    print("Ответ:")
    print(ask_ai(history))


if __name__ == "__main__":
    main()
