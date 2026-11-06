async def admin_import_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    try:
        # Đọc file danhsach.txt đặt cùng thư mục với bot
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
            f"✅ **Import tất cả thành công!**\n"
            f"📦 Đã thêm vào kho: **{count}** tài khoản từ file `danhsach.txt`.",
            parse_mode="Markdown"
        )
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ Không tìm thấy file `danhsach.txt`!\n"
            "👉 Hãy tạo file `danhsach.txt` chứa toàn bộ danh sách tài khoản cùng thư mục với bot trên server/Railway.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi xử lý file: {e}")
