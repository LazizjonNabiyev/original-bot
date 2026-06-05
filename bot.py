import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
ADMIN_IDS  = [int(x) for x in os.environ.get("ADMIN_IDS", "0").split(",")]

# State xotira
user_state = {}

def get_state(uid):
    return user_state.get(str(uid), {})

def set_state(uid, s):
    user_state[str(uid)] = s

def del_state(uid):
    user_state.pop(str(uid), None)

# Klaviaturalar
def kb_lang():
    return ReplyKeyboardMarkup([["🇺🇿 O'zbekcha", "🇷🇺 Русский"]], resize_keyboard=True, one_time_keyboard=True)

def kb_menu():
    return ReplyKeyboardMarkup([
        ["📝 Shikoyat", "📝 Жалоба"],
        ["📍 Lokatsiya", "📍 Локация"],
        ["✍️ Murojaat", "✍️ Обращение"]
    ], resize_keyboard=True)

def kb_photo():
    return ReplyKeyboardMarkup([["📷 Ha, rasm", "➡️ Yo'q, yuborish"]], resize_keyboard=True, one_time_keyboard=True)

def kb_skip():
    return ReplyKeyboardMarkup([["⏭ O'tkazib yuborish"]], resize_keyboard=True, one_time_keyboard=True)

# /start
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    del_state(update.effective_user.id)
    await update.message.reply_text("🌐 Tilni tanlang / Выберите язык:", reply_markup=kb_lang())

# /stats
async def stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        return
    total = len(user_state)
    await update.message.reply_text(f"📊 Faol sessiyalar: {total}")

# Kanalga yuborish
async def send_to_channel(bot, type_label, text, user, photo_id=None):
    from datetime import datetime
    import pytz
    tz = pytz.timezone("Asia/Tashkent")
    now = datetime.now(tz).strftime("%d.%m.%Y %H:%M")
    name = " ".join(filter(None, [user.first_name, user.last_name])) or "—"
    uname = f"@{user.username}" if user.username else "—"

    type_map = {
        "📝 Shikoyat": "📝 SHIKOYAT", "📝 Жалоба": "📝 ЖАЛОБА",
        "📍 Lokatsiya": "📍 LOKATSIYA", "📍 Локация": "📍 ЛОКАЦИЯ",
        "✍️ Murojaat": "✍️ MUROJAAT", "✍️ Обращение": "✍️ ОБРАЩЕНИЕ",
    }
    label = type_map.get(type_label, "📩 XABAR")

    msg = (
        f"{label}\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 {name}\n"
        f"🔗 {uname}\n"
        f"🆔 {user.id}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💬 {text}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🕐 {now}"
    )

    if photo_id:
        await bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=msg)
    else:
        await bot.send_message(chat_id=CHANNEL_ID, text=msg)

# Xabarlar
async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = msg.from_user.id
    text = (msg.text or "").strip()
    s = get_state(uid)

    # Admin reply
    if uid in ADMIN_IDS and text.startswith("/reply "):
        parts = text.split(" ", 2)
        if len(parts) == 3:
            await ctx.bot.send_message(chat_id=parts[1], text=f"📩 Original Supermarket javobi:\n\n{parts[2]}")
            await msg.reply_text("✅ Javob yuborildi!")
        return

    # Til tanlash
    if text in ["🇺🇿 O'zbekcha", "🇷🇺 Русский"]:
        lang = "uz" if "O'zbekcha" in text else "ru"
        set_state(uid, {"step": "menu", "lang": lang})
        name = msg.from_user.first_name or "Do'stim"
        w = f"Salom, {name}! Murojaat turini tanlang:" if lang == "uz" else f"Привет, {name}! Выберите тип:"
        await msg.reply_text(f"🛒 Original Supermarket\n\n{w}", reply_markup=kb_menu())
        return

    # Menyu
    menu_types = ["📝 Shikoyat","📝 Жалоба","📍 Lokatsiya","📍 Локация","✍️ Murojaat","✍️ Обращение"]
    if text in menu_types:
        set_state(uid, {**s, "step": "get_text", "type": text})
        is_loc = "Lokata" in text or "Локац" in text
        prompt = ("📍 Manzilni yozing:" if is_loc else "✏️ Xabaringizni yozing:")
        await msg.reply_text(prompt)
        return

    # Matn kiritish
    if s.get("step") == "get_text":
        content = text
        if msg.location:
            content = f"Geo: {msg.location.latitude}, {msg.location.longitude}"
        if not content:
            return
        set_state(uid, {**s, "step": "ask_photo", "text": content})
        await msg.reply_text("📸 Rasm biriktirmoqchimisiz? / Фото?", reply_markup=kb_photo())
        return

    # Rasm so'rash
    if s.get("step") == "ask_photo":
        if text == "📷 Ha, rasm":
            set_state(uid, {**s, "step": "get_photo"})
            await msg.reply_text("📸 Rasmni yuboring:", reply_markup=kb_skip())
            return
        await send_to_channel(ctx.bot, s["type"], s["text"], msg.from_user)
        del_state(uid)
        await msg.reply_text("✅ Qabul qilindi! / Принято! 🙏", reply_markup=kb_menu())
        return

    # Rasm olish
    if s.get("step") == "get_photo":
        photo_id = msg.photo[-1].file_id if msg.photo else None
        await send_to_channel(ctx.bot, s["type"], s["text"], msg.from_user, photo_id)
        del_state(uid)
        await msg.reply_text("✅ Qabul qilindi! / Принято! 🙏", reply_markup=kb_menu())
        return

    # Default
    await msg.reply_text("🌐 Tilni tanlang / Выберите язык:", reply_markup=kb_lang())

import asyncio

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.ALL, on_message))
    print("Bot ishga tushdi...")
    async with app:
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
