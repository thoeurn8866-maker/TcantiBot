import os
import re
import asyncio
import threading
import logging
from datetime import datetime
import pytz  # 🇰🇭 Import Timezone សម្រាប់កំណត់ម៉ោងនៅកម្ពុជា
from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler, 
    ContextTypes, filters
)

# --- Web Server សម្រាប់ Render Free Plan ---
web_app = Flask('')

@web_app.route('/')
def home():
    return "Anti-Virus & Protection System Bot is Active!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# ------------------------------------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 🔑 Configuration System
LOG_CHAT_ID = 2127600841  # ID របស់ Log Channel/Group សម្រាប់រាយការណ៍ការល្មើស
DOCS_ARCHIVE_CHANNEL_ID = -1004493775116  # ID របស់ Archive Channel របស់បង

# 🚫 ប្រភេទ File មេរោគ
DANGEROUS_EXTENSIONS = (
    '.exe', '.apk', '.vbs', '.bat', '.cmd', '.scr', 
    '.js', '.zip', '.rar', '.iso', '.ps1', '.msi'
)

# 🚫 Regex ចាប់ Link ស្ពែម
URL_REGEX = r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,})"

# 🚫 បញ្ជីពាក្យអាក្រក់/អាសអាភាស
BAD_WORDS = ['អាសអាភាស', 'ក្ត', 'ចដ', 'ចុយ', 'សិច', 'sex', 'porn', 'nude', 'xxx']

# 📌 កន្លែងផ្ទុកចំនួនដងនៃការព្រមាន និងប្រវត្តិផ្ញើ File/រូបភាព
user_warnings = {}
sent_files_history = {} # Format: {file_unique_id: date_string}

# 🇰🇭 កំណត់ Timezone កម្ពុជា (Phnom Penh)
CAMBODIA_TZ = pytz.timezone('Asia/Phnom_Penh')

async def send_log_to_admin(context: ContextTypes.DEFAULT_TYPE, log_message: str):
    """ មុខងារផ្ញើ Log Report ទៅកាន់ Admin/Channel """
    if LOG_CHAT_ID and LOG_CHAT_ID != -1001234567890:
        try:
            await context.bot.send_message(
                chat_id=LOG_CHAT_ID, 
                text=log_message, 
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to send log to admin: {e}")

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """ ពិនិត្យមើលថាអ្នកផ្ញើជា Admin ឬអត់ """
    if update.effective_chat.type == 'private':
        return True
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id, 
            update.effective_user.id
        )
        return member.status in ['creator', 'administrator']
    except Exception as e:
        logging.error(f"Error checking admin status: {e}")
        return False

