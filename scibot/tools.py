import logging
import json
import re
import os
import time
import datetime
import feedparser
import dateutil.parser
from os.path import expanduser
from scibot.telebot import telegram_bot_sendtext
from schedule import Scheduler

# logging parameters
logger = logging.getLogger("bot logger")
# handler determines where the logs go: stdout/file
file_handler = logging.FileHandler(f"{datetime.date.today()}_scibot.log")

logger.setLevel(logging.DEBUG)
file_handler.setLevel(logging.DEBUG)

fmt_file = (
    "%(levelname)s %(asctime)s [%(filename)s: %(funcName)s:%(lineno)d] %(message)s"
)

file_formatter = logging.Formatter(fmt_file)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


class Settings:
    """Twitter bot application settings.

    Enter the RSS feed you want to tweet, or keywords you want to retweet.
    """

    IGNORE_ERRORS = [327, 139]
    # RSS feeds to read and post tweets from.
    feed_urls = [
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1ZGxMH1ktXCFn5mIeUkvIfOkRa7o7gTqNbl35-RTs7ogzkMQtY/?limit=100&utm_campaign=pubmed-2&fc=20210510224137",
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1XSES1Yl3kEgnfOg6EStNFyWMogtYXic2VVXS8rpsyNHTjv1HK/?limit=100&utm_campaign=pubmed-2&fc=20210510224301",
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1jAe3RzQKmf7SOUEM-Dt7QQtMWNG2UffuIIo_GGKHPfoKqhY9f/?limit=100&utm_campaign=pubmed-2&fc=20210510224348",
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1bCr63ThlO22Eg5TxBaIQ5mzH02TqtmtM1QIkqa66iqK4SsMJm/?limit=100&utm_campaign=pubmed-2&fc=20210510224551",
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1hEma6JdH30sOOO0DiTP1jZh-6ZgoypoEsw_B9tXZejk_E8QuX/?limit=100&utm_campaign=pubmed-2&fc=20210510230918",
    ]

    pre_combined_feed = [feedparser.parse(url)["entries"] for url in feed_urls]

    # (combined_feed)

    combined_feed = [item for feed in pre_combined_feed for item in feed]
    combined_feed.sort(
        key=lambda x: dateutil.parser.parse(x["published"]), reverse=True
    )

    # Log file to save all tweeted RSS links (one URL per line).
    posted_urls_output_file = expanduser("~/drugscibot/publications.json")

    # Log file to save all retweeted tweets (one tweetid per line).
    posted_retweets_output_file = expanduser("~/drugscibot/posted-retweets.log")

    # Log file to save all retweeted tweets (one tweetid per line).
    faved_tweets_output_file = expanduser("~/drugscibot/faved-tweets.log")

    # Log file to save followers list.
    users_json_file = expanduser("~/drugscibot/users.json")

    # Include tweets with these words when retweeting.
    retweet_include_words = [
        "drugpolicy",
        "drugspolicy",
        "transformdrugspolicy",
        "transformdrugpolicy",
        "drugchecking",
        "regulatestimulants",
        "regulatedrugs",
        "sensibledrugpolicy",
        "drugpolicyreform",
        "safeconsumption",
        "harmreduction",
        "druguse",
        "regular",
        "reduccion de riesgo",
        "reduccion de dano",
        "dosis minima",
        "regulacion",
        "droga",
        "sicoactiva",
        "psicoactiva",
        "politica de droga",
        "legalización",
        "safesuply",
        "safersuply",
    ]

    # Do not include tweets with these words when retweeting.
    retweet_exclude_words = [
        "sex",
        "sexual",
        "sexwork",
        "sexualwork",
        "fuck",
        "vaping",
        "vape",
        "cigarretes",
        "nicotine",
        "smoke",
        "smoking",
        "zigaretten",
    ]

    add_hashtag = [
        "psilocybin",
        "psilocybine",
        "psychedelic",
        "hallucinogenic",
        "overdose",
        "microdosing",
        "drug-policy",
        "drugspolicy",
        "mdma",
        "drug checking",
        "drugpolicy",
        "drug policy",
        "ayahuasca",
        "psychopharmacology",
        "neurogenesis",
        "5-meo-dmt",
        "serotonergic",
        "ketamine",
        "psychotherapy",
        "harm reduction",
        "methadone",
    ]  # trip

    # do not retweet if search results include only a single of these keywords
    watch_add_hashtag = [
        "alzheimer",
        "depression",
        "anxiety",
        "dmt",
        "droga",
        "lsd",
        "therapy",
        "psychiatry",
        "mentalhealth",
        "trip",
        "mental health",
        "clinical trial",
        "consciousness",
        "meta-analysis",
        "dopamine",
        "serotonin",
        "psychological",
        "metaanalysis",
        "reform",
    ]

    # list of the distribution
    mylist_id = "1306244304000749569"


