import os, asyncio, logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
ADMIN_IDS  = [int(x) for x in os.environ.get("ADMIN_IDS", "920162633").split(",") if x]

# Bog'lanish ma'lumotlari
PHONE     = "+998914654068"
INSTAGRAM = "https://instagram.com/original_supermarket_"
LOCATION_TEXT = "📍 Original Supermarket\nQarshi, Qashqadaryo Viloyati\n\n🗺 Google Maps:"
LOCATION_URL  = "https://maps.app.goo.gl/SkDRLYso1tjY9xmF9"

# State & vakansiyalar xotirasi
user_state  = {}
vacancies   = {}  # {id: {title, desc, active}}
vac_counter = [0]

def get_s(uid): return user_state.get(str(uid), {})
def set_s(uid, s): user_state[str(uid)] = s
def del_s(uid): user_state.pop(str(uid), None)
def is_admin(uid): return int(uid) in ADMIN_IDS

# ─── KLAVIATURALAR ────────────────────────────────────────────
def kb_lang():
    return ReplyKeyboardMarkup(
        [["🇺🇿 O'zbekcha", "🇷🇺 Русский"]],
        resize_keyboard=True, one_time_keyboard=True
    )

def kb_menu(lang):
    if lang == "ru":
        return ReplyKeyboardMarkup([
            ["📝 Жалоба"],
            ["📍 Локация", "📞 Контакты"],
            ["💼 Вакансии"],
        ], resize_keyboard=True)
    return ReplyKeyboardMarkup([
        ["📝 Shikoyat"],
        ["📍 Lokatsiya", "📞 Bog'lanish"],
        ["💼 Vakansiyalar"],
    ], resize_keyboard=True)

def kb_admin():
    return ReplyKeyboardMarkup([
        ["📊 Statistika", "💼 Vakansiya qo'shish"],
        ["📋 Vakansiyalar ro'yxati", "👤 Admin qo'shish"],
        ["🔙 Chiqish"],
    ], resize_keyboard=True)

def kb_back(lang):
    txt = "🔙 Orqaga" if lang == "uz" else "🔙 Назад"
    return ReplyKeyboardMarkup([[txt]], resize_keyboard=True, one_time_keyboard=True)

def kb_photo(lang):
    if lang == "ru":
        return ReplyKeyboardMarkup([["📷 Да, фото", "➡️ Нет, отправить"]], resize_keyboard=True, one_time_keyboard=True)
    return ReplyKeyboardMarkup([["📷 Ha, rasm", "➡️ Yo'q, yuborish"]], resize_keyboard=True, one_time_keyboard=True)

def kb_skip(lang):
    txt = "⏭ O'tkazib yuborish" if lang == "uz" else "⏭ Пропустить"
    return ReplyKeyboardMarkup([[txt]], resize_keyboard=True, one_time_keyboard=True)

# ─── API ─────────────────────────────────────────────────────
async def tg_send(bot, chat_id, text, kb=None):
    p = {"chat_id": chat_id, "text": text}
    if kb: p["reply_markup"] = kb
    await bot.send_message(**p)

# ─── SHEETS (ixtiyoriy) ───────────────────────────────────────
def save_user(user):
    pass  # Render da sheets yo'q, kelajakda qo'shiladi

# ─── KANAL ────────────────────────────────────────────────────
async def send_to_channel(bot, type_label, text, user, photo_id=None):
    from datetime import datetime
    import pytz
    now = datetime.now(pytz.timezone("Asia/Tashkent")).strftime("%d.%m.%Y %H:%M")
    name  = " ".join(filter(None, [user.first_name, user.last_name])) or "—"
    uname = f"@{user.username}" if user.username else "—"
    msg = (
        f"{type_label}\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 {name}\n"
        f"🔗 {uname}\n"
        f"🆔 {user.id}\n"
        f"━━━━━━━━━━━━━━\n"
        f"💬 {text}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🕐 {now}\n"
        f"💬 Javob: /reply {user.id} <xabar>"
    )
    if photo_id:
        await bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=msg)
    else:
        await bot.send_message(chat_id=CHANNEL_ID, text=msg)

# ─── /start ──────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    del_s(update.effective_user.id)
    await update.message.reply_text(
        "🌐 Tilni tanlang / Выберите язык:",
        reply_markup=kb_lang()
    )

