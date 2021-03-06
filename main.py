#!/usr/bin/python3
import random

import requests
import json
import time
import datetime
import pickle
import logging
import sys

URL_TELEGRAM = "https://api.telegram.org/bot"
TOKEN = "284065983:AAGiyvMiLJRg0Q-g8ke-nZmG0T-rjEF3j_A"
BOT_NAME = "kak_diplom_bot"


def create_request_url(request):
    return URL_TELEGRAM + TOKEN + "/" + request


updates_url = create_request_url("getUpdates")
send_url = create_request_url("sendMessage")


def get_updates(offset=0):
    payload = {"offset": offset}
    response = requests.get(updates_url, json=payload)
    json_response = json.loads(response.text)

    if not json_response["ok"]:
        dump("so sorry, response updates: {}".format(json_response))

    return json_response["result"]


def send(chat_id, text):
    global last_sent_time

    dump("send to chat_id = {}, text = {}".format(chat_id, text))
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(send_url, json=payload)
    json_response = json.loads(response.text)

    if "error_code" in json_response:
        dump("error SEND: {}".format(response.text))

        try:
            existing_chats.remove(chat_id)
        except:
            pass

        try:
            del last_sent_time[chat_id]
        except:
            pass

        try:
            motivated_chats.remove(chat_id)
        except:
            pass

        return -1
    else:
        dump("SEND: {}".format(response.text))

        if not json_response["ok"]:
            dump("so sorry, response: {}".format(json_response))

        # if chat_id in motivated_chats:
        last_sent_time[chat_id] = datetime.datetime.now()

        return 0


def start_cmd(chat_id):
    dump("in start_cmd")
    global existing_chats
    send(chat_id, "Oh Yes")
    existing_chats.add(chat_id)


def stop_motivate_cmd(chat_id):
    send(chat_id, "No, please!")

    motivated_chats.remove(chat_id)


def stop_cmd(chat_id):
    global existing_chats

    dump("in stop_cmd")
    send(chat_id, "No, please :(")

    existing_chats.remove(chat_id)
    motivated_chats.remove(chat_id)

    if chat_id in last_sent_time:
        del last_sent_time[chat_id]


def next_cmd(chat_id):
    global g_motivation_num
    global quotes

    dump("in next_cmd")
    if chat_id in existing_chats:
        send(chat_id, quotes[g_motivation_num])
        # send(chat_id, quotes[-1])
        g_motivation_num += 1
        if g_motivation_num == len(quotes):
            g_motivation_num = 0
            random.shuffle(quotes)


def motivate_cmd(chat_id):
    global motivated_chats
    if chat_id in existing_chats:
        motivated_chats.add(chat_id)


def read_quotes(*_):
    global quotes
    dump("read_quotes")
    with open("quotes.txt") as q:
        whole_file = q.read()
        quotes = whole_file.split("--------")


def dump_users(*_):
    global last_dumped_time
    last_dumped_time = datetime.datetime.now()

    dump("dump users")
    with open("users.txt", "wb") as u:
        pickle.dump(existing_chats, u)
        pickle.dump(motivated_chats, u)
        pickle.dump(last_sent_time, u)
        pickle.dump(last_update_id, u)
        pickle.dump(g_chat_id, u)


def load_users(*_):
    global existing_chats
    global motivated_chats
    global last_sent_time
    global last_update_id
    global g_chat_id

    dump("load_users")
    try:
        with open("users.txt", "rb") as u:
            existing_chats = pickle.load(u)
            motivated_chats = pickle.load(u)
            last_sent_time = pickle.load(u)
            last_update_id = pickle.load(u)
            g_chat_id = pickle.load(u)

            dump(existing_chats)
    except Exception as e:
        dump("users.txt doesn't exist")
        dump(e)


def setup_logger():
    global dump

    formatter = logging.Formatter('%(asctime)s (%(threadName)-10s) %(message)s', datefmt='%H:%M:%S')
    file_handler = logging.FileHandler("diplom.log", mode='w')
    file_handler.setFormatter(formatter)

    logger = logging.getLogger("diplom")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    dump = logger.debug


def duplicate_commands_with_bot_name():
    global commands
    new_commands = {}
    for name, cmd in commands.items():
        new_commands[name + "@" + BOT_NAME] = cmd

    commands.update(new_commands)


def shut_down(chat_id, *_):
    global proceed

    # for deleting recent shut_down request
    unused = get_updates(last_update_id)
    send(chat_id, "shut down :(")

    dump("shut_donw")
    dump_users()
    proceed = False


def add_quote(chat_id, text):
    global quotes

    dump("add_quote: {}".format(text))
    quotes.append(text)

    with open("quotes.txt", "a") as quotes_txt:
        quotes_txt.write("--------\n")
        quotes_txt.write(text)
        quotes_txt.write("\n")

    send(chat_id, "successfully add quote")


proceed = True
quotes = []
existing_chats = set()
motivated_chats = set()
last_update_id = 0
g_chat_id = 0
g_motivation_num = 0
last_sent_time = {}
last_dumped_time = datetime.datetime.now()

commands = {"/start": start_cmd,
            "/stop": stop_cmd,
            "/next": next_cmd,
            "/motivate": motivate_cmd,
            "/stop_motivate": stop_motivate_cmd,
            "/upd_quotes": read_quotes,
            "/dump_users": dump_users,
            "/shut_down": shut_down}

prefix_commands = {"/add_quote": add_quote}

if __name__ == "__main__":
    setup_logger()
    read_quotes()
    load_users()
    duplicate_commands_with_bot_name()

    while proceed:
        try:
            json_response = get_updates(last_update_id)

            for entry in json_response:
                msg = entry["message"]
                if "text" in msg:
                    dump("entry: {}".format(entry))
                    text = msg["text"]
                    g_chat_id = msg["chat"]["id"]
                    last_update_id = max(last_update_id, entry["update_id"] + 1)

                    if text in commands:
                        dump("command, chat_id: {} {}".format(text, g_chat_id))
                        commands[text](g_chat_id)
                    else:
                        for pref_cmd, fun_cmd in prefix_commands.items():
                            n = len(pref_cmd)
                            if pref_cmd == text[:n]:
                                fun_cmd(g_chat_id, text[n + 1:])
                                break

            time.sleep(1)

            cur = datetime.datetime.now()
            for chat in motivated_chats:
                if chat in last_sent_time:
                    if cur - last_sent_time[chat] > datetime.timedelta(seconds=3):
                        next_cmd(chat)
                else:
                    next_cmd(chat)

            for chat in existing_chats:
                if chat in last_sent_time:
                    if cur - last_sent_time[chat] > datetime.timedelta(days=1) + datetime.timedelta(hours=random.randint(0, 7)):
                        dump("kak diplom to chat: {}".format(chat))
                        if send(chat, "Как диплом? :\\") == -1:
                            dump("delete1 this chat {}".format(chat))
                else:
                    dump("kak diplom to chat: {}".format(chat))
                    if send(chat, "Как диплом? :\\") == -1:
                        dump("delete2 this chat {}".format(chat))

            if cur - last_dumped_time > datetime.timedelta(minutes=1):
                dump_users()
        except Exception as e:
            dump_users()
            dump(e)
