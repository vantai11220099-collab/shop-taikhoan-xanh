import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']

app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
application = Application.builder().token(TOKEN).updater(None).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot sống rồi 💸 Gõ /nap để lấy STK")

loop.run_until_complete(application.initialize())
application.add_handler(CommandHandler("start", start))

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    loop.run_until_complete(application.process_update(update))
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
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
