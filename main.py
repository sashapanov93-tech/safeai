import logging
import os
import tempfile
from datetime import datetime

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update
)
from memory import save_message, get_history
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters
)

from config import ADMIN_ID, BOT_TOKEN, BOT_USERNAME

from database import (
    create_tables,
    add_user,
    get_user,
    add_event,
    add_message,
    add_trusted_contact,
    get_all_trusted_contact_details,
    get_all_users,
    get_trusted_contact_details,
    get_trusted_contacts,
    get_user_conversation,
    get_voice_auto_reply,
    get_preferred_voice,
    set_preferred_voice,
    set_voice_auto_reply,
    touch_user
)

from ai_router import get_response
from privacy_filter import BLOCKED_RESPONSE, is_internal_info_request
from personal_memory import MEMORY_LABELS, learn_from_message
from database import clear_user_memories, get_user_memories
from voice_service import VoiceServiceError, synthesize_voice, transcribe


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


KEYBOARD_ROWS = [
    ["🚀 Начать", "💬 Поговорить"],
    ["🆘 SOS", "✅ Я в безопасности"],
    ["👤 Контакт", "👥 Мои контакты"],
    ["⚙️ Настройки"]
]


SOS_KEYBOARD = ReplyKeyboardMarkup(
    KEYBOARD_ROWS,
    resize_keyboard=True,
    is_persistent=True
)


LOCATION_REQUEST_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("📍 Отправить геолокацию", request_location=True)], *KEYBOARD_ROWS],
    resize_keyboard=True,
    is_persistent=True,
    one_time_keyboard=True,
)


ADMIN_KEYBOARD = ReplyKeyboardMarkup(
    KEYBOARD_ROWS + [
        ["👑 Все пользователи"],
        ["🔗 Все приглашения"],
        ["🧠 Память пользователей"]
    ],
    resize_keyboard=True,
    is_persistent=True
)


def keyboard_for(user_id):
    if user_id == ADMIN_ID:
        return ADMIN_KEYBOARD

    return SOS_KEYBOARD



async def error_handler(update, context):

    logging.error(
        "Ошибка:",
        exc_info=context.error
    )



async def start(update: Update, context):

    user = update.effective_user

    add_user(
        user.id,
        user.username,
        user.first_name
    )


    # подключение по приглашению

    if context.args:

        payload = context.args[0]


        if payload.startswith("trust_"):
            owner_id_text = payload.removeprefix("trust_")

            if not owner_id_text.isdigit():
                await update.message.reply_text(
                    "⚠️ Некорректная ссылка-приглашение."
                )
                return

            owner_id = int(owner_id_text)

            if owner_id == user.id:
                await update.message.reply_text(
                    "⚠️ Нельзя добавить себя в доверенные контакты."
                )
                return


            add_trusted_contact(
                owner_id,
                user.id,
                user.first_name
            )


            await update.message.reply_text(
                "✅ Ты добавлен как доверенный контакт.\n\n"
                "Теперь ты можешь получать SOS-сигналы.\n\n"
                "Ты также можешь пользоваться SafeAI для себя: "
                "написать мне, вызвать SOS или добавить свои контакты.",
                reply_markup=keyboard_for(user.id)
            )

            return



    await update.message.reply_text(
        f"Привет, {user.first_name} 👋\n\n"
        "Я твой помощник, с которым можно спокойно "
        "поговорить и быстро попросить о помощи.\n\n"
        "💬 Нажми «Поговорить», чтобы начать диалог.\n"
        "🆘 Нажми SOS, если нужна срочная помощь.\n"
        "👤 В разделе «Контакт» можно добавить близкого человека.\n\n"
        "Чтобы я мог лучше помогать в будущем, расскажи немного о себе: "
        "что тебя поддерживает, что вызывает тревогу и как тебе комфортнее "
        "общаться. Я запомню эту информацию и буду учитывать её, когда "
        "помогаю тебе.\n\n"
        "Выбери действие:",
        reply_markup=keyboard_for(user.id)
    )



