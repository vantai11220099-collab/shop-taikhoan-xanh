import os, asyncio, sqlite3, re
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']
ADMIN_ID =  8718318418  # Thay ID admin của bạn
STK = "106886640236" # Thay STK
BANK = "Vietinbank" # Thay bank
TEN_CTK = ""PHAM VAN TAI" # Thay tên
SUPPORT_URL = "https://t.me/btshopmmo" # Link tele hỗ trợ

app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
application = Application.builder().token(TOKEN).updater(None).build()

# DB
conn = sqlite3.connect('shop.db', check_same_thread=False)
conn.execute('''CREATE TABLE IF NOT EXISTS products
                (id INTEGER PRIMARY KEY, name TEXT, price INTEGER, stock TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS users
                (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
conn.execute('''CREATE TABLE IF NOT EXISTS orders
                (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, time TEXT)''')
conn.commit()

def get_balance(user_id):
    cur = conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row: return row[0]
    conn.execute("INSERT INTO users VALUES (?,0)", (user_id,))
    conn.commit()
    return 0

def add_balance(user_id, amount):
    get_balance(user_id)
    conn.execute("UPDATE users SET balance = balance +? WHERE user_id=?", (amount, user_id))
    conn.commit()

def get_product(pid):
    cur = conn.execute("SELECT name, price, stock FROM products WHERE id=?", (pid,))
    return cur.fetchone()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = get_balance(user_id)
    cur = conn.execute("SELECT id, name, price FROM products WHERE stock!= ''")
    products = cur.fetchall()

    keyboard = []
    row = []
    for i, (pid, name, price) in enumerate(products):
        icon = "🎬" if "netflix" in name.lower() else "🎵" if "spotify" in name.lower() else "📺" if "youtube" in name.lower() else "⭐"
        btn = InlineKeyboardButton(f"{icon} {name} {price}k", callback_data=f'buy_{pid}')
        row.append(btn)
        if len(row) == 3 or i == len(products) - 1:
            keyboard.append(row)
            row = []

    keyboard.append([
        InlineKeyboardButton("💰 Nạp tiền", callback_data='nap_tien'),
        InlineKeyboardButton("👛 Số dư", callback_data='sodu'),
        InlineKeyboardButton("🆘 Hỗ trợ", url=SUPPORT_URL)
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"🎉 **BT SHOP** 🎉\n\n👤 {update.effective_user.first_name}\n💵 Số dư: `{bal:,}đ`\n\n👇 **CHỌN DỊCH VỤ:**"
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    noidung = f"BT{user_id}"
    text = f"""💸 **NẠP TIỀN TỰ ĐỘNG**

Ngân hàng: `{BANK}`
Số TK: `{STK}`
Chủ TK: `{TEN_CTK}`
Nội dung: `{noidung}`

⚠️ CHUYỂN ĐÚNG NỘI DUNG ĐỂ AUTO + TIỀN"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def sodu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = get_balance(update.effective_user.id)
    await update.message.reply_text(f"👛 Số dư: `{bal:,}đ`", parse_mode='Markdown')

async def mua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        pid = int(context.args[0])
        product = get_product(pid)
        if not product: return await update.message.reply_text("❌ ID sản phẩm không tồn tại")
        name, price, stock = product
        bal = get_balance(user_id)

        if bal < price: return await update.message.reply_text(f"❌ Không đủ tiền\nCần: {price:,}đ | Có: {bal:,}đ\nGõ /nap để nạp")
        if not stock: return await update.message.reply_text("❌ Hết hàng")

        conn.execute("UPDATE users SET balance = balance -? WHERE user_id=?", (price, user_id))
        conn.execute("UPDATE products SET stock =? WHERE id=?", ('', pid))
        conn.execute("INSERT INTO orders (user_id, product_id, time) VALUES (?,?,datetime('now'))", (user_id, pid))
        conn.commit()

        new_bal = get_balance(user_id)
        await update.message.reply_text(f"✅ **MUA THÀNH CÔNG**\n\n📦 SP: {name}\n🔑 TK: `{stock}`\n💵 Dư: {new_bal:,}đ", parse_mode='Markdown')
        await context.bot.send_message(ADMIN_ID, f"🔔 Đơn mới\nUser: {user_id}\nSP: {name}\nGiá: {price:,}đ")
    except:
        await update.message.reply_text("Cú pháp: `/mua 1`\nGõ /start xem ID", parse_mode='Markdown')

async def add_tk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        text = " ".join(context.args)
        parts = text.split('|')
        stock = parts[1].strip()
        name_price = parts[0].strip().split()
        price = int(name_price[-1])
        name = " ".join(name_price[:-1])
        conn.execute("INSERT INTO products (name, price, stock) VALUES (?,?,?)", (name, price, stock))
        conn.commit()
        await update.message.reply_text(f"✅ Đã thêm: {name} - {price:,}đ")
    except:
        await update.message.reply_text("Cú pháp: `/add_tk Netflix 1 tháng 45 acc@gmail.com|pass123`", parse_mode='Markdown')

async def cong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        add_balance(user_id, amount)
        new_bal = get_balance(user_id)
        await update.message.reply_text(f"✅ Đã cộng {amount:,}đ cho {user_id}\nDư: {new_bal:,}đ")
        await context.bot.send_message(user_id, f"🎉 Admin vừa cộng {amount:,}đ!\nSố dư: {new_bal:,}đ")
    except:
        await update.message.reply_text("Cú pháp: `/cong 123456789 50000`", parse_mode='Markdown')

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'nap_tien':
        await nap(query, context)
    elif query.data == 'sodu':
        bal = get_balance(user_id)
        await query.edit_message_text(f"👛 Số dư: `{bal:,}đ`", parse_mode='Markdown')
    elif query.data.startswith('buy_'):
        pid = int(query.data.split('_')[1])
        product = get_product(pid)
        if product:
            await query.edit_message_text(f"📦 **{product[0]}**\n💰 Giá: `{product[1]:,}đ`\n\nGõ `/mua {pid}` để mua ngay", parse_mode='Markdown')

loop.run_until_complete(application.initialize())
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("nap", nap))
application.add_handler(CommandHandler("sodu", sodu))
application.add_handler(CommandHandler("mua", mua))
application.add_handler(CommandHandler("add_tk", add_tk))
application.add_handler(CommandHandler("cong", cong))
application.add_handler(CallbackQueryHandler(button))

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    loop.run_until_complete(application.process_update(update))
    return 'ok'

@app.route('/casso', methods=['POST'])
def casso():
    data = request.json['data'][0]
    amount = data['amount']
    desc = data['description']
    match = re.search(r'BT(\d+)', desc)
    if match:
        user_id = int(match.group(1))
        add_balance(user_id, amount)
        new_bal = get_balance(user_id)
        loop.run_until_complete(application.bot.send_message(user_id, f"✅ Nạp thành công {amount:,}đ\nSố dư: {new_bal:,}đ"))
        loop.run_until_complete(application.bot.send_message(ADMIN_ID, f"💰 {user_id} vừa nạp {amount:,}đ"))
    return 'ok'

@app.route('/')
def home():
    return 'Bot BT Shop đang chạy'

if __name__ == '__main__':
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
