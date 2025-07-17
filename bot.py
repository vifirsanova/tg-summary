#!/usr/bin/env python3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import tomli
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError
import logging
from run_gemma import GemmaSummarizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load config
try:
    with open("config.toml", "rb") as f:
        config = tomli.load(f)
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load config.toml: {e}")
    raise

class ChatSummaryBot:
    """Telegram bot for generating chat summaries (выжимки)."""
    
    def __init__(self):
        """Initialize bot with settings from config."""
        try:
            self.bot = Bot(token=config["telegram"]["bot_token"])
            self.dp = Dispatcher()
            self.chat_messages = {}  # {chat_id: [(datetime, username, text)]}
            self.summarizer = GemmaSummarizer()
            self._setup_handlers()
            self._setup_keyboard()
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.error(f"Bot initialization failed: {e}")
            raise

    def _setup_keyboard(self):
        """Initialize period selection keyboard."""
        self.period_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="24 часа"), KeyboardButton(text="3 дня")],
                [KeyboardButton(text="1 неделя")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

    def _setup_handlers(self):
        """Register bot command handlers."""
        
        @self.dp.message(Command("start"))
        async def start_command(message: types.Message):
            """Handle /start command."""
            try:
                await message.reply(
                    "🤖 Добро пожаловать в бот для выжимок чатов!\n"
                    "Используйте /summary для получения краткой выжимки сообщений",
                    reply_markup=self.period_keyboard
                )
                logger.info(f"Start command received from {message.from_user.id}")
            except Exception as e:
                logger.error(f"Error in start_command: {e}")

        @self.dp.message(Command("summary"))
        async def summary_command(message: types.Message):
            """Handle /summary command."""
            try:
                await message.reply(
                    "⏳ Выберите период для генерации выжимки:",
                    reply_markup=self.period_keyboard
                )
                logger.info(f"Summary command received from {message.from_user.id}")
            except Exception as e:
                logger.error(f"Error in summary_command: {e}")

        @self.dp.message()
        async def handle_message(message: types.Message):
            """Handle all incoming messages."""
            try:
                if message.text in ["24 часа", "3 дня", "1 неделя"]:
                    if message.reply_to_message and "выжимки" in message.reply_to_message.text:
                        await self._process_summary_request(message)
                    return
                
                self._store_message(message)
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    def _store_message(self, message: types.Message):
        """Store message in memory for future summarization."""
        chat_id = message.chat.id
        now = datetime.utcnow()
        username = message.from_user.full_name
        text = message.text or "<сообщение без текста>"
        
        record = (now, username, text)
        self.chat_messages.setdefault(chat_id, []).append(record)
        logger.debug(f"Stored message from {username} in chat {chat_id}")

    async def _process_summary_request(self, message: types.Message):
        """Generate and send summary for requested period."""
        chat_id = message.chat.id
        period = message.text
        user_id = message.from_user.id
        
        try:
            cutoff = self._get_cutoff_time(period)
            messages = self._get_messages_for_period(chat_id, cutoff)

            if not messages:
                await message.reply("❌ Сообщений за этот период не найдено.", reply_markup=self.period_keyboard)
                logger.info(f"No messages found for {period} in chat {chat_id}")
                return

            chat_history = self._format_chat_history(messages)
            logger.info(f"Generating summary for {len(messages)} messages in chat {chat_id}")

            processing_msg = await message.reply("🔄 Генерирую выжимку... Это может занять до 30 секунд")
            
            try:
                summary = await asyncio.to_thread(
                    self.summarizer.generate_summary, 
                    chat_history
                )
                
                await processing_msg.edit_text(
                    f"📋 Выжимка чата за {period.lower()}:\n\n{summary}"
                )
                logger.info(f"Successfully delivered summary to {user_id}")
                
            except Exception as e:
                await processing_msg.edit_text(
                    "⚠️ Произошла ошибка при генерации выжимки. Пожалуйста, попробуйте позже."
                )
                logger.error(f"Summary generation failed for {user_id}: {e}")
                
        except TelegramRetryAfter as e:
            logger.warning(f"Rate limited: {e}")
            await asyncio.sleep(e.retry_after)
            await self._process_summary_request(message)
        except TelegramAPIError as e:
            logger.error(f"Telegram API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in summary processing: {e}")
            raise

    def _get_cutoff_time(self, period: str) -> datetime:
        """Calculate cutoff time based on selected period."""
        now = datetime.utcnow()
        periods = {
            "24 часа": timedelta(hours=24),
            "3 дня": timedelta(days=3),
            "1 неделя": timedelta(weeks=1)
        }
        return now - periods.get(period, timedelta(days=1))

    def _get_messages_for_period(self, chat_id: int, cutoff: datetime) -> list:
        """Filter messages for specific period."""
        messages = self.chat_messages.get(chat_id, [])
        return [m for m in messages if m[0] >= cutoff]

    def _format_chat_history(self, messages: list) -> str:
        """Format chat history for prompt."""
        return "\n".join(
            f"[{dt.strftime('%Y-%m-%d %H:%M:%S')}] {user}: {text}"
            for dt, user, text in messages
        )

    async def run(self):
        """Start the bot with error handling."""
        try:
            logger.info("Starting chat summary bot...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.critical(f"Bot crashed: {e}")
        finally:
            await self.bot.session.close()
            logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        bot = ChatSummaryBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
