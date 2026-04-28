import asyncio
import time
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ================= CONFIG =================
TOKEN = "8571259903:AAFCyMsZXiO3RervyGY2a0hMBmuJm84SzPA"
ADMIN_IDS = [8503115617, 6761125512]
SUPPORT_URL = "https://t.me/Mar1xff"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

DB = "store.db"

USD_TO_INR = 93
FLUCTUATION = 1.10


# ================= HELPERS =================
def convert_price(usd):
    return round(usd * USD_TO_INR * FLUCTUATION, 2)


def nav(back="menu"):
    return [
        [
            InlineKeyboardButton(text="🆘 Support", url=SUPPORT_URL),
            InlineKeyboardButton(text="🔙 Back", callback_data=back)
        ]
    ]


# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            total_spent REAL DEFAULT 0,
            purchases INTEGER DEFAULT 0
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product TEXT,
            price REAL,
            time INTEGER
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS banned (
            user_id INTEGER PRIMARY KEY
        )
        """)
        await db.commit()


async def is_banned(uid):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT 1 FROM banned WHERE user_id=?", (uid,))
        return await cur.fetchone() is not None


async def save_user(uid):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (uid,))
        await db.commit()


async def get_user(uid):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT balance, total_spent, purchases FROM users WHERE user_id=?",
            (uid,)
        )
        row = await cur.fetchone()
        return row if row else (0, 0, 0)


async def update_balance(uid, amount):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid))
        await db.commit()


async def deduct_balance(uid, amount):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, uid))
        await db.commit()


async def save_order(uid, product, price):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO orders (user_id, product, price, time) VALUES (?, ?, ?, ?)",
            (uid, product, price, int(time.time()))
        )
        await db.execute("""
        UPDATE users SET total_spent = total_spent + ?, purchases = purchases + 1 WHERE user_id = ?
        """, (price, uid))
        await db.commit()


# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛍 Shop", callback_data="shop"),
            InlineKeyboardButton(text="📦 Orders", callback_data="orders")
        ],
        [
            InlineKeyboardButton(text="📊 Stats", callback_data="stats"),
            InlineKeyboardButton(text="💰 Balance", callback_data="balance")
        ],
        [
            InlineKeyboardButton(text="📊 Transactions", callback_data="tx"),
            InlineKeyboardButton(text="🆘 Support", url=SUPPORT_URL)
        ]
    ])


# ================= START =================
@dp.message(Command("start"))
async def start(msg: Message):
    if await is_banned(msg.from_user.id):
        return await msg.answer("🚫 You are banned")

    await save_user(msg.from_user.id)
    bal, spent, purchases = await get_user(msg.from_user.id)

    await msg.answer(f"""
🛍 *WELCOME*

👤 {msg.from_user.first_name}

