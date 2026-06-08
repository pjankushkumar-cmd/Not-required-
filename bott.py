import logging
import sqlite3
import json
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ChatJoinRequestHandler, ContextTypes, MessageHandler, filters

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# =================== [ CRITICAL CONFIGURATION ] ===================
BOT_TOKEN = "8831391243:AAFNUMEngpQns6MQk3Hf9WZb9uBDuk_3mRw" 
ADMIN_ID = 8767998937 
# ===================================================================

if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or ADMIN_ID == 123456789:
    print("\n❌ ERROR: Pehle apna BOT_TOKEN aur ADMIN_ID code me sahi se badlo, tabhi admin panel chalega!\n")
    sys.exit(1)

def init_db():
    conn = sqlite3.connect('final_pro_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, count INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    
    # FIX: SQLite me AUTOINCREMENT hota hai, AUTO_INCREMENT nahi!
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages_list (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        chat_id TEXT, 
                        msg_id TEXT,
                        media_type TEXT,
                        text_backup TEXT,
                        file_id_backup TEXT
                    )''')

    cursor.execute("INSERT OR IGNORE INTO settings VALUES ('auto_accept', 'OFF')")
    cursor.execute("INSERT OR IGNORE INTO stats VALUES ('total_requests', 0)")
    cursor.execute("INSERT OR IGNORE INTO stats VALUES ('accepted', 0)")
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect('final_pro_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else None

def set_setting(key, value):
    conn = sqlite3.connect('final_pro_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def add_saved_message(chat_id, msg_id, media_type, text="", file_id=""):
    conn = sqlite3.connect('final_pro_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages_list (chat_id, msg_id, media_type, text_backup, file_id_backup) VALUES (?, ?, ?, ?, ?)", 
                   (str(chat_id), str(msg_id), media_type, text, file_id))
    conn.commit()
    conn.close()

def clear_saved_messages():
    conn = sqlite3.connect('final_pro_bot.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages_list")
    conn.commit()
    conn.close()

def get_all_saved_messages():
    conn = sqlite3.connect('final_pro_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, msg_id, media_type, text_backup, file_id_backup FROM messages_list ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_user(user_id):
    conn = sqlite3.connect('final_pro_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('final_pro_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_stats():
    conn = sqlite3.connect('final_pro_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT key, count FROM stats")
    res = dict(cursor.fetchall())
    conn.close()
    return res

def update_stat(key, amount=1):
    conn = sqlite3.connect('final_pro_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE stats SET count = count + ? WHERE key=?", (amount, key))
    conn.commit()
    conn.close()

def get_main_menu():
    stats = get_stats()
    total_users = len(get_all_users())
    keyboard = [
        [InlineKeyboardButton(f"📊 Total Requests: {stats.get('total_requests', 0)}", callback_data="none")],
        [InlineKeyboardButton(f"✅ Auto-Approved: {stats.get('accepted', 0)}", callback_data="none")],
        [InlineKeyboardButton(f"👥 Database Users: {total_users}", callback_data="none")],
        [InlineKeyboardButton("⚙️ Welcome Settings", callback_data="welcome_settings"), InlineKeyboardButton("📣 Broadcast Tool", callback_data="broadcast_tool")],
        [InlineKeyboardButton("🔄 Refresh Panel", callback_data="refresh_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_welcome_menu():
    auto_status = get_setting("auto_accept")
    status_emoji = "🟢 ON (Auto Accept)" if auto_status == "ON" else "🔴 OFF (Manual/No Accept)"
    total_saved = len(get_all_saved_messages())
    keyboard = [
        [InlineKeyboardButton(f"Status: {status_emoji}", callback_data="toggle_auto")],
        [InlineKeyboardButton(f"➕ Add Message / Voice / Media", callback_data="edit_welcome")],
        [InlineKeyboardButton(f"🗑️ Clear All Saved ({total_saved})", callback_data="clear_welcome")],
        [InlineKeyboardButton("👁️ Test Sequence Message", callback_data="test_msg")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="refresh_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_sequence_messages(bot, chat_id, name_placeholder=None):
    saved_messages = get_all_saved_messages()
    
    if not saved_messages:
        await bot.send_message(chat_id=chat_id, text="👋 Aapki join request received ho gayi hai!")
        return

    for row in saved_messages:
        s_chat_id, s_msg_id, media_type, text_backup, file_id_backup = row
        try:
            # VIP Copy Method: Bina /start dabaye direct inbox me deliver hoga
            await bot.copy_message(chat_id=chat_id, from_chat_id=int(s_chat_id), message_id=int(s_msg_id))
        except Exception as e:
            logging.error(f"Copy message failed in sequence, running fallback: {e}")
            try:
                text_content = text_backup.replace("{name}", name_placeholder) if name_placeholder else text_backup
                if media_type == "text" or not file_id_backup:
                    await bot.send_message(chat_id=chat_id, text=text_content, parse_mode="HTML")
                elif media_type == "photo":
                    await bot.send_photo(chat_id=chat_id, photo=file_id_backup, caption=text_content, parse_mode="HTML")
                elif media_type == "video":
                    await bot.send_video(chat_id=chat_id, video=file_id_backup, caption=text_content, parse_mode="HTML")
                elif media_type == "animation":
                    await bot.send_animation(chat_id=chat_id, animation=file_id_backup, caption=text_content, parse_mode="HTML")
                elif media_type == "voice":
                    await bot.send_voice(chat_id=chat_id, voice=file_id_backup, caption=text_content, parse_mode="HTML")
            except Exception as ex:
                logging.error(f"Complete fallback failed: {ex}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    if update.effective_user.id != ADMIN_ID:
        add_user(update.effective_user.id)
        return
        
    add_user(update.effective_user.id)
    await update.message.reply_text("👑 **PRO Admin Control Panel v4** 👑\n\nAapka swagat hai admin! Sabhi functions niche se control karein:", reply_markup=get_main_menu(), parse_mode="Markdown")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or query.from_user.id != ADMIN_ID:
        await query.answer("Access Denied!", show_alert=True)
        return
    await query.answer()

    if query.data == "refresh_main":
        await query.edit_message_text("👑 **PRO Admin Control Panel v4** 👑\n\nAapka swagat hai admin! Sabhi functions niche se control karein:", reply_markup=get_main_menu(), parse_mode="Markdown")

    elif query.data == "welcome_settings":
        auto_status = get_setting("auto_accept")
        total_saved = len(get_all_saved_messages())
        text = f"⚙️ **Welcome Sequence Settings**\n\n🔄 Auto Accept Status: **{auto_status}**\n📦 Total Messages Added in Sequence: **{total_saved}**\n\n📌 *Aap ek se zyada Voice Notes, Photos, Videos ya Texts line-by-line add kar sakte hain. Jab koi request bhejega toh saare messages ek ke baad ek chale jayenge.*"
        await query.edit_message_text(text, reply_markup=get_welcome_menu(), parse_mode="Markdown")

    elif query.data == "toggle_auto":
        current = get_setting("auto_accept")
        set_setting("auto_accept", "ON" if current == "OFF" else "OFF")
        auto_status = get_setting("auto_accept")
        total_saved = len(get_all_saved_messages())
        text = f"⚙️ **Welcome Sequence Settings**\n\n🔄 Auto Accept Status: **{auto_status}**\n📦 Total Messages Added in Sequence: **{total_saved}**"
        await query.edit_message_text(text, reply_markup=get_welcome_menu(), parse_mode="Markdown")

    elif query.data == "edit_welcome":
        context.user_data['state'] = 'waiting_welcome'
        await query.edit_message_text("📝 **Apna Welcome Message/Voice Note/Media bhejein:**\n\nJo bhi message aap sequence mein add karna chahte hain wo bhejein. Aap ek ke baad ek multiple messages bhej sakte hain. Stop karne ke liye dubara `/start` likhein.")

    elif query.data == "clear_welcome":
        clear_saved_messages()
        auto_status = get_setting("auto_accept")
        text = f"🗑️ **Saare saved messages delete kar diye gaye hain!**\n\n🔄 Auto Accept Status: **{auto_status}**\n📦 Total Messages Added in Sequence: **0**"
        await query.edit_message_text(text, reply_markup=get_welcome_menu(), parse_mode="Markdown")

    elif query.data == "broadcast_tool":
        context.user_data['state'] = 'waiting_broadcast'
        await query.edit_message_text("📣 **Broadcast Post bhejein:**\n\nJo bhi post sabhi users ko bhejni hai, use send karein. Cancel ke liye /start likhein.")

    elif query.data == "test_msg":
        await query.message.reply_text("🔄 *Test sequence aapko niche deliver kiya ja raha hai...*")
        try:
            await send_sequence_messages(context.bot, ADMIN_ID, name_placeholder=query.from_user.first_name)
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {e}")

async def content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != ADMIN_ID:
        return
    state = context.user_data.get('state')
    if not state:
        return

    text = update.message.caption_html if update.message.caption else update.message.text_html
    if not text: text = ""
    file_id, media_type = None, "text"

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        file_id = update.message.video.file_id
        media_type = "video"
    elif update.message.animation:
        file_id = update.message.animation.file_id
        media_type = "animation"
    elif update.message.document:
        file_id = update.message.document.file_id
        media_type = "document"
    elif update.message.audio:
        file_id = update.message.audio.file_id
        media_type = "audio"
    elif update.message.voice:
        file_id = update.message.voice.file_id
        media_type = "voice"

    if state == 'waiting_welcome':
        add_saved_message(update.message.chat_id, update.message.message_id, media_type, text, file_id)
        total_saved = len(get_all_saved_messages())
        await update.message.reply_text(f"✅ Message sequence mein add ho gaya! (Total Added: {total_saved})\n\nAgar koi aur voice/media bhi iske sath bhejna hai toh send karte rahiye, ya rukne ke liye `/start` dabayein.")

    elif state == 'waiting_broadcast':
        context.user_data['state'] = None
        users = get_all_users()
        await update.message.reply_text(f"🚀 Broadcast Shuru! Total Users: {len(users)}")
        s, f = 0, 0
        for u_id in users:
            try:
                await context.bot.copy_message(chat_id=u_id, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
                s += 1
            except Exceptio