async def auto_archive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ 📁 មុខងារប្រមូល និងរក្សាទុកតែ File ឯកសារស្វ័យប្រវត្តិក្នុង Archive Channel (Silent Storage) """
    message = update.message
    
    # ✅ កែប្រែឈ្មោះ Variable ឱ្យត្រូវគ្នាជាមួយ DOCS_ARCHIVE_CHANNEL_ID
    if not DOCS_ARCHIVE_CHANNEL_ID or DOCS_ARCHIVE_CHANNEL_ID == -1001234567890:
        return

    # ✅ ចាប់យកតែសារណាដែលជា File Document តែប៉ុណ្ណោះ (Word, Excel, PDF, ផ្សេងៗ)
    if message.document:
        user = message.from_user
        user_name = user.full_name
        user_handle = f"@{user.username}" if user.username else "គ្មាន Username"
        chat_title = update.effective_chat.title or "Group"
        time_str = datetime.now(CAMBODIA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        file_name = message.document.file_name or "ឯកសារគ្មានឈ្មោះ"

        # បង្កើតអត្ថបទព័ត៌មានភ្ជាប់ជាមួយ File ក្នុង Archive Channel
        archive_caption = (
            f"📄 **[ប្រមូលឯកសារស្វ័យប្រវត្តិ]**\n\n"
            f"📁 **ឈ្មោះ File៖** `{file_name}`\n"
            f"👥 **Group៖** {chat_title}\n"
            f"👤 **អ្នកផ្ញើ៖** {user_name} ({user_handle})\n"
            f"🆔 **User ID៖** `{user.id}`\n"
            f"⏰ **កាលបរិច្ឆេទ៖** {time_str}\n"
            f"📝 **Caption ដើម៖** {message.caption or 'គ្មាន'}"
        )

        try:
            # 🤫 Copy ឯកសារផ្ញើទៅកាន់ Archive Channel ដោយស្ងាត់ៗ (Silent)
            await message.copy(
                chat_id=DOCS_ARCHIVE_CHANNEL_ID,
                caption=archive_caption,
                parse_mode='Markdown'
            )
            logging.info(f"Successfully archived document {file_name} from user {user.id}")
        except Exception as e:
            logging.error(f"Failed to copy file to Archive Channel: {e}")

async def process_violation(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
    """ មុខងារគ្រប់គ្រងការព្រមាន, Remove សមាជិក និងផ្ញើ Log """
    message = update.message
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Private Chat"
    user = message.from_user
    user_id = user.id
    user_name = user.full_name
    user_handle = f"@{user.username}" if user.username else "គ្មាន Username"
    
    user_mention = f"[{user_name}](tg://user?id={user_id})"
    time_str = datetime.now(CAMBODIA_TZ).strftime("%Y-%m-%d %H:%M:%S")

    try:
        await message.delete()

        current_warns = user_warnings.get(user_id, 0) + 1
        user_warnings[user_id] = current_warns

        if current_warns < 3:
            warn_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ **សារព្រមានលើកទី {current_warns}/3!**\n\n"
                     f"🔔 **ជូនចំពោះសមាជិក៖** {user_mention}\n"
                     f"📌 **មូលហេតុ៖** {reason}\n"
                     f"⏰ **កាលបរិច្ឆេទ៖** {time_str}\n\n"
                     f"*(ប្រសិនបើប្រព្រឹត្តល្មើសដល់លើកទី ៣ ប្រព័ន្ធនឹង Remove ចេញពី Group ស្វ័យប្រវត្តិ!)*\n"
                     f"*(នាយកដ្ឋានរដ្ឋបាលនិងធនធានមនុស្សនៃទូរគមនាគមន៍កម្ពុជា)*",
                parse_mode='Markdown'
            )

            log_text = (
                f"⚠️ **[LOG REPORT] ការព្រមានសមាជិក ({current_warns}/3)**\n"
                f"👥 **Group:** {chat_title}\n"
                f"👤 **សមាជិក:** {user_name} ({user_handle})\n"
                f"🆔 **User ID:** `{user_id}`\n"
                f"📌 **មូលហេតុ:** {reason}\n"
                f"⏰ **ពេល (កម្ពុជា):** {time_str}"
            )
            await send_log_to_admin(context, log_text)

            await asyncio.sleep(120)
            await warn_msg.delete()

        else:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            user_warnings.pop(user_id, None)

            ban_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 **ប្រព័ន្ធបាន Remove {user_mention} ចេញពី Group!**\n\n"
                     f"📌 **មូលហេតុ៖** ទទួលបានការព្រមានគ្រប់ ៣ ដង ({reason})\n"
                     f"⏰ **កាលបរិច្ឆេទ៖** {time_str}\n\n"
                     f"*(នាយកដ្ឋានរដ្ឋបាលនិងធនធានមនុស្សនៃទូរគមនាគមន៍កម្ពុជា)*",
                parse_mode='Markdown'
            )

            log_text = (
                f"🚨 **[LOG REPORT] បាន REMOVE / BAN សមាជិក!**\n"
                f"👥 **Group:** {chat_title}\n"
                f"👤 **សមាជិក:** {user_name} ({user_handle})\n"
                f"🆔 **User ID:** `{user_id}`\n"
                f"📌 **មូលហេតុ៖** ល្មើសបទបញ្ជាគ្រប់ {current_warns} ដង ({reason})\n"
                f"⏰ **ពេល (កម្ពុជា):** {time_str}"
            )
            await send_log_to_admin(context, log_text)

            await asyncio.sleep(60)
            await ban_msg.delete()

    except Exception as e:
        logging.error(f"Error processing violation: {e}")

async def monitor_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ ស្កែនមើលរាល់សារទាំងអស់ដែលផ្ញើចូល Group """
    message = update.message
    if not message:
        return

    text_content = message.text or message.caption or ""
    today_str = datetime.now(CAMBODIA_TZ).strftime("%Y-%m-%d")

    # 1. ការត្រួតពិនិត្យបទល្មើស
    if not await is_admin(update, context):
        file_unique_id = None
        if message.document:
            file_unique_id = message.document.file_unique_id
        elif message.photo:
            file_unique_id = message.photo[-1].file_unique_id
        elif message.video:
            file_unique_id = message.video.file_unique_id

        if file_unique_id:
            if file_unique_id in sent_files_history and sent_files_history[file_unique_id] == today_str:
                await process_violation(update, context, "ផ្ញើរូបភាព ឬ ឯកសារដដែលៗ (Spam) ក្នុងថ្ងៃតែមួយ")
                return
            else:
                sent_files_history[file_unique_id] = today_str

        if message.document:
            file_name = message.document.file_name.lower() if message.document.file_name else ""
            if file_name.endswith(DANGEROUS_EXTENSIONS):
                await process_violation(update, context, f"ផ្ញើ File មានហានិភ័យ/មេរោគ (`{file_name}`)")
                return

        if re.search(URL_REGEX, text_content):
            await process_violation(update, context, "ផ្ញើ Link ស្ពែមចូលក្នុង Group")
            return

        if any(bad_word in text_content.lower() for bad_word in BAD_WORDS):
            await process_violation(update, context, "ប្រើប្រាស់ពាក្យពេចន៍/សារអាសអាភាស")
            return

    # 2. ប្រមូលឯកសារស្វ័យប្រវត្តិ (Silent Archive)
    await auto_archive_file(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛡️ Anti-Virus Bot កំពុងការពារ Group!បង្កើតឡើងដោយ ឡេង ប៊ុនធឿន ទូរសព្ទ៖ 089976679")

async def main():
    TOKEN = '8950817942:AAFvAnahRVijtETT246VqlLp5s23XA7-xHc'

    threading.Thread(target=run_flask, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, monitor_messages))
    app.add_handler(CommandHandler('start', start))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
