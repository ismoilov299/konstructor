@client_bot_router.message(DownloaderBotFilter())
@client_bot_router.message(Download.download)
async def youtube_download_handler(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        await message.answer("❗ Отправьте ссылку на видео")
        return

    url = message.text.strip()
    me = await bot.get_me()

    if 'tiktok.com' in url:
        await handle_tiktok(message, url, me, bot, state)
    elif 'instagram.com' in url or 'instagr.am' in url or 'inst.ae' in url:
        await handle_instagram(message, url, me, bot)
    elif 'youtube.com' in url or 'youtu.be' in url:
        await handle_youtube(message, url, me, bot, state)  # Yangilangan funksiya
    else:
        await message.answer("❗ Поддерживаются только YouTube, Instagram и TikTok ссылки")


@client_bot_router.callback_query(F.data.startswith("yt_dl_"))
async def process_youtube_download(callback: CallbackQuery, state: FSMContext):
    """YouTube download callback"""
    try:
        await callback.answer()

        format_index = int(callback.data.split('_')[2])

        data = await state.get_data()
        video_data = data.get('youtube_data')
        formats = data.get('youtube_formats', [])

        if not video_data or not formats or format_index >= len(formats):
            await callback.message.edit_text("❌ Yuklab olish ma'lumotlari topilmadi")
            return

        selected_format = formats[format_index]
        title = video_data.get('title', 'Video')

        await callback.message.edit_text(
            f"⏳ <b>Yuklab olmoqda...</b>\n\n"
            f"🎥 <b>{title[:50]}...</b>\n"
            f"📋 <b>Format:</b> {selected_format['quality']} {selected_format['ext'].upper()}",
            parse_mode="HTML"
        )

        # Download URL ni topish
        download_url = None
        itag = selected_format['itag']

        # Progressive formatlardan qidirish
        if 'formats' in video_data:
            for fmt in video_data['formats']:
                if fmt.get('itag') == itag:
                    download_url = fmt.get('url')
                    break

        # Adaptive formatlardan qidirish
        if not download_url and 'adaptiveFormats' in video_data:
            for fmt in video_data['adaptiveFormats']:
                if fmt.get('itag') == itag:
                    download_url = fmt.get('url')
                    break

        if not download_url:
            await callback.message.edit_text("❌ Yuklab olish URL topilmadi")
            return

        # Faylni yuklab olish va yuborish
        await download_and_send_youtube(callback, download_url, selected_format, video_data, title)

    except Exception as e:
        logger.error(f"YouTube download callback error: {e}")
        await callback.message.edit_text("❌ Yuklab olish xatoligi")


async def download_and_send_youtube(callback, download_url, format_data, video_data, title):
    """YouTube faylni yuklab olib Telegram ga yuborish"""
    temp_dir = None
    try:
        # Temp directory yaratish
        temp_dir = tempfile.mkdtemp(prefix='yt_api_')
        file_ext = format_data['ext']
        filename = f"{title[:50]}.{file_ext}".replace('/', '_').replace('\\', '_')
        filepath = os.path.join(temp_dir, filename)

        # Progress yangilash
        await callback.message.edit_text(
            f"⏬ <b>Yuklab olmoqda...</b>\n\n"
            f"🎥 <b>{title[:50]}...</b>\n"
            f"📋 <b>Format:</b> {format_data['quality']} {format_data['ext'].upper()}\n"
            f"📦 <b>Hajmi:</b> {format_data['size']:.1f} MB",
            parse_mode="HTML"
        )

        # Faylni yuklab olish
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url) as response:
                if response.status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    with open(filepath, 'wb') as file:
                        async for chunk in response.content.iter_chunked(8192):
                            file.write(chunk)
                            downloaded += len(chunk)

                            # Har 1MB da progress yangilash
                            if downloaded % (1024 * 1024) == 0:
                                progress = (downloaded / total_size) * 100 if total_size else 0
                                await callback.message.edit_text(
                                    f"⏬ <b>Yuklab olmoqda: {progress:.0f}%</b>\n\n"
                                    f"🎥 <b>{title[:50]}...</b>\n"
                                    f"📋 <b>Format:</b> {format_data['quality']} {format_data['ext'].upper()}\n"
                                    f"📦 <b>Hajmi:</b> {format_data['size']:.1f} MB",
                                    parse_mode="HTML"
                                )
                else:
                    raise Exception(f"Download failed: HTTP {response.status}")

        # Fayl hajmini tekshirish
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)

        if file_size_mb > 50:
            await callback.message.edit_text(
                f"❌ <b>Fayl juda katta</b>\n\n"
                f"📦 <b>Hajmi:</b> {file_size_mb:.1f} MB\n"
                f"📏 <b>Telegram limiti:</b> 50 MB\n\n"
                f"💡 Kichikroq sifat tanlang",
                parse_mode="HTML"
            )
            return

        # Telegram ga yuborish
        await callback.message.edit_text(
            f"📤 <b>Telegram ga yubormoqda...</b>\n\n"
            f"🎥 <b>{title[:50]}...</b>",
            parse_mode="HTML"
        )

        caption = (
            f"🎥 {title}\n"
            f"👤 {video_data.get('channelTitle', 'Unknown')}\n"
            f"📋 {format_data['quality']} {format_data['ext'].upper()}\n"
            f"📦 {file_size_mb:.1f} MB\n"
            f"🎯 YouTube API orqali yuklab olindi"
        )

        try:
            if format_data['type'] == 'audio':
                await callback.bot.send_audio(
                    chat_id=callback.message.chat.id,
                    audio=FSInputFile(filepath),
                    caption=caption,
                    title=title,
                    performer=video_data.get('channelTitle', 'Unknown'),
                    duration=int(video_data.get('lengthSeconds', 0))
                )
            else:
                await callback.bot.send_video(
                    chat_id=callback.message.chat.id,
                    video=FSInputFile(filepath),
                    caption=caption,
                    supports_streaming=True,
                    duration=int(video_data.get('lengthSeconds', 0))
                )

            await callback.message.delete()

            # Analytics
            try:
                await shortcuts.add_to_analitic_data(
                    (await callback.bot.get_me()).username,
                    callback.message.chat.id
                )
            except:
                pass

        except Exception as send_error:
            logger.error(f"Error sending file: {send_error}")
            await callback.message.edit_text(
                f"❌ <b>Faylni yuborishda xatolik</b>\n\n"
                f"📋 <b>Xatolik:</b> {str(send_error)[:150]}...",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Download and send error: {e}")
        await callback.message.edit_text(
            f"❌ <b>Yuklab olishda xatolik</b>\n\n"
            f"📋 <b>Xatolik:</b> {str(e)[:150]}...",
            parse_mode="HTML"
        )
    finally:
        # Temp fayllarni tozalash
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass


async def handle_youtube(message: Message, url: str, me, bot, state: FSMContext):
    logger.info(f"🎬 YouTube handler started")
    logger.info(f"🔗 URL: {url}")

    try:
        progress_msg = await message.answer("🔍 Анализирую YouTube видео...")
        logger.info("✅ Progress message sent")

        # Video ID ni olish
        video_id = extract_youtube_id(url)
        if not video_id:
            logger.error("❌ Could not extract video ID")
            await progress_msg.edit_text("❌ Неверная ссылка YouTube")
            return

        # API dan ma'lumot olish
        logger.info(f"🔍 Getting video info for ID: {video_id}")
        video_data = await get_youtube_info_via_fast_api(video_id, "247")

        if not video_data:
            logger.error("❌ No video data received from API")
            await progress_msg.edit_text(
                "❌ <b>Не удалось получить данные видео</b>\n\n"
                "💡 Проверьте ссылку или попробуйте позже",
                parse_mode="HTML"
            )
            return

        # Video ma'lumotlarini formatlash
        size_mb = int(video_data.get('size', 0)) / (1024 * 1024) if video_data.get('size') else 0
        logger.info(f"📦 Video size: {size_mb:.1f} MB")

        info_text = (
            f"✅ <b>YouTube видео найдено!</b>\n\n"
            f"🆔 <b>ID видео:</b> {video_id}\n"
            f"📋 <b>Качество:</b> {video_data.get('quality', 'Неизвестно')}\n"
            f"📦 <b>Размер:</b> {size_mb:.1f} МБ\n"
            f"🎞 <b>Формат:</b> {video_data.get('mime', 'Неизвестно')}\n"
            f"⚡ <b>Битрейт:</b> {video_data.get('bitrate', 'Неизвестно')}\n\n"
            f"📥 <b>Выберите формат:</b>"
        )

        keyboard = create_youtube_format_keyboard()

        # State ga saqlash
        await state.update_data(
            youtube_url=url,
            youtube_video_id=video_id,
            youtube_api_type="fast_api"
        )
        logger.info("💾 Data saved to state")

        await progress_msg.edit_text(
            info_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
        logger.info("✅ YouTube handler completed successfully")

    except Exception as e:
        logger.error(f"❌ YouTube handler error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"📍 Traceback: {traceback.format_exc()}")
        await message.answer("❌ Ошибка при обработке YouTube видео")


@client_bot_router.callback_query(F.data.startswith("yt_fast_dl_"))
async def process_youtube_fast_download(callback: CallbackQuery, state: FSMContext):
    logger.info(f"📱 Fast download callback triggered")
    logger.info(f"📋 Callback data: {callback.data}")

    try:
        await callback.answer()

        # Quality ID ni olish
        parts = callback.data.split('_')
        logger.info(f"📋 Callback parts: {parts}")

        if len(parts) < 4:
            logger.error(f"❌ Invalid callback data format: {callback.data}")
            await callback.message.edit_text("❌ Неверный формат данных")
            return

        quality_id = parts[3]  # yt_fast_dl_360 -> 360
        logger.info(f"🎯 Selected quality ID: {quality_id}")

        # State dan ma'lumot olish
        data = await state.get_data()
        video_id = data.get('youtube_video_id')
        logger.info(f"💾 Video ID from state: {video_id}")

        if not video_id:
            logger.error("❌ No video ID in state")
            await callback.message.edit_text("❌ Данные видео не найдены")
            return

        # Quality tekshirish
        qualities = get_available_youtube_qualities()
        if quality_id not in qualities:
            logger.error(f"❌ Invalid quality ID: {quality_id}")
            await callback.message.edit_text("❌ Неверный формат выбран")
            return

        selected_format = qualities[quality_id]
        logger.info(f"✅ Selected format: {selected_format}")

        await callback.message.edit_text(
            f"⏳ <b>Отправляю запрос на загрузку...</b>\n\n"
            f"🆔 <b>ID видео:</b> {video_id}\n"
            f"📋 <b>Формат:</b> {selected_format['desc']}\n"
            f"⚙️ <b>ID качества:</b> {quality_id}",
            parse_mode="HTML"
        )

        # API dan download URL olish
        logger.info(f"🔍 Getting download URL for quality: {quality_id}")
        download_data = await get_youtube_info_via_fast_api(video_id, quality_id)

        if not download_data:
            logger.error("❌ No download data received")
            await callback.message.edit_text("❌ Данные для загрузки не получены")
            return

        if 'file' not in download_data:
            logger.error(f"❌ No 'file' key in download data: {list(download_data.keys())}")
            await callback.message.edit_text("❌ URL для загрузки не найден")
            return

        download_url = download_data['file']
        size_mb = int(download_data.get('size', 0)) / (1024 * 1024)
        logger.info(f"✅ Download URL obtained: {download_url[:50]}...")
        logger.info(f"📦 File size: {size_mb:.1f} MB")

        # Telegram limit tekshirish
        if size_mb > 50:
            logger.warning(f"⚠️ File too large: {size_mb:.1f} MB")
            await callback.message.edit_text(
                f"❌ <b>Файл слишком большой!</b>\n\n"
                f"📦 <b>Размер:</b> {size_mb:.1f} МБ\n"
                f"📏 <b>Лимит Telegram:</b> 50 МБ\n\n"
                f"💡 Выберите формат меньшего размера",
                parse_mode="HTML"
            )
            return

        await callback.message.edit_text(
            f"⏳ <b>Жду готовности файла...</b>\n\n"
            f"🆔 <b>ID видео:</b> {video_id}\n"
            f"📋 <b>Формат:</b> {selected_format['desc']}\n"
            f"📦 <b>Размер:</b> {size_mb:.1f} МБ\n\n"
            f"⏱ <b>Максимальное ожидание:</b> 3 минуты",
            parse_mode="HTML"
        )

        # Fayl tayyor bo'lishini kutish
        logger.info("⏳ Starting file ready check...")
        is_ready = await wait_for_youtube_file_ready(download_url, max_wait_minutes=3)

        if not is_ready:
            logger.error("⏰ File not ready after waiting")
            await callback.message.edit_text(
                f"⏰ <b>Файл не готов через 3 минуты</b>\n\n"
                f"💡 Попробуйте позже или выберите другой формат",
                parse_mode="HTML"
            )
            return

        # Faylni yuklab olib yuborish
        logger.info("📥 Starting file download and send...")
        await download_and_send_youtube_fast(callback, download_url, selected_format, video_id, size_mb)

    except Exception as e:
        logger.error(f"❌ Fast download callback error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"📍 Traceback: {traceback.format_exc()}")
        await callback.message.edit_text("❌ Ошибка при загрузке")


@client_bot_router.callback_query(F.data == "yt_more_formats")
async def show_more_formats(callback: CallbackQuery):
    logger.info("🔧 More formats requested")
    await callback.answer()
    keyboard = create_more_formats_keyboard()
    await callback.message.edit_text(
        "🔧 <b>Дополнительные форматы:</b>\n\n"
        "🎬 Только видео - без звука\n"
        "📹 Видео+Аудио - полный формат",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


@client_bot_router.callback_query(F.data == "yt_main_formats")
async def show_main_formats(callback: CallbackQuery):
    logger.info("📹 Main formats requested")
    await callback.answer()
    keyboard = create_youtube_format_keyboard()
    await callback.message.edit_text(
        "📥 <b>Основные форматы:</b>\n\n"
        "📹 = Видео + Аудио вместе",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )


async def download_and_send_youtube_fast(callback, download_url, format_data, video_id, size_mb):
    logger.info(f"📥 Starting download and send process")
    logger.info(f"🔗 Download URL: {download_url[:50]}...")
    logger.info(f"📋 Format: {format_data}")

    temp_dir = None
    try:
        # Temp directory yaratish
        temp_dir = tempfile.mkdtemp(prefix='yt_fast_')
        filename = f"youtube_{video_id}_{format_data['quality']}.mp4"
        filepath = os.path.join(temp_dir, filename)
        logger.info(f"📁 Temp file path: {filepath}")

        await callback.message.edit_text(
            f"⏬ <b>Загружаю...</b>\n\n"
            f"🆔 <b>ID видео:</b> {video_id}\n"
            f"📋 <b>Формат:</b> {format_data['desc']}\n"
            f"📦 <b>Размер:</b> {size_mb:.1f} МБ",
            parse_mode="HTML"
        )

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'identity'
        }

        downloaded = 0
        start_time = time.time()

        logger.info("🌐 Starting file download...")
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(download_url, timeout=300) as response:
                status = response.status
                logger.info(f"📡 Download response status: {status}")

                if status == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    logger.info(f"📦 Total download size: {total_size} bytes")

                    with open(filepath, 'wb') as file:
                        last_update = time.time()

                        async for chunk in response.content.iter_chunked(8192):
                            file.write(chunk)
                            downloaded += len(chunk)

                            current_time = time.time()
                            if current_time - last_update >= 3:
                                if total_size > 0:
                                    progress = (downloaded / total_size) * 100
                                    speed = downloaded / (current_time - start_time) / (1024 * 1024)
                                    logger.info(f"📊 Progress: {progress:.0f}%, Speed: {speed:.1f} MB/s")

                                    await callback.message.edit_text(
                                        f"⏬ <b>Загружаю: {progress:.0f}%</b>\n\n"
                                        f"🆔 <b>ID видео:</b> {video_id}\n"
                                        f"📋 <b>Формат:</b> {format_data['desc']}\n"
                                        f"📊 <b>Скорость:</b> {speed:.1f} МБ/с\n"
                                        f"📦 <b>Загружено:</b> {downloaded / (1024 * 1024):.1f} МБ",
                                        parse_mode="HTML"
                                    )

                                last_update = current_time
                else:
                    raise Exception(f"Download failed: HTTP {status}")

        # Fayl hajmini tekshirish
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"✅ File downloaded: {file_size_mb:.1f} MB")

        if file_size_mb > 50:
            logger.error(f"❌ File too large for Telegram: {file_size_mb:.1f} MB")
            await callback.message.edit_text(
                f"❌ <b>Файл слишком большой для Telegram</b>\n\n"
                f"📦 <b>Размер:</b> {file_size_mb:.1f} МБ\n"
                f"📏 <b>Лимит:</b> 50 МБ",
                parse_mode="HTML"
            )
            return

        # Telegram ga yuborish
        await callback.message.edit_text(
            f"📤 <b>Отправляю в Telegram...</b>\n\n"
            f"🆔 <b>ID видео:</b> {video_id}",
            parse_mode="HTML"
        )

        caption = (
            f"🎥 YouTube Видео\n"
            f"🆔 {video_id}\n"
            f"📋 {format_data['desc']}\n"
            f"📦 {file_size_mb:.1f} МБ\n"
            f"🚀 Загружено через Fast API"
        )

        logger.info("📤 Sending to Telegram...")
        try:
            if format_data['type'] == 'progressive':
                await callback.bot.send_video(
                    chat_id=callback.message.chat.id,
                    video=FSInputFile(filepath),
                    caption=caption,
                    supports_streaming=True
                )
            else:
                await callback.bot.send_document(
                    chat_id=callback.message.chat.id,
                    document=FSInputFile(filepath),
                    caption=caption
                )

            await callback.message.delete()
            logger.info("✅ File sent successfully!")

            # Analytics
            try:
                await shortcuts.add_to_analitic_data(
                    (await callback.bot.get_me()).username,
                    callback.message.chat.id
                )
            except Exception as analytics_error:
                logger.warning(f"⚠️ Analytics error: {analytics_error}")

        except Exception as send_error:
            logger.error(f"❌ Error sending file: {send_error}")
            await callback.message.edit_text(
                f"❌ <b>Ошибка отправки файла</b>\n\n"
                f"📋 <b>Ошибка:</b> {str(send_error)[:100]}...",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"❌ Download and send error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"📍 Traceback: {traceback.format_exc()}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка при загрузке</b>\n\n"
            f"📋 <b>Ошибка:</b> {str(e)[:100]}...",
            parse_mode="HTML"
        )
    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info("🗑️ Temp files cleaned up")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Cleanup error: {cleanup_error}")


@client_bot_router.callback_query(F.data == "too_large")
async def handle_too_large_callback(callback: CallbackQuery):
    """Handle too large file selection"""
    await callback.answer(
        "Этот файл слишком большой для Telegram (более 50 MB). "
        "Выберите формат с меньшим качеством.",
        show_alert=True
    )







from modul.loader import client_bot_router
from aiogram import F
import json
RAPIDAPI_KEY = "532d0e9edemsh5566c31aceb7163p1343e7jsn11577b0723dd"
RAPIDAPI_HOST = "youtube-video-fast-downloader-24-7.p.rapidapi.com"


def extract_youtube_id(url):
    """YouTube URL dan video ID ni olish"""
    logger.info(f"Extracting video ID from URL: {url}")

    patterns = [
        r'(?:youtube\.be/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com/v/)([a-zA-Z0-9_-]+)',
        r'(?:youtube\.com/shorts/)([a-zA-Z0-9_-]+)',
        r'(?:youtu\.be/)([a-zA-Z0-9_-]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            logger.info(f"✅ Video ID extracted: {video_id}")
            return video_id

    logger.error(f"❌ Could not extract video ID from: {url}")
    return None

def get_available_youtube_qualities():
    """Mavjud YouTube sifatlari"""
    return {
        "18": {"quality": "360p", "type": "progressive", "format": "MP4", "desc": "360p MP4 (Video+Audio)"},
        "22": {"quality": "720p", "type": "progressive", "format": "MP4", "desc": "720p MP4 (Video+Audio)"},
        "247": {"quality": "720p", "type": "video", "format": "WebM", "desc": "720p WebM (Video only)"},
        "248": {"quality": "1080p", "type": "video", "format": "WebM", "desc": "1080p WebM (Video only)"},
        "360": {"quality": "360p", "type": "progressive", "format": "MP4", "desc": "360p (Video+Audio)"},
        "720": {"quality": "720p", "type": "progressive", "format": "MP4", "desc": "720p (Video+Audio)"},
        "1080": {"quality": "1080p", "type": "progressive", "format": "MP4", "desc": "1080p (Video+Audio)"}
    }


async def get_youtube_info_via_fast_api(video_id, quality="247"):
    """Fast API orqali YouTube video ma'lumotlarini olish - DEBUGGING BILAN"""
    logger.info(f"🔍 API request starting...")
    logger.info(f"   Video ID: {video_id}")
    logger.info(f"   Quality: {quality}")
    logger.info(f"   API Host: {RAPIDAPI_HOST}")

    try:
        url = f"https://{RAPIDAPI_HOST}/download_short/{video_id}"
        params = {"quality": quality}
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST
        }

        logger.info(f"📡 Request URL: {url}")
        logger.info(f"📋 Request params: {params}")
        logger.info(f"🔑 Request headers: {headers}")

        async with aiohttp.ClientSession() as session:
            logger.info("🌐 Making HTTP request...")
            async with session.get(url, headers=headers, params=params, timeout=30) as response:
                status = response.status
                logger.info(f"📡 Response status: {status}")

                if status == 200:
                    try:
                        data = await response.json()
                        logger.info(f"✅ API Success! Response keys: {list(data.keys())}")
                        logger.info(f"📄 Full response: {json.dumps(data, indent=2)}")
                        return data
                    except Exception as json_error:
                        logger.error(f"❌ JSON parsing error: {json_error}")
                        text_response = await response.text()
                        logger.error(f"📄 Raw response: {text_response}")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"❌ API error {status}: {error_text}")
                    return None

    except asyncio.TimeoutError:
        logger.error("⏰ API request timeout (30s)")
        return None
    except Exception as e:
        logger.error(f"❌ API request error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"📍 Traceback: {traceback.format_exc()}")
        return None


async def wait_for_youtube_file_ready(file_url, max_wait_minutes=3):
    """YouTube fayl tayyor bo'lishini kutish"""
    logger.info(f"⏳ Waiting for file to be ready...")
    logger.info(f"🔗 File URL: {file_url}")
    logger.info(f"⏱ Max wait time: {max_wait_minutes} minutes")

    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    check_interval = 10

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }

    attempt = 1

    while time.time() - start_time < max_wait_seconds:
        try:
            logger.info(f"🔄 Attempt #{attempt} - checking file status...")

            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.head(file_url, timeout=10) as response:
                    status = response.status
                    logger.info(f"📡 HEAD response status: {status}")

                    if status == 200:
                        content_length = response.headers.get('content-length', 'Unknown')
                        content_type = response.headers.get('content-type', 'Unknown')
                        logger.info(f"✅ File ready! Size: {content_length}, Type: {content_type}")
                        return True

                    elif status == 404:
                        elapsed = time.time() - start_time
                        remaining = max_wait_seconds - elapsed
                        logger.info(f"⏳ File not ready yet (404). Remaining: {remaining/60:.1f} min")

                    else:
                        logger.warning(f"⚠️ Unexpected status: {status}")

            if time.time() - start_time < max_wait_seconds:
                logger.info(f"💤 Sleeping {check_interval} seconds...")
                await asyncio.sleep(check_interval)
                attempt += 1

        except Exception as e:
            logger.error(f"❌ Check error: {type(e).__name__}: {e}")
            await asyncio.sleep(check_interval)
            attempt += 1

    logger.error(f"⏰ Wait time expired ({max_wait_minutes} min)")
    return False


def create_youtube_format_keyboard():
    keyboard = InlineKeyboardBuilder()
    qualities = get_available_youtube_qualities()

    # Asosiy formatlar
    popular_formats = ["22", "18", "720", "360"]

    for quality_id in popular_formats:
        if quality_id in qualities:
            fmt = qualities[quality_id]
            icon = "📹" if fmt["type"] == "progressive" else "🎬"
            button_text = f"{icon} {fmt['desc']}"
            keyboard.row(InlineKeyboardButton(
                text=button_text,
                callback_data=f"yt_fast_dl_{quality_id}"
            ))

    keyboard.row(InlineKeyboardButton(text="🔧 Другие форматы", callback_data="yt_more_formats"))
    keyboard.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_download"))
    return keyboard


def create_more_formats_keyboard():
    keyboard = InlineKeyboardBuilder()
    qualities = get_available_youtube_qualities()
    additional_formats = ["1080", "247", "248"]

    for quality_id in additional_formats:
        if quality_id in qualities:
            fmt = qualities[quality_id]
            icon = "📹" if fmt["type"] == "progressive" else "🎬"
            button_text = f"{icon} {fmt['desc']}"
            keyboard.row(InlineKeyboardButton(
                text=button_text,
                callback_data=f"yt_fast_dl_{quality_id}"
            ))

    keyboard.row(InlineKeyboardButton(text="⬅️ Основные форматы", callback_data="yt_main_formats"))
    keyboard.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_download"))
    return keyboard



def format_video_info(video_data):
    """Video ma'lumotlarini formatlash"""
    title = video_data.get('title', 'Video')
    channel = video_data.get('channelTitle', 'Unknown')
    duration = video_data.get('lengthSeconds', 0)
    views = video_data.get('viewCount', 0)

    # Duration formatlash
    duration_str = ""
    if duration:
        duration = int(duration)
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            duration_str = f"{minutes:02d}:{seconds:02d}"

    # Views formatlash
    views_str = ""
    if views:
        views = int(views)
        if views >= 1_000_000:
            views_str = f"{views / 1_000_000:.1f}M"
        elif views >= 1_000:
            views_str = f"{views / 1_000:.1f}K"
        else:
            views_str = f"{views:,}"

    info_text = (
        f"✅ <b>Video topildi!</b>\n\n"
        f"🎥 <b>{title}</b>\n"
        f"👤 <b>Kanal:</b> {channel}\n"
        f"⏱ <b>Davomiyligi:</b> {duration_str}\n"
        f"👀 <b>Ko'rishlar:</b> {views_str}\n\n"
        f"📥 <b>Formatni tanlang:</b>\n"
        f"✅ = Video + Audio birga"
    )

    return info_text

@client_bot_router.callback_query(F.data == "cancel_download")
async def cancel_download_callback(callback: CallbackQuery, state: FSMContext):
    """Handle download cancellation"""
    await callback.message.edit_text("❌ Загрузка отменена.")
    await callback.answer("Отменено")
    await state.clear()



class InstagramDownloader:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'max_filesize': 50000000,
            'format': 'best',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': 'https://www.instagram.com',
                'Referer': 'https://www.instagram.com/',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Connection': 'keep-alive',
            }
        }

    async def download_with_yt_dlp(self, url):
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    async def download_with_api(self, url):
        # API endpoints for different Instagram content types
        api_endpoints = [
            "https://api.instagram.com/oembed/?url={}",
            "https://www.instagram.com/api/v1/media/{}/info/",
            "https://www.instagram.com/p/{}/?__a=1&__d=1"
        ]

        # Extract media ID from URL
        media_id = re.search(r'/p/([^/]+)', url)
        if not media_id:
            media_id = re.search(r'/reel/([^/]+)', url)
        if not media_id:
            return None

        media_id = media_id.group(1)

        async with aiohttp.ClientSession() as session:
            for endpoint in api_endpoints:
                try:
                    formatted_url = endpoint.format(url if '{}' in endpoint else media_id)
                    async with session.get(formatted_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'video_url' in data:
                                return {'url': data['video_url'], 'ext': 'mp4'}
                            elif 'thumbnail_url' in data:
                                return {'url': data['thumbnail_url'], 'ext': 'jpg'}
                except Exception as e:
                    logger.error(f"API endpoint error: {e}")
                    continue
        return None


async def handle_instagram(message: Message, url: str, me, bot: Bot):
    progress_msg = await message.answer("⏳ Загружаю медиа из Instagram...")
    message_deleted = False

    try:
        # Clean up URL - remove tracking parameters
        if '?' in url:
            url = url.split('?')[0]

        # Check if URL is valid Instagram URL
        if not any(domain in url for domain in ['instagram.com', 'instagr.am', 'instagram']):
            try:
                await progress_msg.edit_text("❌ Это не похоже на ссылку Instagram")
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await message.answer("❌ Это не похоже на ссылку Instagram")
            return

        logger.info(f"Processing Instagram URL: {url}")

        # Определяем, является ли это reel или обычным постом
        is_reel = "/reel/" in url
        logger.info(f"Is this a reel? {is_reel}")

        # Create temp directory for files if it doesn't exist
        temp_dir = "/var/www/downloads"
        os.makedirs(temp_dir, exist_ok=True)

        # Generate unique ID for this request
        import hashlib
        import time
        request_id = hashlib.md5(f"{url}_{time.time()}".encode()).hexdigest()[:10]

        # Helper function to send Instagram files
        async def send_instagram_files(message, directory, files, me, bot):
            """Helper function to send downloaded Instagram files"""
            sent_count = 0
            media_files = []

            # Логируем все найденные файлы для отладки
            logger.info(f"Files in directory {directory}: {files}")

            # Проверяем, содержит ли имя директории или файлы слово "reel" - это поможет определить видео
            is_file_reel = "reel" in directory.lower() or any("reel" in f.lower() for f in files)
            logger.info(f"Files indicate reel: {is_file_reel}")

            # First sort files to ensure correct order and filter unwanted files
            for f in sorted(files):
                filepath = os.path.join(directory, f)
                if not os.path.isfile(filepath):
                    continue

                # Skip small files and metadata files
                filesize = os.path.getsize(filepath)
                if filesize < 1000 or '.json' in f or '.txt' in f:
                    continue

                # Determine file type by extension
                ext = os.path.splitext(f)[1].lower()

                # Determine if this is a video by file extension
                if ext in ['.mp4', '.mov', '.webm']:
                    media_type = 'video'
                elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    # If we know this is a reel but file is an image, it's a thumbnail
                    media_type = 'thumbnail' if (is_reel or is_file_reel) else 'photo'
                else:
                    # Log unusual extensions for analysis
                    logger.info(f"Unusual file extension found: {ext} in file {f}")
                    continue

                media_files.append((filepath, media_type))

            # Then send files
            total_files = len(media_files)
            logger.info(f"Found {total_files} media files in directory {directory}")

            for i, (filepath, media_type) in enumerate(media_files):
                try:
                    logger.info(f"Sending file {i + 1}/{total_files}: {filepath} as {media_type}")

                    if media_type == 'video':
                        try:
                            await bot.send_video(
                                chat_id=message.chat.id,
                                video=FSInputFile(filepath),
                                caption=f"📹 Instagram видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                            )
                            sent_count += 1
                        except Exception as video_error:
                            logger.error(f"Error sending as video, trying as document: {video_error}")
                            await bot.send_document(
                                chat_id=message.chat.id,
                                document=FSInputFile(filepath),
                                caption=f"📹 Instagram видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                            )
                            sent_count += 1
                    elif media_type == 'thumbnail':
                        await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=FSInputFile(filepath),
                            caption=f"🎞 Instagram превью видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                        )
                        sent_count += 1
                    else:  # photo
                        await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=FSInputFile(filepath),
                            caption=f"🖼 Instagram фото {i + 1}/{total_files}\nСкачано через @{me.username}"
                        )
                        sent_count += 1

                    # Add small delay between posts
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error sending file {filepath}: {e}")

                    # Try alternate method if primary fails
                    try:
                        await bot.send_document(
                            chat_id=message.chat.id,
                            document=FSInputFile(filepath),
                            caption=f"📄 Instagram медиа {i + 1}/{total_files}\nСкачано через @{me.username}"
                        )
                        sent_count += 1
                    except Exception as fallback_error:
                        logger.error(f"Fallback error for file {filepath}: {fallback_error}")

            return sent_count > 0

        # Безопасное редактирование сообщения
        async def safe_edit_message(msg, text):
            nonlocal message_deleted
            if not message_deleted:
                try:
                    await msg.edit_text(text)
                except Exception as e:
                    logger.error(f"Error editing message: {e}")
                    message_deleted = True
                    await message.answer(text)

        # First, try direct API method if this is a reel (fastest method)
        if is_reel:
            await safe_edit_message(progress_msg, "🔍 Использую прямой API метод для reel...")

            try:
                import re
                import aiohttp

                # Extract shortcode
                match = re.search(r'/reel/([^/]+)', url)
                if match:
                    shortcode = match.group(1)

                    # Try specialized API endpoint for reels
                    api_url = f"https://www.instagram.com/graphql/query/?query_hash=b3055c01b4b222b8a47dc12b090e4e64&variables={{\"shortcode\":\"{shortcode}\"}}"

                    headers = {
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 12_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 105.0.0.11.118 (iPhone11,8; iOS 12_3_1; en_US; en-US; scale=2.00; 828x1792; 165586599)",
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Origin": "https://www.instagram.com",
                        "Referer": url,
                        "x-ig-app-id": "936619743392459",
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.get(api_url, headers=headers, timeout=10) as response:
                            if response.status == 200:
                                data = await response.json()

                                if 'data' in data and 'shortcode_media' in data['data']:
                                    media = data['data']['shortcode_media']

                                    if media.get('is_video') and 'video_url' in media:
                                        video_url = media['video_url']
                                        logger.info(f"Found video URL via API: {video_url}")

                                        try:
                                            await bot.send_video(
                                                chat_id=message.chat.id,
                                                video=video_url,
                                                caption=f"📹 Instagram видео\nСкачано через @{me.username}"
                                            )
                                            await shortcuts.add_to_analitic_data(me.username, url)
                                            try:
                                                await progress_msg.delete()
                                                message_deleted = True
                                            except:
                                                pass
                                            return
                                        except Exception as video_err:
                                            logger.error(f"Error sending video: {video_err}")

                                    # If video not found but we have image
                                    if 'display_url' in media:
                                        display_url = media['display_url']
                                        logger.info(f"Found image URL via API: {display_url}")

                                        try:
                                            await bot.send_photo(
                                                chat_id=message.chat.id,
                                                photo=display_url,
                                                caption=f"🎞 Instagram превью видео\nСкачано через @{me.username}"
                                            )
                                            await shortcuts.add_to_analitic_data(me.username, url)
                                            try:
                                                await progress_msg.delete()
                                                message_deleted = True
                                            except:
                                                pass
                                            return
                                        except Exception as photo_err:
                                            logger.error(f"Error sending image: {photo_err}")
            except Exception as e:
                logger.error(f"Direct API method error: {e}")

        # Approach 1: Direct instaloader method (using Python subprocess)
        await safe_edit_message(progress_msg, "🔍 Загружаю через instaloader (метод 1/3)...")

        try:
            # Check if instaloader is installed
            instaloader_present = False
            try:
                subprocess.run(["instaloader", "--version"], capture_output=True, text=True, check=True)
                instaloader_present = True
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.info("Instaloader not found, skipping method 1")

            if instaloader_present:
                # Extract shortcode from URL
                import re
                match = re.search(r'/(p|reel)/([^/]+)', url)
                if not match:
                    logger.warning(f"Could not extract shortcode from URL: {url}")
                else:
                    shortcode = match.group(2)
                    output_dir = os.path.join(temp_dir, f"insta_{request_id}")
                    os.makedirs(output_dir, exist_ok=True)

                    # Try to download using instaloader
                    cmd = [
                        "instaloader",
                        "--no-metadata-json",
                        "--no-captions",
                        "--no-video-thumbnails",
                        "--login", "anonymous",
                        f"--dirname-pattern={output_dir}",
                        f"--filename-pattern={shortcode}",
                        f"-- -{shortcode}"  # Format for downloading by shortcode
                    ]

                    try:
                        process = await asyncio.create_subprocess_exec(
                            *cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()

                        if process.returncode == 0:
                            # Find downloaded files
                            files = os.listdir(output_dir)

                            if files:
                                success = await send_instagram_files(message, output_dir, files, me, bot)
                                if success:
                                    await shortcuts.add_to_analitic_data(me.username, url)
                                    try:
                                        await progress_msg.delete()
                                        message_deleted = True
                                    except:
                                        pass
                                    # Clean up
                                    shutil.rmtree(output_dir, ignore_errors=True)
                                    return
                    except Exception as e:
                        logger.error(f"Instaloader error: {e}")
        except Exception as e:
            logger.error(f"Approach 1 error: {e}")

        # Approach 2: Gallery-dl method (external tool)
        await safe_edit_message(progress_msg, "🔍 Загружаю через gallery-dl (метод 2/3)...")

        try:
            # Check if gallery-dl is installed
            gallery_dl_present = False
            try:
                subprocess.run(["gallery-dl", "--version"], capture_output=True, text=True, check=True)
                gallery_dl_present = True
            except (subprocess.SubprocessError, FileNotFoundError):
                logger.info("Gallery-dl not found, skipping method 2")

            if gallery_dl_present:
                output_dir = os.path.join(temp_dir, f"insta_{request_id}")
                os.makedirs(output_dir, exist_ok=True)

                # Try to download using gallery-dl
                cmd = [
                    "gallery-dl",
                    "--cookies", "none",
                    "--dest", output_dir,
                    url
                ]

                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    # Check if files were downloaded
                    files = os.listdir(output_dir)

                    if files:
                        success = await send_instagram_files(message, output_dir, files, me, bot)
                        if success:
                            await shortcuts.add_to_analitic_data(me.username, url)
                            try:
                                await progress_msg.delete()
                                message_deleted = True
                            except:
                                pass
                            # Clean up
                            shutil.rmtree(output_dir, ignore_errors=True)
                            return
                except Exception as e:
                    logger.error(f"Gallery-dl error: {e}")
        except Exception as e:
            logger.error(f"Approach 2 error: {e}")

        # Approach 3: youtube-dl / yt-dlp method (fallback)
        await safe_edit_message(progress_msg, "🔍 Загружаю через yt-dlp (метод 3/3)...")

        try:
            output_file = os.path.join(temp_dir, f"insta_{request_id}")

            # Advanced yt-dlp options with writethumbnail
            ydl_opts = {
                'format': 'best',
                'outtmpl': f"{output_file}.%(ext)s",
                'writethumbnail': True,  # Save thumbnails too
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Referer': 'https://www.instagram.com/',
                    'Origin': 'https://www.instagram.com',
                    'x-ig-app-id': '936619743392459',
                }
            }

            # Попробуем сначала без cookie
            try:
                no_cookie_opts = ydl_opts.copy()

                with YoutubeDL(no_cookie_opts) as ydl:
                    await asyncio.get_event_loop().run_in_executor(
                        executor,
                        lambda: ydl.extract_info(url, download=True)
                    )
            except Exception as no_cookie_error:
                logger.error(f"Failed without cookies: {no_cookie_error}")

                # Try with cookies
                cookies_file = os.path.join(temp_dir, f"cookies_{request_id}.txt")
                with open(cookies_file, "w") as f:
                    f.write("""# Netscape HTTP Cookie File
.instagram.com\tTRUE\t/\tFALSE\t1999999999\tcsrftoken\tsomerandomcsrftoken
.instagram.com\tTRUE\t/\tFALSE\t1999999999\tmid\tYf8XQgABAAHaJf3kDKq0ZiVw4YHl
.instagram.com\tTRUE\t/\tFALSE\t1999999999\tds_user_id\t1234567890
.instagram.com\tTRUE\t/\tFALSE\t1999999999\tsessionid\t1234567890%3A12345abcdef%3A1
""")
                ydl_opts['cookiefile'] = cookies_file

                try:
                    with YoutubeDL(ydl_opts) as ydl:
                        await asyncio.get_event_loop().run_in_executor(
                            executor,
                            lambda: ydl.extract_info(url, download=True)
                        )
                except Exception as e:
                    logger.error(f"Failed with cookies too: {e}")

            # Check for downloaded files - first check for videos
            media_found = False

            # First check for video files
            for ext in ['mp4', 'webm', 'mov']:
                filepath = f"{output_file}.{ext}"
                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    logger.info(f"Found video file: {filepath} size: {os.path.getsize(filepath)}")
                    try:
                        await bot.send_video(
                            chat_id=message.chat.id,
                            video=FSInputFile(filepath),
                            caption=f"📹 Instagram видео\nСкачано через @{me.username}"
                        )
                        media_found = True
                        await shortcuts.add_to_analitic_data(me.username, url)
                        try:
                            await progress_msg.delete()
                            message_deleted = True
                        except:
                            pass
                        break
                    except Exception as send_error:
                        logger.error(f"Error sending video: {send_error}")
                        # Try as document if video fails
                        try:
                            await bot.send_document(
                                chat_id=message.chat.id,
                                document=FSInputFile(filepath),
                                caption=f"📹 Instagram видео\nСкачано через @{me.username}"
                            )
                            media_found = True
                            await shortcuts.add_to_analitic_data(me.username, url)
                            try:
                                await progress_msg.delete()
                                message_deleted = True
                            except:
                                pass
                            break
                        except Exception as doc_error:
                            logger.error(f"Error sending as document: {doc_error}")
                    finally:
                        try:
                            if os.path.exists(filepath):
                                os.remove(filepath)
                        except:
                            pass

            # If no video found, check for images
            if not media_found:
                image_files = []
                for ext in ['jpg', 'jpeg', 'png', 'webp']:
                    # Check direct filename matches
                    filepath = f"{output_file}.{ext}"
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        image_files.append(filepath)

                    # Also check for alternate filenames (like thumbnails)
                    for alt_file in glob.glob(f"{output_file}*.{ext}"):
                        if os.path.exists(alt_file) and os.path.getsize(alt_file) > 0:
                            image_files.append(alt_file)

                # Sort by size - larger files first (usually better quality)
                image_files.sort(key=lambda f: os.path.getsize(f), reverse=True)

                for filepath in image_files:
                    try:
                        logger.info(f"Found image file: {filepath} size: {os.path.getsize(filepath)}")

                        # Determine if this is a reel thumbnail or regular photo
                        caption = "🎞 Instagram превью видео" if is_reel else "🖼 Instagram фото"

                        await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=FSInputFile(filepath),
                            caption=f"{caption}\nСкачано через @{me.username}"
                        )
                        media_found = True
                        await shortcuts.add_to_analitic_data(me.username, url)
                        try:
                            await progress_msg.delete()
                            message_deleted = True
                        except:
                            pass
                        break
                    except Exception as send_error:
                        logger.error(f"Error sending image: {send_error}")
                        # Try as document if photo fails
                        try:
                            await bot.send_document(
                                chat_id=message.chat.id,
                                document=FSInputFile(filepath),
                                caption=f"{caption}\nСкачано через @{me.username}"
                            )
                            media_found = True
                            await shortcuts.add_to_analitic_data(me.username, url)
                            try:
                                await progress_msg.delete()
                                message_deleted = True
                            except:
                                pass
                            break
                        except Exception as doc_error:
                            logger.error(f"Error sending as document: {doc_error}")
                    finally:
                        try:
                            if os.path.exists(filepath):
                                os.remove(filepath)
                        except:
                            pass

            # Clean up all related files
            for f in glob.glob(f"{output_file}*"):
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except:
                    pass

            # Clean up cookies file if it exists
            cookies_file = os.path.join(temp_dir, f"cookies_{request_id}.txt")
            try:
                if os.path.exists(cookies_file):
                    os.remove(cookies_file)
            except:
                pass

            if media_found:
                return

        except Exception as e:
            logger.error(f"Approach 3 error: {e}")

        # If all approaches failed, try one final direct API request for thumbnails
        try:
            await safe_edit_message(progress_msg, "🔍 Использую запасной метод...")

            import re
            import aiohttp

            # Extract shortcode
            match = re.search(r'/(p|reel)/([^/]+)', url)
            if match:
                shortcode = match.group(2)
                post_type = match.group(1)

                # Try OEmbed API - works well for thumbnails
                oembed_url = f"https://api.instagram.com/oembed/?url=https://www.instagram.com/{post_type}/{shortcode}/"

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json",
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(oembed_url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()

                                if 'thumbnail_url' in data:
                                    thumbnail_url = data['thumbnail_url']
                                    logger.info(f"Found thumbnail URL via OEmbed: {thumbnail_url}")

                                    caption = "🎞 Instagram превью видео" if is_reel else "🖼 Instagram фото"

                                    try:
                                        await bot.send_photo(
                                            chat_id=message.chat.id,
                                            photo=thumbnail_url,
                                            caption=f"{caption}\nСкачано через @{me.username}"
                                        )
                                        await shortcuts.add_to_analitic_data(me.username, url)
                                        try:
                                            await progress_msg.delete()
                                            message_deleted = True
                                        except:
                                            pass
                                        return
                                    except Exception as photo_err:
                                        logger.error(f"Error sending image: {photo_err}")
                            except Exception as json_error:
                                logger.error(f"JSON parsing error: {json_error}")
        except Exception as e:
            logger.error(f"Final fallback method error: {e}")

        # If all approaches failed, send error message
        if not message_deleted:
            try:
                await progress_msg.delete()
                message_deleted = True
            except:
                pass

        await message.answer(
            "❌ Не удалось загрузить медиа из Instagram. Instagram часто блокирует подобные загрузки. Попробуйте другой пост или позже.")

    except Exception as e:
        logger.error(f"Instagram handler error: {e}")
        if not message_deleted:
            try:
                await progress_msg.delete()
            except:
                pass

        await message.answer("❌ Ошибка при скачивании из Instagram. Возможно, пост приватный или удалён.")


async def send_instagram_files(message, directory, files, me, bot):
    """Helper function to send downloaded Instagram files"""
    sent_count = 0
    media_files = []

    # Логируем все найденные файлы для отладки
    logger.info(f"Files in directory {directory}: {files}")

    # Проверяем, содержит ли имя директории "reel" - это поможет нам определить, что это видео
    is_reel = "reel" in directory.lower() or any("reel" in f.lower() for f in files)
    logger.info(f"Is this a reel? {is_reel}")

    # First sort files to ensure correct order and filter unwanted files
    for f in sorted(files):
        filepath = os.path.join(directory, f)
        if not os.path.isfile(filepath):
            continue

        # Skip small files and metadata files
        filesize = os.path.getsize(filepath)
        if filesize < 1000 or '.json' in f or '.txt' in f:
            continue

        # Determine file type by extension
        ext = os.path.splitext(f)[1].lower()

        # Determine if this is a video by file extension
        if ext in ['.mp4', '.mov', '.webm']:
            media_type = 'video'
        elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
            # If we know this is a reel but file is an image, it's a thumbnail
            media_type = 'thumbnail' if is_reel else 'photo'
        else:
            # Log unusual extensions for analysis
            logger.info(f"Unusual file extension found: {ext} in file {f}")
            continue

        media_files.append((filepath, media_type))

    # Then send files
    total_files = len(media_files)
    logger.info(f"Found {total_files} media files in directory {directory}")

    for i, (filepath, media_type) in enumerate(media_files):
        try:
            logger.info(f"Sending file {i + 1}/{total_files}: {filepath} as {media_type}")

            if media_type == 'video':
                try:
                    await bot.send_video(
                        chat_id=message.chat.id,
                        video=FSInputFile(filepath),
                        caption=f"📹 Instagram видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                    )
                    sent_count += 1
                except Exception as video_error:
                    logger.error(f"Error sending as video, trying as document: {video_error}")
                    await bot.send_document(
                        chat_id=message.chat.id,
                        document=FSInputFile(filepath),
                        caption=f"📹 Instagram видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                    )
                    sent_count += 1
            elif media_type == 'thumbnail':
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=FSInputFile(filepath),
                    caption=f"🎞 Instagram превью видео {i + 1}/{total_files}\nСкачано через @{me.username}"
                )
                sent_count += 1
            else:  # photo
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=FSInputFile(filepath),
                    caption=f"🖼 Instagram фото {i + 1}/{total_files}\nСкачано через @{me.username}"
                )
                sent_count += 1

            # Add small delay between posts
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error sending file {filepath}: {e}")

            # Try alternate method if primary fails
            try:
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=FSInputFile(filepath),
                    caption=f"📄 Instagram медиа {i + 1}/{total_files}\nСкачано через @{me.username}"
                )
                sent_count += 1
            except Exception as fallback_error:
                logger.error(f"Fallback error for file {filepath}: {fallback_error}")

    return sent_count > 0


async def download_and_send_video(message: Message, url: str, ydl_opts: dict, me, bot: Bot, platform: str,state: FSMContext):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)

            if os.path.exists(video_path):
                try:
                    video = FSInputFile(video_path)
                    await bot.send_video(
                        chat_id=message.chat.id,
                        video=video,
                        caption=f"📹 {info.get('title', 'Video')} (Низкое качество)\nСкачано через @{me.username}",
                        supports_streaming=True
                    )
                    await state.set_state(Download.download)
                finally:
                    # Всегда удаляем файл после отправки
                    if os.path.exists(video_path):
                        os.remove(video_path)
            else:
                raise FileNotFoundError("Downloaded video file not found")

    except Exception as e:
        logger.error(f"Error downloading and sending video from {platform}: {e}")
        await message.answer(f"❌ Не удалось скачать видео из {platform}")


async def handle_tiktok(message: Message, url: str, me, bot: Bot,state: FSMContext):
    try:
        ydl_opts = {
            'format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 40000000,
        }

        if '?' in url:
            url = url.split('?')[0]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Получаем информацию о видео без скачивания
                info = ydl.extract_info(url, download=False)
                if info and 'url' in info:
                    try:
                        await bot.send_video(
                            chat_id=message.chat.id,
                            video=info['url'],
                            caption=f"📹 TikTok video\nСкачано через @{me.username}",
                        )
                        await state.set_state(Download.download)
                        await shortcuts.add_to_analitic_data(me.username, url)
                        return
                    except Exception:

                        await download_and_send_video(message, url, ydl_opts, me, bot, "TikTok",state)
                else:
                    await message.answer("❌ Не удалось получить ссылку на видео")

            except Exception as e:
                logger.error(f"TikTok processing error: {e}")
                await message.answer("❌ Ошибка при скачивании из TikTok")

    except Exception as e:
        logger.error(f"TikTok handler error: {e}")
        await message.answer("❌ Ошибка при обработке TikTok видео")
