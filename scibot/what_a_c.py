import feedparser
import os, string
import sys
import tweepy, time
import schedule
import time
import re
import logging
import logging.handlers
from os.path import expanduser
from dotenv import load_dotenv

env_path = expanduser('~/.env')
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger()
logger.addHandler(logging.handlers.SMTPHandler(mailhost=(os.getenv('GHOST'), os.getenv('PORT')),
                                            fromaddr=os.getenv('GUSERNAME'),
                                            toaddrs=os.getenv('RECEIVER'),
                                            subject=u"Script error!",
                                            credentials=(os.getenv('GUSERNAME'),
                                            os.getenv('GMAIL_PASS')),
                                            secure=()))




def main():
    if len(sys.argv) > 1:
        try:

            if sys.argv[1].lower() == "rss":
                read_rss_and_tweet(url=Settings.combined_feed)
            elif sys.argv[1].lower() == "rtg":
                search_and_retweet('global_search')
            elif sys.argv[1].lower() == "rtl":
                search_and_retweet('list_search')
            elif sys.argv[1].lower() == "rto":
                retweet_own()
            elif sys.argv[1].lower() == "sch":

                scheduled_job()

        except Exception as e:
            logging.exception(e)

        else:
            display_help()
    else:
        display_help()

add_hashtag = ['psilocybin', 'psilocybine' , 'psychedelic','psychological','hallucinogenic'
               'trip', 'therapy', 'psychiatry','dmt','mentalhealth','alzheimer','depression','axiety',
               'dopamine', 'serotonin', 'lsd', 'drug-policy','drugspolicy','drugpolicy', 'mdma',
               'microdosing', 'drug', 'ayahuasca', 'psychopharmacology', 'clinical trial',
               'neurogenesis','serotonergic','ketamine',
               'consciousness', 'psychotherapy','meta-analysis']

## list of the distribution
mylist_id = '1306244304000749569'  # todo add covid example
## reosted error to ignore for the log.list
IGNORE_ERRORS = [327]


# Setup API:
def twitter_setup():
    # Authenticate and access using keys:
    auth = tweepy.OAuthHandler(os.getenv('CONSUMER_KEY'), os.getenv('CONSUMER_SECRET'))
    auth.set_access_token(os.getenv('ACCESS_TOKEN'), os.getenv('ACCESS_SECRET'))

    # Return API access:
    api = tweepy.API(auth)
    return (api)


class Settings:
    """Twitter bot application settings.

    Enter the RSS feed you want to tweet, or keywords you want to retweet.
    """
    # RSS feeds to read and post tweets from.
    feed_urls = [
        "https://pubmed.ncbi.nlm.nih.gov/rss/search/1Di1IZzM0R4FRnKYsI1qINYHDYUiWSVAWo0rd3bhufn34wQ9HU/?limit=100&utm_campaign=pubmed-2&fc=20201028084526",
        'http://export.arxiv.org/api/query?search_query=all:psilocybin*&start=0&max_results=100&sortBy=lastUpdatedDate&sortOrder=descending',
        ]
    # nested list/dictionary comprehension to parse multiple RSS feeds
    combined_feed = [feedparser.parse(url) for url in
                     feed_urls]  # Log file to save all tweeted RSS links (one URL per line).
    posted_urls_output_file = "/home/farcila/what_a_c/posted-urls.log"

    # Log file to save all retweeted tweets (one tweetid per line).
    posted_retweets_output_file = "/home/farcila/what_a_c/posted-retweets.log"

    # Include tweets with these words when retweeting.
    retweet_include_words = ["drugpolicy","drugspolicy","transformdrugspolicy","transformdrugspolicy", "drugchecking",
    "regulatestimulants", "safeconsumption","harmreduction","druguse", "decriminalize", "safersuply"]

    # Do not include tweets with these words when retweeting.
    retweet_exclude_words = ["sex", "sexual", "sexwork", "sexualwork", "fuck"]


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
    title=item["title"]
    for x in add_hashtag:
        if re.search(fr'\b{x}', title.lower()):
            title=(re.sub(fr'\b{x}',f'#{x}', title.lower()))
    link, _ = item["link"], item["description"]
    message = shorten_text(title, maxlength=250) + " " + link
    return message


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
    return (text[:maxlength] + '...') if len(text) > maxlength else text


