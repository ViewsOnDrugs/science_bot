import logging
import re
import os
import time
import datetime
import feedparser
import dateutil.parser
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
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1Di1IZzM0R4FRnKYsI1qINYHDYUiWSVAWo0rd3bhufn34wQ9HU/?limit=100&utm_campaign=pubmed-2&fc=20201028084526",
        "http://export.arxiv.org/api/query?search_query=all:psilocybin*&start=0&max_results=100&sortBy=lastUpdatedDate&sortOrder=descending",
    ]

    pre_combined_feed = [feedparser.parse(url)['entries'] for url in feed_urls]

    # (combined_feed)

    combined_feed = [item for feed in pre_combined_feed for item in feed]
    combined_feed.sort(key=lambda x: dateutil.parser.parse(x['published']), reverse=True)



    # Log file to save all tweeted RSS links (one URL per line).
    posted_urls_output_file = "/home/farcila/what_a_c/posted-urls.log"

    # Log file to save all retweeted tweets (one tweetid per line).
    posted_retweets_output_file = "/home/farcila/what_a_c/posted-retweets.log"

    # Log file to save all retweeted tweets (one tweetid per line).
    faved_tweets_output_file = "/home/farcila/what_a_c/faved-tweets.log"

    # Log file to save followers list.
    users_json_file = "/home/farcila/what_a_c/users.json"


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
        "safesuply",
        "safersuply",
    ]

    # Do not include tweets with these words when retweeting.
    retweet_exclude_words = ["sex", "sexual", "sexwork", "sexualwork", "fuck", "vaping", "vape"]

    add_hashtag = ['psilocybin', 'psilocybine', 'psychedelic', 'psychological',
                   'hallucinogenictrip', 'therapy', 'psychiatry', 'dmt',
                   'mentalhealth', 'alzheimer', 'depression', 'anxiety',
                   'dopamine', 'serotonin', 'lsd', 'drug-policy', 'drugspolicy',
                   'drugpolicy', 'mdma', 'microdosing', 'drug', 'ayahuasca',
                   'psychopharmacology', 'clinical trial', 'neurogenesis',
                   'serotonergic', 'ketamine', 'consciousness', 'psychotherapy',
                   'meta-analysis']
    ## list of the distribution
    mylist_id = "1306244304000749569"  # todo add covid example
    ## reosted error to ignore for the log.list



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
        If reschedule_on_failure is True, jobs will be rescheduled for their
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
            job.last_run = datetime.datetime.now()
            job._schedule_next_run()

def insert_hash(string, index):
    return string[:index] + "#" + string[index:]

def compose_message(item: feedparser.FeedParserDict) -> str:
    """Compose a tweet from an RSS item (title, link, description)
    and return final tweet message.

    Parameters
    ----------
    item: feedparser.FeedParserDict
        An RSS item.

    Returns
    -------
    str
        Returns a message suited for a Twitter status update.
    """
    title = item["title"]

    for x in Settings.add_hashtag:
        if re.search(fr"\b{x}", title.lower()):
            pos = (re.search(fr"\b{x}", title.lower())).start()
            title = insert_hash(title, pos)
    link, _ = item["link"], item["description"]
    message = shorten_text(title, maxlength=250) + " " + link
    return message

def is_in_logfile(content: str, filename: str) -> bool:
    """Does the content exist on any line in the log file?

    Parameters
    ----------
    content: str
        Content to search file for.
    filename: str
        Full path to file to search.

    Returns
    -------
    bool
        Returns `True` if content is found in file, otherwise `False`.
    """
    if os.path.isfile(filename):
        with open(filename) as f:
            lines = f.readlines()
        if (str(content) + "\n" or content) in lines:
            return True
    return False


def write_to_logfile(content: str, filename: str):
    """Append content to log file, on one line.

    Parameters
    ----------
    content: str
        Content to append to file.
    filename: str
        Full path to file that should be appended.
    """
    try:
        with open(filename, "a") as f:
            f.write(content + "\n")
    except IOError as e:
        logger.exception(e)


def shorten_text(text: str, maxlength: int) -> str:
    """Truncate text and append three dots (...) at the end if length exceeds
    maxlength chars.

    Parameters
    ----------
    text: str
        The text you want to shorten.
    maxlength: int
        The maximum character length of the text string.

    Returns
    -------
    str
        Returns a shortened text string.
    """
    return (text[:maxlength] + "...") if len(text) > maxlength else text


def scheduled_job(check_new_followers,read_rss_and_tweet,retweet_own,search_and_retweet):
    schedule = SafeScheduler()
    # job 0 check followers
    schedule.every().day.at("00:20").do(check_new_followers)
    # job 1
    schedule.every().day.at("22:20").do(read_rss_and_tweet, url=Settings.combined_feed)
    schedule.every().day.at("06:20").do(read_rss_and_tweet, url=Settings.combined_feed)
    schedule.every().day.at("14:20").do(read_rss_and_tweet, url=Settings.combined_feed)
    # job 2
    schedule.every().day.at("01:10").do(retweet_own)
    schedule.every().day.at("09:10").do(retweet_own)
    schedule.every().day.at("17:10").do(retweet_own)
    # job 3
    schedule.every().day.at("00:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("03:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("06:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("09:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("12:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("15:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("18:20").do(search_and_retweet, "global_search")
    schedule.every().day.at("21:20").do(search_and_retweet, "global_search")

    schedule.every().day.at("01:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("04:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("07:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("10:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("13:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("16:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("19:25").do(search_and_retweet, "list_search")
    schedule.every().day.at("22:25").do(search_and_retweet, "list_search")
    # job love
    schedule.every(58).minutes.do(search_and_retweet, "give_love")

    while 1:
        schedule.run_pending()
        time.sleep(1)