async def talk_button(update: Update, context):

    user_id = update.effective_user.id
    touch_user(user_id)


    add_event(
        user_id,
        "Начат разговор",
        "talk",
        1
    )


    await update.message.reply_text(
        "💬 Я рядом.\n\n"
        "Расскажи, что сейчас происходит."
    )



async def sos_button(update: Update, context):

    user_id = update.effective_user.id
    user = update.effective_user
    touch_user(user_id)


    add_event(
        user_id,
        "Нажата кнопка SOS",
        "critical",
        10
    )


    contacts = get_trusted_contacts(
        user_id
    )

    if not contacts:

        await update.message.reply_text(
            "⚠️ У тебя пока нет доверенных контактов.\n\n"
            "Используй /invite чтобы добавить человека."
        )

        return

    # Telegram only gives coordinates after an explicit action by the user.
    # Limit forwarding to a location shared as part of this SOS flow.
    context.user_data["awaiting_sos_location"] = True
    await update.message.reply_text(
        "🆘 SOS активирован. Я уведомляю доверенные контакты.\n\n"
        "Если можешь, нажми «📍 Отправить геолокацию» — координаты будут "
        "отправлены только им.",
        reply_markup=LOCATION_REQUEST_KEYBOARD,
    )



    for contact_id in contacts:

        try:

            await context.bot.send_message(
                chat_id=contact_id,
                text=(
                    "🆘 SOS СИГНАЛ\n\n"
                    f"{user.first_name} "
                    "запросил помощь.\n\n"
                    "Пожалуйста, свяжись с ним."
                )
            )


        except Exception as e:

            print(
                "Ошибка отправки SOS:",
                e
            )


async def safe_button(update: Update, context):

    user_id = update.effective_user.id
    context.user_data.pop("awaiting_sos_location", None)
    touch_user(user_id)

    add_event(
        user_id,
        "Пользователь подтвердил безопасность",
        "safe",
        0
    )

    await update.message.reply_text(
        "✅ Хорошо, отмечаю, что ты в безопасности.\n\n"
        "Если снова понадобится помощь — нажми SOS или напиши мне.",
        reply_markup=keyboard_for(user_id)
    )



async def sos(update: Update, context):
    # Keep command and keyboard button behaviour identical.
    await sos_button(update, context)


async def location(update: Update, context):
    """Forward a user-approved SOS location to trusted contacts."""
    user_id = update.effective_user.id
    user = update.effective_user
    location_data = update.message.location
    touch_user(user_id)

    if not context.user_data.pop("awaiting_sos_location", False):
        await update.message.reply_text(
            "Геолокация отправляется доверенным контактам только после нажатия SOS.",
            reply_markup=keyboard_for(user_id),
        )
        return

    contacts = get_trusted_contacts(user_id)
    if not contacts:
        await update.message.reply_text(
            "⚠️ Геолокация получена, но доверенных контактов пока нет. "
            "Используй /invite, чтобы добавить человека.",
            reply_markup=keyboard_for(user_id),
        )
        return

    delivered = 0
    for contact_id in contacts:
        try:
            await context.bot.send_message(
                chat_id=contact_id,
                text=(
                    "📍 Геолокация по SOS\n\n"
                    f"{user.first_name} отправил(а) свои координаты."
                ),
            )
            await context.bot.send_location(
                chat_id=contact_id,
                latitude=location_data.latitude,
                longitude=location_data.longitude,
            )
            delivered += 1
        except Exception:
            logging.exception("Не удалось отправить SOS-геолокацию контакту %s", contact_id)

    if delivered:
        add_event(user_id, "Отправлена геолокация по SOS", "critical", 10)
        await update.message.reply_text(
            f"✅ Геолокация отправлена {delivered} доверенному(ым) контакту(ам).",
            reply_markup=keyboard_for(user_id),
        )
    else:
        await update.message.reply_text(
            "⚠️ Не удалось доставить геолокацию. Попробуй связаться с близкими напрямую.",
            reply_markup=keyboard_for(user_id),
        )



