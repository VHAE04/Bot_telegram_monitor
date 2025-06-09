from tokens import *  # telegrambot, adminchatid
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import psutil
import time
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
import requests

# --- Configuration ---
memorythreshold = 85
poll = 300
# --- thay link proxy clooudflare vao day
proxy_base_url = f"https://xxx-proxy-telegram.xxxx.workers.dev/bot{telegrambot}"

# --- State ---
shellexecution = []
timelist = []
memlist = []
cpulist = []
xaxis = []
settingmemth = []
setpolling = []
graphstart = datetime.now()
last_update_id = 0

# --- Message Templates ---
help_message = """
*Server Stats Bot Commands*
/help - Show this help message
/stats - Display server statistics (CPU, memory, disk usage)
/memgraph - Show memory usage graph (last 10s)
/cpugraph - Show CPU usage graph (last 10s)
/shell - Execute shell commands
/setmem - Set memory threshold for alerts
/setpoll - Set polling interval

Current memory threshold: {}%
Current polling interval: {} seconds
"""

# --- Telegram Communication ---
def send_telegram_message(chat_id, message, parse_mode="Markdown"):
    url = f"{proxy_base_url}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": parse_mode}
    requests.post(url, data=data)

def send_telegram_photo(chat_id, photo_file):
    url = f"{proxy_base_url}/sendPhoto"
    files = {'photo': photo_file}
    data = {"chat_id": chat_id}
    requests.post(url, files=files, data=data)

def send_chat_action(chat_id, action="typing"):
    url = f"{proxy_base_url}/sendChatAction"
    data = {"chat_id": chat_id, "action": action}
    requests.post(url, data=data)

def get_updates(offset=None):
    url = f"{proxy_base_url}/getUpdates"
    params = {'timeout': 30}
    if offset:
        params['offset'] = offset
    return requests.get(url, params=params).json()

# --- Graph Functions ---
def plotmemgraph(memlist, xaxis, tmperiod):
    plt.figure(figsize=(8, 4))
    plt.xlabel(tmperiod)
    plt.ylabel('% Used')
    plt.title('Memory Usage (Last 10 seconds)')
    plt.plot(xaxis, memlist, 'b-', label='Memory Usage')
    plt.axhline(y=memorythreshold, color='r', linestyle='--', label='Threshold')
    plt.ylim(0, 100)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig('graph.png')
    plt.close()
    return open('graph.png', 'rb')

def plotcpugraph(cpulist, xaxis, tmperiod):
    plt.figure(figsize=(8, 4))
    plt.xlabel(tmperiod)
    plt.ylabel('% Used')
    plt.title('CPU Usage (Last 10 seconds)')
    plt.plot(xaxis, cpulist, 'g-', label='CPU Usage')
    plt.ylim(0, 100)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig('cpugraph.png')
    plt.close()
    return open('cpugraph.png', 'rb')

# --- Core ---
def clearall(chat_id):
    for lst in (shellexecution, settingmemth, setpolling):
        if chat_id in lst:
            lst.remove(chat_id)

def send_long_message(chat_id, text, max_length=4000):
    for i in range(0, len(text), max_length):
        send_telegram_message(chat_id, text[i:i+max_length])

def handle_command(chat_id, text):
    global memorythreshold, poll

    if text == '/stats' and chat_id not in shellexecution:
        send_chat_action(chat_id)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boottime = datetime.fromtimestamp(psutil.boot_time())
        now = datetime.now()
        timedif = f"Online for: {(now - boottime).total_seconds() / 3600:.1f} Hours"
        reply = (
            f"{timedif}\n"
            f"Total memory: {memory.total / 1e9:.2f} GB\n"
            f"Available memory: {memory.available / 1e9:.2f} GB\n"
            f"Used memory: {memory.percent}%\n"
            f"Disk used: {disk.percent}%\n\n"
        )
        procs = {}
        for pid in psutil.pids():
            try:
                p = psutil.Process(pid)
                pmem = p.memory_percent()
                if pmem > 0.5:
                    procs[p.name()] = procs.get(p.name(), 0) + pmem
            except:
                continue
        for name, percent in sorted(procs.items(), key=lambda x: x[1], reverse=True):
            reply += f"{name} {percent:.2f}%\n"
        send_long_message(chat_id, reply)

    elif text == '/setpoll' and chat_id not in setpolling:
        setpolling.append(chat_id)
        send_telegram_message(chat_id, "Send polling interval (seconds > 10)")

    elif chat_id in setpolling:
        try:
            val = int(text)
            if val > 10:
                poll = val
                send_telegram_message(chat_id, "Polling interval updated.")
                clearall(chat_id)
            else:
                raise ValueError
        except:
            send_telegram_message(chat_id, "Invalid value. Must be an integer > 10.")

    elif text == '/setmem' and chat_id not in settingmemth:
        settingmemth.append(chat_id)
        send_telegram_message(chat_id, "Send new memory threshold (% < 100)")

    elif chat_id in settingmemth:
        try:
            val = int(text)
            if val < 100:
                memorythreshold = val
                send_telegram_message(chat_id, "Memory threshold updated.")
                clearall(chat_id)
            else:
                raise ValueError
        except:
            send_telegram_message(chat_id, "Invalid value. Must be an integer < 100.")

    elif text == '/shell' and chat_id not in shellexecution:
        shellexecution.append(chat_id)
        send_telegram_message(chat_id, "Send shell command to execute")

    elif chat_id in shellexecution:
        try:
            p = Popen(text, shell=True, stdout=PIPE, stderr=STDOUT)
            output = p.stdout.read().decode()
            if output:
                send_long_message(chat_id, output)
            else:
                send_telegram_message(chat_id, "No output.")
        except Exception as e:
            send_telegram_message(chat_id, f"Error: {e}")

    elif text == '/memgraph':
        send_chat_action(chat_id)
        send_telegram_photo(chat_id, plotmemgraph(memlist, xaxis, "Time (s)"))

    elif text == '/cpugraph':
        send_chat_action(chat_id)
        send_telegram_photo(chat_id, plotcpugraph(cpulist, xaxis, "Time (s)"))

    elif text == '/help' or text == '/start':
        msg = help_message.format(memorythreshold, poll)
        send_telegram_message(chat_id, msg)

    elif text.lower() == 'stop':
        clearall(chat_id)
        send_telegram_message(chat_id, "All operations stopped.")

# --- Main loop ---
print("Bot running...")
tr = 0
xx = 0

while True:
    updates = get_updates(last_update_id + 1)
    for update in updates.get("result", []):
        last_update_id = update["update_id"]
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")

        if chat_id in adminchatid and text:
            handle_command(chat_id, text)

    # Poll every second to get recent 10 seconds data
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)

    if len(memlist) >= 10:
        memlist.pop(0)
        cpulist.pop(0)
        xaxis.pop(0)

    memlist.append(mem.percent)
    cpulist.append(cpu)
    xaxis.append(xx)
    xx += 1

    if tr >= poll:
        tr = 0
        if mem.percent > memorythreshold:
            for adminid in adminchatid:
                send_telegram_message(adminid, f"⚠️ CRITICAL MEMORY: {mem.available / 1e9:.2f} GB available")
                send_telegram_photo(adminid, plotmemgraph(memlist, xaxis, "Last 10 seconds"))

    time.sleep(1)
    tr += 1
