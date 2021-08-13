#!/usr/bin/env python3
import json
import os
import sys
import re
import time
from os.path import expanduser
from random import randint

import tweepy
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from scibot.telebot import telegram_bot_sendtext
from scibot.tools import (
    logger,
    Settings,
    insert_hashtag,
    shorten_text,
    compose_message,
    is_in_logfile,
    write_to_logfile,
    scheduled_job,
)

env_path = expanduser("~/.env")
load_dotenv(dotenv_path=env_path)


def main():
    """
    Main function of scibot

    """

    logger.info("\n### sciBot started ###\n\n")
    if len(sys.argv) > 1:
        try:
            check_json_exists(
                Settings.users_json_file,
                {"test": {"follower": False, "interactions": 0}},
            )
            check_json_exists(Settings.faved_tweets_output_file, {"test": {}})
            check_json_exists(
                Settings.posted_retweets_output_file,
                {"test": {}},
            )
            check_json_exists(
                Settings.posted_urls_output_file,
                {"test": {}},
            )

            if sys.argv[1].lower() == "rss":
                read_rss_and_tweet()
            elif sys.argv[1].lower() == "rtg":
                search_and_retweet("global_search")
            elif sys.argv[1].lower() == "glv":
                search_and_retweet("give_love")
            elif sys.argv[1].lower() == "rtl":
                search_and_retweet("list_search")
            elif sys.argv[1].lower() == "rto":
                retweet_old_own()
            elif sys.argv[1].lower() == "sch":
                scheduled_job(read_rss_and_tweet, retweet_old_own, search_and_retweet)

        except Exception as e:
            logger.exception(e, exc_info=True)
            telegram_bot_sendtext(f"[Exception] {e}")

        except IOError as errno:
            logger.exception(f"[ERROR] {errno}")
            telegram_bot_sendtext(f"[ERROR] {errno}")

    else:
        display_help()
    logger.info("\n\n### sciBot finished ###")


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


def check_json_exists(file_path: os.path, init_dict: dict) -> None:
    """

    Create a folder and json file if does not exists

    Args:
        file_path: Log files file path
        init_dict: Dictionary to initiate a json file

    Returns: None

    """

    if not os.path.exists(os.path.dirname(os.path.abspath(file_path))):
        os.makedirs(file_path)

    if not os.path.isfile(file_path):
        with open(file_path, "w") as json_file:
            json.dump(init_dict, json_file, indent=4)


def get_followers_list() -> list:
    """
    Read json file of followers from Settings.users_json_file
    Returns: List of followers

    """

    with open(Settings.users_json_file, "r") as json_file:
        users_dic = json.load(json_file)
    return [x for x in users_dic if users_dic[x]["follower"] is True]


def update_thread(text: str, tweet: tweepy.Status, api: tweepy.API) -> tweepy.Status:
    """
    Add a tweet to a initiated thread
    Args:
        text: text to add to tweet as thread
        tweet: tweepy status to add reply to
        api: tweepy.API object

    Returns: post a reply to a tweet

    """
    return api.update_status(
        status=text, in_reply_to_status_id=tweet.id, auto_populate_reply_metadata=True
    )


def post_thread(dict_one_pub: dict, maxlength: int, count: int = 1) -> int:
    """
    Initiate and post a thread of tweets
    Args:
        dict_one_pub: dictionary object with processed publication item
        maxlength: length of the message to post (max tweet is 280 char)
        count: count of replies on the thread

    Returns: tweet id of the first tweet of thread

    """
    api = twitter_setup()
    original_tweet = api.update_status(status=compose_message(dict_one_pub))
    telegram_bot_sendtext(f"Posting thread:, twitter.com/drugscibot/status/{original_tweet.id}")

    text = dict_one_pub["abstract"]
    max_len =  round(len(text)/3)
    if max_len < 240:
        maxlength = max_len


    for index in range(0, len(text), maxlength):
        if count < 4:
            count += 1
            time.sleep(2)
            thread_message = (
                insert_hashtag(text[index : index + maxlength]) + f"... {count}/5"
            )
            if count == 2:
                reply1_tweet = update_thread(thread_message, original_tweet, api)
            if count == 3:
                reply2_tweet = update_thread(thread_message, reply1_tweet, api)
            if count == 4:
                reply3_tweet = update_thread(thread_message, reply2_tweet, api)

    time.sleep(2)
    count += 1
    last_msg = shorten_text(dict_one_pub["author-s"][0], 250) + f" {count}/{count}"

    update_thread(last_msg, reply3_tweet, api)

    return original_tweet.id