async def profile(update: Update, context):

    user_id = update.effective_user.id
    touch_user(user_id)

    user = get_user(user_id)


    if user:

        await update.message.reply_text(
            f"👤 Профиль\n\n"
            f"Имя: {user[2]}\n"
            f"Username: @{user[1]}"
        )

    else:

        await update.message.reply_text(
            "Профиль не найден"
        )



async def invite(update: Update, context):

    user_id = update.effective_user.id
    touch_user(user_id)


    link = (
        f"https://t.me/{BOT_USERNAME}"
        f"?start=trust_{user_id}"
    )


    await update.message.reply_text(
        "👤 Приглашение доверенного контакта:\n\n"
        f"{link}\n\n"
        "Отправь эту ссылку человеку."
    )



async def contact_button(update: Update, context):

    await invite(
        update,
        context
    )


def format_person(user_id, first_name, username=None):

    name = first_name or "Без имени"

    if username:
        return f"{name} (@{username}, ID: {user_id})"

    return f"{name} (ID: {user_id})"


def format_last_active(last_active_at):

    if not last_active_at:
        return "нет данных"

    seconds = max(
        0,
        int((datetime.now() - datetime.fromisoformat(last_active_at)).total_seconds())
    )

    if seconds < 60:
        return "только что"

    minutes = seconds // 60

    if minutes < 60:
        return f"{minutes} мин. назад"

    hours = minutes // 60

    if hours < 24:
        return f"{hours} ч. назад"

    return f"{hours // 24} дн. назад"


def format_admin_person(user_id, first_name, username=None):

    name = first_name or "Без имени"
    username_text = f", username: {username}" if username else ""

    return f"{name} (ID: {user_id}{username_text})"


async def send_lines(update, lines):

    await send_lines_to(update.message, lines)


async def send_lines_to(message_target, lines):

    message = ""

    for line in lines:
        candidate = f"{message}\n{line}" if message else line

        if len(candidate) > 4000:
            await message_target.reply_text(message)
            message = line
        else:
            message = candidate

    if message:
        await message_target.reply_text(message)


async def contacts(update: Update, context):

    user_id = update.effective_user.id
    touch_user(user_id)
    contacts = get_trusted_contact_details(user_id)

    if not contacts:
        await update.message.reply_text(
            "У тебя пока нет доверенных контактов.\n\n"
            "Используй кнопку «👤 Контакт», чтобы пригласить человека."
        )
        return

    lines = ["👥 Твои доверенные контакты:"]

    for contact_id, contact_name, username in contacts:
        lines.append(f"• {format_person(contact_id, contact_name, username)}")

    await send_lines(update, lines)


async def memory_command(update: Update, context):
    if not is_admin(update):
        await update.message.reply_text("⛔ Эта команда доступна только администратору.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Использование: /memory <ID пользователя>")
        return

    user_id = int(context.args[0])
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return

    memories = get_user_memories(user_id)

    if not memories:
        await update.message.reply_text("В памяти этого пользователя пока нет записей.")
        return

    lines = [f"🧠 Память пользователя {format_person(user_id, user[2], user[1])}:"]
    lines.extend(f"• {MEMORY_LABELS[category]}: {value}" for category, value in memories)
    lines.append(f"Удалить всю память: /forget_memory {user_id}")
    await send_lines(update, lines)


async def forget_memory_command(update: Update, context):
    if not is_admin(update):
        await update.message.reply_text("⛔ Эта команда доступна только администратору.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Использование: /forget_memory <ID пользователя>")
        return

    user_id = int(context.args[0])
    if not get_user(user_id):
        await update.message.reply_text("Пользователь не найден.")
        return

    deleted = clear_user_memories(user_id)
    await update.message.reply_text(
        "✅ Память пользователя очищена." if deleted else "Память пользователя уже была пуста.",
        reply_markup=keyboard_for(update.effective_user.id),
    )


