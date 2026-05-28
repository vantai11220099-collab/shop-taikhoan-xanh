import os, sqlite3, re, random, string, sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from aiohttp import web

print("1. Import xong", flush=True)

try:
    TOKEN = os.environ['BOT_TOKEN']
    WEBHOOK_URL = os.environ['WEBHOOK_URL']
    print("2. Đọc ENV xong", flush=True)
except Exception as e:
    print(f"LỖI ENV: {e}", flush=True)
    sys.exit(1)

ADMIN_ID = 8718318418
STK = "106886640236"
BANK = "VietinBank"
BANK_CODE = "icb"
TEN_CTK = "PHAM VAN TAI"
SUPPORT_URL = "https://t.me/btshopmmo"
PORT = int(os.environ.get('PORT', 8080))

print("3. Bắt đầu tạo DB", flush=True)
conn = sqlite3.connect('/tmp/shop.db', check_same_thread=False)
conn.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER, stock TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
conn.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, time TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS trans (code TEXT PRIMARY KEY, user_id INTEGER, amount INTEGER, status TEXT)''')
conn.commit()
print("4. Tạo DB xong", flush=True)

def random_code(): return 'BT' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
def get_balance(user_id):
    cur = conn.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row: return row[0]
    conn.execute("INSERT INTO users VALUES (?,0)", (user_id,)); conn.commit(); return 0
def add_balance(user_id, amount): get_balance(user_id); conn.execute("UPDATE users SET balance = balance +? WHERE user_id=?", (amount, user_id)); conn.commit()
def get_product(pid): cur = conn.execute("SELECT name, price, stock FROM products WHERE id=?", (pid,)); return cur.fetchone()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id; bal = get_balance(user_id)
    cur = conn.execute("SELECT id, name, price FROM products WHERE stock!= ''"); products = cur.fetchall()
    keyboard, row = [], []
    for i, (pid, name, price) in enumerate(products):
        icon = "🎬" if "netflix" in name.lower() else "🎵" if "spotify" in name.lower() else "📺" if "youtube" in name.lower() else "⭐"
        btn = InlineKeyboardButton(f"{icon} {name} {price}k", callback_data=f'buy_{pid}'); row.append(btn)
        if len(row) == 3 or i == len(products) - 1: keyboard.append(row); row = []
    keyboard.append([InlineKeyboardButton("💰 Nạp tiền", callback_data='nap_tien'), InlineKeyboardButton("👛 Số dư", callback_data='sodu'), InlineKeyboardButton("🆘 Hỗ trợ", url=SUPPORT_URL)])
    await update.message.reply_text(f"🎉 **BT SHOP** 🎉\n\n👤 {update.effective_user.first_name}\n💵 Số dư: `{bal:,}đ`\n\n👇 **CHỌN DỊCH VỤ:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def kho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        return await update.message.reply_text("❌ Bạn không phải admin")
    cur = conn.execute("SELECT id, name, price, stock FROM products")
    rows = cur.fetchall()
    if not rows:
        return await update.message.reply_text("📦 Kho trống")
    text = "**📦 KHO HÀNG**\n\n"
    for pid, name, price, stock in rows:
        text += f"ID `{pid}` - {name} - `{price}k`\nStock: `{stock if stock else 'HẾT'}`\n\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def cong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        return await update.message.reply_text("❌ Bạn không phải admin")
    try:
        uid = int(context.args[0]); amount = int(context.args[1])
        add_balance(uid, amount)
        await update.message.reply_text(f"✅ Đã cộng {amount:,}đ cho `{uid}`\nDư mới: `{get_balance(uid):,}đ`", parse_mode='Markdown')
    except:
        await update.message.reply_text("Dùng: `/cong UserID SốTiền`\nVD: `/cong 123456 100000`", parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        return await update.message.reply_text("❌ Bạn không phải admin")
    cur = conn.execute("SELECT COUNT(*), SUM(price) FROM orders JOIN products ON orders.product_id = products.id WHERE products.id IS NOT NULL")
    total_don, doanh_thu = cur.fetchone()
    cur = conn.execute("SELECT COUNT(*) FROM users")
    total_user = cur.fetchone()[0]
    text = f"📊 **THỐNG KÊ**\n\n👥 User: `{total_user}`\n📦 Đơn: `{total_don or 0}`\n💰 Doanh thu: `{(doanh_thu or 0):,}đ`"
    await update.message.reply_text(text, parse_mode='Markdown')

async def sodu(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text(f"👛 Số dư: `{get_balance(update.effective_user.id):,}đ`", parse_mode='Markdown')

async def add_tk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        text = " ".join(context.args); parts = text.split('|'); stock = parts[1].strip()
        name_price = parts[0].strip().split(); price = int(name_price[-1]); name = " ".join(name_price[:-1])
        conn.execute("INSERT INTO products (name, price, stock) VALUES (?,?,?)", (name, price, stock)); conn.commit()
        await update.message.reply_text(f"✅ Đã thêm: {name} - {price:,}đ")
    except: await update.message.reply_text("Cú pháp: `/add_tk Netflix 1 tháng 45 acc|pass`", parse_mode='Markdown')

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); user_id = query.from_user.id
    if query.data == 'nap_tien': await nap(update, context)
    elif query.data == 'sodu': await query.edit_message_text(f"👛 Số dư: `{get_balance(user_id):,}đ`\n\nGõ /start về menu", parse_mode='Markdown')
    elif query.data.startswith('buy_'):
        pid = int(query.data.split('_')[1]); product = get_product(pid)
        if not product: return await query.edit_message_text("❌ Sản phẩm đã hết hàng")
        name, price, stock = product; bal = get_balance(user_id)
        if bal < price:
            keyboard = [[InlineKeyboardButton("💰 Nạp tiền ngay", callback_data='nap_tien')]]
            return await query.edit_message_text(f"❌ **KHÔNG ĐỦ SỐ DƯ**\n\nSP: {name}\nGiá: `{price:,}đ`\nCó: `{bal:,}đ`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        if not stock: return await query.edit_message_text("❌ Hết hàng rồi bro")
        conn.execute("UPDATE users SET balance = balance -? WHERE user_id=?", (price, user_id))
        conn.execute("UPDATE products SET stock =? WHERE id=?", ('', pid))
        conn.execute("INSERT INTO orders (user_id, product_id, time) VALUES (?,?,datetime('now'))", (user_id, pid)); conn.commit()
        await query.edit_message_text(f"✅ **MUA THÀNH CÔNG**\n\n📦 SP: {name}\n🔑 TK: `{stock}`\n💵 Dư: `{get_balance(user_id):,}đ`", parse_mode='Markdown')
        await context.bot.send_message(ADMIN_ID, f"🔔 Đơn mới\nUser: `{user_id}` @{query.from_user.username}\nSP: {name}\nGiá: {price:,}đ")

async def webhook_handler(request):
    data = await request.json()
    await application.update_queue.put(Update.de_json(data, application.bot))
    return web.Response()

async def casso_webhook(request):
    data = await request.json(); amount = data['data'][0]['amount']; desc = data['data'][0]['description'].upper()
    match = re.search(r'BT[A-Z0-9]{6}', desc)
    if not match: return web.Response(text='ok')
    code = match.group(0); cur = conn.execute("SELECT user_id, status FROM trans WHERE code=?", (code,)); row = cur.fetchone()
    if not row or row[1] == 'done': return web.Response(text='ok')
    user_id = row[0]; add_balance(user_id, amount)
    conn.execute("UPDATE trans SET status='done', amount=? WHERE code=?", (amount, code)); conn.commit()
    await application.bot.send_message(user_id, f"✅ Nạp thành công {amount:,}đ\nMã: `{code}`\nDư: `{get_balance(user_id):,}đ`", parse_mode='Markdown')
    await application.bot.send_message(ADMIN_ID, f"💰 {user_id} nạp {amount:,}đ\nMã: {code}")
    return web.Response(text='ok')

application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("sodu", sodu))
application.add_handler(CommandHandler("add_tk", add_tk))
application.add_handler(CommandHandler("kho", kho))        # Thêm dòng này
application.add_handler(CommandHandler("cong", cong))      # Thêm dòng này
application.add_handler(CommandHandler("stats", stats))    # Thêm dòng này
application.add_handler(CallbackQueryHandler(button))

async def on_startup(app):
    print("6. Startup...", flush=True)
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    print("7. Set webhook xong", flush=True)

async def on_cleanup(app):
    await application.stop()
    await application.shutdown()

app = web.Application()
app.router.add_post('/webhook', webhook_handler)
app.router.add_post('/casso', casso_webhook)
app.router.add_get('/', lambda r: web.Response(text='Bot running'))
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == '__main__':
    print("8. Chạy web.run_app", flush=True)
    web.run_app(app, port=PORT)
