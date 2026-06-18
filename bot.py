import os, asyncio, logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request

logging.basicConfig(level=logging.INFO)

BOT_TOKEN   = os.environ.get("BOT_TOKEN", "8719817989:AAFUBTAK2Kw3GCLSprw-SLzleSVCUev8kaU")
CHANNEL_ID  = os.environ.get("CHANNEL_ID", "")
ADMIN_IDS   = [int(x) for x in os.environ.get("ADMIN_IDS", "920162633").split(",") if x]
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://original-bot-production-f466.up.railway.app")

PHONE        = "+998914654068"
INSTAGRAM    = "https://instagram.com/original_supermarket_"
LOCATION_URL = "https://maps.app.goo.gl/SkDRLYso1tjY9xmF9"

user_state  = {}
vacancies   = {}
vac_counter = [0]

def get_s(uid): return user_state.get(str(uid), {})
def set_s(uid, s): user_state[str(uid)] = s
def del_s(uid): user_state.pop(str(uid), None)
def is_admin(uid): return int(uid) in ADMIN_IDS

def kb_lang():
    return ReplyKeyboardMarkup([["🇺🇿 O'zbekcha","🇷🇺 Русский"]], resize_keyboard=True, one_time_keyboard=True)

def kb_menu(lang):
    if lang=="ru":
        return ReplyKeyboardMarkup([
            ["📝 Жалоба","💡 Предложение"],
            ["📍 Локация","📞 Контакты"],
            ["💼 Вакансии"]
        ], resize_keyboard=True)
    return ReplyKeyboardMarkup([
        ["📝 Shikoyat","💡 Taklif"],
        ["📍 Lokatsiya","📞 Bog'lanish"],
        ["💼 Vakansiyalar"]
    ], resize_keyboard=True)

def kb_admin():
    return ReplyKeyboardMarkup([
        ["📊 Statistika","💼 Vakansiya qo'shish"],
        ["📋 Vakansiyalar","👤 Admin qo'shish"],
        ["🔙 Chiqish"]
    ], resize_keyboard=True)

def kb_back(lang):
    return ReplyKeyboardMarkup([["🔙 Orqaga" if lang=="uz" else "🔙 Назад"]], resize_keyboard=True, one_time_keyboard=True)

def kb_photo(lang):
    if lang=="ru": return ReplyKeyboardMarkup([["📷 Да, фото","➡️ Нет, отправить"]], resize_keyboard=True, one_time_keyboard=True)
    return ReplyKeyboardMarkup([["📷 Ha, rasm","➡️ Yo'q, yuborish"]], resize_keyboard=True, one_time_keyboard=True)

def kb_skip(lang):
    return ReplyKeyboardMarkup([["⏭ O'tkazib yuborish" if lang=="uz" else "⏭ Пропустить"]], resize_keyboard=True, one_time_keyboard=True)

async def send_to_channel(bot, label, text, user, photo_id=None):
    from datetime import datetime
    import pytz
    now   = datetime.now(pytz.timezone("Asia/Tashkent")).strftime("%d.%m.%Y %H:%M")
    name  = " ".join(filter(None,[user.first_name, user.last_name])) or "—"
    uname = f"@{user.username}" if user.username else "—"
    msg   = (f"{label}\n━━━━━━━━━━━━━━\n"
             f"👤 {name}\n🔗 {uname}\n🆔 {user.id}\n"
             f"━━━━━━━━━━━━━━\n💬 {text}\n"
             f"━━━━━━━━━━━━━━\n🕐 {now}\n"
             f"Javob: /reply {user.id} xabar")
    if photo_id:
        await bot.send_photo(chat_id=CHANNEL_ID, photo=photo_id, caption=msg)
    else:
        await bot.send_message(chat_id=CHANNEL_ID, text=msg)