def return_doi_str(article):
    """return doi link if exists"""
    title_search = re.search('(DOI:<a href=")(.*)(">)', str(article))
    if title_search:
        return title_search.group(2)
    else:
        return article.link


def make_literature_dict(feed: list) -> dict:
    """
    filter publications from an RSS feed having an abstract, parse html abstract as plane string
    Args:
        feed: list of RSS feed items

    Returns: dictionary of processed publications

    """

    dict_publications = {}

    for item in feed:
        if hasattr(item, "content") and not 'No abstract' in item.description:
            dict_publications[item.id] = {
                "title": item.title,
                "abstract": BeautifulSoup(item.content[0].value, "html.parser")
                .get_text()
                .split("ABSTRACT")[1],
                "link": return_doi_str(item),
                "description": item.description,
                "author-s": [
                    "Authors: " + ", ".join([x["name"] for x in item.authors]),
                    "Author: " + item.author,
                ],
            }
    return dict_publications


def read_rss_and_tweet() -> None:
    """

    Read RSS objects and tweet one calling the post thread function
    Returns: None, updates log file with the posted article id

    """
    dict_publications = make_literature_dict(Settings.combined_feed)

    with open(Settings.posted_urls_output_file, "r") as jsonFile:
        article_log = json.load(jsonFile)

    for article in sorted(dict_publications.keys(), reverse=True):

        if not is_in_logfile(article, Settings.posted_urls_output_file):
            try:
                article_log[article] = {
                    "count": 1,
                    "tweet_id": post_thread(dict_publications[article], 240),
                }

                write_to_logfile(article_log, Settings.posted_urls_output_file)
                break
            except tweepy.TweepError as e:
                logger.error(f"RSS error, possible duplicate {e}, {article}")
                write_to_logfile(article_log, Settings.posted_urls_output_file)
                continue


def json_add_new_friend(user_id: str) -> None:
    """
    add user friends to the interactions json file
    Args:
        user_id: user id to add to the interactions file

    Returns: None, updates interaction file

    """

    with open(Settings.users_json_file, "r") as json_file:
        users_dic = json.load(json_file)
    if user_id not in users_dic:
        users_dic[user_id] = {"follower": True, "interactions": 1}
    else:
        users_dic[user_id]["follower"] = True

    with open(Settings.users_json_file, "w") as json_file:
        json.dump(users_dic, json_file, indent=4)


def post_tweet(message: str) -> None:
    """
    Post tweet message to account.
    Args:
        message: Message to post on Twitter

    Returns: None

    """
    try:
        twitter_api = twitter_setup()
        logger.info(f"post_tweet():{message}")
        twitter_api.update_status(status=message)
    except tweepy.TweepError as e:
        logger.error(e)


def filter_repeated_tweets(result_search: list, flag: str) -> list:
    """

    Args:
        result_search:
        flag:

    Returns:

    """

    if flag == "give_love":
        out_file = Settings.faved_tweets_output_file
    else:
        out_file = Settings.posted_retweets_output_file

    unique_results = {}

    for status in result_search:
        if hasattr(status, "retweeted_status"):
            check_id = status.retweeted_status.id_str
        else:
            check_id = status.id_str

        if not is_in_logfile(check_id, out_file):
            unique_results[status.full_text] = status

    return [unique_results[x] for x in unique_results]


def json_add_user(user_id: str) -> None:
    """
    add user to the interactions json file
    Args:
        user_id: user id

    Returns: None

    """
    with open(Settings.users_json_file, "r") as json_file:
        users_dic = json.load(json_file)
    if user_id not in users_dic:
        users_dic[user_id] = {"follower": False, "interactions": 1}
    else:
        users_dic[user_id]["interactions"] += 1

    with open(Settings.users_json_file, "w") as json_file:
        json.dump(users_dic, json_file, indent=4)


def get_query() -> str:
    """
    Create Twitter search query with included words minus the
    excluded words.

    Returns:  string with the Twitter search query

    """
    include = " OR ".join(Settings.retweet_include_words)
    exclude = " -".join(Settings.retweet_exclude_words)
    exclude = "-" + exclude if exclude else ""
    return include + " " + exclude


