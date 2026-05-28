import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']

app = Flask(__name__)
application = Application.builder().token(TOKEN).updater(None).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot webhook sống rồi 💸 Gõ /nap để lấy STK")

application.add_handler(CommandHandler("start", start))

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        asyncio.run(application.process_update(
            Update.de_json(request.get_json(force=True), application.bot)
        ))
    except Exception as e:
        print(f"Lỗi webhook: {e}")
    return 'ok'

@app.route('/')
def home():
    return 'Bot đang chạy'

@app.route('/casso', methods=['POST'])
def casso():
    print("Casso:", request.json)
    return 'ok'

if __name__ == '__main__':
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get('PORT', 8080)),
        webhook_url=f"{WEBHOOK_URL}/webhook"
    )
