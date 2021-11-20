#!/usr/bin/python3.6
import tweepy
from scibot.telebot import telegram_bot_sendtext
from dotenv import load_dotenv
from os.path import expanduser
import os

env_path = expanduser("~/.env")
load_dotenv(dotenv_path=env_path, override=True)

# Setup API:
def twitter_setup():
    """
    Setup Twitter connection for a developer account
    Returns: tweepy.API object

    """
    # Authenticate and access using keys:
    auth = tweepy.OAuthHandler(os.getenv("CONSUMER_KEY"), os.getenv("CONSUMER_SECRET"))
    auth.set_access_token(os.getenv("ACCESS_TOKEN"), os.getenv("ACCESS_SECRET"))

    # Return API access:
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
    return api

api = twitter_setup()

banned_profiles = ['nydancesafe']

class MyStreamListener(tweepy.StreamListener):

    def on_status(self, status):

        if hasattr(status, "retweeted_status"):  # Check if Retweet
#             try:
#                 print('rt',status['retweeted_status']['extended_tweet']["full_text"])
#             except AttributeError:
            telegram_bot_sendtext(f" check if retweet:, {status.retweeted_status.text}")
            if "constellation" not in status.retweeted_status.text.lower():
                pass
        else:
            try:
                ## catch nesting
                if status.user.screen_name in banned_profiles or status.in_reply_to_screen_name:
                    pass
                replied_to=status.in_reply_to_screen_name
                answer_user=status.user.screen_name
                answer_id=status.id
                answer_user_id = status.user.id
                ## ignore replies that by default contain mention
                in_reply_to_status_id=status.in_reply_to_status_id
                in_reply_to_user_id=status.in_reply_to_user_id

                telegram_bot_sendtext(f"{replied_to}, 'nesting', {in_reply_to_user_id}, 'replied to', {replied_to}, 'message', {status.text}")

            except AttributeError:

                replied_to=status.in_reply_to_screen_name
                answer_user=status.user.screen_name
                answer_user_id = status.user.id
                answer_id=status.id
                in_reply_to_status_id=status.in_reply_to_status_id
                in_reply_to_user_id=status.in_reply_to_user_id

                telegram_bot_sendtext(f"ATRIB ERROR: {replied_to}, 'nesting', {in_reply_to_user_id}, 'replied to', {replied_to}, 'message', {status.text}")

            update_status = f""" #ConstellationsFest live RT. From 16-24 NOV:

https://twitter.com/{answer_user}/status/{answer_id}
             """

            # don't reply to yourself!!
            self_ids=[1319577341056733184, 1118874276961116162]
            if status.user.id not in self_ids:

                api.update_status(update_status,
                auto_populate_reply_metadata=True)


    def on_error(self, status):
        telegram_bot_sendtext(f"ERROR with: {status}")

def listen_stream_and_rt(keywords_list):
    api = twitter_setup()
    myStreamListener = MyStreamListener()
    try:
        myStream = tweepy.Stream(auth=api.auth, listener=myStreamListener)
        myStream.filter(track=keywords_list, is_async=True)
    except Exception as ex:
        telegram_bot_sendtext(f"ERROR with: {ex}")
        pass