def check_interactions(tweet: tweepy.Status) -> None:
    """
    check if previously interacted with a user
    Args:
        tweet:

    Returns:

    """

    if tweet.author.screen_name.lower() == "viewsondrugsbot":
        pass  # don't fav your self

    auth_id = tweet.author.id_str
    with open(Settings.users_json_file, "r") as json_file:
        users_dic = json.load(json_file)

        user_list = [
            users_dic[x]["interactions"]
            for x in users_dic
            if users_dic[x]["follower"] == False
        ]

        down_limit = round(sum(user_list) / len(user_list))

        if auth_id in users_dic:
            if users_dic[auth_id]["interactions"] >= down_limit:
                return True
            else:
                return False
        else:
            return False


def try_retweet(
    twitter_api: tweepy.API, tweet_text: str, in_tweet_id: str, self_followers: list
) -> None:
    """
    try to retweet, if already retweeted try next fom the list
    of recent tweets
    Args:
        twitter_api:
        tweet_text:
        in_tweet_id:
        self_followers:

    Returns:

    """

    tweet_id = find_simple_users(twitter_api, in_tweet_id, self_followers)

    if not is_in_logfile(in_tweet_id, Settings.posted_retweets_output_file):
        try:
            twitter_api.retweet(id=tweet_id)
            logger.info(f"Trying to rt {tweet_id}")
            write_to_logfile({in_tweet_id: {}}, Settings.posted_retweets_output_file)
            _status = twitter_api.get_status(tweet_id)
            json_add_user(_status.author.id_str)
            if tweet_id == in_tweet_id:
                id_mess = f"{tweet_id} original"
            else:
                id_mess = f"{tweet_id} from a nested profile"
            message_log = (
                "Retweeted and saved to file >  https://twitter.com/i/status/{}".format(
                    id_mess
                )
            )
            logger.info(message_log)
            telegram_bot_sendtext(message_log)
            return True
        except tweepy.TweepError as e:
            if e.api_code in Settings.IGNORE_ERRORS:
                write_to_logfile(
                    {in_tweet_id: {}}, Settings.posted_retweets_output_file
                )
                logger.exception(e)
                return False
            else:
                logger.error(e)
                return True
    else:
        logger.info(
            "Already retweeted {} (id {})".format(
                shorten_text(tweet_text, maxlength=140), tweet_id
            )
        )


def get_longest_text(status: tweepy.Status) -> str:
    """
    Get the text of a quoted status
    Args:
        status: tweepy.Status object

    Returns: text of the quoted tweet

    """
    if hasattr(status, "retweeted_status"):
        return status.retweeted_status.full_text
    else:
        return status.full_text


def find_simple_users(
    twitter_api: tweepy.API, tweet_id: str, followers_list: list
) -> int:
    """
    retweet/fav from users retweeting something interesting
    Args:
        twitter_api:
        tweet_id:
        followers_list:

    Returns: id of the retweeted/faved tweet

    """
    # get original retweeter:
    down_lev_tweet = twitter_api.get_status(tweet_id)

    if hasattr(down_lev_tweet, "retweeted_status"):
        retweeters = twitter_api.retweets(down_lev_tweet.retweeted_status.id_str)
    else:
        retweeters = twitter_api.retweets(tweet_id)

    future_friends = []
    for retweet in retweeters:

        if check_interactions(retweet):
            continue
        try:
            follows_friends_ratio = (
                retweet.author.followers_count / retweet.author.friends_count
            )
        except ZeroDivisionError:
            follows_friends_ratio = 0

        future_friends_dic = {
            "id_str": retweet.author.id_str,
            "friends": retweet.author.friends_count,
            "followers": retweet.author.followers_count,
            "follows_friends_ratio": follows_friends_ratio,
        }
        if future_friends_dic["friends"] > future_friends_dic["followers"]:
            future_friends.append(
                (
                    future_friends_dic["follows_friends_ratio"],
                    retweet.id_str,
                    future_friends_dic,
                )
            )
        else:
            future_friends.append(
                (future_friends_dic["followers"], retweet.id_str, future_friends_dic)
            )
    if future_friends:
        try:  # give prioroty to non followers of self
            min_friend = min(
                [x for x in future_friends if x[2]["id_str"] not in followers_list]
            )
            logger.info(
                f"try retweeting/fav https://twitter.com/i/status/{min_friend[1]} from potential friend profile: {min_friend[2]['id_str']} friends= {min_friend[2]['friends']}, followrs={min_friend[2]['followers']}"
            )
            return min_friend[1]
        except:
            min_friend = min(future_friends)
            logger.info(
                f"try retweeting/fav https://twitter.com/i/status/{min_friend[1]} from potential friend profile: {min_friend[2]['id_str']} friends= {min_friend[2]['friends']}, followrs={min_friend[2]['followers']}"
            )
            return min_friend[1]
    else:
        logger.info(
            f"try retweeting from original post: https://twitter.com/i/status/{tweet_id}"
        )
        return tweet_id


