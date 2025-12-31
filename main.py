import os
import json
import asyncio
from telethon import TelegramClient, events, Button
from flask import Flask
from threading import Thread

# ================= تنظیمات سرور (برای ۲۴ ساعته ماندن) =================
app = Flask('')

@app.route('/')
def home():
    return "I am alive! Bot is running..."

def run_web():
    # این پورت برای Render و سرویس‌های ابری ضروری است
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ================= تنظیمات ربات =================
# ⚠️ حتماً اطلاعات خودت رو اینجا جایگزین کن
API_ID = 12345678  # جایگزین کن
API_HASH = 'YOUR_API_HASH_HERE' # جایگزین کن
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE' # جایگزین کن

HARDCODED_BOSSES = [5503318159, 60494146]
DB_FILE = "final_bot_db.json"
conv_state = {} 

# ================= دیتابیس =================
def load_data():
    default = {"groups": {}, "extra_bosses": []}
    if not os.path.exists(DB_FILE): return default
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except: return default

def save_data(data):
    try:
        with open(DB_FILE, 'w') as f: json.dump(data, f)
    except: pass

def is_boss(user_id):
    data = load_data()
    return (user_id in HARDCODED_BOSSES) or (user_id in data.get('extra_bosses', []))

client = TelegramClient('bot_session', API_ID, API_HASH)

# ================= پنل مدیریت =================
async def main_menu_keyboard():
    return [
        [Button.inline("Add Admin (Select Group)", b"btn_add_admin_menu"), Button.inline("Remove Admin", b"btn_del_admin_select_g")],
        [Button.inline("Connect Channel", b"btn_connect"), Button.inline("Add Boss", b"btn_add_boss")],
        [Button.inline("List Admins", b"btn_list_admins"), Button.inline("Close", b"btn_close")]
    ]

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if event.is_group: return 
    if is_boss(event.sender_id):
        conv_state[event.sender_id] = None
        await event.reply("Welcome Boss!", buttons=await main_menu_keyboard())
    else:
        await event.reply("Access Denied.")

@client.on(events.CallbackQuery)
async def callback_handler(event):
    uid = event.sender_id
    if not is_boss(uid): return await event.answer("No Access!", alert=True)

    cmd = event.data.decode()
    
    if cmd == "main_menu":
        conv_state[uid] = None
        await event.edit("Main Menu:", buttons=await main_menu_keyboard())
        return
    if cmd == "btn_close": await event.delete(); return

    if cmd == "btn_add_admin_menu":
        data = load_data()
        btns = []
        for g_id in data['groups']:
            btns.append([Button.inline(f"Group: {g_id}", f"sel_add_g_{g_id}".encode())])
        btns.append([Button.inline("Back", b"main_menu")])
        if len(btns) == 1: 
            await event.answer("No groups found. Run /run in a group.", alert=True)
        else:
            await event.edit("Select Group:", buttons=btns)

    elif cmd == "btn_connect":
        conv_state[uid] = "wait_g_connect"
        await event.edit("Send Group ID:", buttons=[Button.inline("Cancel", b"main_menu")])

    elif cmd == "btn_add_boss":
        conv_state[uid] = "wait_new_boss"
        await event.edit("Send New Boss ID:", buttons=[Button.inline("Cancel", b"main_menu")])

    elif cmd == "btn_del_admin_select_g":
        data = load_data()
        btns = []
        for g_id in data['groups']:
            if data['groups'][g_id]['admins']:
                btns.append([Button.inline(f"Group: {g_id}", f"sel_del_g_{g_id}".encode())])
        btns.append([Button.inline("Back", b"main_menu")])
        if not btns or len(btns)==1: await event.answer("No admins found.", alert=True)
        else: await event.edit("Select Group:", buttons=btns)

    elif cmd == "btn_list_admins":
        data = load_data()
        btns = []
        for g_id in data['groups']:
            if data['groups'][g_id]['admins']:
                btns.append([Button.inline(f"Group: {g_id}", f"sel_list_g_{g_id}".encode())])
        btns.append([Button.inline("Back", b"main_menu")])
        if len(btns)==1: await event.answer("List is empty.", alert=True)
        else: await event.edit("Select Group:", buttons=btns)

    elif cmd.startswith("sel_add_g_"):
        g_id = cmd.replace("sel_add_g_", "")
        conv_state[uid] = f"adding_admin_to|{g_id}"
        await event.edit(f"Group {g_id} selected.\nSend Admin ID (Number) or Forward message:", buttons=[Button.inline("Cancel", b"main_menu")])

    elif cmd.startswith("sel_del_g_"):
        g_id = cmd.replace("sel_del_g_", "")
        data = load_data()
        admins = data['groups'][g_id]['admins']
        btns = []
        for admin_id in admins:
            btns.append([Button.inline(f"Remove {admin_id}", f"do_del_{g_id}_{admin_id}".encode())])
        btns.append([Button.inline("Back", b"main_menu")])
        await event.edit(f"Remove admin from {g_id}:", buttons=btns)

    elif cmd.startswith("do_del_"):
        parts = cmd.split('_')
        g_id, admin_id = parts[2], int(parts[3])
        data = load_data()
        if admin_id in data['groups'][g_id]['admins']:
            data['groups'][g_id]['admins'].remove(admin_id)
            save_data(data)
            await event.answer("Removed.", alert=True)
            await event.edit("Back to menu.", buttons=await main_menu_keyboard())
        else:
            await event.answer("Already removed.", alert=True)

    elif cmd.startswith("sel_list_g_"):
        g_id = cmd.replace("sel_list_g_", "")
        data = load_data()
        admins = data['groups'][g_id]['admins']
        txt = f"Admins in {g_id}:\n\n"
        for a in admins: txt += f"{a}\n"
        await event.edit(txt, buttons=[Button.inline("Back", b"main_menu")])