# ─── ASOSIY HANDLER ──────────────────────────────────────────
async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message
    if not msg or not msg.from_user: return
    uid  = msg.from_user.id
    text = (msg.text or "").strip()
    s    = get_s(uid)
    lang = s.get("lang", "uz")

    # /start
    if text == "/start":
        del_s(uid)
        await msg.reply_text("🌐 Tilni tanlang / Выберите язык:", reply_markup=kb_lang())
        return

    # Admin buyruqlari
    if is_admin(uid):
        if text == "/admin":
            set_s(uid, {**s, "admin_mode": True})
            await msg.reply_text("🔧 Admin Panel:", reply_markup=kb_admin())
            return

        if text.startswith("/reply "):
            parts = text.split(" ", 2)
            if len(parts) == 3:
                try:
                    await ctx.bot.send_message(
                        chat_id=int(parts[1]),
                        text=f"📩 Original Supermarket javobi:\n\n{parts[2]}"
                    )
                    await msg.reply_text("✅ Javob yuborildi!")
                except:
                    await msg.reply_text("❌ Xato: foydalanuvchi topilmadi")
            return

        if text.startswith("/addadmin "):
            new_id = text.split(" ", 1)[1].strip()
            try:
                ADMIN_IDS.append(int(new_id))
                await msg.reply_text(f"✅ {new_id} admin qilindi!")
            except:
                await msg.reply_text("❌ Xato ID")
            return

    # Admin panel
    if s.get("admin_mode"):
        if text == "🔙 Chiqish":
            set_s(uid, {"lang": lang})
            await msg.reply_text("Asosiy menyu:", reply_markup=kb_menu(lang))
            return

        if text == "📊 Statistika":
            total = len(user_state)
            vac_count = len([v for v in vacancies.values() if v.get("active")])
            await msg.reply_text(
                f"📊 Statistika\n\n"
                f"👥 Faol sessiyalar: {total}\n"
                f"💼 Faol vakansiyalar: {vac_count}\n"
                f"👤 Adminlar: {len(ADMIN_IDS)}"
            )
            return

        if text == "👤 Admin qo'shish":
            set_s(uid, {**s, "admin_step": "add_admin"})
            await msg.reply_text("Yangi admin Telegram ID sini yuboring:")
            return

        if s.get("admin_step") == "add_admin":
            try:
                new_id = int(text)
                ADMIN_IDS.append(new_id)
                set_s(uid, {**s, "admin_step": None})
                await msg.reply_text(f"✅ {new_id} admin qilindi!", reply_markup=kb_admin())
            except:
                await msg.reply_text("❌ Raqam kiriting")
            return

        if text == "💼 Vakansiya qo'shish":
            set_s(uid, {**s, "admin_step": "vac_title"})
            await msg.reply_text("💼 Vakansiya lavozimini yozing:\n(Masalan: Kassir, Yuk tashuvchi)")
            return

        if s.get("admin_step") == "vac_title":
            set_s(uid, {**s, "admin_step": "vac_desc", "vac_title": text})
            await msg.reply_text("📝 Vakansiya tavsifini yozing:\n(Ish vaqti, maosh, talablar)")
            return

        if s.get("admin_step") == "vac_desc":
            vac_counter[0] += 1
            vid = vac_counter[0]
            vacancies[vid] = {
                "title": s.get("vac_title"),
                "desc": text,
                "active": True
            }
            set_s(uid, {**s, "admin_step": None, "vac_title": None})
            await msg.reply_text(
                f"✅ Vakansiya qo'shildi!\n\n"
                f"💼 {vacancies[vid]['title']}\n"
                f"📝 {vacancies[vid]['desc']}",
                reply_markup=kb_admin()
            )
            return

        if text == "📋 Vakansiyalar ro'yxati":
            active = [(vid, v) for vid, v in vacancies.items() if v.get("active")]
            if not active:
                await msg.reply_text("Hozircha vakansiya yo'q")
                return
            result = "📋 Faol vakansiyalar:\n\n"
            for vid, v in active:
                result += f"🔹 [{vid}] {v['title']}\n{v['desc']}\n/delvac_{vid} — o'chirish\n\n"
            await msg.reply_text(result)
            return

        if text.startswith("/delvac_"):
            try:
                vid = int(text.replace("/delvac_", ""))
                if vid in vacancies:
                    vacancies[vid]["active"] = False
                    await msg.reply_text(f"✅ Vakansiya #{vid} o'chirildi")
                else:
                    await msg.reply_text("Topilmadi")
            except:
                await msg.reply_text("Xato")
            return

    # Til tanlash
    if text == "🇺🇿 O'zbekcha":
        save_user(msg.from_user)
        set_s(uid, {"step": "menu", "lang": "uz"})
        name = msg.from_user.first_name or "Do'stim"
        await msg.reply_text(
            f"🛒 Original Supermarket\n\nSalom, {name}! Quyidagilardan birini tanlang:",
            reply_markup=kb_menu("uz")
        )
        return

    if text == "🇷🇺 Русский":
        save_user(msg.from_user)
        set_s(uid, {"step": "menu", "lang": "ru"})
        name = msg.from_user.first_name or "Друг"
        await msg.reply_text(
            f"🛒 Original Supermarket\n\nПривет, {name}! Выберите раздел:",
            reply_markup=kb_menu("ru")
        )
        return

    # Orqaga
    if text in ["🔙 Orqaga", "🔙 Назад"]:
        set_s(uid, {"step": "menu", "lang": lang})
        await msg.reply_text(
            "Asosiy menyu:" if lang == "uz" else "Главное меню:",
            reply_markup=kb_menu(lang)
        )
        return

    # SHIKOYAT
    if text in ["📝 Shikoyat", "📝 Жалоба"]:
        set_s(uid, {**s, "step": "get_text", "type": text})
        prompt = "✏️ Shikoyatingizni yozing:" if lang == "uz" else "✏️ Напишите вашу жалобу:"
        await msg.reply_text(prompt, reply_markup=kb_back(lang))
        return

    # LOKATSIYA
    if text in ["📍 Lokatsiya", "📍 Локация"]:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🗺 Google Maps da ochish", url=LOCATION_URL)
        ]])
        await msg.reply_text(
            f"📍 *Original Supermarket*\n\n"
            f"🏪 Manzil: Qarshi, Qashqadaryo\n"
            f"📌 RQJM+9Q9, Qarshi\n\n"
            f"Pastdagi tugmani bosing:",
            parse_mode="Markdown",
            reply_markup=kb
        )
        return

    # BOG'LANISH
    if text in ["📞 Bog'lanish", "📞 Контакты"]:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📞 Telefon", url=f"tel:{PHONE}")],
            [InlineKeyboardButton("📸 Instagram", url=INSTAGRAM)],
            [InlineKeyboardButton("💬 Telegram adminga yozish", url=f"https://t.me/LazizjonNabiyev")],
        ])
        await msg.reply_text(
            f"📞 *Bog'lanish / Контакты*\n\n"
            f"📱 Tel: {PHONE}\n"
            f"📸 Instagram: @original_supermarket_\n"
            f"💬 Telegram: @Technologeee",
            parse_mode="Markdown",
            reply_markup=kb
        )
        return

    # VAKANSIYALAR
    if text in ["💼 Vakansiyalar", "💼 Вакансии"]:
        active = [(vid, v) for vid, v in vacancies.items() if v.get("active")]
        if not active:
            no_vac = "Hozircha bo'sh ish o'rinlari yo'q 😔" if lang == "uz" else "Пока нет открытых вакансий 😔"
            await msg.reply_text(no_vac)
            return
        result = "💼 Bo'sh ish o'rinlari:\n\n" if lang == "uz" else "💼 Открытые вакансии:\n\n"
        for vid, v in active:
            result += f"🔹 *{v['title']}*\n{v['desc']}\n\n"
        result += "📞 Murojaat uchun: " + PHONE if lang == "uz" else "📞 По вопросам: " + PHONE
        await msg.reply_text(result, parse_mode="Markdown")
        return

    # Matn kiritish (shikoyat)
    if s.get("step") == "get_text":
        content = text
        if msg.location:
            content = f"Geo: {msg.location.latitude}, {msg.location.longitude}"
        if not content:
            return
        set_s(uid, {**s, "step": "ask_photo", "text": content})
        ask = "📸 Rasm biriktirmoqchimisiz?" if lang == "uz" else "📸 Хотите прикрепить фото?"
        await msg.reply_text(ask, reply_markup=kb_photo(lang))
        return

    # Rasm so'rash
    if s.get("step") == "ask_photo":
        if text in ["📷 Ha, rasm", "📷 Да, фото"]:
            set_s(uid, {**s, "step": "get_photo"})
            ask = "📸 Rasmni yuboring:" if lang == "uz" else "📸 Отправьте фото:"
            await msg.reply_text(ask, reply_markup=kb_skip(lang))
            return
        type_labels = {
            "📝 Shikoyat": "📝 SHIKOYAT",
            "📝 Жалоба": "📝 ЖАЛОБА",
        }
        label = type_labels.get(s.get("type", ""), "📝 SHIKOYAT")
        await send_to_channel(ctx.bot, label, s["text"], msg.from_user)
        del_s(uid)
        ok = "✅ Shikoyatingiz qabul qilindi! Tez orada javob beramiz 🙏" if lang == "uz" else "✅ Ваша жалоба принята! Ответим в ближайшее время 🙏"
        await msg.reply_text(ok, reply_markup=kb_menu(lang))
        return

    # Rasm olish
    if s.get("step") == "get_photo":
        photo_id = msg.photo[-1].file_id if msg.photo else None
        type_labels = {
            "📝 Shikoyat": "📝 SHIKOYAT",
            "📝 Жалоба": "📝 ЖАЛОБА",
        }
        label = type_labels.get(s.get("type", ""), "📝 SHIKOYAT")
        await send_to_channel(ctx.bot, label, s.get("text", "—"), msg.from_user, photo_id)
        del_s(uid)
        ok = "✅ Shikoyatingiz qabul qilindi! 🙏" if lang == "uz" else "✅ Принято! 🙏"
        await msg.reply_text(ok, reply_markup=kb_menu(lang))
        return

    # Default
    await msg.reply_text("🌐 Tilni tanlang / Выберите язык:", reply_markup=kb_lang())


async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, on_message))
    app.add_handler(MessageHandler(filters.COMMAND, on_message))
    print("✅ Bot ishga tushdi!")
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
