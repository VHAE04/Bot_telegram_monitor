from tokens import *
import matplotlib
matplotlib.use("Agg") # has to be before any other matplotlibs imports to set a "headless" backend
import matplotlib.pyplot as plt
import psutil
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
import operator
import collections
# import sys
import time
# import threading
# import random
import telepot
# from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardHide, ForceReply
# from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
# from telepot.namedtuple import InlineQueryResultArticle, InlineQueryResultPhoto, InputTextMessageContent



memorythreshold = 85  # If memory usage more this %
poll = 300  # seconds

# Define help message with available commands
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

shellexecution = []
timelist = []
memlist = []
cpulist = []  # Track CPU usage over time
xaxis = []
settingmemth = []
setpolling = []
graphstart = datetime.now()

stopmarkup = {'keyboard': [['Stop']]}
hide_keyboard = {'hide_keyboard': True}

def clearall(chat_id):
    if chat_id in shellexecution:
        shellexecution.remove(chat_id)
    if chat_id in settingmemth:
        settingmemth.remove(chat_id)
    if chat_id in setpolling:
        setpolling.remove(chat_id)

def plotmemgraph(memlist, xaxis, tmperiod):
    # print(memlist)
    # print(xaxis)
    plt.xlabel(tmperiod)
    plt.ylabel('% Used')
    plt.title('Memory Usage Graph')
    plt.text(0.1*len(xaxis), memorythreshold+2, 'Threshold: '+str(memorythreshold)+ ' %')
    memthresholdarr = []
    for xas in xaxis:
        memthresholdarr.append(memorythreshold)
    plt.plot(xaxis, memlist, 'b-', xaxis, memthresholdarr, 'r--')
    plt.axis([0, len(xaxis)-1, 0, 100])
    plt.savefig('graph.png')
    plt.close()
    f = open('graph.png', 'rb')  # some file on local disk
    return f

def plotcpugraph(cpulist, xaxis, tmperiod):
    plt.figure(figsize=(10, 6))
    plt.xlabel(tmperiod)
    plt.ylabel('% Used')
    plt.title('CPU Usage Graph')
    plt.plot(xaxis, cpulist, 'g-')  # Green line for CPU usage
    plt.axis([0, len(xaxis)-1, 0, 100])
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.savefig('cpugraph.png')
    plt.close()
    f = open('cpugraph.png', 'rb')
    return f