async def settings_button(update: Update, context):
    user_id = update.effective_user.id
    enabled = get_voice_auto_reply(user_id)
    state = "включён" if enabled else "выключен"
    voice = get_preferred_voice(user_id)
    voice_text = {"male": "мужской", "female": "женский"}.get(voice, "не выбран")
    toggle = "voice_auto:off" if enabled else "voice_auto:on"
    action = "Выключить" if enabled else "Включить"
    await update.message.reply_text(
        "⚙️ Настройки\n\n"
        f"Голосовой автоответ: {state}.\n"
        f"Голос для ответов: {voice_text}.\n"
        "Когда он включён, на голосовое сообщение бот отвечает голосом; "
        "на текст — текстом.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{action} голосовой автоответ", callback_data=toggle)],
            [
                InlineKeyboardButton("Мужской голос", callback_data="voice:male"),
                InlineKeyboardButton("Женский голос", callback_data="voice:female"),
            ],
        ]),
    )


async def set_voice_auto_reply_callback(update: Update, context):
    query = update.callback_query
    enabled = query.data == "voice_auto:on"
    set_voice_auto_reply(query.from_user.id, enabled)
    await query.answer("Настройка сохранена")
    state = "включён" if enabled else "выключен"
    toggle = "voice_auto:off" if enabled else "voice_auto:on"
    action = "Выключить" if enabled else "Включить"
    await query.edit_message_text(
        "⚙️ Настройки\n\n"
        f"Голосовой автоответ: {state}.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{action} голосовой автоответ", callback_data=toggle)],
            [
                InlineKeyboardButton("Мужской голос", callback_data="voice:male"),
                InlineKeyboardButton("Женский голос", callback_data="voice:female"),
            ],
        ]),
    )


async def set_voice_callback(update: Update, context):
    query = update.callback_query
    voice = query.data.removeprefix("voice:")
    if voice not in {"male", "female"}:
        await query.answer("Не удалось сохранить настройку.", show_alert=True)
        return
    set_preferred_voice(query.from_user.id, voice)
    voice_name = "Ирина (женский)" if voice == "female" else "Дмитрий (мужской)"
    await query.answer("Настройка сохранена")
    await query.message.reply_text(
        f"✅ Сохранено. Для голосовых ответов будет использоваться: {voice_name}."
    )


def is_admin(update):
    return update.effective_user.id == ADMIN_ID


async def admin_users(update: Update, context):

    if not is_admin(update):
        await update.message.reply_text("⛔ Эта команда доступна только администратору.")
        return

    touch_user(update.effective_user.id)
    users = get_all_users()

    if not users:
        await update.message.reply_text("Пользователей пока нет.")
        return

    lines = [
        f"👑 Пользователи бота: {len(users)}",
        "Для просмотра запросов нажмите кнопку «📨 История» ниже."
    ]

    for user_id, username, first_name, last_active_at in users:
        lines.append(
            f"• {format_admin_person(user_id, first_name, username)} — "
            f"активен в боте: {format_last_active(last_active_at)}"
        )

    await send_lines(update, lines)

    buttons = []

    for user_id, username, first_name, _ in users:
        label = first_name or username or str(user_id)
        buttons.append([
            InlineKeyboardButton(
                f"📨 История: {label}"[:60],
                callback_data=f"user_requests:{user_id}"
            )
        ])

    for index in range(0, len(buttons), 50):
        await update.message.reply_text(
            "Нажмите на пользователя, чтобы посмотреть его запросы к боту:",
            reply_markup=InlineKeyboardMarkup(buttons[index:index + 50])
        )


async def admin_links(update: Update, context):

    if not is_admin(update):
        await update.message.reply_text("⛔ Эта команда доступна только администратору.")
        return

    touch_user(update.effective_user.id)
    contacts = get_all_trusted_contact_details()

    if not contacts:
        await update.message.reply_text("Привязанных контактов пока нет.")
        return

    lines = [f"👑 Привязки по приглашениям: {len(contacts)}"]

    for owner_id, owner_name, contact_id, contact_name in contacts:
        owner = format_person(owner_id, owner_name)
        contact = format_person(contact_id, contact_name)
        lines.append(f"• {owner} → {contact}")

    await send_lines(update, lines)


