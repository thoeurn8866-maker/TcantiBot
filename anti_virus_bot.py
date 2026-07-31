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

# 📁 Configuration សម្រាប់កន្លែងផ្ទុកឯកសារ (Archive)
DOCS_ARCHIVE_CHANNEL_ID = -1004493775116  # ID របស់ Archive Channel សម្រាប់តែឯកសារ (PDF, Zip,...)

# 🖼️ កែប្រែថ្មី៖ ID របស់ Channel សម្រាប់ដាក់រូបថត និងវីដេអូ (សូមប្តូរ ID នេះ)
MEDIA_ARCHIVE_CHANNEL_ID = -1004478811243  # 👈 ដាក់ ID Channel ថ្មីរបស់បងនៅទីនេះ

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

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ 👋 មុខងារស្វាគមន៍សមាជិកថ្មី និងរំលឹកពីបទបញ្ជាក្រុម (Auto-Delete ក្នុង ១ នាទី) """
    message = update.message
    
    if message.new_chat_members:
        for new_member in message.new_chat_members:
            if new_member.is_bot:
                continue

            user_name = new_member.full_name
            user_id = new_member.id
            user_mention = f"[{user_name}](tg://user?id={user_id})"
            chat_title = update.effective_chat.title or "Group"
            time_str = datetime.now(CAMBODIA_TZ).strftime("%Y-%m-%d %H:%M:%S")

            welcome_text = (
                f"👋 **សូមស្វាគមន៍ {user_mention} មកកាន់ {chat_title}!**\n\n"
                f"ដើម្បីរក្សាសុវត្ថិភាព និងរបៀបរៀបរយក្នុង Group សូមសមាជិកមេត្តាជ្រាបពី **បទបញ្ជាសុវត្ថិភាព** ដូចខាងក្រោម៖\n\n"
                f"🚫 **ហាមផ្ញើ Link/URL ស្ពែម ឬ Link គ្មានប្រភពច្បាស់លាស់**\n"
                f"🚫 **ហាមផ្ញើ File មេរោគ ឬ Executable Files (.exe, .apk, .zip, ...)**\n"
                f"🚫 **ហាមផ្ញើរូបភាព/សារដដែលៗ (Spam) និងពាក្យអសុរោះ/អាសអាភាស**\n\n"
                f"⚠️ *(ប្រព័ន្ធការពារនឹងព្រមាន ឬ Remove ចេញពី Group ស្វ័យប្រវត្តិប្រសិនបើមានការល្មើស)*\n\n"
                f"⏰ **កាលបរិច្ឆេទ៖** {time_str}\n"
                f"*(សារស្វាគមន៍នេះនឹងត្រូវលុបស្វ័យប្រវត្តិក្នុងរយៈពេល ១ នាទី)*"
            )

            try:
                sent_msg = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=welcome_text,
                    parse_mode='Markdown'
                )

                await asyncio.sleep(60)
                await sent_msg.delete()
                
                try:
                    await message.delete()
                except Exception:
                    pass

            except Exception as e:
                logging.error(f"Failed to send welcome message: {e}")

# 📁 កែប្រែថ្មី៖ បំបែកមុខងារ Archive ជា ២ (ឯកសារ និង មេឌៀ)

async def auto_archive_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ 📁 មុខងារប្រមូល និងរក្សាទុកឯកសារ រូបថត វីដេអូ ស្វ័យប្រវត្តិទៅកាន់ Channel ផ្សេងៗគ្នា """
    message = update.message
    if not message: return

    user = message.from_user
    user_name = user.full_name
    user_handle = f"@{user.username}" if user.username else "គ្មាន Username"
    chat_title = update.effective_chat.title or "Group"
    time_str = datetime.now(CAMBODIA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    # ប្រមូលព័ត៌មានមូលដ្ឋានសម្រាប់ Caption
    base_info = (
        f"👥 **Group៖** {chat_title}\n"
        f"👤 **អ្នកផ្ញើ៖** {user_name} ({user_handle})\n"
        f"🆔 **User ID៖** `{user.id}`\n"
        f"⏰ **កាលបរិច្ឆេទ៖** {time_str}\n"
        f"📝 **Caption ដើម៖** {message.caption or 'គ្មាន'}"
    )

    # --- ករណីទី ១៖ ជា File ឯកសារ (Document) ---
    if message.document and DOCS_ARCHIVE_CHANNEL_ID and DOCS_ARCHIVE_CHANNEL_ID != -1001234567890:
        # កុំ Archive បើជា File មេរោគ (ទុកឱ្យ Monitor លុប)
        file_name = message.document.file_name.lower() if message.document.file_name else ""
        if file_name.endswith(DANGEROUS_EXTENSIONS): return

        archive_caption = f"📄 **[ប្រមូលឯកសារស្វ័យប្រវត្តិ]**\n\n📁 **ឈ្មោះ File៖** `{message.document.file_name}`\n{base_info}"
        
        try:
            await message.copy(chat_id=DOCS_ARCHIVE_CHANNEL_ID, caption=archive_caption, parse_mode='Markdown')
            logging.info(f"Archived document to Docs Channel from user {user.id}")
        except Exception as e:
            logging.error(f"Failed to copy file to Docs Archive Channel: {e}")

    # --- ករណីទី ២៖ ជា រូបថត ឬ វីដេអូ (Photo or Video) ---
    elif (message.photo or message.video) and MEDIA_ARCHIVE_CHANNEL_ID and MEDIA_ARCHIVE_CHANNEL_ID != -100XXXXXXXXXX:
        media_type = "រូបថត" if message.photo else "វីដេអូ"
        archive_caption = f"🖼️ **[ប្រមូល{media_type}ស្វ័យប្រវត្តិ]**\n\n{base_info}"

        try:
            # ប្រើ copy ដូចគ្នា វានឹងយក Photo size ធំបំផុត ឬ Video ទៅដោយស្វ័យប្រវត្តិ
            await message.copy(chat_id=MEDIA_ARCHIVE_CHANNEL_ID, caption=archive_caption, parse_mode='Markdown')
            logging.info(f"Archived {media_type} to Media Channel from user {user.id}")
        except Exception as e:
            logging.error(f"Failed to copy {media_type} to Media Archive Channel: {e}")

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
                     f"📌 **មូលហេតុ៖អាចបង កូដបានកែសម្រួលដើម្បីបំបែកកន្លែងទុកដាក់ឱ្យស្របតាមប្រភេទឯកសារ៖
1.  **File ឯកសារ** (PDF, Doc,...) ទៅ Channel ដើម (`DOCS_ARCHIVE_CHANNEL_ID`)
2.  **រូបថត និង វីដេអូ** ទៅ Channel ថ្មី (`MEDIA_ARCHIVE_CHANNEL_ID`)

**សំខាន់៖** បងត្រូវបង្កើត Channel ថ្មីមួយទៀត យករូបថត និងវីដេអូ Add Bot ចូលជា Admin រួចយក ID Channel ថ្មីនោះមកដាក់ជំនួសត្រង់ `MEDIA_ARCHIVE_CHANNEL_ID = -100XXXXXXXXXX` នៅក្នុងកូដខាងក្រោម៖

```python
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

# 📁 Configuration សម្រាប់កន្លែងផ្ទុក (Archive)
DOCS_ARCHIVE_CHANNEL_ID = -1004493775116  # ID របស់ Archive Channel សម្រាប់តែឯកសារ (PDF, Doc,...)

# 🖼️ កែប្រែថ្មី៖ ID របស់ Channel សម្រាប់ដាក់រូបថត និងវីដេអូ (សូមប្តូរ ID នេះ)
MEDIA_ARCHIVE_CHANNEL_ID = -100XXXXXXXXXX  # 👈 ដាក់ ID Channel ថ្មីរបស់បងនៅទីនេះ

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

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ 👋 មុខងារស្វាគមន៍សមាជិកថ្មី និងរំលឹកពីបទបញ្ជាក្រុម (Auto-Delete ក្នុង ១ នាទី) """
    message = update.message
    
    if message.new_chat_members:
        for new_member in message.new_chat_members:
            if new_member.is_bot:
                continue

            user_name = new_member.full_name
            user_id = new_member.id
            user_mention = f"[{user_name}](tg://user?id={user_id})"
            chat_title = update.effective_chat.title or "Group"
            time_str = datetime.now(CAMBODIA_TZ).strftime("%Y-%m-%d %H:%M:%S")

            welcome_text = (
                f"👋 **សូមស្វាគមន៍ {user_mention} មកកាន់ {chat_title}!**\n\n"
                f"ដើម្បីរក្សាសុវត្ថិភាព និងរបៀបរៀបរយក្នុង Group សូមសមាជិកមេត្តាជ្រាបពី **បទបញ្ជាសុវត្ថិភាព** ដូចខាងក្រោម៖\n\n"
                f"🚫 **ហាមផ្ញើ Link/URL ស្ពែម ឬ Link គ្មានប្រភពច្បាស់លាស់**\n"
                f"🚫 **ហាមផ្ញើ File មេរោគ ឬ Executable Files (.exe, .apk, .zip, ...)**\n"
                f"🚫 **ហាមផ្ញើរូបភាព/សារដដែលៗ (Spam) និងពាក្យអសុរោះ/អាសអាភាស**\n\n"
                f"⚠️ *(ប្រព័ន្ធការពារនឹងព្រមាន ឬ Remove ចេញពី Group ស្វ័យប្រវត្តិប្រសិនបើមានការល្មើស)*\n\n"
                f"⏰ **កាលបរិច្ឆេទ៖** {time_str}\n"
                f"*(សារស្វាគមន៍នេះនឹងត្រូវលុបស្វ័យប្រវត្តិក្នុងរយៈពេល ១ នាទី)*"
            )

            try:
                sent_msg = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=welcome_text,
                    parse_mode='Markdown'
                )

                await asyncio.sleep(60)
                await sent_msg.delete()
                
                try:
                    await message.delete()
                except Exception:
                    pass

            except Exception as e:
                logging.error(f"Failed to send welcome message: {e}")

# 📁 កែប្រែថ្មី៖ មុខងារ Archive Content បំបែកប្រភេទឯកសារ និង មេឌៀ

async def auto_archive_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ 📁 មុខងារប្រមូល និងរក្សាទុកឯកសារ រូបថត វីដេអូ ស្វ័យប្រវត្តិទៅកាន់ Channel ផ្សេងៗគ្នា (Silent Storage) """
    message = update.message
    if not message: return

    # កុំ Archive បើសារនោះ COMMAND (ដូចជា /start)
    if message.text and message.text.startswith('/'): return

    user = message.from_user
    user_name = user.full_name
    user_handle = f"@{user.username}" if user.username else "គ្មាន Username"
    chat_title = update.effective_chat.title or "Group"
    time_str = datetime.now(CAMBODIA_TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    # ប្រមូលព័ត៌មានមូលដ្ឋានសម្រាប់ Caption
    base_info = (
        f"👥 **Group៖** {chat_title}\n"
        f"👤 **អ្នកផ្ញើ៖** {user_name} ({user_handle})\n"
        f"🆔 **User ID៖** `{user.id}`\n"
        f"⏰ **កាលបរិច្ឆេទ៖** {time_str}\n"
        f"📝 **Caption ដើម៖** {message.caption or 'គ្មាន'}"
    )

    # --- ករណីទី ១៖ ជា File ឯកសារ (Document) -> ទៅ Docs Channel ---
    if message.document and DOCS_ARCHIVE_CHANNEL_ID and DOCS_ARCHIVE_CHANNEL_ID != -1001234567890:
        # មិន Archive បើជា File គ្រោះថ្នាក់ (ទុកឱ្យ monitor_messages លុប និងព្រមាន)
        file_name = message.document.file_name.lower() if message.document.file_name else ""
        if file_name.endswith(DANGEROUS_EXTENSIONS): return

        archive_caption = f"📄 **[ប្រមូលឯកសារស្វ័យប្រវត្តិ]**\n\n📁 **ឈ្មោះ File៖** `{message.document.file_name}`\n{base_info}"
        
        try:
            await message.copy(chat_id=DOCS_ARCHIVE_CHANNEL_ID, caption=archive_caption, parse_mode='Markdown')
            logging.info(f"Archived document to Docs Channel from user {user.id}")
        except Exception as e:
            logging.error(f"Failed to copy file to Docs Archive Channel: {e}")

    # --- ករណីទី ២៖ ជា រូបថត ឬ វីដេអូ (Photo or Video) -> ទៅ Media Channel ---
    elif (message.photo or message.video) and MEDIA_ARCHIVE_CHANNEL_ID and MEDIA_ARCHIVE_CHANNEL_ID != -100XXXXXXXXXX:
        media_type = "រូបថត" if message.photo else "វីដេអូ"
        archive_caption = f"🖼️ **[ប្រមូល{media_type}ស្វ័យប្រវត្តិ]**\n\n{base_info}"

        try:
            # ការប្រើ copy() វានឹងយក Photo ទំហំធំបំផុត ឬឯកសារវីដេអូទៅដោយស្វ័យប្រវត្តិ
            await message.copy(chat_id=MEDIA_ARCHIVE_CHANNEL_ID, caption=archive_caption, parse_mode='Markdown')
            logging.info(f"Archived {media_type} to Media Channel from user {user.id}")
        except Exception as e:
            logging.error(f"Failed to copy {media_type} to Media Archive Channel: {e}")

async def process_violation(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str):
    """ មុខងារគ្រប់គ្រងការព្រមាន, Remove សមាជិក និងផ្ញើ Log """
    message = update.message
    if not message: return
    
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

        signature = f"\n\n*(នាយកដ្ឋានរដ្ឋបាលនិងធនធានមនុស្សនៃទូរគមនាគមន៍កម្ពុជា)*"

        if current_warns < 3:
            warn_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ **សារព្រមានលើកទី {current_warns}/3!**\n\n"
                     f"🔔 **ជូនចំពោះសមាជិក៖** {user_mention}\n"
                     f"📌 **មូលហេតុ៖** {reason}\n"
                     f"⏰ **កាលបរិច្ឆេទ៖** {time_str}\n\n"
                     f"*(ប្រសិនបើប្រព្រឹត្តល្មើសដល់លើកទី ៣ ប្រព័ន្ធនឹង Remove ចេញពី Group ស្វ័យប្រវត្តិ!)*" + signature,
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

            await asyncio.sleep(60)
            await warn_msg.delete()

        else:
            # ប្រមូល ៣ ដង -> Ban/Remove
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            user_warnings.pop(user_id, None) # លុបប្រវត្តិព្រមានក្រោយ Ban

            ban_msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"🚫 **ប្រព័ន្ធបាន Remove {user_mention} ចេញពី Group!**\n\n"
                     f"📌 **មូលហេតុ៖** ទទួលបានការព្រមានគ្រប់ ៣ ដង ({reason})\n"
                     f"⏰ **កាលបរិច្ឆេទ៖** {time_str}" + signature,
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

    # 👋 ១. ពិនិត្យមើល និងស្វាគមន៍សមាជិកថ្មី
    if message.new_chat_members:
        await welcome_new_member(update, context)
        return

    text_content = message.text or message.caption or ""
    today_str = datetime.now(CAMBODIA_TZ).strftime("%Y-%m-%d")

    # 🔍 ២. ការត្រួតពិនិត្យបទល្មើស (កុំពិនិត្យ Admin)
    if not await is_admin(update, context):
        # ស្កែនរក Spam File/Photo (ដោយប្រើ unique_id)
        file_unique_id = None
        if message.document:
            file_unique_id = message.document.file_unique_id
        elif message.photo:
            file_unique_id = message.photo[-1].file_unique_id # យករូបធំបំផុត
        elif message.video:
            file_unique_id = message.video.file_unique_id

        if file_unique_id:
            if file_unique_id in sent_files_history and sent_files_history[file_unique_id] == today_str:
                await process_violation(update, context, "ផ្ញើរូបភាព/វីដេអូ ឬ ឯកសារដដែលៗ (Spam) ក្នុងថ្ងៃតែមួយ")
                return # ឈប់ធ្វើការងារបន្ត បើល្មើស
            else:
                sent_files_history[file_unique_id] = today_str

        # ស្កែនរក File មេរោគ
        if message.document:
            file_name = message.document.file_name.lower() if message.document.file_name else ""
            if file_name.endswith(DANGEROUS_EXTENSIONS):
                await process_violation(update, context, f"ផ្ញើ File មានហានិភ័យ/មេរោគ (`{file_name}`)")
                return

        # ស្កែនរក Link ស្ពែម
        if re.search(URL_REGEX, text_content):
            await process_violation(update, context, "ផ្ញើ Link ស្ពែមចូលក្នុង Group")
            return

        # ស្កែនរកពាក្យអសុរោះ
        if any(bad_word in text_content.lower() for bad_word in BAD_WORDS):
            await process_violation(update, context, "ប្រើប្រាស់ពាក្យពេចន៍/សារអាសអាភាស")
            return

    # 📁 ៣. ប្រមូលខ្លឹមសារស្វ័យប្រវត្តិ (Silent Archive) -> កែប្រែថ្មី (បំបែក Channel)
    # ហៅមុខងារនេះទោះជា Admin ឬសមាជិកផ្ញើ (ឱ្យតែមិនល្មើសខាងលើ)
    await auto_archive_content(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Command /start """
    # ពិនិត្យ timezone ម្តងទៀតដើម្បីប្រាកដ
    time_now = datetime.now(CAMBODIA_TZ).strftime("%H:%M:%S")
    await update.message.reply_text(
        f"🛡️ **Anti-Virus Bot កំពុងការពារ Group!**\n\n"
        f"ហៅ COMMAND នៅម៉ោង៖ {time_now} (ម៉ោងនៅកម្ពុជា)\n"
        f"បង្កើតឡើងដោយ ឡេង ប៊ុនធឿន\nទូរសព្ទ៖ 089976679",
        parse_mode='Markdown'
    )

async def main():
    # 🔑 Bot Token
    TOKEN = '8950817942:AAFvAnahRVijtETT246VqlLp5s23XA7-xHc'

    # ចាប់ផ្តើម Web Server ក្នុង Thread ផ្សេង (daemon=True ដើម្បីបិទពេល Bot បិទ)
    threading.Thread(target=run_flask, daemon=True).start()

    # បង្កើត Application
    app = ApplicationBuilder().token(TOKEN).build()

    # បន្ថែម Handlers
    # ប្រើ filters.ALL ដើម្បីចាប់គ្រប់សារ (Text, Photo, Doc, ...) លើកលែង COMMAND
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, monitor_messages))
    app.add_handler(CommandHandler('start', start))

    # រៀបចំ និងចាប់ផ្តើម Bot
    await app.initialize()
    await app.start()
    # drop_pending_updates=True ដើម្បីកុំឱ្យ Bot ឆ្លើយតបសារចាស់ៗពេលវា Offline
    await app.updater.start_polling(drop_pending_updates=True)
    
    # រក្សា Bot ឱ្យដំណើរការរហូត
    await asyncio.Event().wait()

if __name__ == '__main__':
    try:
        # បើកដំណើរការ Main Event Loop
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped by user.")
