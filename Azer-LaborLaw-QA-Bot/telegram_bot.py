import os
import asyncio
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Mövcud Sual-Cavab sistemini import edirik
from qa_system import QASystem

# Logging (xətaları görmək üçün)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# .env faylından tokenləri yükləyirik
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Sual-Cavab sistemini yalnız bir dəfə, bot işə düşəndə yükləyirik.
# Bu, hər mesajda modeli yenidən yükləməyin qarşısını alır və performansı artırır.
print("Sual-Cavab sistemi yüklənir...")
qa_bot = QASystem(index_path='law_embeddings.faiss', chunks_path='chunks_for_retrieval.pkl')
print("Sual-Cavab sistemi uğurla yükləndi. Bot işə salınır...")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start əmri göndərildikdə bu funksiya işə düşür."""
    user = update.effective_user
    await update.message.reply_html(
        f"Salam, {user.mention_html()}!\n\nMən Azərbaycan Respublikasının Əmək Məcəlləsi üzrə köməkçinizəm. Mənə sualınızı yazın, mən Məcəlləyə əsasən cavablandırım.",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help əmri göndərildikdə bu funksiya işə düşür."""
    await update.message.reply_text(
        "Sadəcə sualınızı mətn şəklində göndərin. Məsələn:\n"
        "• Minimum məzuniyyət müddəti neçə gündür?\n"
        "• Sınaq müddəti nə qədər ola bilər?\n"
        "• Əmək müqaviləsinə hansı halda xitam verilə bilər?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """İstifadəçidən gələn mətn mesajlarını emal edir."""
    user_question = update.message.text

    # İstifadəçiyə gözləmə mesajı göndəririk
    processing_message = await update.message.reply_text(
        "Sualınız emal olunur, zəhmət olmasa bir neçə saniyə gözləyin...")

    try:
        # QASystem sinfinin answer_question metodu sinxron olduğu üçün
        # onu asinxron mühitdə bloklamadan işlətmək üçün asyncio.to_thread istifadə edirik.
        answer = await asyncio.to_thread(qa_bot.answer_question, user_question)

        # Gözləmə mesajını silib, yekun cavabı göndəririk
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)
        await update.message.reply_text(answer, parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Xəta baş verdi: {e}")
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_message.message_id)
        await update.message.reply_text(
            "Üzr istəyirəm, cavab hazırlanarkən bir xəta baş verdi. Zəhmət olmasa bir az sonra yenidən cəhd edin.")


def main() -> None:
    """Telegram botunu başladır."""
    if not TELEGRAM_BOT_TOKEN:
        logging.error("Telegram bot tokeni tapılmadı! .env faylını yoxlayın.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Müxtəlif əmrlər üçün handler-lər əlavə edirik
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Mətn mesajları üçün handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Botu işə salırıq
    application.run_polling()


if __name__ == '__main__':
    main()