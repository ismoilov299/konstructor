import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
import yt_dlp
from urllib.parse import urlparse

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token - @BotFather dan olingan
BOT_TOKEN = "7400666200:AAE0q92yJUwJ-FVdAq88HK2HBjo7vOqX3_0"

# Bot va Dispatcher yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Yuklab olingan fayllar uchun papka
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def is_valid_youtube_url(url):
    """YouTube URL ni tekshirish"""
    parsed = urlparse(url)
    return (parsed.netloc in ['www.youtube.com', 'youtube.com', 'youtu.be', 'm.youtube.com'] or
            'youtube.com' in parsed.netloc)


async def download_video(url, user_id):
    """YouTube video yuklab olish"""
    try:
        # yt-dlp sozlamalari
        ydl_opts = {
            'format': 'best[height<=720]',  # 720p yoki undan past sifat
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Video ma'lumotlarini olish
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)

            # Video uzunligini tekshirish (10 daqiqadan kam bo'lishi kerak)
            if duration > 600:  # 10 daqiqa
                return None, "Video juda uzun! Maksimal 10 daqiqalik videolarni yuklab olishingiz mumkin."

            # Video yuklab olish
            ydl.download([url])

            # Yuklab olingan fayl nomini topish
            filename = ydl.prepare_filename(info)

            return filename, None

    except Exception as e:
        logger.error(f"Video yuklab olishda xatolik: {str(e)}")
        return None, f"Video yuklab olishda xatolik: {str(e)}"


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    """Start komandasi"""
    await message.answer(
        "🎬 YouTube Video Yuklovchi Bot\n\n"
        "Menga YouTube video havolasini yuboring va men uni sizga yuborib beraman!\n\n"
        "⚠️ Cheklovlar:\n"
        "• Maksimal 10 daqiqalik videolar\n"
        "• Faqat YouTube havolalari\n"
        "• Maksimal 720p sifat\n\n"
        "Misol: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    """Yordam komandasi"""
    await message.answer(
        "📋 Qo'llanma:\n\n"
        "1. YouTube video havolasini yuboring\n"
        "2. Bot video yuklab oladi\n"
        "3. Tayyor bo'lgach, sizga yuboradi\n\n"
        "Qo'llab-quvvatlanadigan formatlar:\n"
        "• https://www.youtube.com/watch?v=...\n"
        "• https://youtu.be/...\n"
        "• https://m.youtube.com/watch?v=...\n\n"
        "Muammoga duch kelsangiz, /start ni bosing."
    )


@dp.message()
async def handle_url(message: types.Message):
    """URL larni qayta ishlash"""
    text = message.text

    if not text:
        await message.answer("❌ Iltimos, YouTube video havolasini yuboring!")
        return

    if not is_valid_youtube_url(text):
        await message.answer("❌ Noto'g'ri havola! Iltimos, YouTube video havolasini yuboring.")
        return

    # Yuklab olish jarayonini boshlash
    status_message = await message.answer("⏳ Video yuklab olinmoqda...")

    try:
        # Video yuklab olish
        filename, error = await download_video(text, message.from_user.id)

        if error:
            await status_message.edit_text(f"❌ {error}")
            return

        if not filename or not os.path.exists(filename):
            await status_message.edit_text("❌ Video yuklab olishda xatolik yuz berdi!")
            return

        # Fayl hajmini tekshirish (50MB dan kam bo'lishi kerak)
        file_size = os.path.getsize(filename)
        if file_size > 50 * 1024 * 1024:  # 50MB
            await status_message.edit_text("❌ Video juda katta! Maksimal 50MB li videolarni yuborishim mumkin.")
            os.remove(filename)
            return

        # Video yuborish
        await status_message.edit_text("📤 Video yuborilmoqda...")

        video_file = FSInputFile(filename)
        await message.answer_video(
            video=video_file,
            caption="✅ Video muvaffaqiyatli yuklab olindi!\n\n🤖 @YourBotUsername"
        )

        # Vaqtinchalik faylni o'chirish
        os.remove(filename)

        # Status xabarini o'chirish
        await status_message.delete()

    except Exception as e:
        logger.error(f"Video yuborishda xatolik: {str(e)}")
        await status_message.edit_text(f"❌ Video yuborishda xatolik: {str(e)}")

        # Xatolik bo'lsa faylni o'chirish
        if 'filename' in locals() and filename and os.path.exists(filename):
            os.remove(filename)


async def main():
    """Botni ishga tushirish"""
    logger.info("Bot ishga tushmoqda...")

    try:
        # Polling rejimida ishga tushirish
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot ishga tushirishda xatolik: {str(e)}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())