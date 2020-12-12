 #  Bot, what a concept! 
 
 # :cactus:

Built on top of @peterdalle's [Twitterbot](https://github.com/peterdalle/twitterbot), uses `tweepy` instead of `twython` and adds further functionality: 

* Reads and parses a list of RSS feeds. Tweets an article's title and link to a Twitter account.
* Retweets previous RSS post after a given time. 
* Retweets the second most up-voted and retweeted posts from:
* * a globall search for specified keywords or hashtags.
* * a given distribution twitter list.
* Schedule jobs for any of the above. 

All functions can be used independently.

## Install

0. Download or git clone Twitterbot:
- `git clone https://github.com/franasal/concept_bot`
1. Install dependencies:
- `pip install feedparser`
- `pip install tweepy`
- `pip install schedule`
2. Create a [Twitter application](https://apps.twitter.com/), and generate keys, tokens etc.
3. Modifiy the settings in the source code.
- Modify `feed_urls` list to add the RSS feeds of your choice. see some [examples](https://github.com/roblanf/phypapers) on how to ser an RSS search.
- Modify the variables in the `access.py` file and add keys, tokens etc. for connecting to your Twitter app.
- Modify `retweet_include_words` for keywords you want to search and retweet, and `retweet_exclude_words` for keywords you would like to exclude from retweeting. For example `retweet_include_words = ["foo"]` and `retweet_exclude_words = ["bar"]` will include any tweet with the word "foo", as long as the word "bar" is absent. This list can also be left empty, i.e. `retweet_exclude_words = []`.
- Modify or add jobs to the `scheduled_job()` function.

## Requirements
* Python 3+
* * Twitter account

## Usage

Read the RSS feeds and post to Twitter account:

```bash
$ python d_what_a_c.py rss   
```

Search globally for tweets and retweet them:

```bash
$ python d_what_a_c.py rtg
```
Search for tweets within a Twitter list and retweet them:

```bash
$ python d_what_a_c.py rtl
```
Retweet last own tweet:

```bash
$ python d_what_a_c.py rto 
```
### deploy:

[Here](https://schedule.readthedocs.io/en/stable/) you can learn how set up tasks for the the `scheduled_job()` function

There are some nice free cloud solutions such as [pythonanywhere](https://www.pythonanywhere.com/), where you can deploy the bot
to do that just run:

```bash
$ python d_what_a_c.py  sch
```

Take a look at an [example bot](https://twitter.com/drugSciBot) providing scientific facts and educated opinions on psychedelic research and drug policy issues.

:hibiscus:
