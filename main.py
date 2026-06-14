import logging
import re
import os
import threading
import io
import time
import requests
import random
import sys
import asyncio
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from motor.motor_asyncio import AsyncIOMotorClient
from flask import Flask
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

# ========================================================
# ⚙️ SYSTEM CORE & PRODUCTION CREDENTIALS
# ========================================================
MASTER_OWNER_ID = 6015356597 
CREATOR_IDS = [6015356597, 7189668208, 7954534406, 6487086190, 6220068124] 
OWNER_USERNAME = "Hello_Im_DexterMorgan"
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"
API_ID = 35766004
API_HASH = 'd15b4226b81724722279bae6af69e22d'
BOT_TOKEN = "7857238353:AAEkDQnXqxyvXOQufwJwzZ7tXlwrmzM6XyI"
TARGET_GROUP_ID = -1003707008733
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# 📁 Database Connections
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client['telegram_bot']
neweraborn_col = db["neweraborn"]   # 🌟 String Session နှင့် Prompts များသိမ်းဆည်းမည့် New Collection
talk_col = db["random_talk"]       # 💬 စာသားထောင်ပေါင်းများစွာရှိသည့် Collection

# 🤖 Runtime Global Memory Registries
ai_agents = {}          # { "1": client, "2": client ... }
agent_id_to_idx = {}    # { 12345678: "1", 87654321: "2" } -> သက်ဆိုင်ရာ Telegram ID အား အညွှန်းခွဲရန်
last_ai_speak_time = 0

app = Flask('')

@app.route('/')
def home():
    return "⚡ New Era Born: Multi-Agent Simulation Active 🔥"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ─── 🔄 GLOBAL ASYNCIO LOOP FIX FOR PYTHON 3.14 ───
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Overlord Manager Bot (ဆောက်ထားတဲ့ loop ကို explicit လှမ်းပေးလိုက်ပါတယ်)
bot = TelegramClient('manager_bot', API_ID, API_HASH, loop=loop)

# ========================================================
# 🔑 AGENT ACTIVATION RUNTIME (UP TO 4 ACCOUNTS)
# ========================================================
async def start_single_agent(agent_idx, session_string):
    global ai_agents, agent_id_to_idx
    try:
        if agent_idx in ai_agents:
            try: await ai_agents[agent_idx].disconnect()
            except: pass
            
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.start()
        
        me = await client.get_me()
        ai_agents[agent_idx] = client
        agent_id_to_idx[me.id] = agent_idx # ID အား မှတ်ပုံတင်ခြင်း
        
        # သက်ဆိုင်ရာ Agent Client ထဲသို့ သီးသန့် Event Listener များ ထည့်သွင်းခြင်း
        register_agent_events(client, agent_idx)
        
        # Status ကို Active အမြဲဖြစ်အောင် ထိန်းထားခြင်း
        asyncio.create_task(keep_agent_online(client, agent_idx))
        return True
    except Exception as e:
        logging.error(f"Agent {agent_idx} Initialization Failure: {e}")
        return False

async def keep_agent_online(client, agent_idx):
    while True:
        try:
            await client(functions.account.UpdateStatusRequest(offline=False))
        except: pass
        await asyncio.sleep(150)

# ========================================================
# 🎭 DYNAMIC AI SIMULATION & BEHAVIOR GRID
# ========================================================


