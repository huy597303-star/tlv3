import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Cấu hình sẵn Token và Admin ID của bạn
TOKEN = "7547076899:AAEj41pXoF80Ea4fK2Jk8yXb_Q1n4JqN74g"
ADMIN_IDS = [9047366482]

# Khởi tạo Database SQLite
def init_db():
    conn = sqlite3.connect("bot_store.db")
    cursor = conn.cursor()
    # Bảng người dùng
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    ''')
    # Bảng kho hàng
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            product_name TEXT NOT NULL,
            account_info TEXT NOT NULL,
            status TEXT DEFAULT 'AVAILABLE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ----------------- HÀM TƯƠNG TÁC DB ----------------- #
def get_user_balance(user_id):
    conn = sqlite3.connect("bot_store.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        conn.commit()
        balance = 0
    else:
        balance = row[0]
    conn.close()
    return balance

def update_user_balance(user_id, amount):
    conn = sqlite3.connect("bot_store.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?", (user_id, amount, amount))
    conn.commit()
    conn.close()

# ----------------- CHỨC NĂNG BOT ----------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = get_user_balance(user_id)
    
    keyboard = [
        [InlineKeyboardButton("💳 Tài khoản", callback_data="me"), InlineKeyboardButton("📜 Lịch sử", callback_data="history")],
        [InlineKeyboardButton("📦 Kho hàng", callback_data="stock"), InlineKeyboardButton("🛒 Mua hàng", callback_data="buy_menu")],
        [InlineKeyboardButton("💵 Nạp tiền", callback_data="recharge")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Xin chào {update.effective_user.first_name}!\n"
        f"💰 Số dư hiện tại: {balance:,} VNĐ\n"
        f"Vui lòng chọn chức năng bên dưới:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "stock":
        conn = sqlite3.connect("bot_store.db")
        cursor = conn.cursor()
        # Sửa lỗi đếm kho: gom nhóm và đếm đúng số lượng AVAILABLE
        cursor.execute('''
            SELECT platform, product_name, COUNT(*) 
            FROM accounts 
            WHERE status = 'AVAILABLE' 
            GROUP BY LOWER(platform), LOWER(product_name)
        ''')
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            text = "📦 **KHO HÀNG HIỆN TẠI ĐANG TRỐNG!**"
        else:
            text = "📦 **DANH SÁCH KHO HÀNG HỆ THỐNG:**\n\n"
            for platform, p_name, count in rows:
                text += f"• [{platform.upper()}] {p_name}: Còn **{count}** tài khoản\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data="home")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "buy_menu":
        conn = sqlite3.connect("bot_store.db")
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT platform, product_name 
            FROM accounts 
            WHERE status = 'AVAILABLE'
        ''')
        items = cursor.fetchall()
        conn.close()

        if not items:
            await query.edit_message_text("❌ Hiện chưa có sản phẩm nào có sẵn để mua!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="home")]]))
            return

        keyboard = []
        for platform, p_name in items:
            keyboard.append([InlineKeyboardButton(f"🛒 Mua {platform.upper()} - {p_name}", callback_data=f"buy_prod|{p_name}")])
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data="home")])
        
        await query.edit_message_text("🛒 **CHỌN SẢN PHẨM BẠN MUỐN MUA:**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("buy_prod|"):
        product_name = data.split("|")[1]
        PRICE_PER_ITEM = 2000 # Giá mặc định mỗi sản phẩm
        
        user_balance = get_user_balance(user_id)
        if user_balance < PRICE_PER_ITEM:
            await query.edit_message_text(
                f"❌ **Số dư không đủ!**\nSản phẩm: `{product_name}`\nGiá: {PRICE_PER_ITEM:,} VNĐ\nSố dư của bạn: {user_balance:,} VNĐ",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Nạp tiền", callback_data="recharge"), InlineKeyboardButton("🔙 Quay lại", callback_data="buy_menu")]])
            )
            return

        conn = sqlite3.connect("bot_store.db")
        cursor = conn.cursor()
        
        # Sửa lỗi mua Gmail / tài khoản: Lấy chính xác bản ghi AVAILABLE
        cursor.execute('''
            SELECT id, account_info 
            FROM accounts 
            WHERE LOWER(product_name) = LOWER(?) AND status = 'AVAILABLE' 
            LIMIT 1
        ''', (product_name,))
        
        acc = cursor.fetchone()
        
        if not acc:
            conn.close()
            await query.edit_message_text("❌ Rất tiếc, loại tài khoản này vừa hết hàng!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="buy_menu")]]))
            return

        acc_id, account_info = acc
        
        # Chuyển trạng thái sang SOLD và trừ tiền
        cursor.execute("UPDATE accounts SET status = 'SOLD' WHERE id = ?", (acc_id,))
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (PRICE_PER_ITEM, user_id))
        conn.commit()
        conn.close()

        # Trả tài khoản thành công cho khách
        await query.edit_message_text(
            f"✅ **MUA TÀI KHOẢN THÀNH CÔNG!**\n\n"
            f"📌 **Sản phẩm:** `{product_name}`\n"
            f"💰 **Trừ số dư:** {PRICE_PER_ITEM:,} VNĐ\n"
            f"🔑 **Thông tin tài khoản:**\n`{account_info}`\n\n"
            f"_Lưu ý: Hãy đổi mật khẩu ngay sau khi nhận!_",
            parse_mode="Markdown"
        )

    elif data == "recharge":
        # Tích hợp thông tin MoMo và VPBank của bạn
        recharge_text = (
            "💵 **HƯỚNG DẪN NẠP TIỀN TỰ ĐỘNG / THỦ CÔNG**\n\n"
            "Quý khách vui lòng chuyển khoản theo thông tin bên dưới:\n\n"
            "💜 **MOMO:**\n"
            "• Số điện thoại: `0869561613`\n"
            "• Chủ tài khoản: **PHAM VAN TUNG**\n\n"
            "💚 **VPBANK:**\n"
            "• Số tài khoản: `0204098386`\n"
            "• Chủ tài khoản: **PHAM VAN TUNG**\n\n"
            "📝 **Nội dung chuyển khoản:** `nap " + str(user_id) + "`\n\n"
            "_(Sau khi chuyển khoản thành công, Admin sẽ duyệt hoặc hệ thống cộng tiền cho bạn)_"
        )
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data="home")]]
        await query.edit_message_text(recharge_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "me":
        balance = get_user_balance(user_id)
        await query.edit_message_text(
            f"👤 **THÔNG TIN TÀI KHOẢN**\n\n"
            f"🆔 Telegram ID: `{user_id}`\n"
            f"💰 Số dư hiện tại: **{balance:,} VNĐ**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="home")]])
        )

    elif data == "history":
        await query.edit_message_text(
            "📜 **LỊCH SỬ GIAO DỊCH**\n\nTính năng đang được cập nhật...",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_data="home")]])
        )

    elif data == "home":
        balance = get_user_balance(user_id)
        keyboard = [
            [InlineKeyboardButton("💳 Tài khoản", callback_data="me"), InlineKeyboardButton("📜 Lịch sử", callback_data="history")],
            [InlineKeyboardButton("📦 Kho hàng", callback_data="stock"), InlineKeyboardButton("🛒 Mua hàng", callback_data="buy_menu")],
            [InlineKeyboardButton("💵 Nạp tiền", callback_data="recharge")]
        ]
        await query.edit_message_text(
            f"Xin chào {query.from_user.first_name}!\n"
            f"💰 Số dư hiện tại: {balance:,} VNĐ\n"
            f"Vui lòng chọn chức năng bên dưới:",
            reply_markup=keyboard
        )

