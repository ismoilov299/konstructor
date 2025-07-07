import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
import yt_dlp
import requests
from urllib.parse import urlparse

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7400666200:AAE0q92yJUwJ-FVdAq88HK2HBjo7vOqX3_0"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def is_valid_url(url):
    """Qo'llab-quvvatlanadigan URL larni tekshirish"""
    supported_domains = [
        'youtube.com', 'youtu.be', 'm.youtube.com',
        'vimeo.com', 'dailymotion.com', 'tiktok.com',
        'instagram.com', 'facebook.com', 'twitter.com',
        'twitch.tv', 'streamable.com'
    ]

    parsed = urlparse(url)
    return any(domain in parsed.netloc for domain in supported_domains)


async def download_with_api(url):
    """API orqali yuklab olish (muqobil yechim)"""
    try:
        # Bu yerda bepul YouTube downloader API lardan foydalanish mumkin
        # Misol: rapidapi.com da YouTube downloader API lar bor

        # Hozircha oddiy yt-dlp dan foydalanamiz
        ydl_opts = {
            'format': 'worst[ext=mp4]/worst',
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['configs', 'webpage'],
                }
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None, "Video ma'lumotlarini olishda xatolik"

            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)

            if duration and duration > 600:
                return None, "Video juda uzun!"

            ydl.download([url])
            filename = ydl.prepare_filename(info)

            return filename, None

    except Exception as e:
        return None, str(e)


async def download_video_alternative(url, user_id):
    """Muqobil yuklab olish usuli"""

    # Birinchi - API orqali sinash
    try:
        filename, error = await download_with_api(url)
        if filename and os.path.exists(filename):
            return filename, None
    except Exception as e:
        logger.error(f"API usuli xatolik: {str(e)}")

    # Ikkinchi - Proxy bilan sinash
    try:
        ydl_opts = {
            'format': 'worst[height<=360]/worst',
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s_%(id)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'ignoreerrors': True,
            'quiet': True,
            'no_warnings': True,
            # Proxy qo'shish mumkin (agar bor bo'lsa)
            # 'proxy': 'http://proxy-server:port',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                ydl.download([url])
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return filename, None

    except Exception as e:
        logger.error(f"Proxy usuli xatolik: {str(e)}")

    return None, "Barcha usullar muvaffaqiyatsiz. YouTube cheklovlari tufayli video yuklab olib bo'lmadi."


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    """Start komandasi"""
    await message.answer(
        "🎬 Universal Video Downloader Bot\n\n"
        "Qo'llab-quvvatlanadigan platformalar:\n"
        "• YouTube\n"
        "• Vimeo\n"
        "• TikTok\n"
        "• Instagram\n"
        "• Facebook\n"
        "• Twitter\n"
        "• Twitch\n\n"
        "🔗 Video havolasini yuboring!"
    )


@dp.message(Command("platforms"))
async def platforms_handler(message: types.Message):
    """Qo'llab-quvvatlanadigan platformalar"""
    await message.answer(
        "📱 Qo'llab-quvvatlanadigan platformalar:\n\n"
        "✅ YouTube - youtube.com, youtu.be\n"
        "✅ Vimeo - vimeo.com\n"
        "✅ TikTok - tiktok.com\n"
        "✅ Instagram - instagram.com\n"
        "✅ Facebook - facebook.com\n"
        "✅ Twitter - twitter.com\n"
        "✅ Twitch - twitch.tv\n"
        "✅ Streamable - streamable.com\n\n"
        "💡 Maslahat: Agar YouTube ishlamasa, boshqa platformalarni sinab ko'ring!"
    )


@dp.message()
async def handle_url(message: types.Message):
    """URL larni qayta ishlash"""
    text = message.text

    if not text:
        await message.answer("❌ Iltimos, video havolasini yuboring!")
        return

    if not is_valid_url(text):
        await message.answer(
            "❌ Qo'llab-quvvatlanmaydigan havola!\n\n"
            "Qo'llab-quvvatlanadigan platformalar:\n"
            "YouTube, Vimeo, TikTok, Instagram, Facebook, Twitter, Twitch\n\n"
            "/platforms - to'liq ro'yxat"
        )
        return

    status_message = await message.answer("⏳ Video yuklab olinmoqda...")

    try:
        filename, error = await download_video_alternative(text, message.from_user.id)

        if error:
            await status_message.edit_text(f"❌ {error}")
            return

        if not filename or not os.path.exists(filename):
            await status_message.edit_text("❌ Video yuklab olishda xatolik!")
            return

        file_size = os.path.getsize(filename)
        if file_size > 50 * 1024 * 1024:
            await status_message.edit_text("❌ Video juda katta!")
            os.remove(filename)
            return

        await status_message.edit_text("📤 Video yuborilmoqda...")

        file_to_send = FSInputFile(filename)

        if filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            await message.answer_video(
                video=file_to_send,
                caption="✅ Video muvaffaqiyatli yuklab olindi!"
            )
        else:
            await message.answer_document(
                document=file_to_send,
                caption="✅ Fayl muvaffaqiyatli yuklab olindi!"
            )

        os.remove(filename)
        await status_message.delete()

    except Exception as e:
        logger.error(f"Xatolik: {str(e)}")
        await status_message.edit_text(f"❌ Xatolik: {str(e)}")

        if 'filename' in locals() and filename and os.path.exists(filename):
            os.remove(filename)


async def main():
    """Botni ishga tushirish"""
    logger.info("Universal Video Downloader Bot ishga tushmoqda...")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Xatolik: {str(e)}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())