def register_agent_events(client, agent_idx):
    agent_info = AI_AGENTS_CONFIG[agent_idx]

    @client.on(events.NewMessage(chats=TARGET_GROUP_ID, incoming=True))
    async def simulation_intellect_loop(event):
        global last_ai_speak_time
        if not event.text or event.text.startswith(('/', '.')): return
        
        sender = await event.get_sender()
        if not sender or getattr(sender, 'bot', False): return
        
        # 🔍 စာရိုက်သူသည် ဖန်ဆင်းရှင်အဖွဲ့ဝင် ဟုတ်/မဟုတ် စစ်ဆေးခြင်း
        is_creator = (sender.id in CREATOR_IDS)
        is_other_agent = (sender.id in agent_id_to_idx)
        
        # ─── 🛡️ SMART MATRIX CONTROLLER (MULTI-CREATOR) ───
        if is_creator:
            # ဖန်ဆင်းရှင် ဘယ်သူပဲစာရိုက်ရိုက် AI အေးဂျင့်များက ၁၀၀% ဦးညွှတ်ပြီး ချက်ချင်း တုံ့ပြန်မယ်
            reply_chance = 1.0
            delay = random.randint(1, 3) 
        elif is_other_agent:
            # အေးဂျင့်အချင်းချင်း ဖြစ်ပါက Loop မပတ်အောင် ထိန်းချုပ်ခြင်း
            current_time = time.time()
            if current_time - last_ai_speak_time < 10: return
                
            reply_chance = 0.35 
            delay = random.randint(3, 6) 
        else:
            return

        if random.random() < reply_chance:
            await asyncio.sleep(delay)
            
            agent_data = await neweraborn_col.find_one({"agent_idx": agent_idx})
            system_prompt = agent_data.get("system_prompt") if agent_data else None
            if not system_prompt: return 

            try:
                url = "https://models.inference.ai.azure.com/chat/completions"
                headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Content-Type": "application/json"}
                
                payload = {
                    "messages": [
                        {"role": "system", "content": f"{system_prompt}\nCRITICAL Directive: Respond in raw, flawless, masculine native Burmese slang."},
                        {"role": "user", "content": event.text}
                    ],
                    "model": "gpt-4o-mini",
                    "temperature": 0.65
                }
                res = requests.post(url, headers=headers, json=payload).json()
                if "choices" in res and res["choices"]:
                    ai_response = res["choices"][0]["message"]["content"]
                    
                    await event.reply(ai_response)
                    if is_other_agent: last_ai_speak_time = time.time()
                    
                    # 📩 Absolute Reporting: ဘယ်ဖန်ဆင်းရှင်က လာမွှေသွားလဲဆိုတာ ဆရာ့ (MASTER_OWNER) DM ကိုပဲ အကုန်ပို့ပေးမှာပါ
                    sender_name = getattr(sender, 'first_name', 'Unknown Creator')
                    await bot.send_message(MASTER_OWNER_ID, f"🤖 **[DM REPORT] Agent {agent_idx} Triggered by God!**\n"
                                                           f"┆ 👑 **Creator:** {sender_name} (ID: {sender.id})\n"
                                                           f"┆ 🌐 **Prompt/Text:** {event.text}\n"
                                                           f"┆ 📤 **AI Response:** {ai_response}\n"
                                                           f"╰───────────────────────────────────❖")
            except Exception as e:
                logging.error(f"Agent {agent_idx} Error: {e}")
              

# ========================================================
# 🎛️ OVERLORD MASTER CONTROL INTERFACE (MAIN BOT)
# ========================================================

# ၁။ /born [Index] [Session] - String Session သစ်များအား ၄ ခုအထိ သိမ်းဆည်း အသက်သွင်းခြင်း
@bot.on(events.NewMessage(pattern=r'^/born (\d) (.*)'))
async def born_new_era_agent(event):
    if event.sender_id != OWNER_ID: return
    idx = event.pattern_match.group(1).strip()
    session_string = event.pattern_match.group(2).strip()
    
    if idx not in ["1", "2", "3", "4"]:
        return await event.reply("❌ Agent Index သည် 1, 2, 3, 4 သာ ဖြစ်ရပါမည်။")
        
    await event.reply(f"⏳ New Era Database တွင် Node {idx} အား နေရာချထားပါသည်...")
    
    # Storage into new collection
    await neweraborn_col.update_one(
        {"agent_idx": idx},
        {"$set": {"session_string": session_string}},
        upsert=True
    )
    
    success = await start_single_agent(idx, session_string)
    if success:
        await event.reply(f"🟢 Agent {idx} အသစ် အောင်မြင်စွာ ဖန်တီးခဲ့သည်။")
        await bot.send_message(OWNER_ID, f"ℹ️ System Deployment: Agent {idx} Connection initialized on Cloud Matrix.")
    else:
        await event.reply(f"❌ Agent {idx} မွေးဖွားမှု မအောင်မြင်ပါ။ String Session ကို စစ်ဆေးပါ။")

# ၂။ စရိုက်လက္ခဏာ (Prompt Trainer) - Agent ရဲ့စာကို Reply ထောက်ပြီး prompt ပေးမှ DB ထဲမှတ်ခြင်း
@bot.on(events.NewMessage(chats=TARGET_GROUP_ID))
async def train_agent_persona_prompt(event):
    if event.sender_id != OWNER_ID or not event.is_reply: return
    if not event.text or event.text.startswith(('/', '.')): return
    
    # Reply ထောက်ထားသည့် စာသားအား စစ်ဆေးခြင်း
    reply_msg = await event.get_reply_message()
    target_agent_id = reply_msg.sender_id
    
    # ၎င်း ID သည် ကျွန်ုပ်တို့ အသက်သွင်းထားသော Agent ဖြစ်ပါက
    if target_agent_id in agent_id_to_idx:
        idx = agent_id_to_idx[target_agent_id]
        prompt_text = event.text.strip()
        
        # ဒေတာဘက်စ်ထဲ စနစ်တကျ မှတ်သားခြင်း
        await neweraborn_col.update_one(
            {"agent_idx": idx},
            {"$set": {"system_prompt": prompt_text}},
            upsert=True
        )
        
        await event.reply(f"📝 **Systematic Record Verified:** Agent {idx} ၏ ဉာဏ်ရည်တု စရိုက်စနစ်အား ပြောင်းလဲသတ်မှတ်ပြီးပါပြီ။")
        await bot.send_message(OWNER_ID, f"🤖 **[DM REPORT] Prompt Learned:** Owner trained Agent {idx} with core configuration:\n`{prompt_text}`")

