import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
import yt_dlp
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Настройки для скачивания аудио с SoundCloud в MP3 с тегами (для профиля TG)
YDL_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }, {
        'key': 'FFmpegMetadata',
    }],
}

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer(
        "Привет! Напиши название трека или исполнителя из SoundCloud.\n"
        "Я пришлю аудиофайл — просто нажми на него и выбери «Добавить в профиль»."
    )

@dp.message(F.text)
async def search_and_send(message: types.Message):
    query = message.text.strip()
    status_msg = await message.answer(f"🔎 Ищу «{query}» на SoundCloud...")

    os.makedirs("downloads", exist_ok=True)
    
    try:
        # Ищем первый трек на SoundCloud через scsearch1:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, download_track, query)
        
        if not info:
            await status_msg.edit_text("❌ Ничего не найдено на SoundCloud.")
            return

        file_path = info['filepath']
        title = info.get('track') or info.get('title', 'Unknown')
        performer = info.get('artist') or info.get('uploader', 'SoundCloud')

        await status_msg.edit_text("📤 Загружаю трек в Telegram...")
        
        audio_file = FSInputFile(file_path)
        await message.answer_audio(
            audio=audio_file,
            title=title,
            performer=performer,
            caption="Нажми на трек -> «Добавить в профиль» 🎵"
        )
        await status_msg.delete()

        # Удаляем файл с сервера после отправки
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        logging.error(e)
        await status_msg.edit_text("⚠️ Ошибка при скачивании трека. Попробуй другой запрос.")

def download_track(query: str):
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        search_result = ydl.extract_info(f"scsearch1:{query}", download=True)
        if 'entries' in search_result and len(search_result['entries']) > 0:
            entry = search_result['entries'][0]
            filename = ydl.prepare_filename(entry)
            mp3_path = os.path.splitext(filename)[0] + ".mp3"
            entry['filepath'] = mp3_path
            return entry
    return None

# Мини веб-сервер, чтобы бесплатный хостинг (Render) не усыплял бота
async def health_check(request):
    return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