def filter_tweet(search_results: list, twitter_api):
    """

    function to ensure that retweets are on-topic
    by the hashtag list

    Args:
        search_results:
        twitter_api:
        flag:

    Returns:

    """
    filtered_search_results = []

    for status in search_results:

        faved_sum = (
            status.retweet_count,
            status.favorite_count,
            status.retweet_count + status.favorite_count,
        )

        if status.is_quote_status:
            try:
                quoted_tweet = twitter_api.get_status(
                    status.quoted_status_id_str, tweet_mode="extended"
                )

            except tweepy.TweepError as e:
                telegram_bot_sendtext(f"ERROR {e}, {status.quoted_status_id_str}")
                quoted_tweet = ""
                continue

            end_status = get_longest_text(status) + get_longest_text(quoted_tweet)
        else:
            end_status = get_longest_text(status)

        if len(end_status.split()) > 3 and faved_sum[2] > 1:

            joined_list = Settings.add_hashtag + Settings.retweet_include_words

            # remove elements from the exclude words list
            keyword_matches = [
                x
                for x in joined_list + Settings.watch_add_hashtag
                if x in end_status.lower()
                and not any(
                    [
                        x
                        for x in Settings.retweet_exclude_words
                        if x in end_status.lower()
                    ]
                )
            ]

            if keyword_matches:

                if any(
                    [x for x in keyword_matches if x not in Settings.watch_add_hashtag]
                ):
                    print(keyword_matches, status.full_text)

                    filtered_search_results.append(
                        (faved_sum, status.id_str, status.full_text)
                    )
                else:
                    logger.info(f">> skipped, {keyword_matches}, {end_status}")


    return sorted(filtered_search_results)


def try_give_love(twitter_api, in_tweet_id, self_followers):
    """
    try to favorite a post from simple users
    Args:
        twitter_api:
        in_tweet_id:
        self_followers:

    Returns:

    """
    # todo add flag to use sleep or fav immediately

    tweet_id = find_simple_users(twitter_api, in_tweet_id, self_followers)

    if not is_in_logfile(in_tweet_id, Settings.faved_tweets_output_file):

        try:
            time.sleep(randint(0, 250))
            twitter_api.create_favorite(id=tweet_id)
            write_to_logfile({in_tweet_id: {}}, Settings.faved_tweets_output_file)
            _status = twitter_api.get_status(tweet_id)
            json_add_user(_status.author.id_str)
            message_log = (
                "faved tweet succesful: https://twitter.com/i/status/{}".format(
                    tweet_id
                )
            )
            logger.info(message_log)
            telegram_bot_sendtext(message_log)

            return True

        except tweepy.TweepError as e:
            if e.api_code in Settings.IGNORE_ERRORS:
                write_to_logfile({in_tweet_id: {}}, Settings.faved_tweets_output_file)
                logger.debug(f"throw a en error {e}")
                logger.exception(e)
                return False
            else:
                logger.error(e)
                return True

    else:
        logger.info("Already faved (id {})".format(tweet_id))


