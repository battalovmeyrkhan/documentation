'''
bot.py — Настройка бота Telegram
'''

from telegram import TeleBot
import secrets

bot = TeleBot(secrets.TG_TOKEN)

# ──────────────────────────────────────────────
# 1. Обработчики команд
# ──────────────────────────────────────────────
 
@bot.on_command("start")
def cmd_start(msg):
    name = msg.get("from", {}).get("first_name", "друг")
    bot.reply(msg, f"Привет, {name}! Я работаю на MicroPython.")
 
 
@bot.on_command("help")
def cmd_help(msg):
    bot.reply(msg,
        "/start - приветствие\n"
        "/help  - эта справка\n"
        "/btn   - пример кнопок\n"
        "/unique_id  - уникальный ID"
    )
 
 
@bot.on_command("btn")
def cmd_btn(msg):
    kb = bot.inline_keyboard([
        [("Уникальный ID", "get_unique_id"), ("Инфо", "get_info")],
        [("Anthropic", None, "https://anthropic.com")],
    ])
    bot.reply(msg, "Выберите действие:", reply_markup=kb)
 
 
@bot.on_command("unique_id")
def cmd_unique_id(msg):
    try:
        import machine
        unique_id = machine.unique_id()
        bot.reply(msg, f"Уникальный ID: {unique_id}")
    except Exception:
        bot.reply(msg, "Не удалось получить уникальный ID.")
 
# ──────────────────────────────────────────────
# 2. Обработчики inline-кнопок (callback)
# ──────────────────────────────────────────────
 
@bot.on_callback("get_unique_id")
def cb_get_unique_id(cq):
    bot.answer_callback_query(cq["id"])
    cmd_unique_id(cq["message"])
 
@bot.on_callback("get_info")
def cb_get_info(cq):
    bot.answer_callback_query(cq["id"], text="Получаю инфо...")
    info = bot.get_me()
    bot.reply(cq, f"Бот: @{info.get('username', '?')}\nID: {info.get('id', '?')}")
 
# ──────────────────────────────────────────────
# 3. Общий обработчик текста и ошибок
# ──────────────────────────────────────────────
 
@bot.on_message
def echo(msg):
    text = msg.get("text", "")
    bot.reply(msg, f"Вы написали: {text}")
 
@bot.on_error
def handle_error(exc):
    print("[ERROR]", exc)
