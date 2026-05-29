import os
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

TOKEN = os.environ["TOKEN"]
PORT = int(os.environ.get("PORT", 8000))

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    WEBHOOK_URL = os.environ["WEBHOOK_URL"]
    logger.info(f"Starting webhook on port {PORT}")
    logger.info(f"Setting webhook to: {WEBHOOK_URL}/webhook")

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
