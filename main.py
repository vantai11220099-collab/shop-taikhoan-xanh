import os
import sys
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8718318418"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", "8000"))

if not TOKEN:
    print("ERROR: TOKEN is None", file=sys.stderr)
    sys.exit(1)
if not WEBHOOK_URL:
    print("ERROR: WEBHOOK_URL is None", file=sys.stderr)
    sys.exit(1)

print(f"TOKEN loaded: {TOKEN[:10]}...")
print(f"WEBHOOK_URL loaded: {WEBHOOK_URL}")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🛒 Mua tài khoản", callback_data="buy")],
                [InlineKeyboardButton("💰 Nạp tiền", callback_data="nap")],
                [InlineKeyboardButton("📦 Đơn hàng", callback_data="orders")]]
    await update.message.reply_text("Chào mừng đến Shop Tài Khoản Xanh 💸", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Bạn không có quyền.")
        return
    await update.message.reply_text("Admin Panel - Coming soon")

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

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    full_webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
    logger.info(f"Starting webhook on port {PORT}")
    logger.info(f"Setting webhook to: {full_webhook_url}")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=full_webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
