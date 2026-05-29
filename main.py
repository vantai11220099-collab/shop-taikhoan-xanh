import os
import sqlite3
import logging
import urllib.parse
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ========== CONFIG ==========
TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8718318418 # <-- ID ADMIN ĐÃ FIX Ở ĐÂY
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # https://xxx.up.railway.app
PORT = int(os.getenv("PORT", 8000))

# CONFIG NGÂN HÀNG - SỬA THÔNG TIN CỦA BẠN
BANK_ID = "ICB" # VCB, TCB, MBBank, ACB...
ACCOUNT_NO = "106886640236" # STK của bạn
ACCOUNT_NAME = "PHAM VAN " # Tên chủ TK, viết hoa không dấu
CASSO_API_KEY = os.getenv("CASSO_API_KEY", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== DATABASE ==========
conn = sqlite3.connect('shop.db', check_same_thread=False)
cur = conn.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)''')

cur.execute('''CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price INTEGER,
    stock TEXT
)''')

cur.execute("INSERT OR IGNORE INTO products (id, name, price, stock) VALUES (1, 'Netflix 1 tháng', 50000, 'test1@gmail.com:123456\ntest2@gmail.com:654321')")
conn.commit()

# ========== DB FUNCTIONS ==========
def get_balance(user_id):
    cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        conn.commit()
        return 0
    return row[0]

def add_balance(user_id, amount):
    get_balance(user_id)
    cur.execute("UPDATE users SET balance = balance +? WHERE user_id=?", (amount, user_id))
    conn.commit()

def get_product(pid):
    cur.execute("SELECT id, name, price, stock FROM products WHERE id=?", (pid,))
    return cur.fetchone()

def add_stock(pid, accounts_text):
    cur.execute("SELECT stock FROM products WHERE id=?", (pid,))
    old_stock = cur.fetchone()[0] or ""
    new_stock = (old_stock + "\n" + accounts_text).strip()
    cur.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, pid))
    conn.commit()

# ========== ADMIN STATE ==========
admin_state = {}

# ========== BOT HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_balance(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("🛒 Kho hàng", callback_data='kho_hang')],
        [InlineKeyboardButton("💰 Nạp tiền", callback_data='nap_tien')],
        [InlineKeyboardButton("💵 Số dư", callback_data='sodu')]
    ]
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data='admin')])
    await update.message.reply_text("🏪 Chào mừng đến Shop!", reply_markup=InlineKeyboardMarkup(keyboard))

async def kho(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT id, name, price, stock FROM products")
    rows = cur.fetchall()
    if not rows:
        return await update.callback_query.message.reply_text("❌ Shop chưa có sản phẩm nào")
    keyboard = []
    for pid, name, price, stock in rows:
        stock_count = len([s for s in stock.split('\n') if s.strip()]) if stock else 0
        keyboard.append([InlineKeyboardButton(f"{name} - {price:,}đ | Còn: {stock_count}", callback_data=f'buy_{pid}')])
    keyboard.append([InlineKeyboardButton("🔙 Về menu", callback_data='menu')])
    await update.callback_query.message.reply_text("📦 Chọn sản phẩm:", reply_markup=InlineKeyboardMarkup(keyboard))

def gen_qr_url(amount, user_id):
    desc = f"NAP {user_id}"
    encoded_desc = urllib.parse.quote(desc)
    return f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact.png?amount={amount}&addInfo={encoded_desc}&accountName={ACCOUNT_NAME}"

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'menu':
        keyboard = [
            [InlineKeyboardButton("🛒 Kho hàng", callback_data='kho_hang')],
            [InlineKeyboardButton("💰 Nạp tiền", callback_data='nap_tien')],
            [InlineKeyboardButton("💵 Số dư", callback_data='sodu')]
        ]
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data='admin')])
        await query.message.edit_text("🏪 Menu chính:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'kho_hang':
        await kho(update, context)

    elif query.data == 'nap_tien':
        amount_list = [50000, 100000, 200000, 500000]
        keyboard = []
        for amount in amount_list:
            keyboard.append([InlineKeyboardButton(f"{amount:,}đ", callback_data=f'qr_{amount}')])
        keyboard.append([InlineKeyboardButton("💸 Nhập số khác", callback_data='qr_custom')])
        keyboard.append([InlineKeyboardButton("🔙 Về menu", callback_data='menu')])
        await query.message.reply_text("💳 **NẠP TIỀN AUTO**\n\nChọn số tiền:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'sodu':
        await query.message.reply_text(f"💰 **SỐ DƯ CỦA BẠN**\n\n`{get_balance(user_id):,}đ`", parse_mode='Markdown')

    elif query.data.startswith('qr_'):
        if query.data == 'qr_custom':
            return await query.message.reply_text("Nhập lệnh: `/nap 100000` để tạo QR 100k", parse_mode='Markdown')
        amount = int(query.data.split('_')[1])
        qr_url = gen_qr_url(amount, user_id)
        caption = f"📷 **QUÉT QR ĐỂ NẠP {amount:,}đ**\n\nSTK: `{ACCOUNT_NO}`\nNgân hàng: {BANK_ID}\nNội dung: `NAP {user_id}`\n\n⚠️ Chuyển đúng nội dung để auto cộng tiền!"
        await query.message.reply_photo(photo=qr_url, caption=caption, parse_mode='Markdown')

    elif query.data.startswith('buy_'):
        pid = int(query.data.split('_')[1])
        product = get_product(pid)
        if not product:
            return await query.message.reply_text("❌ Sản phẩm không tồn tại")

        pid, name, price, stock_text = product
        bal = get_balance(user_id)

        if not stock_text or not stock_text.strip():
            return await query.message.reply_text("❌ Hết hàng rồi bro")

        if bal < price:
            keyboard = [[InlineKeyboardButton("💰 Nạp tiền ngay", callback_data='nap_tien')]]
            return await query.message.reply_text(
                f"❌ **KHÔNG ĐỦ SỐ DƯ**\n\nSản phẩm: {name}\nGiá: `{price:,}đ`\nBạn có: `{bal:,}đ`",
                parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

        stock_list = [line.strip() for line in stock_text.split('\n') if line.strip()]
        if not stock_list:
            return await query.message.reply_text("❌ Hết hàng rồi bro")

        item = stock_list.pop(0)
        new_stock = '\n'.join(stock_list)

        cur.execute("UPDATE users SET balance = balance -? WHERE user_id=?", (price, user_id))
        cur.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, pid))
        conn.commit()

        await query.message.reply_text(
            f"✅ **MUA THÀNH CÔNG**\n\n📦 Sản phẩm: {name}\n🔑 Tài khoản: `{item}`\n💵 Số dư còn: `{get_balance(user_id):,}đ`",
            parse_mode='Markdown'
        )

        if ADMIN_ID:
            await context.bot.send_message(ADMIN_ID, f"🔔 **ĐƠN HÀNG MỚI**\nUser: `{user_id}`\nSP: {name}\nGiá: {price:,}đ\nTK: `{item}`")

    # ========== ADMIN PANEL ==========
    elif query.data == 'admin' and user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("➕ Thêm sản phẩm", callback_data='admin_add_product')],
            [InlineKeyboardButton("📦 Thêm stock", callback_data='admin_add_stock')],
            [InlineKeyboardButton("📊 Thống kê", callback_data='admin_stats')],
            [InlineKeyboardButton("🔙 Về menu", callback_data='menu')]
        ]
        await query.message.edit_text("⚙️ **ADMIN PANEL**", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'admin_add_product' and user_id == ADMIN_ID:
        admin_state[user_id] = {'action': 'add_product'}
        await query.message.reply_text("Gửi theo format:\n`Tên sản phẩm | Giá`\nVD: `Spotify 3 tháng | 90000`\n\n/cancel để hủy", parse_mode='Markdown')

    elif query.data == 'admin_add_stock' and user_id == ADMIN_ID:
        cur.execute("SELECT id, name FROM products")
        rows = cur.fetchall()
        keyboard = []
        for pid, name in rows:
            keyboard.append([InlineKeyboardButton(name, callback_data=f'admin_stock_{pid}')])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='admin')])
        await query.message.edit_text("Chọn sản phẩm để thêm tài khoản:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith('admin_stock_') and user_id == ADMIN_ID:
        pid = int(query.data.split('_')[2])
        admin_state[user_id] = {'action': 'add_stock', 'pid': pid}
        product = get_product(pid)
        await query.message.reply_text(
            f"📝 **THÊM STOCK CHO: {product[1]}**\n\n"
            f"Gửi danh sách tài khoản, mỗi tài khoản 1 dòng:\n"
            f"`email1:pass1`\n`email2:pass2`\n\n"
            f"Gửi /cancel để hủy",
            parse_mode='Markdown'
        )

    elif query.data == 'admin_stats' and user_id == ADMIN_ID:
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        cur.execute("SELECT SUM(balance) FROM users")
        total_balance = cur.fetchone()[0] or 0
        await query.message.reply_text(
            f"📊 **THỐNG KÊ**\n\n"
            f"👥 Tổng user: `{total_users}`\n"
            f"💰 Tổng số dư: `{total_balance:,}đ`",
            parse_mode='Markdown'
        )

# ========== LỆNH ==========
async def nap_lenh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return await update.message.reply_text("Dùng: `/nap 50000`", parse_mode='Markdown')
    try:
        amount = int(context.args[0])
        if amount < 10000: return await update.message.reply_text("Min 10,000đ")
    except: return await update.message.reply_text("Số tiền không hợp lệ")
    qr_url = gen_qr_url(amount, user_id)
    caption = f"📷 **QUÉT QR ĐỂ NẠP {amount:,}đ**\n\nNội dung: `NAP {user_id}`"
    await update.message.reply_photo(photo=qr_url, caption=caption, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID and user_id in admin_state:
        state = admin_state[user_id]
        if update.message.text == '/cancel':
            del admin_state[user_id]
            return await update.message.reply_text("Đã hủy")

        if state['action'] == 'add_product':
            try:
                name, price = update.message.text.split('|')
                name = name.strip()
                price = int(price.strip())
                cur.execute("INSERT INTO products (name, price, stock) VALUES (?,?,?)", (name, price, ""))
                conn.commit()
                del admin_state[user_id]
                await update.message.reply_text(f"✅ Đã thêm sản phẩm: {name} - {price:,}đ")
            except:
                await update.message.reply_text("Sai format. Dùng: `Tên | Giá`")

        elif state['action'] == 'add_stock':
            accounts = update.message.text.strip()
            count = len([a for a in accounts.split('\n') if a.strip()])
            add_stock(state['pid'], accounts)
            del admin_state[user_id]
            await update.message.reply_text(f"✅ Đã thêm {count} tài khoản vào kho!")

# ========== WEBHOOK CASSO ==========
async def casso_webhook(request):
    try:
        data = await request.json()
        logger.info(f"Casso data: {data}")
        if data.get('error') == 0:
            for transaction in data.get('data', []):
                desc = transaction.get('description', '')
                amount = transaction.get('amount', 0)
                if 'NAP ' in desc:
                    try:
                        user_id = int(desc.split('NAP ')[1].split()[0])
                        add_balance(user_id, amount)
                        await application.bot.send_message(
                            user_id,
                            f"✅ **NẠP TIỀN THÀNH CÔNG**\n\nCộng: `{amount:,}đ`\nSố dư: `{get_balance(user_id):,}đ`",
                            parse_mode='Markdown'
                        )
                        if ADMIN_ID:
                            await application.bot.send_message(ADMIN_ID, f"💰 Auto nạp: {user_id} +{amount:,}đ")
                    except Exception as e:
                        logger.error(f"Loi nap: {e}")
        return web.Response(text='ok')
    except Exception as e:
        logger.error(f"Casso error: {e}")
        return web.Response(text='error', status=500)

# ========== AIOHTTP SETUP ==========
async def webhook_handler(request):
    data = await request.json()
    await application.update_queue.put(Update.de_json(data, application.bot))
    return web.Response()

async def on_startup(app):
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    logger.info("Bot started")

async def on_cleanup(app):
    await application.stop()
    await application.shutdown()

# ========== INIT ==========
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("nap", nap_lenh))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app = web.Application()
app.router.add_post('/webhook', webhook_handler)
app.router.add_post('/casso', casso_webhook)
app.router.add_get('/', lambda r: web.Response(text='Bot running'))
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == '__main__':
    web.run_app(app, port=PORT)