@client.on(events.NewMessage)
async def input_handler(event):
    if event.is_group: return 
    uid = event.sender_id
    if uid not in conv_state or not conv_state[uid]: return

    st = conv_state[uid]
    text = event.message.text
    target_id = str(event.message.forward.chat_id) if (event.message.forward and event.message.forward.chat_id) else text

    if st.startswith("adding_admin_to|"):
        g_id = st.split("|")[1]
        new_ids = []
        if event.message.forward and event.message.forward.sender_id:
            new_ids.append(event.message.forward.sender_id)
        else:
            new_ids = [int(x) for x in text.replace('\n', ' ').split() if x.isdigit()]

        if not new_ids:
            await event.reply("⚠️ No ID found!")
            return

        data = load_data()
        if g_id not in data['groups']: 
             await event.reply("Error: Group mismatch.")
             return

        count = 0
        for i in new_ids:
            if i not in data['groups'][g_id]['admins']:
                data['groups'][g_id]['admins'].append(i)
                count += 1
        save_data(data)
        await event.reply(f"✅ {count} Admin(s) added.", buttons=[Button.inline("Menu", b"main_menu")])
        conv_state[uid] = None

    elif st == "wait_g_connect":
        conv_state[uid] = f"connecting_g|{target_id}"
        await event.reply(f"Group {target_id} selected.\nNow send Channel ID:", buttons=[Button.inline("Cancel", b"main_menu")])
    
    elif st.startswith("connecting_g|"):
        g_id = st.split("|")[1]
        try:
            c_id = int(target_id)
            data = load_data()
            if g_id not in data['groups']: data['groups'][g_id] = {"channel": 0, "admins": []}
            data['groups'][g_id]['channel'] = c_id
            save_data(data)
            await event.reply(f"Connected!\nGroup: {g_id}\nChannel: {c_id}", buttons=[Button.inline("Menu", b"main_menu")])
            conv_state[uid] = None
        except: await event.reply("Channel ID must be a number.")

    elif st == "wait_new_boss":
        try:
            new_boss = int(target_id)
            data = load_data()
            if new_boss not in data['extra_bosses']:
                data['extra_bosses'].append(new_boss)
                save_data(data)
                await event.reply(f"New Boss ({new_boss}) added.", buttons=[Button.inline("Menu", b"main_menu")])
            else: await event.reply("Already Boss.", buttons=[Button.inline("Menu", b"main_menu")])
            conv_state[uid] = None
        except: await event.reply("Must be a number.")