class SafeScheduler(Scheduler):
    """
    An implementation of Scheduler that catches jobs that fail, logs their
    exception tracebacks as errors, optionally reschedules the jobs for their
    next run time, and keeps going.
    Use this to run jobs that may or may not crash without worrying about
    whether other jobs will run or if they'll crash the entire script.
    """

    def __init__(self, reschedule_on_failure=True):
        """

        Args:
            reschedule_on_failure: if is True, jobs will be rescheduled for their
        next run as if they had completed successfully. If False, they'll run
        on the next run_pending() tick.
        """
        self.reschedule_on_failure = reschedule_on_failure
        super().__init__()

    def _run_job(self, job):
        try:
            super()._run_job(job)

        except Exception as e:
            logger.exception(e)
            telegram_bot_sendtext(f"[Job Error] {e}")
            job.last_run = datetime.datetime.now()
            job._schedule_next_run()


def shorten_text(text: str, maxlength: int) -> str:
    """
    Truncate text and append three dots (...) at the end if length exceeds
    maxlength chars.

    Args:
        text: The to shorten.
        maxlength: The maximum character length of the text string.

    Returns: Shortened text string.

    """
    return (text[:maxlength] + "...") if len(text) > maxlength else text


def insert_hashtag(title: str) -> str:
    """
    Add hashtag on title for keywords found on Settings.add_hashtag
    Args:
        title: Text to parse for inserting hash symbols

    Returns: Text with inserted hashtags

    """

    for x in Settings.add_hashtag:
        if re.search(fr"\b{x}", title.lower()):
            pos = (re.search(fr"\b{x}", title.lower())).start()
            if " " in x:
                title = title[:pos] + "#" + title[pos:].replace(" ", "", 1)
            else:
                title = title[:pos] + "#" + title[pos:]
    return title


def compose_message(item: feedparser.FeedParserDict) -> str:
    """
    Compose a tweet from an RSS item (title, link, description)
    and return final tweet message.

    Args:
        item: feedparser.FeedParserDict
        An RSS item

    Returns: mMssage suited for a Twitter status update.

    """
    title = insert_hashtag(item["title"])

    message = shorten_text(title, maxlength=250) + " 1/5  " + item["link"]
    return message


def is_in_logfile(content: str, filename: str) -> bool:
    """
    Does the content exist on any line in the log file?

    Args:
        content: Content to search file for.
        filename: Full path to file to search.

    Returns: `True` if content is found in file, otherwise `False`.

    """
    if os.path.isfile(filename):
        with open(filename, "r") as jsonFile:
            article_log = json.load(jsonFile)
        if content in article_log:
            return True
    return False


def write_to_logfile(content: dict, filename: str) -> None:
    """
    Append content to json file.

    Args:
        content: Content to append to file
        filename: Full path to file that should be appended.

    Returns: None

    """
    try:
        with open(filename, "w") as fp:
            json.dump(content, fp, indent=4)
    except IOError as e:
        logger.exception(e)


def scheduled_job(read_rss_and_tweet, retweet_own, search_and_retweet):
    schedule = SafeScheduler()
    # job 1
    schedule.every().day.at("22:20").do(read_rss_and_tweet)
    schedule.every().day.at("06:20").do(read_rss_and_tweet)
    schedule.every().day.at("14:20").do(read_rss_and_tweet)
    # job 2
    schedule.every().day.at("01:10").do(retweet_own)
    schedule.every().day.at("09:10").do(retweet_own)
    schedule.every().day.at("17:10").do(retweet_own)
    # job 3
    schedule.every().day.at("00:20").do(search_and_retweet, "list_search")
    schedule.every().day.at("03:20").do(search_and_retweet, "list_search")
    schedule.every().day.at("06:20").do(search_and_retweet, "list_search")
    schedule.every().day.at("09:20").do(search_and_retweet, "list_search")
    schedule.every().day.at("12:20").do(search_and_retweet, "list_search")
    schedule.every().day.at("15:20").do(search_and_retweet, "list_search")
    schedule.every().day.at("18:20").do(search_and_retweet, "list_search")
    schedule.every().day.at("21:20").do(search_and_retweet, "list_search")

    schedule.every().day.at("01:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("04:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("07:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("10:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("13:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("16:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("19:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("22:25").do(search_and_retweet, "list_search")
    # job love
    schedule.every(5).minutes.do(search_and_retweet, "give_love")

    while 1:
        schedule.run_pending()
        time.sleep(1)