async def admin_memories(update: Update, context):
    if not is_admin(update):
        await update.message.reply_text("⛔ Эта команда доступна только администратору.")
        return

    touch_user(update.effective_user.id)
    users = get_all_users()
    if not users:
        await update.message.reply_text("Пользователей пока нет.")
        return

    buttons = []
    for user_id, username, first_name, _ in users:
        label = first_name or username or str(user_id)
        buttons.append([
            InlineKeyboardButton(
                f"🧠 Память: {label}"[:60],
                callback_data=f"user_memory:{user_id}",
            )
        ])

    for index in range(0, len(buttons), 50):
        await update.message.reply_text(
            "Выберите пользователя, чтобы посмотреть его сохранённую память:",
            reply_markup=InlineKeyboardMarkup(buttons[index:index + 50]),
        )


async def admin_user_memory(update: Update, context):
    query = update.callback_query
    if not is_admin(update):
        await query.answer("Эта функция доступна только администратору.", show_alert=True)
        return

    await query.answer()
    try:
        user_id = int(query.data.removeprefix("user_memory:"))
    except ValueError:
        await query.message.reply_text("Не удалось открыть память пользователя.")
        return

    user = get_user(user_id)
    if not user:
        await query.message.reply_text("Пользователь не найден.")
        return

    memories = get_user_memories(user_id)
    title = format_person(user_id, user[2], user[1])
    if not memories:
        await query.message.reply_text(f"🧠 У пользователя {title} пока нет записей памяти.")
        return

    lines = [f"🧠 Память пользователя {title}:"]
    lines.extend(f"• {MEMORY_LABELS[category]}: {value}" for category, value in memories)
    lines.append(f"Очистить: /forget_memory {user_id}")
    await send_lines_to(query.message, lines)


async def admin_user_requests(update: Update, context):

    query = update.callback_query

    if not is_admin(update):
        await query.answer("Эта функция доступна только администратору.", show_alert=True)
        return

    await query.answer()

    try:
        user_id = int(query.data.removeprefix("user_requests:"))
    except ValueError:
        await query.message.reply_text("Не удалось открыть историю пользователя.")
        return

    user = get_user(user_id)
    conversation = get_user_conversation(user_id)

    if not user:
        await query.message.reply_text("Пользователь не найден.")
        return

    title = format_person(user_id, user[2], user[1])

    if not conversation:
        await query.message.reply_text(
            f"💬 Диалог пользователя {title}:\n\n"
            "Пользователь пока не отправлял сообщений боту."
        )
        return

    lines = [f"💬 Последние сообщения диалога с пользователем {title}:"]

    for role, text, created_at in conversation:
        timestamp = created_at.replace("T", " ")[:16] if created_at else "без даты"
        sender = "👤 Пользователь" if role == "user" else "🤖 Помощник"
        lines.append(f"[{timestamp}] {sender}\n{text}")

    await send_lines_to(query.message, lines)



async def respond_to_text(update: Update, context, text, voice_reply=False):
    """Process text from either a typed or transcribed voice message."""
    user_id = update.effective_user.id

    # Do not persist or pass internal-information requests to GPT. This avoids
    # leaking such a request through a later message's conversation history.
    if is_internal_info_request(text):
        await update.message.reply_text(BLOCKED_RESPONSE, reply_markup=keyboard_for(user_id))
        return

    # Сохраняем сообщение пользователя
    save_message(
        user_id,
        "user",
        text
    )

    learn_from_message(user_id, text)

    # Получаем историю
    history = get_history(user_id)

    # Получаем ответ AI
    answer = get_response(
        user_id,
        history,
        text
    )

    # Сохраняем ответ AI
    save_message(
        user_id,
        "assistant",
        answer
    )

    if voice_reply:
        output_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as output_file:
                output_path = output_file.name
            synthesize_voice(answer, output_path, get_preferred_voice(user_id))
            with open(output_path, "rb") as voice_file:
                await update.message.reply_voice(voice=voice_file)
            return
        except VoiceServiceError as error:
            logging.warning("Голосовой ответ недоступен: %s", error)
        finally:
            if output_path:
                try:
                    os.unlink(output_path)
                except FileNotFoundError:
                    pass

    await update.message.reply_text(answer)


