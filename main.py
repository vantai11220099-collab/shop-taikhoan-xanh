import os, sqlite3, re, random, string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from aiohttp import web

TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']
ADMIN_ID = 8718318418
STK = "106886640236"
BANK = "VietinBank"
BANK_CODE = "icb"
TEN_CTK = "PHAM VAN TAI"
SUPPORT_URL = "https://t.me/btshopmmo"
PORT = int(os.environ.get('PORT', 8080))

conn = sqlite3.connect('shop.db', check_same_thread=False)
conn.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER, stock TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
conn.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, time TEXT)''')
conn.execute('''CREATE TABLE IF NOT EXISTS trans (code TEXT PRIMARY KEY, user_id INTEGER, amount INTEGER, status TEXT)''')
conn.commit()

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

async def nap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id; code = random_code()
    conn.execute("INSERT INTO trans (code, user_id, status) VALUES (?,?,?)", (code, user_id, 'pending')); conn.commit()
    qr_url = f"https://img.vietqr.io/image/{BANK_CODE}-{STK}-compact2.png?amount=&addInfo={code}&accountName={TEN_CTK}"
    text = f"""💸 **NẠP TIỀN TỰ ĐỘNG**\n\nNgân hàng: `{BANK}`\nSố TK: `{STK}`\nChủ TK: `{TEN_CTK}`\nNội dung: `{code}`\n\n⚠️ MÃ CHỈ DÙNG 1 LẦN\n👇 Quét QR chuyển nhanh"""
    if update.callback_query: await update.callback_query.message.reply_photo(photo=qr_url, caption=text, parse_mode='Markdown')
    else: await update.message.reply_photo(photo=qr_url, caption=text, parse_mode='Markdown')

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
    query = update
