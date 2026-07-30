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
    return "Anti-Virus Group Bot is Active!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# ------------------------------------------------

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 🚫 កំណត់ប្រភេទ File ដែលចាត់ទុកជាមេរោគ/ហានិភ័យ
DANGEROUS_EXTENSIONS = (
    '.exe', '.apk', '.vbs', '.bat', '.cmd', '.scr', 
    '.js', '.zip', '.rar', '.iso', '.ps1', '.msi'
)

# 🚫 Regex សម្រាប់ចាប់ Link ស្ពែម
URL_REGEX = r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,})"

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """ មុខងារពិនិត្យមើលថា តើអ្នកផ្ញើសារជា Admin ឬអត់ """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # ប្រសិនបើជា Private Chat មិនបាច់ Check ទេ
    if update.effective_chat.type == 'private':
        return True

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ['creator', 'administrator']
    except Exception:
        return False

async def handle_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ ស្កែន និងលុប File មេរោគ """
    # ប្រសិនបើ Admin ជាអ្នកផ្ញើ មិនលុបទេ
    if await check_admin(update, context):
        return

    message = update.message
    file_name = message.document.file_name.lower() if message.document.file_name else ""

    # ពិនិត្យមើល Extension របស់ File
    if file_name.endswith(DANGEROUS_EXTENSIONS):
        user_name = message.from_user.full_name
        try:
            # លុប File មេរោគចោលភ្លាមៗ
            await message.delete()
            
            # ផ្ញើសារព្រមាន
            warn_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ **សារប្រុងប្រយ័ត្ន!**\n"
                     f"សូមទោស {user_name}! ប្រព័ន្ធបានលុបឯកសារ `{file_name}` ព្រោះវាជាប្រភេទ File មានហានិភ័យ ឬអាចជាមេរោគ។"
            )
            # លុបសារព្រមានចោលវិញក្រោយ 10 វិនាទី កុំឱ្យស្ទះ Group
            await asyncio.sleep(10)
            await warn_msg.delete()
            
        except Exception as e:
            logging.error(f"Error deleting virus file: {e}")

async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ ស្កែន និងលុប Link ស្ពែម """
    # ប្រសិនបើ Admin ជាអ្នកផ្ញើ មិនលុបទេ
    if await check_admin(update, context):
        return

    message = update.message
    text = message.text or message.caption or ""

    # ពិនិត្យមើលថាតើមាន Link ក្នុងសារឬទេ
    if re.search(URL_REGEX, text):
        user_name = message.from_user.full_name
        try:
            # លុបសារដែលមាន Link ចោល
            await message.delete()
            
            # ផ្ញើសារព្រមាន
            warn_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🚫 **សមាជិកមិនត្រូវអនុញ្ញាតឱ្យផ្ញើ Link ឡើយ!**\n"
                     f"សាររបស់ {user_name} ត្រូវបានលុបចេញពី Group។"
            )
            await asyncio.sleep(8)
            await warn_msg.delete()
            
        except Exception as e:
            logging.error(f"Error deleting link message: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛡️ Anti-Virus & Anti-Spam Bot កំពុងដំណើរការការពារ Group របស់អ្នក!")

async def main():
    # ⚠️ ជំនួស API TOKEN របស់ Anti-Virus Bot នៅទីនេះ
    TOKEN = 'YOUR_ANTIVIRUS_BOT_TOKEN_HERE'

    threading.Thread(target=run_flask, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    # លុប File មេរោគ
    app.add_handler(MessageHandler(filters.Document.ALL, handle_documents))
    
    # លុប Link ស្ពែម
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_links))
    
    app.add_handler(CommandHandler('start', start))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())