import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- CÁC HÀM XỬ LÝ KHÁC CỦA BẠN GIỮ NGUYÊN Ở ĐÂY ---

# --- HÀM IMPORT TÀI KHOẢN TỪ FILE DANHSACH.TXT ---
async def admin_import_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Thay thế ADMIN_IDS bằng danh sách ID quản trị viên của bạn nếu cần
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

def main():
    # Khởi tạo bot token của bạn
    app = Application.builder().token("TOKEN_BOT_CỦA_BẠN").build()

    # --- ĐĂNG KÝ CÁC HANDLER KHÁC ---
    
    # ĐĂNG KÝ LỆNH IMPORT (Dòng bắt buộc phải có)
    app.add_handler(CommandHandler("import", admin_import_file))

    # Chạy bot
    app.run_polling()

if __name__ == "__main__":
    main()