class YourBot(telepot.Bot):
    def __init__(self, *args, **kwargs):
        super(YourBot, self).__init__(*args, **kwargs)
        self._answerer = telepot.helper.Answerer(self)
        self._message_with_inline_keyboard = None

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        # Do your stuff according to `content_type` ...
        print("Your chat_id:" + str(chat_id)) # this will tell you your chat_id
        if chat_id in adminchatid:  # Store adminchatid variable in tokens.py
            if content_type == 'text':
                if msg['text'] == '/stats' and chat_id not in shellexecution:
                    bot.sendChatAction(chat_id, 'typing')
                    memory = psutil.virtual_memory()
                    disk = psutil.disk_usage('/')
                    boottime = datetime.fromtimestamp(psutil.boot_time())
                    now = datetime.now()
                    timedif = "Online for: %.1f Hours" % (((now - boottime).total_seconds()) / 3600)
                    memtotal = "Total memory: %.2f GB " % (memory.total / 1000000000)
                    memavail = "Available memory: %.2f GB" % (memory.available / 1000000000)
                    memuseperc = "Used memory: " + str(memory.percent) + " %"
                    diskused = "Disk used: " + str(disk.percent) + " %"
                    pids = psutil.pids()
                    pidsreply = ''
                    procs = {}
                    for pid in pids:
                        p = psutil.Process(pid)
                        try:
                            pmem = p.memory_percent()
                            if pmem > 0.5:
                                if p.name() in procs:
                                    procs[p.name()] += pmem
                                else:
                                    procs[p.name()] = pmem
                        except:
                            print("Hm")
                    sortedprocs = sorted(procs.items(), key=operator.itemgetter(1), reverse=True)
                    for proc in sortedprocs:
                        pidsreply += proc[0] + " " + ("%.2f" % proc[1]) + " %\n"
                    reply = timedif + "\n" + \
                            memtotal + "\n" + \
                            memavail + "\n" + \
                            memuseperc + "\n" + \
                            diskused + "\n\n" + \
                            pidsreply
                    send_long_message(bot, chat_id, reply)
                elif msg['text'] == "Stop":
                    clearall(chat_id)
                    bot.sendMessage(chat_id, "All operations stopped.", reply_markup=hide_keyboard)
                elif msg['text'] == '/setpoll' and chat_id not in setpolling:
                    bot.sendChatAction(chat_id, 'typing')
                    setpolling.append(chat_id)
                    bot.sendMessage(chat_id, "Send me a new polling interval in seconds? (higher than 10)", reply_markup=stopmarkup)
                elif chat_id in setpolling:
                    bot.sendChatAction(chat_id, 'typing')
                    try:
                        global poll
                        poll = int(msg['text'])
                        if poll > 10:
                            bot.sendMessage(chat_id, "All set!")
                            clearall(chat_id)
                        else:
                            1/0
                    except:
                        bot.sendMessage(chat_id, "Please send a proper numeric value higher than 10.")
                elif msg['text'] == "/shell" and chat_id not in shellexecution:
                    bot.sendMessage(chat_id, "Send me a shell command to execute", reply_markup=stopmarkup)
                    shellexecution.append(chat_id)
                elif msg['text'] == "/setmem" and chat_id not in settingmemth:
                    bot.sendChatAction(chat_id, 'typing')
                    settingmemth.append(chat_id)
                    bot.sendMessage(chat_id, "Send me a new memory threshold to monitor?", reply_markup=stopmarkup)
                elif chat_id in settingmemth:
                    bot.sendChatAction(chat_id, 'typing')
                    try:
                        global memorythreshold
                        memorythreshold = int(msg['text'])
                        if memorythreshold < 100:
                            bot.sendMessage(chat_id, "All set!")
                            clearall(chat_id)
                        else:
                            1/0
                    except:
                        bot.sendMessage(chat_id, "Please send a proper numeric value below 100.")

                elif chat_id in shellexecution:
                    bot.sendChatAction(chat_id, 'typing')
                    p = Popen(msg['text'], shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
                    output = p.stdout.read()
                    if output != b'':
                        send_long_message(bot, chat_id, output.decode())
                    else:
                        bot.sendMessage(chat_id, "No output.", disable_web_page_preview=True)
                elif msg['text'] == '/memgraph':
                    bot.sendChatAction(chat_id, 'typing')
                    tmperiod = "Last %.2f hours" % ((datetime.now() - graphstart).total_seconds() / 3600)
                    bot.sendPhoto(chat_id, plotmemgraph(memlist, xaxis, tmperiod))
                elif msg['text'] == '/cpugraph':
                    bot.sendChatAction(chat_id, 'typing')
                    tmperiod = "Last %.2f hours" % ((datetime.now() - graphstart).total_seconds() / 3600)
                    bot.sendPhoto(chat_id, plotcpugraph(cpulist, xaxis, tmperiod))
                elif msg['text'] == '/help' or msg['text'] == '/start':
                    bot.sendChatAction(chat_id, 'typing')
                    formatted_help = help_message.format(memorythreshold, poll)
                    bot.sendMessage(chat_id, formatted_help, parse_mode='Markdown')



def send_long_message(bot, chat_id, text, max_length=4000):
    for i in range(0, len(text), max_length):
        bot.sendMessage(chat_id, text[i:i+max_length], disable_web_page_preview=True)

TOKEN = telegrambot

bot = YourBot(TOKEN)
bot.message_loop()
tr = 0
xx = 0
# Keep the program running.
while 1:
    if tr == poll:
        tr = 0
        timenow = datetime.now()
        memck = psutil.virtual_memory()
        mempercent = memck.percent
        cpupercent = psutil.cpu_percent(interval=1)  # Get CPU percentage with 1 second interval
        
        if len(memlist) > 300:
            # Update memory list
            memq = collections.deque(memlist)
            memq.append(mempercent)
            memq.popleft()
            memlist = memq
            memlist = list(memlist)
            
            # Update CPU list
            cpuq = collections.deque(cpulist)
            cpuq.append(cpupercent)
            cpuq.popleft()
            cpulist = cpuq
            cpulist = list(cpulist)
        else:
            xaxis.append(xx)
            xx += 1
            memlist.append(mempercent)
            cpulist.append(cpupercent)  # Add current CPU usage to list
        memfree = memck.available / 1000000
        if mempercent > memorythreshold:
            memavail = "Available memory: %.2f GB" % (memck.available / 1000000000)
            graphend = datetime.now()
            tmperiod = "Last %.2f hours" % ((graphend - graphstart).total_seconds() / 3600)
            for adminid in adminchatid:
                bot.sendMessage(adminid, "CRITICAL! LOW MEMORY!\n" + memavail)
                bot.sendPhoto(adminid, plotmemgraph(memlist, xaxis, tmperiod))
    time.sleep(10)  # 10 seconds
    tr += 10
