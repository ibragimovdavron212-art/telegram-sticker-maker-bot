import asyncio
import os
import signal
import sys
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from contextlib import suppress

from config import BOT_TOKEN, SUPPORTED_IMAGE_FORMATS, SUPPORTED_VIDEO_FORMATS
from keyboards import get_start_keyboard, get_processing_keyboard
from utils.media_processor import MediaProcessor
from utils.logger import setup_logger


logger = setup_logger()
TEMP_FILES = set()


class UserState(StatesGroup):
    choosing_type = State()
    processing_sticker = State()
    processing_emoji = State()


bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot ishlayapti!")

    def log_message(self, format, *args):
        return


def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), DummyServer)
    server.serve_forever()


def cleanup_temp_files():
    for file_path in TEMP_FILES:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Error removing temp file {file_path}: {e}")
    TEMP_FILES.clear()


async def shutdown(dispatcher: Dispatcher):
    logger.info("Bot shutdown...")
    cleanup_temp_files()
    await dispatcher.storage.close()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    logger.info("Bot successfully stopped")


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(UserState.choosing_type)
    await message.answer(
        "Welcome! Choose what you want to create:",
        reply_markup=get_start_keyboard()
    )


# ... qolgan bot kodlari ...

async def main():
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        asyncio.create_task(shutdown(dp))
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        logger.info("The bot is running. To stop, press Ctrl+C")
        await dp.start_polling(bot)
    finally:
        await shutdown(dp)


if __name__ == "__main__":
    threading.Thread(target=run_dummy_server, daemon=True).start()
    asyncio.run(main()) 