def fav_or_tweet(max_val, flag, twitter_api):
    """

    use a tweet or a fav function depending on the flag called
    Args:
        max_val:
        flag:
        twitter_api:

    Returns:

    """

    self_followers = get_followers_list()
    count = 0

    while count < len(max_val):

        tweet_id = max_val[-1 - count][1]
        tweet_text = max_val[-1 - count][2]
        logger.info(f"{len(tweet_text.split())}, {tweet_text}")

        if flag == "give_love":
            use_function = try_give_love(twitter_api, tweet_id, self_followers)
            log_message = "fav"

        else:
            use_function = try_retweet(
                twitter_api, tweet_text, tweet_id, self_followers
            )
            log_message = "retweet"

        if use_function:
            logger.info(f"{log_message}ed: id={tweet_id} text={tweet_text}")
            break
        else:
            count += 1
            time.sleep(2)
            if count >= len(max_val):
                logger.debug("no more tweets to post")
            continue


def search_and_retweet(flag: str = "global_search", count: int = 100):
    """
    Search for a query in tweets, and retweet those tweets.

    Args:
        flag: A query to search for on Twitter. it can be `global_search` to search globally
              or `list_search` reduced to a list defined on mylist_id
        count: Number of tweets to search for. You should probably keep this low
               when you use search_and_retweet() on a schedule (e.g. cronjob)

    Returns: None

    """

    try:
        twitter_api = twitter_setup()
        if flag == "global_search":
            # search results retweets globally forgiven keywords
            search_results = twitter_api.search(
                q=get_query(), count=count, tweet_mode="extended"
            )  # standard search results
        elif flag == "list_search":
            # search list retwwets most commented ad rt from the experts lists
            search_results = twitter_api.list_timeline(
                list_id=Settings.mylist_id, count=count, tweet_mode="extended"
            )  # list to tweet from

        else:
            search_results = twitter_api.list_timeline(
                list_id=Settings.mylist_id, count=count, tweet_mode="extended"
            ) + twitter_api.search(q=get_query(), count=count, tweet_mode="extended")

    except tweepy.TweepError as e:
        logger.exception(e.reason)
        telegram_bot_sendtext(f"ERROR : {e.reason}")
        return

    # get the most faved + rtweeted and retweet it
    max_val = filter_tweet(filter_repeated_tweets(search_results, flag), twitter_api)

    fav_or_tweet(max_val, flag, twitter_api)


def retweet(tweet: tweepy.Status):
    """
    re-tweet self last tweeted message.
    Args:
        tweet: tweet object

    Returns: None

    """

    try:
        twitter_api = twitter_setup()

        if not hasattr(tweet, 'retweeted'):
            print(tweet)
            twitter_api.retweet(id=tweet.id)
            logger.info(f"retweeted: twitter.com/i/status/{tweet.id}")
            telegram_bot_sendtext(f"Self retweeted: twitter.com/drugscibot/status/{tweet.id}")

        else:
            twitter_api.unretweet(tweet.id)
            twitter_api.retweet(tweet.id)
            telegram_bot_sendtext(f"Self re-retweeted: twitter.com/drugscibot/status/{tweet.id}")

    except tweepy.TweepError as e:
        logger.exception(e)
        telegram_bot_sendtext(f"ERROR :{e}")


def retweet_old_own():
    """

    Returns: None

    """

    twitter_api = twitter_setup()

    with open(Settings.posted_urls_output_file, "r") as jsonFile:
        article_log = json.load(jsonFile)

    article_log_reversed = {article_log[x]['tweet_id']:{**article_log[x], **{'id':x}} for x in article_log}


    min_val = min(article_log[x]["count"] for x in article_log)

    for art in sorted(list(article_log_reversed), key=None, reverse=False):
        tweet = twitter_api.statuses_lookup([article_log_reversed[art]["tweet_id"]])
        if tweet and article_log_reversed[art]["count"] <= min_val:
            retweet(tweet[0])
            article_log[article_log_reversed[art]['id']]["count"] += 1

            break

    with open(Settings.posted_urls_output_file, "w") as fp:
        json.dump(article_log, fp, indent=4)


def display_help():
    """
    Show available commands.

    Returns: Prints available commands

    """

    print("Syntax: python {} [command]".format(sys.argv[0]))
    print()
    print(" Commands:")
    print("    rss    Read URL and post new items to Twitter")
    print("    rtg    Search and retweet keywords from global feed")
    print("    rtl    Search and retweet keywords from list feed")
    print("    glv    Fav tweets from list or globally")
    print("    rto    Retweet last own tweet")
    print("    sch    Run scheduled jobs on infinite loop")
    print("    help   Show this help screen")


if __name__ == "__main__":
    main()