# ================= دستورات گروهی =================
@client.on(events.NewMessage(pattern='/run'))
async def run_group(event):
    if not event.is_group: return
    if not is_boss(event.sender_id): return
    g_id = str(event.chat_id)
    data = load_data()
    if g_id not in data['groups']:
        data['groups'][g_id] = {"channel": 0, "admins": []}
        save_data(data)
        await event.reply(f"Bot Started!\nGroup ID: {g_id}\nConnect channel: /setchannel -100...")
    else: await event.reply(f"Already running.\nGroup ID: {g_id}")

@client.on(events.NewMessage(pattern='/setchannel'))
async def set_channel_cmd(event):
    if not event.is_group or not is_boss(event.sender_id): return
    g_id = str(event.chat_id)
    data = load_data()
    if g_id not in data['groups']: return await event.reply("Run /run first.")
    try:
        c_id = int(event.message.text.split()[1])
        data['groups'][g_id]['channel'] = c_id
        save_data(data)
        await event.reply(f"Connected to: {c_id}")
    except: await event.reply("Usage: /setchannel -100123456")

@client.on(events.NewMessage(pattern='/addadmin'))
async def add_admin_cmd(event):
    if not event.is_group or not is_boss(event.sender_id): return
    if not event.is_reply:
        return await event.reply("⚠️ Reply to user.")
    g_id = str(event.chat_id)
    data = load_data()
    if g_id not in data['groups']: return
    user = await event.get_reply_message()
    new_admin = user.sender_id
    if new_admin not in data['groups'][g_id]['admins']:
        data['groups'][g_id]['admins'].append(new_admin)
        save_data(data)
        await event.reply(f"User {new_admin} added.")
    else: await event.reply("Already admin.")

@client.on(events.NewMessage(pattern='/deladmin'))
async def del_admin_cmd(event):
    if not event.is_group or not is_boss(event.sender_id): return
    if not event.is_reply:
        return await event.reply("⚠️ Reply to user.")
    g_id = str(event.chat_id)
    data = load_data()
    user = await event.get_reply_message()
    target = user.sender_id
    if g_id in data['groups'] and target in data['groups'][g_id]['admins']:
        data['groups'][g_id]['admins'].remove(target)
        save_data(data)
        await event.reply("Removed.")
    else: await event.reply("Not admin.")

@client.on(events.NewMessage(pattern='/send'))
async def send_handler(event):
    if not event.is_group or not event.is_reply: return
    sender = event.sender_id
    g_id = str(event.chat_id)
    data = load_data()
    if g_id not in data['groups']: return
    boss = is_boss(sender)
    admin = sender in data['groups'][g_id]['admins']
    if not (boss or admin): return 
    c_id = data['groups'][g_id]['channel']
    if c_id == 0:
        if boss: await event.reply("Channel not set!")
        return
    replied = await event.get_reply_message()
    if not boss and replied.sender_id != sender:
        msg = await event.reply("Only your own messages!")
        await asyncio.sleep(3); await msg.delete(); await event.delete(); return
    try:
        try: channel_entity = await client.get_entity(c_id)
        except: return await event.reply("⚠️ Bot can't find channel. Send a message there.")
        if replied.media:
            sent = await client.send_file(channel_entity, replied.media, caption=replied.text, attributes=replied.document.attributes if replied.document else None, force_document=False)
        else:
            sent = await client.send_message(channel_entity, replied.text, link_preview=False)
        cb = f"del_{c_id}_{sent.id}_{sender}".encode()
        await event.reply(f"Sent!", buttons=[[Button.inline("Delete", cb)]])
    except Exception as e: await event.reply(f"Error: {e}")

@client.on(events.CallbackQuery(pattern=b'del_'))
async def delete_post_callback(event):
    parts = event.data.decode().split('_')
    c_id, m_id, owner = int(parts[1]), int(parts[2]), int(parts[3])
    if event.sender_id == owner or is_boss(event.sender_id):
        try: await client.delete_messages(c_id, m_id); await event.edit("Deleted.")
        except: await event.answer("Error", alert=True)
    else: await event.answer("Not yours!", alert=True)

# استارت سرور بیدارباش و ربات
keep_alive()
print("Bot Started...")
client.start(bot_token=BOT_TOKEN)
client.run_until_disconnected()