async def handle_update(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message
    if not msg or not msg.from_user: return
    uid  = msg.from_user.id
    text = (msg.text or "").strip()
    s    = get_s(uid)
    lang = s.get("lang","uz")

    if text=="/start":
        del_s(uid)
        await msg.reply_text("🌐 Tilni tanlang / Выберите язык:", reply_markup=kb_lang())
        return

    if is_admin(uid) and text=="/admin":
        set_s(uid,{**s,"admin_mode":True})
        await msg.reply_text("🔧 Admin Panel:", reply_markup=kb_admin())
        return

    if is_admin(uid) and text.startswith("/reply "):
        parts=text.split(" ",2)
        if len(parts)==3:
            try:
                await ctx.bot.send_message(chat_id=int(parts[1]),text=f"📩 Original Supermarket javobi:\n\n{parts[2]}")
                await msg.reply_text("✅ Javob yuborildi!")
            except: await msg.reply_text("❌ Xato")
        return

    if s.get("admin_mode"):
        if text=="🔙 Chiqish":
            set_s(uid,{"lang":lang})
            await msg.reply_text("Asosiy menyu:", reply_markup=kb_menu(lang)); return
        if text=="📊 Statistika":
            vc=len([v for v in vacancies.values() if v.get("active")])
            await msg.reply_text(f"📊 Statistika\n\n💼 Faol vakansiyalar: {vc}\n👤 Adminlar: {len(ADMIN_IDS)}"); return
        if text=="👤 Admin qo'shish":
            set_s(uid,{**s,"admin_step":"add_admin"})
            await msg.reply_text("Yangi admin Telegram ID sini yuboring:"); return
        if s.get("admin_step")=="add_admin":
            try:
                ADMIN_IDS.append(int(text))
                set_s(uid,{**s,"admin_step":None})
                await msg.reply_text(f"✅ {text} admin qilindi!", reply_markup=kb_admin())
            except: await msg.reply_text("❌ Raqam kiriting")
            return
        if text=="💼 Vakansiya qo'shish":
            set_s(uid,{**s,"admin_step":"vac_title"})
            await msg.reply_text("💼 Vakansiya lavozimini yozing:"); return
        if s.get("admin_step")=="vac_title":
            set_s(uid,{**s,"admin_step":"vac_desc","vac_title":text})
            await msg.reply_text("📝 Tavsifini yozing (ish vaqti, maosh, talablar):"); return
        if s.get("admin_step")=="vac_desc":
            vac_counter[0]+=1
            vid=vac_counter[0]
            vacancies[vid]={"title":s.get("vac_title"),"desc":text,"active":True}
            set_s(uid,{**s,"admin_step":None,"vac_title":None})
            await msg.reply_text(f"✅ Vakansiya qo'shildi!\n\n💼 {vacancies[vid]['title']}\n📝 {text}", reply_markup=kb_admin()); return
        if text=="📋 Vakansiyalar":
            active=[(vid,v) for vid,v in vacancies.items() if v.get("active")]
            if not active:
                await msg.reply_text("Hozircha vakansiya yo'q"); return
            result="📋 Faol vakansiyalar:\n\n"
            for vid,v in active:
                result+=f"🔹 [{vid}] {v['title']}\n{v['desc']}\n/delvac_{vid}\n\n"
            await msg.reply_text(result); return
        if text.startswith("/delvac_"):
            try:
                vid=int(text.replace("/delvac_",""))
                vacancies[vid]["active"]=False
                await msg.reply_text(f"✅ #{vid} o'chirildi", reply_markup=kb_admin())
            except: await msg.reply_text("Xato")
            return

    if text=="🇺🇿 O'zbekcha":
        set_s(uid,{"step":"menu","lang":"uz"})
        name=msg.from_user.first_name or "Do'stim"
        await msg.reply_text(f"🛒 Original Supermarket\n\nSalom, {name}! Tanlang:", reply_markup=kb_menu("uz")); return

    if text=="🇷🇺 Русский":
        set_s(uid,{"step":"menu","lang":"ru"})
        name=msg.from_user.first_name or "Друг"
        await msg.reply_text(f"🛒 Original Supermarket\n\nПривет, {name}! Выберите:", reply_markup=kb_menu("ru")); return

    if text in ["🔙 Orqaga","🔙 Назад"]:
        set_s(uid,{"step":"menu","lang":lang})
        await msg.reply_text("Asosiy menyu:" if lang=="uz" else "Главное меню:", reply_markup=kb_menu(lang)); return

    if text in ["📝 Shikoyat","📝 Жалоба","💡 Taklif","💡 Предложение"]:
        set_s(uid,{**s,"step":"get_text","type":text})
        if "Taklif" in text or "Предложение" in text:
            await msg.reply_text("✏️ Taklifingizni yozing:" if lang=="uz" else "✏️ Напишите предложение:", reply_markup=kb_back(lang))
        else:
            await msg.reply_text("✏️ Shikoyatingizni yozing:" if lang=="uz" else "✏️ Напишите жалобу:", reply_markup=kb_back(lang))
        return

    if text in ["📍 Lokatsiya","📍 Локация"]:
        kb=InlineKeyboardMarkup([[InlineKeyboardButton("🗺 Google Maps", url=LOCATION_URL)]])
        await msg.reply_text("📍 Original Supermarket\n\nQarshi, Qashqadaryo\nRQJM+9Q9", reply_markup=kb); return

    if text in ["📞 Bog'lanish","📞 Контакты"]:
        kb=InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Instagram", url=INSTAGRAM)],
            [InlineKeyboardButton("💬 Telegram", url="https://t.me/LazizjonNabiyev")],
        ])
        await msg.reply_text(f"📞 Bog'lanish\n\n📱 {PHONE}\n📸 @original_supermarket_\n💬 @LazizjonNabiyev", reply_markup=kb); return

    if text in ["💼 Vakansiyalar","💼 Вакансии"]:
        active=[(vid,v) for vid,v in vacancies.items() if v.get("active")]
        if not active:
            await msg.reply_text("Hozircha bo'sh ish o'rinlari yo'q 😔" if lang=="uz" else "Пока нет вакансий 😔"); return
        result="💼 Bo'sh ish o'rinlari:\n\n" if lang=="uz" else "💼 Вакансии:\n\n"
        for vid,v in active:
            result+=f"🔹 *{v['title']}*\n{v['desc']}\n\n"
        result+=f"📞 {PHONE}"
        await msg.reply_text(result, parse_mode="Markdown"); return

    if s.get("step")=="get_text":
        content=text
        if msg.location: content=f"Geo: {msg.location.latitude}, {msg.location.longitude}"
        if not content: return
        set_s(uid,{**s,"step":"ask_photo","text":content})
        await msg.reply_text("📸 Rasm biriktirmoqchimisiz?" if lang=="uz" else "📸 Хотите фото?", reply_markup=kb_photo(lang)); return

    if s.get("step")=="ask_photo":
        t = s.get("type","")
        label = ("💡 TAKLIF" if lang=="uz" else "💡 ПРЕДЛОЖЕНИЕ") if ("Taklif" in t or "Предложение" in t) else ("📝 SHIKOYAT" if lang=="uz" else "📝 ЖАЛОБА")
        if text in ["📷 Ha, rasm","📷 Да, фото"]:
            set_s(uid,{**s,"step":"get_photo"})
            await msg.reply_text("📸 Rasmni yuboring:" if lang=="uz" else "📸 Отправьте фото:", reply_markup=kb_skip(lang)); return
        await send_to_channel(ctx.bot,label,s["text"],msg.from_user)
        del_s(uid)
        await msg.reply_text("✅ Qabul qilindi! 🙏" if lang=="uz" else "✅ Принято! 🙏", reply_markup=kb_menu(lang)); return

    if s.get("step")=="get_photo":
        t = s.get("type","")
        label = ("💡 TAKLIF" if lang=="uz" else "💡 ПРЕДЛОЖЕНИЕ") if ("Taklif" in t or "Предложение" in t) else ("📝 SHIKOYAT" if lang=="uz" else "📝 ЖАЛОБА")
        photo_id=msg.photo[-1].file_id if msg.photo else None
        await send_to_channel(ctx.bot,label,s.get("text","—"),msg.from_user,photo_id)
        del_s(uid)
        await msg.reply_text("✅ Qabul qilindi! 🙏" if lang=="uz" else "✅ Принято! 🙏", reply_markup=kb_menu(lang)); return

    await msg.reply_text("🌐 Tilni tanlang / Выберите язык:", reply_markup=kb_lang())


flask_app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
ptb_app = Application.builder().token(BOT_TOKEN).updater(None).build()
ptb_app.add_handler(CommandHandler("start", handle_update))
ptb_app.add_handler(MessageHandler(filters.ALL, handle_update))

async def init():
    await ptb_app.initialize()
    await ptb_app.start()
    await ptb_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook", drop_pending_updates=True)
    print("✅ Original Supermarket boti ishga tushdi!")

loop.run_until_complete(init())

@flask_app.route("/", methods=["GET"])
def index(): return "Original Supermarket Bot — Ishlayapti! ✅", 200

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    data=request.get_json(force=True)
    update=Update.de_json(data, ptb_app.bot)
    loop.run_until_complete(ptb_app.process_update(update))
    return "OK", 200

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    flask_app.run(host="0.0.0.0", port=port)
