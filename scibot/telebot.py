#!/usr/bin/python3.6
import requests
import os
from os.path import expanduser
from dotenv import load_dotenv

env_path = expanduser("~/.env")
load_dotenv(dotenv_path=env_path)


def telegram_bot_sendtext(bot_message):

    token = os.getenv("API_TOKEN")
    bot_id = os.getenv("BOT_ID")

    send_text = (
        "https://api.telegram.org/bot"
        + token
        + "/sendMessage?chat_id="
        + bot_id
        + "&parse_mode=Markdown&text="
        + bot_message
    )

    response = requests.get(send_text)

    return response.json()
