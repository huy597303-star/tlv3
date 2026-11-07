import sqlite3
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- ĐIỀN CÁC ID ADMIN CỦA BẠN VÀO ĐÂY ---
ADMIN_IDS = [123456789] # Thay thế bằng Telegram ID thật của bạn

# ==========================================
# 1. TÍNH NĂNG IMPORT TÀI KHOẢN TỪ FILE
# ==========================================
async def admin_import_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    try:
        with open("danhsach.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        conn = sqlite3.connect("bot_store.db")
        cursor = conn.cursor()
        count = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            # Tách Tên sản phẩm và Thông tin tài khoản dựa vào dấu | đầu tiên
            parts = line.split("|", 1)
            if len(parts) == 2:
                product_name, account_info = parts
                cursor.execute('''
                    INSERT INTO accounts (product_name, account_info, status)
                    VALUES (?, ?, 'AVAILABLE')
                ''', (product_name.strip(), account_info.strip()))
                count += 1
                
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ **Import thành công!**\n"
            f"📦 Đã thêm vào kho: **{count}** tài khoản từ file `danhsach.txt`.",
            parse_mode="Markdown"
        )
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ Không tìm thấy file `danhsach.txt` trên server!\n"
            "👉 Vui lòng tạo file `danhsach.txt` cùng thư mục với bot.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi xử lý file: {e}")


# ==========================================
# 2. TÍNH NĂNG AUTO CHECK BILL VÀ CỘNG TIỀN
# ==========================================
async def handle_bank_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    message = update.message
    text_content = message.caption or message.text or ""
    
    if not text_content:
        return

    try:
        # Dùng Regex quét tìm Số tiền
        amount_match = re.search(r'(?:[Tt][đd]|[Vv][Nn][Đd]|\b)?\s*([\d.,]+)(?:\s*(?:đ|vnđ|vnd|K))?\b', text_content)
        
        # Dùng Regex tìm Telegram ID của user (chuỗi số 9-10 chữ số)
        user_id_match = re.search(r'\b(1[0-9]{8,9}|[0-9]{9,10})\b', text_content)
        
        if amount_match and user_id_match:
            raw_amount = amount_match.group(1).replace('.', '').replace(',', '')
            amount = int(raw_amount)
            target_user_id = int(user_id_match.group(1))
            
            conn = sqlite3.connect("bot_store.db")
            cursor = conn.cursor()
            
            # Đảm bảo bảng users tồn tại hoặc kiểm tra số dư
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (target_user_id,))
            user = cursor.fetchone()
            
            if user:
                new_balance = user[0] + amount
                cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, target_user_id))
            else:
                new_balance = amount
                cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (target_user_id, new_balance))
                
            conn.commit()
            conn.close()
            
            await message.reply_text(
                f"✅ **Auto Check Bill Thành Công!**\n"
                f"👤 User ID: `{target_user_id}`\n"
                f"💰 Đã cộng: **{amount:,} VNĐ**\n"
                f"💎 Số dư mới: **{new_balance:,} VNĐ**",
                parse_mode="Markdown"
            )
        else:
            await message.reply_text("❌ Không đọc được rõ số tiền hoặc Telegram ID từ nội dung/bill này.")
            
    except Exception as e:
        await message.reply_text(f"❌ Lỗi xử lý bill tự động: {e}")


# ==========================================
# 3. HÀM MAIN KHỞI CHẠY BOT
# ==========================================
def main():
    # Thay "TOKEN_BOT_CỦA_BẠN" bằng Token thật lấy từ BotFather
    TOKEN = "9291585542:AAFkdq6uxLvRsZLI2NKyN4Dxr-rONDe0kdM"
    app = Application.builder().token(TOKEN).build()

    # Đăng ký lệnh import file danh sách tài khoản
    app.add_handler(CommandHandler("import", admin_import_file))
    
    # Đăng ký lắng nghe ảnh bill hoặc tin nhắn chuyển khoản để auto cộng tiền
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_bank_bill))

    print("🤖 Bot đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
