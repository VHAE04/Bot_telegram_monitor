from tokens import *
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
cpu_threshold = 50
poll = 300
proxy_base_url = f"https://xxx-proxy-telegram.xxx.workers.dev/bot{telegrambot}"

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
/memgraph - Show memory usage graph
/cpugraph - Show CPU usage graph
/shell - Execute shell commands
/setmem - Set memory threshold for alerts
/setpoll - Set polling interval

Current memory threshold: {}%
Current polling interval: {} seconds
"""

# --- Telegram Communication ---
def send_telegram_message(chat_id, message, parse_mode="Markdown"):
    url = f"{proxy_base_url}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
    }
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
    plt.figure()
    plt.xlabel(tmperiod)
    plt.ylabel('% Used')
    plt.title('Memory Usage Graph')
    plt.plot(xaxis, memlist, 'b-', label='Memory Usage')
    plt.plot(xaxis, [memorythreshold]*len(xaxis), 'r--', label='Threshold')
    plt.legend()
    plt.axis([0, len(xaxis)-1, 0, 100])
    plt.savefig('graph.png')
    plt.close()
    return open('graph.png', 'rb')

def plotcpugraph(cpulist, xaxis, tmperiod):
    plt.figure()
    plt.xlabel(tmperiod)
    plt.ylabel('% Used')
    plt.title('CPU Usage Graph')
    plt.plot(xaxis, cpulist, 'g-', label='CPU Usage')
    plt.plot(xaxis, [cpu_threshold]*len(xaxis), 'r--', label='Threshold')
    plt.legend()
    plt.axis([0, len(xaxis)-1, 0, 100])
    plt.savefig('cpugraph.png')
    plt.close()
    return open('cpugraph.png', 'rb')

# --- Helpers ---
def clearall(chat_id):
    for lst in (shellexecution, settingmemth, setpolling):
        if chat_id in lst:
            lst.remove(chat_id)

def send_long_message(chat_id, text, max_length=4000):
    for i in range(0, len(text), max_length):
        send_telegram_message(chat_id, text[i:i+max_length])

# --- Command Handler ---
def handle_command(chat_id, text):
    global memorythreshold, poll

    if text == '/stats' and chat_id not in shellexecution:
        send_chat_action(chat_id)
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        boottime = datetime.fromtimestamp(psutil.boot_time())
        now = datetime.now()
        timedif = f"Online for: {(now - boottime).total_seconds() / 3600:.1f} Hours"
        reply = (
            f"{timedif}\n"
            f"Total memory: {memory.total / 1e9:.2f} GB\n"
            f"Available memory: {memory.available / 1e9:.2f} GB\n"
            f"Used memory: {memory.percent}%\n"
            f"CPU usage: {cpu:.2f}%\n"
            f"Disk used: {disk.percent}%\n"
        )
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
            send_long_message(chat_id, output if output else "No output.")
        except Exception as e:
            send_telegram_message(chat_id, f"Error: {e}")

    elif text == '/memgraph':
        send_chat_action(chat_id)
        tmperiod = "Last 10 seconds"
        send_telegram_photo(chat_id, plotmemgraph(memlist, xaxis, tmperiod))

    elif text == '/cpugraph':
        send_chat_action(chat_id)
        tmperiod = "Last 10 seconds"
        send_telegram_photo(chat_id, plotcpugraph(cpulist, xaxis, tmperiod))

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
                send_telegram_message(adminid, f"\u26a0\ufe0f CRITICAL MEMORY: {mem.available / 1e9:.2f} GB available")
                send_telegram_photo(adminid, plotmemgraph(memlist, xaxis, "Last 10 seconds"))

    if cpu > cpu_threshold:
        for adminid in adminchatid:
            send_telegram_message(adminid, f"\u26a0\ufe0f HIGH CPU USAGE: {cpu:.2f}%")

    time.sleep(1)
    tr += 1
