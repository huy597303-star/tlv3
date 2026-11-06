import logging
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---------------- Config ----------------
BOT_TOKEN = "9291585542:AAFkdq6uxLvRsZLI2NKyN4Dxr-rONDe0kdM"
ADMIN_ID = 9047366482

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ---------------- Database Setup ----------------
def init_db():
    conn = sqlite3.connect("bot_store.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            balance REAL DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            product_name TEXT,
            account_info TEXT,
            price REAL DEFAULT 2000,
            status TEXT DEFAULT 'AVAILABLE'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            description TEXT,
            amount REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id, name=""):
    conn = sqlite3.connect("bot_store.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id, name, balance) VALUES (?, ?, 0)", (user_id, name))
        conn.commit()
        row = (user_id, name, 0.0)
    conn.close()
    return {"user_id": row[0], "name": row[1], "balance": row[2]}

# ---------------- Keyboards ----------------
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("💳 Tài khoản", callback_data="menu_account"), InlineKeyboardButton("📜 Lịch sử", callback_data="menu_history")],
        [InlineKeyboardButton("📦 Kho hàng", callback_data="menu_stock"), InlineKeyboardButton("🛒 Mua hàng", callback_data="menu_buy")],
        [InlineKeyboardButton("💵 Nạp tiền", callback_data="menu_deposit")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_home_keyboard():
    keyboard = [
        [InlineKeyboardButton("◀️ Back", callback_data="menu_home"), InlineKeyboardButton("🏠 Home", callback_data="menu_home")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def delete_user_message(update: Update):
    try:
        if update.message:
            await update.message.delete()
    except Exception:
        pass

# ---------------- Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id, user.full_name)
    await delete_user_message(update)
    
    if "last_menu_id" in context.user_data:
        try:
            await context.bot.delete_message(chat_id=user.id, message_id=context.user_data["last_menu_id"])
        except Exception:
            pass

    sent_msg = await update.effective_chat.send_message(
        f"Xin chào {user.full_name}! Vui lòng chọn chức năng bên dưới:",
        reply_markup=main_menu_keyboard()
    )
    context.user_data["last_menu_id"] = sent_msg.message_id

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = get_user(user_id, query.from_user.full_name)
    data = query.data

    if data == "menu_home":
        await query.edit_message_text(
            f"Xin chào {user_data['name']}! Vui lòng chọn chức năng bên dưới:",
            reply_markup=main_menu_keyboard()
        )

    elif data == "menu_account":
        text = (
            f"👤 Thông tin tài khoản\n\n"
            f"• ID: {user_data['user_id']}\n"
            f"• Tên: {user_data['name']}\n"
            f"• Số dư: {user_data['balance']:,.0f} VNĐ"
        )
        await query.edit_message_text(text, reply_markup=back_home_keyboard())

    elif data == "menu_history":
        keyboard = [
            [InlineKeyboardButton("📜 Lịch sử mua acc", callback_data="hist_buy")],
            [InlineKeyboardButton("💳 Lịch sử nạp tiền", callback_data="hist_deposit")],
            [InlineKeyboardButton("◀️ Back", callback_data="menu_home"), InlineKeyboardButton("🏠 Home", callback_data="menu_home")]
        ]
        await query.edit_message_text("Vui lòng chọn loại lịch sử cần xem:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data in ["hist_buy", "hist_deposit"]:
        h_type = "PURCHASE" if data == "hist_buy" else "DEPOSIT"
        title = "Lịch sử mua acc" if h_type == "PURCHASE" else "Lịch sử nạp tiền"
        
        conn = sqlite3.connect("bot_store.db")
        cursor = conn.cursor()
        cursor.execute("SELECT description, amount, timestamp FROM history WHERE user_id = ? AND type = ? ORDER BY id DESC LIMIT 10", (user_id, h_type))
        rows = cursor.fetchall()
        conn.close()

        text = f"📜 {title}\n\n"
        if not rows:
            text += "Chưa có dữ liệu."
        else:
            for r in rows:
                text += f"• [{r[2]}]\n  {r[0]} | Giá: {r[1]:,.0f} VNĐ\n\n"

        await query.edit_message_text(text, reply_markup=back_home_keyboard())

    # BẢO MẬT: Kho hàng chỉ hiển thị số lượng tồn, ẩn toàn bộ thông tin nhạy cảm
    elif data == "menu_stock":
        conn = sqlite3.connect("bot_store.db")
        cursor = conn.cursor()
        platforms = ["Facebook", "Google", "TikTok"]
        text = "📦 Thông tin kho hàng\n\n"
        for p in platforms:
            cursor.execute("SELECT COUNT(*) FROM inventory WHERE LOWER(platform) = LOWER(?) AND status = 'AVAILABLE'", (p,))
            count = cursor.fetchone()[0]
            text += f"• {p}: số lượng còn: {count}\n"
        conn.close()
        
        await query.edit_message_text(text, reply_markup=back_home_keyboard())

    elif data == "menu_buy":
        keyboard = [
            [InlineKeyboardButton("Facebook", callback_data="buy_platform_Facebook")],
            [InlineKeyboardButton("Google", callback_data="buy_platform_Google")],
            [InlineKeyboardButton("TikTok", callback_data="buy_platform_TikTok")],
            [InlineKeyboardButton("◀️ Back", callback_data="menu_home"), InlineKeyboardButton("🏠 Home", callback_data="menu_home")]
        ]
        await query.edit_message_text("Chọn nền tảng bạn muốn mua:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("buy_platform_"):
        platform = data.split("_")[2]
        conn = sqlite3.connect("bot_store.db")
        cursor = conn.cursor()
        cursor.execute("SELECT product_name, price, COUNT(*) FROM inventory WHERE LOWER(platform) = LOWER(?) AND status = 'AVAILABLE' GROUP BY product_name, price", (platform,))
        items = cursor.fetchall()
        conn.close()

        keyboard = []
        if items:
            for item in items:
                p_name, price, qty = item[0], item[1], item[2]
                btn_text = f"{p_name} | Kho: {qty} | Giá: {price:,.0f} VNĐ"
                if platform.lower() == "facebook":
                    conn_tmp = sqlite3.connect("bot_store.db")
                    cur_tmp = conn_tmp.cursor()
                    cur_tmp.execute("SELECT id FROM inventory WHERE LOWER(platform) = 'facebook' AND product_name = ? AND status = 'AVAILABLE' LIMIT 1", (p_name,))
                    fb_item = cur_tmp.fetchone()
                    conn_tmp.close()
                    fb_id = fb_item[0] if fb_item else 0
                    keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"buyfb_{fb_id}")])
                else:
                    keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"buynow_{platform}_{p_name}")])
        else:
            keyboard.append([InlineKeyboardButton("Hết hàng (Kho: 0)", callback_data="noop")])
        
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="menu_buy"), InlineKeyboardButton("🏠 Home", callback_data="menu_home")])
        await query.edit_message_text(f"Danh sách mặt hàng {platform}:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("buyfb_"):
        acc_id = int(data.split("_")[1])
        conn = sqlite3.connect("bot_store.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT platform, product_name, account_info, price FROM inventory WHERE id = ? AND status = 'AVAILABLE'", (acc_id,))
        acc = cursor.fetchone()

        if not acc:
            conn.close()
            await query.edit_message_text("❌ Tài khoản này đã có người mua hoặc không còn tồn tại!", reply_markup=back_home_keyboard())
            return

        platform, p_name, acc_info, price = acc[0], acc[1], acc[2], acc[3]

        if user_data['balance'] < price:
            conn.close()
            await query.edit_message_text(f"❌ Bạn không đủ số dư để mua!\nGiá: {price:,.0f} VNĐ\nSố dư: {user_data['balance']:,.0f} VNĐ", reply_markup=back_home_keyboard())
            return

        new_balance = user_data['balance'] - price
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        cursor.execute("UPDATE inventory SET status = 'SOLD' WHERE id = ?", (acc_id,))
        
        description_text = f"Mua {platform} - {p_name} | {acc_info}"
        cursor.execute("INSERT INTO history (user_id, type, description, amount) VALUES (?, 'PURCHASE', ?, ?)", 
                       (user_id, description_text, price))
        conn.commit()
        conn.close()

        success_msg = (
            f"🎉 Mua hàng thành công!\n"
            f"Sản phẩm: {platform} - {p_name}\n"
            f"Giá: {price:,.0f} VNĐ\n\n"
            f"🔑 Thông tin tài khoản thật:\n{acc_info}"
        )
        await query.edit_message_text(success_msg, reply_markup=back_home_keyboard())

    elif data.startswith("buynow_"):
        parts = data.split("_", 2)
        platform = parts[1]
        p_name = parts[2]

        conn = sqlite3.connect("bot_store.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, account_info, price FROM inventory WHERE LOWER(platform) = LOWER(?) AND product_name = ? AND status = 'AVAILABLE' LIMIT 1", (platform, p_name))
        acc = cursor.fetchone()

        if not acc:
            conn.close()
            await query.edit_message_text("❌ Tạm thời hết hàng cho sản phẩm này!", reply_markup=back_home_keyboard())
            return

        acc_id, acc_info, price = acc[0], acc[1], acc[2]

        if user_data['balance'] < price:
            conn.close()
            await query.edit_message_text(f"❌ Bạn không đủ số dư để mua!\nGiá: {price:,.0f} VNĐ\nSố dư: {user_data['balance']:,.0f} VNĐ", reply_markup=back_home_keyboard())
            return

        new_balance = user_data['balance'] - price
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        cursor.execute("UPDATE inventory SET status = 'SOLD' WHERE id = ?", (acc_id,))
        
        description_text = f"Mua {platform} - {p_name} | {acc_info}"
        cursor.execute("INSERT INTO history (user_id, type, description, amount) VALUES (?, 'PURCHASE', ?, ?)", 
                       (user_id, description_text, price))
        conn.commit()
        conn.close()

        success_msg = (
            f"🎉 Mua hàng thành công!\n"
            f"Sản phẩm: {platform} - {p_name}\n"
            f"Giá: {price:,.0f} VNĐ\n\n"
            f"🔑 Thông tin tài khoản thật:\n{acc_info}"
        )
        await query.edit_message_text(success_msg, reply_markup=back_home_keyboard())

    elif data == "menu_deposit":
        text = (
            "💳 Thông tin chuyển khoản nạp tiền\n\n"
            "• MoMo: 0901234567 (NGUYEN VAN A)\n"
            "• VPBank: 123456789 (NGUYEN VAN A)\n\n"
            "⏱ Thời gian duyệt: 8 - 12h\n"
            f"📝 Nội dung CK: NAP {user_id}"
        )
        await query.edit_message_text(text, reply_markup=back_home_keyboard())

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_user_message(update)
    if update.effective_user.id != ADMIN_ID:
        return

    text = (
        "🛠 Bảng điều khiển Admin\n\n"
        "1. Cộng tiền (CT):\n"
        "Cú pháp: cộng <số tiền> <id_khách> <hoàn thành/fail> <lý do>\n\n"
        "2. Thêm tài khoản thật (THÊM):\n"
        "Cú pháp: thêm <nền_tảng> <tài_khoản> <mật_khẩu> <tên sản phẩm>\n"
        "Ví dụ: thêm Facebook user_abc pass123 via_cổ"
    )
    
    if "last_menu_id" in context.user_data:
        try:
            await context.bot.edit_message_text(
                text=text,
                chat_id=update.effective_chat.id,
                message_id=context.user_data["last_menu_id"]
            )
            return
        except Exception:
            pass

    sent_msg = await update.effective_chat.send_message(text)
    context.user_data["last_menu_id"] = sent_msg.message_id

async def handle_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_user_message(update)
    if update.effective_user.id != ADMIN_ID:
        return

    msg = update.message.text.strip()
    reply_text = ""

    if msg.lower().startswith("cộng "):
        try:
            content = msg[5:].strip()
            parts = content.split(" ", 3)
            amount = float(parts[0])
            target_user_id = int(parts[1])
            status = parts[2].lower()
            reason = parts[3] if len(parts) > 3 else "Nạp tiền Admin"

            if "hoàn" in status:
                conn = sqlite3.connect("bot_store.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_user_id))
                cursor.execute("INSERT INTO history (user_id, type, description, amount) VALUES (?, 'DEPOSIT', ?, ?)",
                               (target_user_id, f"Nạp tiền: {reason}", amount))
                conn.commit()
                conn.close()

                reply_text = f"✅ Đã cộng {amount:,.0f} VNĐ cho ID {target_user_id}. Lý do: {reason}"
                try:
                    await context.bot.send_message(chat_id=target_user_id, text=f"🎉 Bạn đã được cộng {amount:,.0f} VNĐ!\nLý do: {reason}")
                except Exception:
                    pass
            else:
                reply_text = f"❌ Giao dịch thất bại. Lý do: {reason}"
        except Exception as e:
            reply_text = f"⚠️ Cú pháp cộng tiền sai! Lỗi: {e}"

    elif msg.lower().startswith("thêm "):
        try:
            parts = msg.split()
            if len(parts) >= 4:
                platform = parts[1].capitalize()
                acc_user = parts[2]
                acc_pass = parts[3]
                product_name = " ".join(parts[4:]) if len(parts) > 4 else "Tài khoản chung"
                account_info = f"User: {acc_user} | Pass: {acc_pass}"
                price = 2000

                conn = sqlite3.connect("bot_store.db")
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO inventory (platform, product_name, account_info, price, status) VALUES (?, ?, ?, ?, 'AVAILABLE')",
                    (platform, product_name, account_info, price)
                )
                conn.commit()
                
                cursor.execute("SELECT COUNT(*) FROM inventory WHERE platform = ? AND status = 'AVAILABLE'", (platform,))
                total_qty = cursor.fetchone()[0]
                conn.close()

                reply_text = f"✅ Đã thêm 1 tài khoản thật vào kho {platform} ({product_name})!\n📦 Tổng kho {platform} hiện có: {total_qty}"
            else:
                reply_text = "⚠️ Cú pháp thiếu thông tin! VD: thêm Facebook user pass tên_sp"
        except Exception as e:
            reply_text = f"⚠️ Lỗi thêm tài khoản: {e}"

    if reply_text:
        if "last_menu_id" in context.user_data:
            try:
                await context.bot.edit_message_text(
                    text=reply_text,
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data["last_menu_id"]
                )
                return
            except Exception:
                pass
        sent_msg = await update.effective_chat.send_message(reply_text)
        context.user_data["last_menu_id"] = sent_msg.message_id

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_admin_commands))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()