import os, asyncio, sqlite3, re, random, string
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ==== CONFIG ==== Thay 6 dòng này
TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']
ADMIN_ID = 871849512 # ID admin từ @userinfobot
STK = "106886640236" # STK ngân hàng
BANK = "VietinBank" # Tên bank
BANK_CODE = "VTB" # Code bank: mb, vcb, tpb, tcb, acb
TEN_CTK = "PHAM VAN TAI" # Tên chủ TK
SUPPORT_URL = "https://t.me/btshopmmo" # Link hỗ trợ

app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
application = Application.builder().token(TOKEN).updater(None).build()

# ==== DATABASE ====
conn = sqlite3.connect('shop.db', check_same_thread=False)
conn.execute('''CREATE TABLE IF NOT EXISTS products
                (id INTEGER PRIMARY KEY, name TEXT, price INTEGER, stock TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS users
                (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
conn.execute('''CREATE TABLE IF NOT EXISTS orders
                (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, time TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS trans
                (code TEXT PRIMARY KEY, user_id INTEGER, amount INTEGER, status TEXT)''')
conn.commit()

def random_code():
    return 'BT' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

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

# ==== USER ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = get_balance(user_id)
    cur = conn.execute("SELECT id, name, price FROM products WHERE stock!= ''")
    products = cur.fetchall()

    keyboard, row = [], []
    for i, (pid, name, price) in enumerate(products):
        icon = "🎬" if "netflix" in name.lower() else "🎵" if "spotify" in name.lower() else "📺" if "youtube" in name.lower() else "🎨" if "canva" in name.lower() else "⭐"
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
    code = random_code()
    conn.execute("INSERT INTO trans (code, user_id, status) VALUES (?,?,?)", (code, user_id, 'pending'))
    conn.commit()

    # QR VietQR - Tự điền nội dung
    qr_url = f"https://img.vietqr.io/image/{BANK_CODE}-{STK}-compact2.png?amount=&addInfo={code}&accountName={TEN_CTK}"

    text = f"""💸 **NẠP TIỀN TỰ ĐỘNG**

Ngân hàng: `{BANK}`
Số TK: `{STK}`
Chủ TK: `{TEN_CTK}`
Nội dung: `{code}`

⚠️ MÃ CHỈ DÙNG 1 LẦN
👇 Quét QR chuyển nhanh"""

    await update.message.reply_photo(photo=qr_url, caption=text, parse_mode='Markdown')

async def sodu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = get_balance(update.effective_user.id)
    await update.message.reply_text(f"👛 Số dư: `{bal:,}đ`", parse_mode='Markdown')

# ==== ADMIN ====
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
        await update.message.reply_text("Cú pháp: `/add_tk Netflix 1 tháng 45 acc|pass`", parse_mode='Markdown')

async def cong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
        add_balance(user_id, amount)
        new_bal = get_balance(user_id)
        await update.message.reply_text(f"✅ Đã cộng {amount:,}đ cho {user_id}\nDư: {new_bal:,}đ")
        await context.bot.send_message(user_id, f"🎉 Admin cộng {amount:,}đ!\nSố dư: {new_bal:,}đ")
    except:
        await update.message.reply_text("Cú pháp: `/cong 123456789 50000`")

async def list_sp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    cur = conn.execute("SELECT id, name, price, stock FROM products")
    text = "**DANH SÁCH SP:**\n\n"
    for pid, name, price, stock in cur.fetchall():
        status = "✅" if stock else "❌"
        text += f"`{pid}`: {name} - {price:,}đ {status}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def xoa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        pid = int(context.args[0])
        conn.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
        await update.message.reply_text(f"✅ Đã xóa SP ID {pid}")
    except:
        await update.message.reply_text("Cú pháp: `/xoa 1`")

# ==== BUTTON HANDLER - MUA 1 CHẠM ====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'nap_tien':
        await nap(query, context)
    elif query.data == 'sodu':
        bal = get_balance(user_id)
        await query.edit_message_text(f"👛 Số dư: `{bal:,}đ`\n\nGõ /start về menu", parse_mode='Markdown')
    elif query.data.startswith('buy_'):
        pid = int(query.data.split('_')[1])
        product = get_product(pid)
        if not product: return await query.edit_message_text("❌ Sản phẩm đã hết hàng")

        name, price, stock = product
        bal = get_balance(user_id)

        if bal < price:
            return await query.edit_message_text(f"❌ **KHÔNG ĐỦ SỐ DƯ**\n\nSP: {name}\nGiá: `{price:,}đ`\nCó: `{bal:,}đ`\n\n👉 Bấm /nap để nạp", parse_mode='Markdown')

        if not stock: return await query.edit_message_text("❌ Hết hàng rồi bro")

        conn.execute("UPDATE users SET balance = balance -? WHERE user_id=?", (price, user_id))
        conn.execute("UPDATE products SET stock =? WHERE id=?", ('', pid))
        conn.execute("INSERT INTO orders (user_id, product_id, time) VALUES (?,?,datetime('now'))", (user_id, pid))
        conn.commit()

        new_bal = get_balance(user_id)
        await query.edit_message_text(f"✅ **MUA THÀNH CÔNG**\n\n📦 SP: {name}\n🔑 TK: `{stock}`\n💵 Dư: `{new_bal:,}đ`", parse_mode='Markdown')
        await context.bot.send_message(ADMIN_ID, f"🔔 Đơn mới\nUser: `{user_id}` @{query.from_user.username}\nSP: {name}\nGiá: {price:,}đ")

# ==== ROUTES ====
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    loop.run_until_complete(application.process_update(update))
    return 'ok'

@app.route('/casso', methods=['POST'])
def casso():
    data = request.json['data'][0]
    amount = data['amount']
    desc = data['description'].upper()
    match = re.search(r'BT[A-Z0-9]{6}', desc)
    if not match: return 'ok'

    code = match.group(0)
    cur = conn.execute("SELECT user_id, status FROM trans WHERE code=?", (code,))
    row = cur.fetchone()
    if not row or row[1] == 'done': return 'ok'

    user_id = row[0]
    add_balance(user_id, amount)
    conn.execute("UPDATE trans SET status='done', amount=? WHERE code=?", (amount, code))
    conn.commit()

    new_bal = get_balance(user_id)
    loop.run_until_complete(application.bot.send_message(user_id, f"✅ Nạp thành công {amount:,}đ\nMã: `{code}`\nDư: {new_bal:,}đ", parse_mode='Markdown'))
    loop.run_until_complete(application.bot.send_message(ADMIN_ID, f"💰 {user_id} nạp {amount:,}đ\nMã: {code}"))
    return 'ok'

@app.route('/')
def home(): return 'BT Shop Bot đang chạy'

# ==== RUN ====
loop.run_until_complete(application.initialize())
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("nap", nap))
application.add_handler(CommandHandler("sodu", sodu))
application.add_handler(CommandHandler("add_tk", add_tk))
application.add_handler(CommandHandler("cong", cong))
application.add_handler(CommandHandler("list", list_sp))
application.add_handler(CommandHandler("xoa", xoa))
application.add_handler(CallbackQueryHandler(button))

if __name__ == '__main__':
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