# ----------------- HỆ THỐNG LỆNH ADMIN (THÊM / CỘNG TAY) ----------------- #
async def admin_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=3)

    if len(parts) < 4:
        await update.message.reply_text(
            "⚠️ **Sai cú pháp thêm hàng!**\n"
            "👉 Cú pháp: `thêm <platform> <tài_khoản_pass_2fa> <tên_sản_phẩm>`\n"
            "👉 Ví dụ: `thêm google hhakbauvak162@gmail.com pass2fa123 Gmail_Cổ`",
            parse_mode="Markdown"
        )
        return

    _, platform, account_info, product_name = parts

    conn = sqlite3.connect("bot_store.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO accounts (platform, product_name, account_info, status)
        VALUES (?, ?, ?, 'AVAILABLE')
    ''', (platform.lower(), product_name, account_info))
    conn.commit()
    
    cursor.execute('''
        SELECT COUNT(*) FROM accounts 
        WHERE LOWER(product_name) = LOWER(?) AND status = 'AVAILABLE'
    ''', (product_name,))
    total_count = cursor.fetchone()[0]
    conn.close()

    await update.message.reply_text(
        f"✅ **Đã thêm 1 tài khoản thành công!**\n"
        f"📌 Nền tảng: `{platform}`\n"
        f"📦 Tên sản phẩm: `{product_name}`\n"
        f"📊 Tổng kho `{product_name}` hiện có: **{total_count}**",
        parse_mode="Markdown"
    )

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return

    text = update.message.text.strip()
    parts = text.split(maxsplit=4)

    if len(parts) < 5:
        await update.message.reply_text(
            "⚠️ **Sai cú pháp cộng tiền!**\n"
            "👉 Cú pháp: `cộng <số_tiền> <id_khách> <hoàn thành/fail> <lý do>`\n"
            "👉 Ví dụ: `cộng 50000 9047366482 hoàn thành Nạp qua Momo`",
            parse_mode="Markdown"
        )
        return

    _, amount_str, target_uid_str, status_action, reason = parts

    try:
        amount = int(amount_str)
        target_uid = int(target_uid_str)
    except ValueError:
        await update.message.reply_text("❌ Số tiền hoặc User ID phải là chữ số!")
        return

    if status_action.lower() in ["hoàn thành", "thành công", "ok"]:
        update_user_balance(target_uid, amount)
        new_balance = get_user_balance(target_uid)
        
        await update.message.reply_text(
            f"✅ **Cộng tiền thành công!**\n"
            f"👤 User ID: `{target_uid}`\n"
            f"💰 Số tiền cộng: +{amount:,} VNĐ\n"
            f"💳 Số dư mới: {new_balance:,} VNĐ\n"
            f"📝 Lý do: {reason}",
            parse_mode="Markdown"
        )
        try:
            await context.bot.send_message(
                chat_id=target_uid,
                text=f"🎉 **Bạn đã được cộng {amount:,} VNĐ vào tài khoản!**\n📝 Lý do: {reason}\n💳 Số dư mới: {new_balance:,} VNĐ",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    else:
        await update.message.reply_text(f"❌ Đã từ chối giao dịch của UID `{target_uid}`. Lý do: {reason}", parse_mode="Markdown")

# ----------------- MAIN RUNNER ----------------- #
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.Regex(r'^(thêm|Thêm)\s+'), admin_add_account))
    app.add_handler(MessageHandler(filters.Regex(r'^(cộng|Cộng)\s+'), admin_add_balance))

    print("Bot Store Railway đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
