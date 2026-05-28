import os
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get('BOT_TOKEN')
CASSO_API_KEY = os.environ.get('CASSO_API_KEY')
PORT = int(os.environ.get('PORT', 5000))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

app = Flask(__name__)
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).updater(None).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot webhook đã chạy! Test Casso đi bro 💸")

application.add_handler(CommandHandler("start", start))

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(application.process_update(update))
    return 'ok'

@app.route('/casso', methods=['POST']) 
def casso_webhook():
    data = request.json
    print("Casso báo tiền về:", data)
    return 'ok'

@app.route('/')
def index():
    return 'Bot is running'

async def setup():
    await bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    await application.initialize()
    await application.start()

if __name__ == '__main__':
    asyncio.run(setup())
    app.run(host='0.0.0.0', port=PORT)
