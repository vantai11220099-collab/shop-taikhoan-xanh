import os
import sys
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ========= CONFIG =========
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8718318418"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "8000"))
CASSO_API_KEY = os.getenv("CASSO_API_KEY")

# DEBUG TOKEN - Thêm để check biến môi trường
if not TOKEN:
    print("ERROR: TOKEN is None or empty", file=sys.stderr)
    sys.exit(1)
print(f"TOKEN loaded: {TOKEN[:10]}...") # Chỉ in 10 ký tự đầu cho an toàn

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========= HANDLERS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Mua tài khoản", callback_data="buy")],
        [InlineKeyboardButton("💰 Nạp tiền", callback_data="nap")],
        [InlineKeyboardButton("📦 Đơn hàng", callback_data="orders")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Chào mừng đến Shop Tài Khoản Xanh 💸", reply_markup=reply_markup)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Bạn không có quyền.")
        return
    await update.message.reply_text("Admin Panel - Coming soon")

async def nap_lenh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Gửi cú pháp: NAP <số_tiền>\nVD: NAP 50000")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy":
        await query.edit_message_text("Tính năng mua hàng đang phát triển")
    elif query.data == "nap":
        await query.edit_message_text("Gửi cú pháp: NAP <số_tiền>\nVD: NAP 50000")
    elif query.data == "orders":
        await query.edit_message_text("Bạn chưa có đơn hàng nào")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.upper()
    if text.startswith("NAP"):
        await update.message.reply_text(f"Đã nhận lệnh nạp: {text}\nĐang xử lý...")
    else:
        await update.message.reply_text("Gõ /start để xem menu nha")

# ========= MAIN =========
def main():
    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("nap", nap_lenh))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Webhook cho Railway - v20 tự lo hết
    logger.info(f"Starting webhook on port {PORT}")
    logger.info(f"Webhook URL: {WEBHOOK_URL}/{TOKEN}")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
