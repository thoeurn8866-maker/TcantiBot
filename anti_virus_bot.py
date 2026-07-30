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

# 🚫 ប្រភេទ File ដែលចាត់ទុកជាមេរោគ/ហានិភ័យ
DANGEROUS_EXTENSIONS = (
    '.exe', '.apk', '.vbs', '.bat', '.cmd', '.scr', 
    '.js', '.zip', '.rar', '.iso', '.ps1', '.msi'
)

# 🚫 Regex ចាប់ Link ស្ពែម
URL_REGEX = r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,})"

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

async def monitor_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ ស្កែន និងលុបទាំង File មេរោគ និង Link ស្ពែម """
    message = update.message
    if not message:
        return

    # ប្រសិនបើ Admin ជាអ្នកផ្ញើ មិនលុបទេ
    if await is_admin(update, context):
        return

    user_name = message.from_user.full_name if message.from_user else "សមាជិក"
    
    # 1. ស្កែន និងលុប File មេរោគ (Document)
    if message.document:
        file_name = message.document.file_name.lower() if message.document.file_name else ""
        if file_name.endswith(DANGEROUS_EXTENSIONS):
            try:
                await message.delete()
                warn = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ **សារប្រុងប្រយ័ត្ន!**\nសូមទោស {user_name}! ប្រព័ន្ធបានលុបឯកសារ `{file_name}` ព្រោះវាជាប្រភេទ File មានហានិភ័យ/មេរោគ។(ការិយាល័យបុគ្គលិក ទូរសព្ទ 123)"
                )
                await asyncio.sleep(8)
                await warn.delete()
                return
            except Exception as e:
                logging.error(f"Failed to delete virus file: {e}")

    # 2. ស្កែន និងលុប Link ស្ពែម (អត្ថបទធម្មតា ឬ Caption លើរូបភាព/វីដេអូ)
    text_content = message.text or message.caption or ""
    if re.search(URL_REGEX, text_content):
        try:
            await message.delete()
            warn = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🚫 **សូមទោស {user_name}!**\nសមាជិកមិនត្រូវអនុញ្ញាតឱ្យផ្ញើ Link ចូលក្នុង Group ឡើយ។"
            )
            await asyncio.sleep(8)
            await warn.delete()
            return
        except Exception as e:
            logging.error(f"Failed to delete link: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛡️ Anti-Virus & Anti-Spam Bot កំពុងដំណើរការការពារ Group របស់អ្នក!")

async def main():
    # ⚠️ ជំនួស API TOKEN របស់ Anti-Virus Bot នៅទីនេះ
    TOKEN = '8950817942:AAFvAnahRVijtETT246VqlLp5s23XA7-xHc'

    threading.Thread(target=run_flask, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    # ចាប់ស្កែនរាល់ Message ទាំងអស់ដែលផ្ញើចូល Group
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, monitor_messages))
    app.add_handler(CommandHandler('start', start))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
