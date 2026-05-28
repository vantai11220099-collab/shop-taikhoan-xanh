import os, asyncio, sqlite3
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']
ADMIN_ID = 8718318418 # Thay user_id Telegram của bạn

app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
application = Application.builder().token(TOKEN).updater(None).build()

# Tạo DB nếu chưa có
conn = sqlite3.connect('shop.db', check_same_thread=False)
conn.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = conn.execute("SELECT id, name, price FROM products")
    products = cur.fetchall()

    keyboard = []
    for pid, name, price in products:
        keyboard.append([InlineKeyboardButton(f"{name} - {price}k", callback_data=f'buy_{pid}')])
    keyboard.append([InlineKeyboardButton("💰 Nạp tiền", callback_data='nap_tien')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🎉 BT SHOP 🎉\n\n👇 DANH SÁCH TÀI KHOẢN HIỆN CÓ:"
    await update.message.reply_text(text, reply_markup=reply_markup)

# LỆNH ADMIN: /add Tên_sản_phẩm Giá
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        return await update.message.reply_text("Bạn không phải admin")
    try:
        price = int(context.args[-1])
        name = " ".join(context.args[:-1])
        conn.execute("INSERT INTO products (name, price) VALUES (?,?)", (name, price))
        conn.commit()
        await update.message.reply_text(f"Đã thêm: {name} - {price}k")
    except:
        await update.message.reply_text("Sai cú pháp: /add Netflix 1 tháng 45")

# LỆNH ADMIN: /del 1
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    pid = int(context.args[0])
    conn.execute("DELETE FROM products WHERE id =?", (pid,))
    conn.commit()
    await update.message.reply_text(f"Đã xóa sản phẩm ID {pid}")

# LỆNH ADMIN: /list
async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    cur = conn.execute("SELECT id, name, price FROM products")
    text = "Danh sách SP:\n"
    for pid, name, price in cur.fetchall():
        text += f"ID {pid}: {name} - {price}k\n"
    await update.message.reply_text(text)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'nap_tien':
        await query.edit_message_text("Gõ /nap để lấy STK")
    elif query.data.startswith('buy_'):
        await query.edit_message_text("Gõ /nap nạp tiền trước rồi ib admin nha")

loop.run_until_complete(application.initialize())
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add))
application.add_handler(CommandHandler("del", delete))
application.add_handler(CommandHandler("list", list_products))
application.add_handler(CallbackQueryHandler(button))

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    loop.run_until_complete(application.process_update(update))
    return 'ok'

if __name__ == '__main__':
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
