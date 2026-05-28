import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio

TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']

app = Flask(__name__)
bot = Bot(token=TOKEN)

# Quan trọng: updater=None để tắt polling
application = Application.builder().token(TOKEN).updater(None).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot webhook sống rồi 💸")

application.add_handler(CommandHandler("start", start))

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(application.process_update(update))
    return 'ok'

@app.route('/')
def home():
    return 'Bot is running'

@app.route('/casso', methods=['POST'])
def casso():
    print("Casso:", request.json)
    return 'ok'

# Set webhook khi start
async def setup():
    await bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    await application.initialize()

if __name__ == '__main__':
    asyncio.run(setup())
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
