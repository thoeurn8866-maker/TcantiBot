import os
import re
import asyncio
import threading
import logging
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
    return "Anti-Virus & Group Protection Bot is Active!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# ------------------------------------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 🚫 ប្រភេទ File មេរោគ
DANGEROUS_EXTENSIONS = (
    '.exe', '.apk', '.vbs', '.bat', '.cmd', '.scr', 
    '.js', '.zip', '.rar', '.iso', '.ps1', '.msi'
)

# 🚫 Regex ចាប់ Link ស្ពែម
URL_REGEX = r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,})"

# 🚫 បញ្ជីពាក្យអាក្រក់/អាសអាភាស (អាចបន្ថែមពាក្យផ្សេងៗទៀតបាន)
BAD_WORDS = ['អាសអាភាស', 'ក្ត', 'ចដ', 'ចុយ', 'សិច', 'sex', 'porn', 'nude', 'xxx']

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

async def kick_and_clean(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
    """ មុខងារលុបសារ និង Remove (Ban) អ្នកផ្ញើចេញពី Group """
    message = update.message
    chat_id = update.effective_chat.id
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    try:
        # 1. លុបសារដែលខុសច្បាប់ចោល
        await message.delete()

        # 2. Ban (Remove) សមាជិកនោះចេញពី Group ភ្លាមៗ
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)

        # 3. ផ្ញើសារប្រកាសក្នុង Group
        warn = await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚫 **ប្រព័ន្ធបាន Remove {user_name} ចេញពី Group!**\n"
                 f"📌 **មូលហេតុ៖** {reason}"
        )
        await asyncio.sleep(8)
        await warn.delete()

    except Exception as e:
        logging.error(f"Failed to kick user or delete message: {e}")

async def monitor_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ ស្កែនមើលរាល់សារទាំងអស់ដែលផ្ញើចូល Group """
    message = update.message
    if not message:
        return

    # ប្រសិនបើ Admin ជាអ្នកផ្ញើ មិនចាត់វិធានការទេ
    if await is_admin(update, context):
        return

    text_content = message.text or message.caption or ""

    # 1. ស្កែន File មេរោគ (.exe, .apk...)
    if message.document:
        file_name = message.document.file_name.lower() if message.document.file_name else ""
        if file_name.endswith(DANGEROUS_EXTENSIONS):
            await kick_and_clean(update, context, f"ផ្ញើ File មានហានិភ័យ/មេរោគ (`{file_name}`)")
            return

    # 2. ស្កែន Link ស្ពែម
    if re.search(URL_REGEX, text_content):
        await kick_and_clean(update, context, "ផ្ញើ Link ស្ពែមចូលក្នុង Group")
        return

    # 3. ស្កែនពាក្យអាសអាភាស
    if any(bad_word in text_content.lower() for bad_word in BAD_WORDS):
        await kick_and_clean(update, context, "ប្រើប្រាស់ពាក្យពេចន៍/សារអាសអាភាស")
        return

    # 4. ចាប់លុបរូបភាព និង វីដេអូ (ប្រសិនបើមិនចង់ឱ្យសមាជិកផ្ញើរូប/វីដេអូផ្តេសផ្តាស)
    if message.photo or message.video or message.animation:
        await kick_and_clean(update, context, "ផ្ញើរូបភាព/វីដេអូ ដោយគ្មានការអនុញ្ញាត")
        return

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛡️ Anti-Virus & Protection Bot កំពុងការពារ Group របស់អ្នក!")

async def main():
    # ⚠️ ជំនួស API TOKEN របស់ Anti-Virus Bot នៅទីនេះ
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