💰 Balance: ${bal}
📦 Purchases: {purchases}
💸 Spent: ${spent}
""", reply_markup=main_menu())


# ================= MENU CALLBACK =================
@dp.callback_query(F.data == "menu")
async def menu_cb(c: CallbackQuery):
    await c.answer()
    await c.message.edit_text("🏠 Main Menu", reply_markup=main_menu())


# ================= SHOP =================
@dp.callback_query(F.data == "shop")
async def shop(c: CallbackQuery):
    await c.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 IOS", callback_data="ios"),
            InlineKeyboardButton(text="🤖 ANDROID", callback_data="android")
        ],
        [
            InlineKeyboardButton(text="💻 PC", callback_data="pc")
        ],
        *nav("menu")
    ])

    await c.message.edit_text("🛒 Select platform:", reply_markup=kb)


# ================= PRODUCTS =================
PRODUCTS = {
    "ios": {
        "Fluorite": {"1D": 1.5, "7D": 5, "31D": 9},
        "Migul": {"1D": 1, "7D": 5, "31D": 8},
        "Proxy": {"1D": 1, "31D": 5}
    },
    "android": {
        "HG": {"1D": 1.5, "7D": 5, "31D": 9},
        "Drip": {"1D": 1.5, "7D": 5, "31D": 9}
    },
    "pc": {
        "Streamer": {"31D": 18, "LIFE": 28},
        "StreamerPlus": {"31D": 20, "LIFE": 30},
        "Obsidian": {"31D": 16, "LIFE": 26}
    }
}


# ================= CATEGORY =================
@dp.callback_query(F.data.in_(["ios", "android", "pc"]))
async def category(c: CallbackQuery):
    await c.answer()
    cat = c.data

    items = list(PRODUCTS[cat].keys())
    kb = []

    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(text=items[i], callback_data=f"item|{cat}|{items[i]}")]
        if i + 1 < len(items):
            row.append(InlineKeyboardButton(text=items[i+1], callback_data=f"item|{cat}|{items[i+1]}"))
        kb.append(row)

    kb.extend(nav("shop"))

    await c.message.edit_text("📦 Select product:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


# ================= ITEM =================
@dp.callback_query(F.data.startswith("item|"))
async def item(c: CallbackQuery):
    await c.answer()
    _, cat, item = c.data.split("|")

    kb = []
    for plan, price in PRODUCTS[cat][item].items():
        kb.append([
            InlineKeyboardButton(
                text=f"{plan} - ${price} / ₹{convert_price(price)}",
                callback_data=f"buy|{item}|{plan}|1|{price}"
            )
        ])

    kb.extend(nav(cat))

    await c.message.edit_text(f"💎 {item} Plans:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


# ================= BUY =================
@dp.callback_query(F.data.startswith("buy|"))
async def buy(c: CallbackQuery):
    await c.answer()

    _, item, plan, qty, total = c.data.split("|")
    total = float(total)

    bal, _, _ = await get_user(c.from_user.id)

    if bal < total:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Balance", callback_data="balance"),
                InlineKeyboardButton(text="📞 Contact", url=SUPPORT_URL)
            ],
            *nav("shop")
        ])

        return await c.message.edit_text(
            f"❌ Not enough balance\n\n💵 Need: ${total}\n🇮🇳 ₹{convert_price(total)}",
            reply_markup=kb
        )

    await deduct_balance(c.from_user.id, total)
    await save_order(c.from_user.id, f"{item} {plan} x{qty}", total)

    await c.message.edit_text(f"✅ Bought {item} {plan} x{qty}\nPaid: ${total}", reply_markup=InlineKeyboardMarkup(inline_keyboard=nav("menu")))


# ================= BALANCE =================
@dp.callback_query(F.data == "balance")
async def balance(c: CallbackQuery):
    await c.answer()
    bal, _, _ = await get_user(c.from_user.id)

    await c.message.edit_text(f"💰 Balance: ${bal}", reply_markup=InlineKeyboardMarkup(inline_keyboard=nav("menu")))


# ================= ORDERS =================
@dp.callback_query(F.data == "orders")
async def orders(c: CallbackQuery):
    await c.answer()

    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT product, price FROM orders WHERE user_id=?", (c.from_user.id,))
        rows = await cur.fetchall()

    text = "No orders" if not rows else "\n".join([f"{p} - ${pr}" for p, pr in rows])

    await c.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=nav("menu")))


# ================= STATS =================
@dp.callback_query(F.data == "stats")
async def stats(c: CallbackQuery):
    await c.answer()
    bal, spent, purchases = await get_user(c.from_user.id)

    await c.message.edit_text(
        f"📊 Stats\n💰 {bal}\n📦 {purchases}\n💸 {spent}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=nav("menu"))
    )


# ================= ADMIN =================
@dp.message(Command("addbalance"))
async def add_balance(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    _, uid, amount = msg.text.split()
    await save_user(int(uid))
    await update_balance(int(uid), float(amount))
    await msg.answer("✅ Added")


@dp.message(Command("removebalance"))
async def remove_balance(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    _, uid, amount = msg.text.split()
    await update_balance(int(uid), -float(amount))
    await msg.answer("❌ Removed")


@dp.message(Command("user"))
async def user_info(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    uid = int(msg.text.split()[1])
    bal, spent, purchases = await get_user(uid)
    await msg.answer(f"User {uid}\nBalance: ${bal}\nOrders: {purchases}\nSpent: ${spent}")


@dp.message(Command("stats"))
async def stats_admin(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    async with aiosqlite.connect(DB) as db:
        u = await db.execute("SELECT COUNT(*) FROM users")
        o = await db.execute("SELECT COUNT(*) FROM orders")
        await msg.answer(f"Users: {(await u.fetchone())[0]}\nOrders: {(await o.fetchone())[0]}")


# ================= RUN =================
async def main():
    await init_db()
    print("BOT RUNNING")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())