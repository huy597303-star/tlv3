import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CẤU HÌNH THÔNG TIN CỐ ĐỊNH ---
BOT_TOKEN = "9291585542:AAFkdq6uxLvRsZLI2NKyN4Dxr-rONDe0kdM"      # Thay token chuẩn của bạn vào đây
ADMIN_ID = 9047366482              # Thay Telegram User ID của Admin vào đây (dạng số)

# Thông tin thanh toán
MOMO_INFO = {
    "sdt": "0869561613",
    "chu_tai_khoan": "PHAM VAN TUNG"
}

VPBANK_INFO = {
    "stk": "0204098386",
    "chu_tai_khoan": "PHAM VAN TUNG"
}
# ----------------------------------

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Lệnh /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Xin chào {user.first_name}! Chào mừng bạn đến với bot.\n"
        f"Gõ /thanhtoan để xem thông tin chuyển khoản."
    )

# Lệnh /thanhtoan hiển thị thông tin MoMo và VPBank
async def thanhtoan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💳 **THÔNG TIN THANH TOÁN CHÍNH CHỦ** 💳\n\n"
        "🟡 **Ví MoMo:**\n"
        f"• Số điện thoại: `{MOMO_INFO['sdt']}`\n"
        f"• Chủ tài khoản: **{MOMO_INFO['chu_tai_khoan']}**\n\n"
        "🟢 **Ngân hàng VPBank:**\n"
        f"• Số tài khoản: `{VPBANK_INFO['stk']}`\n"
        f"• Chủ tài khoản: **{VPBANK_INFO['chu_tai_khoan']}**\n\n"
        "⚠️ *Vui lòng ghi đúng nội dung chuyển khoản khi thanh toán!*"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# Lệnh dành riêng cho Admin (Ví dụ: /admin)
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Bạn không có quyền sử dụng lệnh này!")
        return
    
    await update.message.reply_text("👑 Chào Admin Phạm Văn Tùng! Đây là bảng điều khiển hệ thống.")

def main():
    # Khởi tạo ứng dụng với token được truyền trực tiếp
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Đăng ký các handlers (lệnh)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("thanhtoan", thanhtoan))
    application.add_handler(CommandHandler("admin", admin_panel))

    logger.info("Bot đang khởi động...")
    # Chạy bot ở chế độ polling
    application.run_polling()

if __name__ == '__main__':
    main()
