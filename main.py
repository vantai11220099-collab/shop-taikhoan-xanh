import os
import sqlite3
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request
import threading
import time
import json

TOKEN = os.getenv("BOT_TOKEN")
CASSO_API_KEY = os.getenv("CASSO_API_KEY") # Lấy từ Casso.vn
CASSO_BANK_ID = os.getenv("CASSO_BANK_ID") # ID tài khoản bank trên Casso
DOMAIN = os.getenv("DOMAIN") # https://xxx.up.railway.app
ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) # ID Telegram admin
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin") # Username admin không có @

# 1. Database
conn = sqlite3.connect('btshop.db', check_same_thread=False)
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS users
            (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, username TEXT, created_at INTEGER)''')
cur.execute('''CREATE TABLE IF NOT EXISTS accounts
            (id INTEGER PRIMARY KEY AUTOINCREMENT, game TEXT, info TEXT, price INTEGER, status TEXT DEFAULT 'stock', created_at INTEGER)''')
cur.execute('''CREATE TABLE IF NOT EXISTS orders
            (order_code TEXT PRIMARY KEY, user_id INTEGER, amount INTEGER, status TEXT, created_at INTEGER)''')
cur.execute('''CREATE TABLE IF NOT EXISTS history
            (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, amount INTEGER, detail TEXT, created_at INTEGER)''')
conn.commit()

# 2. Flask webhook Casso
app = Flask(__name__)

@app.route('/')
def home():
    return "BT Shop đang chạy!"

@app.route('/casso-webhook', methods=['POST'])
def casso_webhook():
    try:
        data = request.json
        # Casso gửi dạng {"error":0,"data":[{...transaction...}]}
        if data.get('error') == 0:
            transactions = data['data']
            for trans in transactions:
                amount = trans['amount']
                memo = trans['description'].upper() # Nội dung CK
                tid = trans['tid'] # Mã giao dịch để tránh duplicate

                # Chỉ xử lý tiền vào và có mã BT
                if amount > 0 and "BT" in memo:
                    # Tách mã đơn: BT1234567890
                    try:
                        order_code = "BT" + memo.split("BT")[1].split(" ")[0]
                    except:
                        continue

                    # Check đã cộng chưa
                    cur.execute("SELECT user_id FROM orders WHERE order_code=? AND status='pending'", (order_code,))
                    result = cur.fetchone()
                    if result:
                        user_id = result[0]
                        # Cộng tiền
                        cur.execute("UPDATE users SET balance = balance +? WHERE user_id=?", (amount, user_id))
                        cur.execute("UPDATE orders SET status='paid' WHERE order_code=?", (order_code,))
                        # Lưu lịch sử
                        cur.execute("INSERT INTO history (user_id, action, amount, detail, created_at) VALUES (?,?,?,?,?)",
                                    (user_id, 'nap', amount, f'Nạp qua Casso - {tid}', int(time.time())))
                        conn.commit()

                        # Báo cho user
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                                      json={"chat_id": user_id,
                                            "text": f"🎉 <b>BT Shop: Nạp thành công {amount:,}đ</b>\n\nSố dư mới: {get_balance(user_id):,}đ\nGõ /start để mua acc ngay!",
                                            "parse_mode": "HTML"})
    except Exception as e:
        print("Casso webhook error:", e)
    return {"success": True}

def run_flask():
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))

# 3. Hàm phụ
def get_balance(user_id):
    cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    res = cur.fetchone()
    return res[0] if res else 0

def add_user(user_id, username):
    cur.execute("INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?,?,?)",
                (user_id, username, int(time.time())))
    conn.commit()

def get_bank_info():
    headers = {"Authorization": f"Apikey {CASSO_API_KEY}"}
    res = requests.get("https://oauth.casso.vn/v2/userInfo", headers=headers).json()
    if res['error'] == 0:
        for bank in res['data']['banks']:
            if bank['id'] == CASSO_BANK_ID:
                return {
                    'bank': bank['bank']['shortName'],
                    'stk': bank['accountNumber'],
                    'name': bank['accountName']
                }
    return None

# 4. Menu chính
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username)

    keyboard = [
        [InlineKeyboardButton("💰 Nạp tiền", callback_data='nap'), InlineKeyboardButton("💳 Số dư", callback_data='sodu')],
        [InlineKeyboardButton("🎮 Mua Acc Game", callback_data='muahang')],
        [InlineKeyboardButton("📦 Lịch sử GD", callback_data='lichsu'), InlineKeyboardButton("📞 Hỗ trợ", callback_data='hotro')]
    ]
    text = f"👋 Chào {user.first_name} đến với <b>BT Shop</b>\n\n" \
           f"🔥 Shop acc game tự động 24/7\n" \
           f"⚡ Nạp tiền auto qua Casso, giao acc ngay\n" \
           f"💎 Số dư: <code>{get_balance(user.id):,}đ</code>\n\n" \
           f"👇 Chọn chức năng:"

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# 5. Xử lý nút
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'menu': await start(update, context)
    elif data == 'nap': await nap_menu(query)
    elif data.startswith('nap_'): await tao_don_nap(query, int(data.split('_')[1]))
    elif data == 'sodu': await check_sodu(query)
    elif data == 'muahang': await list_acc(query)
    elif data.startswith('buy_'): await mua_acc(query, int(data.split('_')[1]))
    elif data == 'lichsu': await lich_su(query)
    elif data == 'hotro': await ho_tro(query)

async def nap_menu(query):
    keyboard = [
        [InlineKeyboardButton("50.000đ", callback_data='nap_50000'), InlineKeyboardButton("100.000đ", callback_data='nap_100000')],
        [InlineKeyboardButton("200.000đ", callback_data='nap_200000'), InlineKeyboardButton("500.000đ", callback_data='nap_500000')],
        [InlineKeyboardButton("1.000.000đ", callback_data='nap_1000000')],
        [InlineKeyboardButton("⬅️ Menu", callback_data='menu')]
    ]
    await query.edit_message_text("💰 <b>NẠP TIỀN BT SHOP</b>\n\nChọn mệnh giá hoặc chuyển khoản lẻ theo HD bên dưới:",
                                  reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def tao_don_nap(query, amount):
    user_id = query.from_user.id
    order_code = f"BT{user_id}{int(time.time())}"[-12:] # BT + 10 số cuối

    bank_info = get_bank_info()
    if not bank_info:
        await query.edit_message_text("❌ Lỗi kết nối ngân hàng. Liên hệ admin!")
        return

    # Lưu đơn pending
    cur.execute("INSERT INTO orders VALUES (?,?,?,?,?)", (order_code, user_id, amount, 'pending', int(time.time())))
    conn.commit()

    qr_url = f"https://img.vietqr.io/image/{bank_info['bank']}-{bank_info['stk']}-compact2.png?amount={amount}&addInfo={order_code}&accountName={bank_info['name']}"

    text = f"💵 <b>ĐƠN NẠP {amount:,}đ</b>\n\n" \
           f"🏦 Ngân hàng: <code>{bank_info['bank']}</code>\n" \
           f"💳 STK: <code>{bank_info['stk']}</code>\n" \
           f"👤 CTK: <code>{bank_info['name']}</code>\n" \
           f"💰 Số tiền: <code>{amount}</code>\n" \
           f"📝 Nội dung: <code>{order_code}</code>\n\n" \
           f"⚠️ <b>BẮT BUỘC CK đúng nội dung để auto cộng tiền!</b>\n" \
           f"⏱️ Tiền vào sau 10-30s khi CK thành công."

    keyboard = [[InlineKeyboardButton("📷 Mở ảnh QR Code", url=qr_url)],
                [InlineKeyboardButton("⬅️ Menu", callback_data='menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def check_sodu(query):
    balance = get_balance(query.from_user.id)
    keyboard = [[InlineKeyboardButton("💰 Nạp thêm", callback_data='nap')], [InlineKeyboardButton("⬅️ Menu", callback_data='menu')]]
    await query.edit_message_text(f"💳 <b>SỐ DƯ BT SHOP</b>\n\nSố dư hiện tại: <code>{balance:,}đ</code>",
                                  reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def list_acc(query):
    cur.execute("SELECT id, game, price FROM accounts WHERE status='stock' ORDER BY price ASC LIMIT 20")
    accs = cur.fetchall()
    if not accs:
        await query.edit_message_text("😭 <b>Hết hàng!</b>\nShop đang nhập thêm acc. Bật thông báo để hóng hàng mới nha",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data='menu')]]))
        return

    keyboard = []
    text = "🎮 <b>KHO ACC BT SHOP</b>\n\n"
    for acc_id, game, price in accs:
        text += f"<code>#{acc_id}</code> | {game} | <b>{price:,}đ</b>\n"
        keyboard.append([InlineKeyboardButton(f"Mua #{acc_id} - {price:,}đ", callback_data=f'buy_{acc_id}')])
    keyboard.append([InlineKeyboardButton("⬅️ Menu", callback_data='menu')])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def mua_acc(query, acc_id):
    user_id = query.from_user.id
    cur.execute("SELECT game, info, price FROM accounts WHERE id=? AND status='stock'", (acc_id,))
    result = cur.fetchone()
    if not result:
        await query.edit_message_text("❌ Acc này vừa có người mua mất rồi!",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kho acc", callback_data='muahang')]]))
        return

    game, info, price = result
    balance = get_balance(user_id)

    if balance < price:
        await query.edit_message_text(
            f"❌ <b>SỐ DƯ KHÔNG ĐỦ</b>\n\nAcc: {game}\nGiá: <code>{price:,}đ</code>\nSố dư: <code>{balance:,}đ</code>\nThiếu: <code>{price-balance:,}đ</code>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰 Nạp tiền ngay", callback_data='nap')],
                                               [InlineKeyboardButton("⬅️ Kho acc", callback_data='muahang')]]))
        return

    # Trừ tiền + giao acc
    cur.execute("UPDATE users SET balance = balance -? WHERE user_id=?", (price, user_id))
    cur.execute("UPDATE accounts SET status='sold' WHERE id=?", (acc_id,))
    cur.execute("INSERT INTO history (user_id, action, amount, detail, created_at) VALUES (?,?,?,?,?)",
                (user_id, 'mua', price, f'Mua acc {game} #{acc_id}', int(time.time())))
    conn.commit()

    await query.edit_message_text(
        f"✅ <b>MUA THÀNH CÔNG</b>\n\n"
        f"🎮 Game: {game}\n"
        f"💵 Giá: {price:,}đ\n"
        f"💳 Số dư còn: {get_balance(user_id):,}đ\n\n"
        f"📦 <b>THÔNG TIN ACC:</b>\n"
        f"<code>{info}</code>\n\n"
        f"⚠️ Vui lòng đổi mật khẩu ngay sau khi nhận!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Mua tiếp", callback_data='muahang'),
                                            InlineKeyboardButton("⬅️ Menu", callback_data='menu')]]),
        parse_mode='HTML')

    # Báo cho admin
    if ADMIN_ID:
        await context.bot.send_message(ADMIN_ID, f"🔔 BT Shop: Có đơn mới\nUser: {user_id}\nAcc: {game} #{acc_id}\nGiá: {price:,}đ")

async def lich_su(query):
    user_id = query.from_user.id
    cur.execute("SELECT action, amount, detail, created_at FROM history WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (user_id,))
    rows = cur.fetchall()
    if not rows:
        text = "📦 Chưa có giao dịch nào"
    else:
        text = "📦 <b>5 GIAO DỊCH GẦN NHẤT</b>\n\n"
        for action, amount, detail, created_at in rows:
            time_str = time.strftime("%d/%m %H:%M", time.localtime(created_at))
            if action == 'nap':
                text += f"✅ +{amount:,}đ | Nạp tiền | {time_str}\n"
            else:
                text += f"❌ -{amount:,}đ | {detail} | {time_str}\n"

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu", callback_data='menu')]]), parse_mode='HTML')

async def ho_tro(query):
    await query.edit_message_text(f"📞 <b>HỖ TRỢ BT SHOP</b>\n\nLiên hệ Admin: @{ADMIN_USERNAME}\nHoạt động 24/7\n\nGặp lỗi nạp tiền/mua acc báo ngay để được xử lý!",
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 Chat với Admin", url=f'https://t.me/{ADMIN_USERNAME}')],
                                                                     [InlineKeyboardButton("⬅️ Menu", callback_data='menu')]]),
                                  parse_mode='HTML')

# 6. Lệnh Admin
async def addacc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        text = " ".join(context.args)
        game, info, price = text.split("|")
        price = int(price.replace(".", "").replace("đ", "").replace(",", "").strip())
        cur.execute("INSERT INTO accounts (game, info, price, created_at) VALUES (?,?,?,?)",
                    (game.strip(), info.strip(), price, int(time.time())))
        conn.commit()
        await update.message.reply_text(f"✅ BT Shop: Đã thêm acc {game.strip()} giá {price:,}đ vào kho")
    except:
        await update.message.reply_text("❌ Sai cú pháp!\nDùng: `/addacc Liên Quân | user:abc pass:123 | 50.000`", parse_mode='Markdown')

async def thongke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    cur.execute("SELECT COUNT(*) FROM accounts WHERE status='stock'")
    ton_kho = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM accounts WHERE status='sold'")
    da_ban = cur.fetchone()[0]
    cur.execute("SELECT SUM(amount) FROM orders WHERE status='paid'")
    doanh_thu = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM users")
    tong_user = cur.fetchone()[0]

    await update.message.reply_text(
        f"📊 <b>THỐNG KÊ BT SHOP</b>\n\n"
        f"👥 Tổng user: {tong_user}\n"
        f"📦 Tồn kho: {ton_kho} acc\n"
        f"✅ Đã bán: {da_ban} acc\n"
        f"💰 Doanh thu: {doanh_thu:,}đ", parse_mode='HTML')

async def congtien(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        user_id, amount = int(context.args[0]), int(context.args[1])
        cur.execute("UPDATE users SET balance = balance +? WHERE user_id=?", (amount, user_id))
        conn.commit()
        await update.message.reply_text(f"✅ Đã cộng {amount:,}đ cho user {user_id}")
        await context.bot.send_message(user_id, f"🎁 BT Shop: Admin vừa cộng {amount:,}đ vào tài khoản bạn!")
    except:
        await update.message.reply_text("Dùng: /congtien user_id số_tiền")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("addacc", addacc))
    application.add_handler(CommandHandler("thongke", thongke))
    application.add_handler(CommandHandler("congtien", congtien))
    application.add_handler(CallbackQueryHandler(button))
    print("BT Shop đã chạy!")
    application.run_polling()