from ai_engine import ask_ai


history = [
    ("user", "Мне сегодня тяжело и я хочу поговорить")
]


print("Отправляю запрос...")

answer = ask_ai(history)

print("Ответ:")
print(answer)