def post_tweet(message: str):
    """Post tweet message to account.

    Parameters
    ----------
    message: str
        Message to post on Twitter.
    """
    try:
        twitter_api = twitter_setup()
        # print('post_tweet():', message)
        twitter_api.update_status(status=message)
    except tweepy.TweepError as e:
        print(e)


def read_rss_and_tweet(url: str):
    """Read RSS and post feed items as a tweet.

    Parameters
    ----------
    url: str
        URL to RSS feed.
    """
    feeds = Settings.combined_feed
    count = 0

    if feeds:
        for feed in feeds:
            while count in range(0, len(feed["items"])):
                item = feed["items"][count]
                link_id = item.id

                if not is_in_logfile(link_id, Settings.posted_urls_output_file):
                    print(item)
                    post_tweet(message=compose_message(item))
                    write_to_logfile(f"{link_id}", Settings.posted_urls_output_file)
                    print("Posted:", link_id, compose_message(item))
                    break
                else:
                    print(count, "Already posted:", link_id, "Trying next")
                    count += 1
    else:
        print("Nothing found in feed", url)


def get_query() -> str:
    """Create Twitter search query with included words minus the
    excluded words.

    Returns
    -------
    str
        Returns a string with the Twitter search query.
    """
    include = " OR ".join(Settings.retweet_include_words)
    exclude = " -".join(Settings.retweet_exclude_words)
    exclude = "-" + exclude if exclude else ""
    return include + " " + exclude


def retweet_from_users(twitter_api,tweet_id):

    """
    retweet from normal users retweeting something interesting
    """

    retweeters = twitter_api.retweets(tweet_id)

    future_friends=[]
    for retweet in retweeters:
        friends= retweet.author.friends_count
        followers = retweet.author.followers_count
        follows_friends_ratio= followers/friends

        if friends > followers:
            future_friends.append((follows_friends_ratio,retweet.id))
            print(retweet.id_str,(retweet.author.screen_name, friends, followers),followers/friends)
        else:
            pass
    if future_friends:
        return min(future_friends)[1]
    else:
        return tweet_id


def try_retweet(twitter_api, tweet_text, tweet_id):
    '''try to retweet, if already retweeted try next fom the list
    of recent tweets'''

    tweet_id=retweet_from_users(twitter_api,tweet_id)

    if not is_in_logfile(
            tweet_id, Settings.posted_retweets_output_file) and len(tweet_text.split()) > 3:
        try:
            twitter_api.retweet(id=tweet_id)
            write_to_logfile(
                tweet_id, Settings.posted_retweets_output_file)
            print("try_retweet(): Retweeted {} (id {})".format(shorten_text(
                tweet_text, maxlength=140), tweet_id))
            return True
        except tweepy.TweepError as e:
            if e.api_code in IGNORE_ERRORS:
                return False
            else:
                print(e)
                return True
    else:
        print("Already retweeted {} (id {})".format(
            shorten_text(tweet_text, maxlength=140), tweet_id))

def filter_tweet(status, twitter_api):
    """
    function to ensure that retweets are on-topic
    by the hashtag list
    """

    if status.is_quote_status:
        quoted_tweet=twitter_api.get_status(status.quoted_status_id_str, tweet_mode="extended")
        end_status= status.full_text+quoted_tweet.full_text
    else:
        end_status= status.full_text
    if [x for x in add_hashtag if x in end_status.lower()]:
        return (status.retweet_count + status.favorite_count, status.id_str, status.full_text)


