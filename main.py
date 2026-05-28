import os, asyncio, sqlite3, re, random, string
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ==== CONFIG ==== Thay 6 dòng này
TOKEN = os.environ['BOT_TOKEN']
WEBHOOK_URL = os.environ['WEBHOOK_URL']
ADMIN_ID = 8718318418
STK = "106886640236"
BANK = "VietinBank"
BANK_CODE = "icb" # VietinBank
TEN_CTK = "PHAM VAN TAI" # VIẾT HOA KHÔNG DẤU
SUPPORT_URL = "https://t.me/btshopmmo"

app = Flask(__name__)
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
        icon = "🎬" if "netflix" in name.lower() else "🎵" if "spotify" in name.lower() else "📺" if "youtube" in name.lower() else "🎨" if "canva