async def message(update: Update, context):
    await respond_to_text(update, context, update.message.text)


async def voice_message(update: Update, context):
    """Transcribe an incoming Telegram voice note and answer in the chosen mode."""
    user_id = update.effective_user.id
    input_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as input_file:
            input_path = input_file.name
        telegram_file = await update.message.voice.get_file()
        await telegram_file.download_to_drive(custom_path=input_path)
        text = transcribe(input_path)
    except VoiceServiceError as error:
        await update.message.reply_text(
            f"⚠️ {error} Пока можешь написать сообщение текстом.",
            reply_markup=keyboard_for(user_id),
        )
        return
    except Exception:
        logging.exception("Не удалось получить голосовое сообщение")
        await update.message.reply_text(
            "⚠️ Не удалось обработать голосовое сообщение. Пока можешь написать текстом.",
            reply_markup=keyboard_for(user_id),
        )
        return
    finally:
        if input_path:
            try:
                os.unlink(input_path)
            except FileNotFoundError:
                pass

    await update.message.reply_text(f"🎤 Я услышал: {text}")
    voice = get_preferred_voice(user_id)
    voice_reply = get_voice_auto_reply(user_id) and voice is not None
    if get_voice_auto_reply(user_id) and voice is None:
        await update.message.reply_text(
            "Для голосового ответа выбери мужской или женский голос в «⚙️ Настройки». "
            "Сейчас отвечу текстом."
        )
    await respond_to_text(update, context, text, voice_reply=voice_reply)



create_tables()


app = Application.builder() \
    .token(BOT_TOKEN) \
    .build()


app.add_error_handler(
    error_handler
)



app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


app.add_handler(
    CommandHandler(
        "memory",
        memory_command
    )
)


app.add_handler(
    CommandHandler(
        "forget_memory",
        forget_memory_command
    )
)


app.add_handler(
    MessageHandler(
        filters.LOCATION,
        location
    )
)


app.add_handler(
    CommandHandler(
        "sos",
        sos
    )
)


app.add_handler(
    CommandHandler(
        "invite",
        invite
    )
)


app.add_handler(
    CommandHandler(
        "profile",
        profile
    )
)


app.add_handler(
    CommandHandler(
        "contacts",
        contacts
    )
)


app.add_handler(
    CommandHandler(
        "admin_users",
        admin_users
    )
)


app.add_handler(
    CommandHandler(
        "admin_links",
        admin_links
    )
)


app.add_handler(
    CallbackQueryHandler(
        admin_user_requests,
        pattern=r"^user_requests:\d+$"
    )
)


app.add_handler(
    CallbackQueryHandler(
        admin_user_memory,
        pattern=r"^user_memory:\d+$"
    )
)


app.add_handler(
    CallbackQueryHandler(
        set_voice_auto_reply_callback,
        pattern=r"^voice_auto:(on|off)$"
    )
)


app.add_handler(
    CallbackQueryHandler(
        set_voice_callback,
        pattern=r"^voice:(male|female)$"
    )
)



app.add_handler(
    MessageHandler(
        filters.Regex("^🚀 Начать$"),
        start
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^🆘 SOS$"),
        sos_button
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^💬 Поговорить$"),
        talk_button
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^✅ Я в безопасности$"),
        safe_button
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^👤 Контакт$"),
        contact_button
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^👥 Мои контакты$"),
        contacts
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^⚙️ Настройки$"),
        settings_button
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^👑 Все пользователи$"),
        admin_users
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^🔗 Все приглашения$"),
        admin_links
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^🧠 Память пользователей$"),
        admin_memories
    )
)


app.add_handler(
    MessageHandler(
        filters.VOICE,
        voice_message
    )
)


app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        message
    )
)



print("SafeAI запущен 🚀")

app.run_polling()