# ၃။ 'တန်းစီ' Command - Active အကောင့်များအား talk col မှ စာတစ်ကြောင်းစီ ရေးခိုင်းခြင်း
@bot.on(events.NewMessage(chats=TARGET_GROUP_ID, pattern=r'^တန်းစီ$'))
async def line_up_and_shout(event):
    if event.sender_id != OWNER_ID: return
    
    await event.reply("🎭 စစ်ဆေးမှုပြီးမြောက်... ဖန်ဆင်းခံ အေးဂျင့်များ တန်းစီ စကားပြောခြင်း စနစ် စတင်ပြီ။")
    
    for idx in ["1", "2", "3", "4"]:
        client = ai_agents.get(idx)
        if not client: continue # အကယ်၍ အကောင့် မသွင်းရသေးပါက ကျော်သွားမည်
        
        # talk_col ထဲမှ စာသား တစ်ကြောင်းအား Random ဆွဲယူခြင်း
        pipeline = [{"$sample": {"size": 1}}]
        cursor = talk_col.aggregate(pipeline)
        docs = await cursor.to_list(length=1)
        
        shout_text = docs[0].get("text", "...") if docs else "..."
        
        # စာပို့ခြင်း
        await asyncio.sleep(random.uniform(1.0, 2.5)) # မသိသာအောင် ကြားထဲ ဖြတ်စောင့်ခြင်း
        await client.send_message(TARGET_GROUP_ID, shout_text)
        
        # တင်ပြခြင်းစနစ်
        await bot.send_message(OWNER_ID, f"🤖 **[DM REPORT] Agent {idx} Action:** Executed 'တန်းစီ' line-shout -> `{shout_text}`")

# ၄။ /name [နာမည်သစ်] - ပြောင်းလဲလိုသော Agent ၏ စာအား Reply ထောက်ကာ နာမည်ပြောင်းလဲခြင်း
@bot.on(events.NewMessage(chats=TARGET_GROUP_ID, pattern=r'^/name\s+(.*)'))
async def change_agent_profile_name(event):
    if event.sender_id != OWNER_ID or not event.is_reply: return
    
    reply_msg = await event.get_reply_message()
    target_id = reply_msg.sender_id
    
    if target_id in agent_id_to_idx:
        idx = agent_id_to_idx[target_id]
        new_name = event.pattern_match.group(1).strip()
        client = ai_agents[idx]
        
        try:
            await client(functions.account.UpdateProfileRequest(first_name=new_name, last_name=""))
            await event.reply(f"✨ **Identity Shifted:** Agent {idx} ၏ အမည်အား `{new_name}` သို့ ပြောင်းလဲပြီးပါပြီ။")
            await bot.send_message(OWNER_ID, f"🤖 **[DM REPORT] Profile Modified:** Agent {idx} changed profile first_name to `{new_name}`")
        except Exception as e:
            await event.reply(f"❌ Name Change Failed: {e}")

# ========================================================
# 🚀 AUTOMATIC CLOUD INITIATOR & BOOTSTRAP
# ========================================================
async def auto_load_all_born_agents():
    print("🔄 Pulling Active Entities from neweraborn Collection...")
    async for config in neweraborn_col.find():
        idx = config.get("agent_idx")
        session = config.get("session_string")
        if idx and session:
            print(f"📦 Resurrecting Agent {idx} from DB Matrix...")
            await start_single_agent(idx, session)

async def main_execution_grid():
    # Production Uptime Listener Port
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Run Overlord Engine
    await bot.start(bot_token=BOT_TOKEN)
    print("🟢 Overlord Core Manager Infrastructure Ready.")
    
    # Auto Resurrection loop
    await auto_load_all_born_agents()
    await bot.run_until_disconnected()

if __name__ == '__main__':
    # asyncio.run() အစား အပေါ်က ဆောက်ခဲ့တဲ့ loop နဲ့ တိုက်ရိုက် run စေခြင်း
    loop.run_until_complete(main_execution_grid())
    