def search_and_retweet(flag='global_search', count=10):
    """Search for a query in tweets, and retweet those tweets.

    Parameters
    ----------
    flag: str
        A query to search for on Twitter. it can be `global_search` to search globally
        or `list_search` reduced to a list defined on mylist_id
    count: int
        Number of tweets to search for. You should probably keep this low
        when you use search_and_retweet() on a schedule (e.g. cronjob).
    """
    try:
        twitter_api = twitter_setup()
        if flag == 'global_search':
            ## search results retweets globally forgiven keywords
            search_results = twitter_api.search(q=get_query(), count=count, tweet_mode="extended")  ## standard search results
        else:
            ## search list retwwets most commented ad rt from the experts lists
            search_results = twitter_api.list_timeline(list_id=mylist_id, count=count, tweet_mode="extended")  ## list to tweet from

    except tweepy.TweepError as e:
        print(e.reason)
        return

    # Make sure we don't retweet any duplicates.
    count = 0
    ## get the most faved+ rtweeted and retweet it
    max_val = sorted(([filter_tweet(x,twitter_api) for x in search_results if filter_tweet(x,twitter_api)]))

    if max_val:
        while (True):
            print(max_val)
            tweet_id = max_val[-1 - count][1]
            tweet_text = max_val[-1 - count][2]
            print(tweet_text)
            if try_retweet(twitter_api, tweet_text, tweet_id):
                break
            elif count > len(search_results) or len(max_val)>2:
                print('no more tweets to publish')
                break
            else:
                count += 1
                time.sleep(2)
                continue

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


def retweet_own():
    """
    re-tweet self last tweetet message.
    """
    count = 0
    try:
        while True:
            twitter_api = twitter_setup()
            tweet = twitter_api.user_timeline(id=twitter_api, count=10)[count]
            if not tweet.retweeted:
                twitter_api.retweet(tweet.id_str)
                print("retweeted: ", tweet.text)
                break
            else:
                print('already retweeted, trying next')
                count += 1

    except tweepy.TweepError as e:
        print(e)


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
        print(e)


def scheduled_job():
    # job 1
    schedule.every().day.at("22:20").do(read_rss_and_tweet, url=Settings.combined_feed)
    schedule.every().day.at("06:20").do(read_rss_and_tweet, url=Settings.combined_feed)
    schedule.every().day.at("14:20").do(read_rss_and_tweet, url=Settings.combined_feed)
    # job 2
    schedule.every().day.at("01:10").do(retweet_own)
    schedule.every().day.at("09:10").do(retweet_own)
    schedule.every().day.at("17:10").do(retweet_own)
    # job 3
    schedule.every().day.at("00:20").do(search_and_retweet, 'global_search')
    schedule.every().day.at("03:20").do(search_and_retweet, 'global_search')
    schedule.every().day.at("06:20").do(search_and_retweet, 'global_search')
    schedule.every().day.at("09:20").do(search_and_retweet, 'global_search')
    schedule.every().day.at("12:20").do(search_and_retweet, 'global_search')
    schedule.every().day.at("15:20").do(search_and_retweet, 'global_search')
    schedule.every().day.at("18:20").do(search_and_retweet, 'global_search')
    schedule.every().day.at("21:20").do(search_and_retweet, 'global_search')
    # job 4
    schedule.every().day.at("01:25").do(search_and_retweet, 'list_search')
    schedule.every().day.at("04:25").do(search_and_retweet, 'list_search')
    schedule.every().day.at("07:25").do(search_and_retweet, 'list_search')
    schedule.every().day.at("10:25").do(search_and_retweet, 'list_search')
    schedule.every().day.at("13:25").do(search_and_retweet, 'list_search')
    schedule.every().day.at("16:25").do(search_and_retweet, 'list_search')
    schedule.every().day.at("19:25").do(search_and_retweet, 'list_search')
    schedule.every().day.at("22:25").do(search_and_retweet, 'list_search')

    while 1:
        schedule.run_pending()
        time.sleep(1)


def display_help():
    """Show available commands."""
    print("Syntax: python {} [command]".format(sys.argv[0]))
    print()
    print(" Commands:")
    print("    rss    Read URL and post new items to Twitter")
    print("    rtg    Search and retweet keywords from global feed")
    print("    rtl    Search and retweet keywords from list feed")
    print("    rto    Retweet last own tweet")
    print("    sch    Run scheduled jobs on infinite loop")
    print("    help   Show this help screen")


if __name__ == "__main__":
    main()