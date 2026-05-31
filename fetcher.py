# fetcher.py
import re
import time
import feedparser
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from database import (
    get_all_users_with_topics,
    link_exists,
    save_seen_link
)


# =========================================================
# CONFIG
# =========================================================


BACKFILL_DAYS = 2

MAX_ITEMS_PER_FEED = 5
MAX_INITIAL_MESSAGES = 10
MAX_ITEMS_PER_TOPIC = 3

HEADERS = {
    "User-Agent": "BeaconFeedBot/1.0"
}


# =========================================================
# GLOBAL RSS FEEDS
# =========================================================

GLOBAL_RSS_FEEDS = [

    # General News
    "https://rss.cnn.com/rss/edition.rss",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.reuters.com/reuters/topNews",

    # Tech
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/index",

    # Cybersecurity
    "https://feeds.feedburner.com/TheHackersNews",

    # Gaming
    "https://www.gamespot.com/feeds/mashup/",

    # Blender
    "https://code.blender.org/feed/",

    # Startups / Hacker News
    "https://hnrss.org/frontpage",

    # Science
    "https://www.sciencedaily.com/rss/all.xml",
]


# =========================================================
# GLOBAL SCRAPE SITES
# =========================================================

GLOBAL_SCRAPE_SITES = [
    "https://news.ycombinator.com/"
]



# =========================================================
# DATE HELPERS
# =========================================================

def is_recent(entry):

    try:

        if hasattr(entry, "published_parsed"):

            published = datetime.fromtimestamp(
                time.mktime(entry.published_parsed)
            )

            cutoff = datetime.now() - timedelta(
                days=BACKFILL_DAYS
            )

            return published >= cutoff

    except:
        pass

    return True


def get_published(entry):

    try:

        if hasattr(entry, "published"):
            return entry.published

    except:
        pass

    return "Unknown"


def parse_entry_time(entry):

    try:

        if hasattr(entry, "published_parsed"):

            return datetime.fromtimestamp(
                time.mktime(
                    entry.published_parsed
                )
            )

    except:
        pass

    return datetime.now()


def format_date(date_str):

    try:

        dt = datetime.strptime(
            date_str,
            "%a, %d %b %Y %H:%M:%S %Z"
        )

        return dt.strftime(
            "%d %b %Y | %I:%M %p"
        )

    except:
        return date_str


# =========================================================
# RSS FETCHER
# =========================================================

def fetch_rss():

    collected = []

    for feed_url in GLOBAL_RSS_FEEDS:

        try:

            print(f"[RSS] Fetching: {feed_url}")

            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:MAX_ITEMS_PER_FEED]:

                if not is_recent(entry):
                    continue

                item = {

                    "source": "RSS",

                    "title": entry.get(
                        "title",
                        ""
                    ),

                    "link": entry.get(
                        "link",
                        ""
                    ),

                    "summary": entry.get(
                        "summary",
                        ""
                    ),

                    "published": get_published(
                        entry
                    ),

                    "published_timestamp":
                    parse_entry_time(entry)
                }

                collected.append(item)

        except Exception as e:

            print(f"[RSS ERROR] {feed_url}")
            print(e)

    return collected


# =========================================================
# SCRAPER
# =========================================================

def fetch_scraped_sites():

    collected = []

    for url in GLOBAL_SCRAPE_SITES:

        try:

            print(f"[SCRAPE] Fetching: {url}")

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=10
            )

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            titles = soup.select(
                ".titleline a"
            )

            for title in titles[:20]:

                item = {

                    "source": "WebScrape",

                    "title": title.text.strip(),

                    "link": title.get("href"),

                    "summary": "",

                    "published": "Live",

                    "published_timestamp":
                    datetime.now()
                }

                collected.append(item)

        except Exception as e:

            print(f"[SCRAPE ERROR] {url}")
            print(e)

    return collected


# =========================================================
# GOOGLE NEWS SEARCH
# =========================================================

def fetch_google_news(topic):

    collected = []

    try:

        encoded_topic = quote(topic)

        rss_url = (
            "https://news.google.com/rss/search?q="
            f"{encoded_topic}"
        )

        print(f"[GOOGLE NEWS] {topic}")

        feed = feedparser.parse(rss_url)

        for entry in feed.entries[:20]:

            if not is_recent(entry):
                continue

            item = {

                "source": "GoogleNews",

                "title": entry.get(
                    "title",
                    ""
                ),

                "link": entry.get(
                    "link",
                    ""
                ),

                "summary": entry.get(
                    "summary",
                    ""
                ),

                "published": get_published(
                    entry
                ),

                "published_timestamp":
                parse_entry_time(entry)
            }

            collected.append(item)

    except Exception as e:

        print(f"[GOOGLE NEWS ERROR] {topic}")
        print(e)

    return collected


# =========================================================
# MASTER CONTENT COLLECTOR
# =========================================================

def collect_global_content(user_topics):

    all_content = []

    # RSS
    all_content.extend(
        fetch_rss()
    )

    # Scraping
    all_content.extend(
        fetch_scraped_sites()
    )

    # Dynamic Google News
    for topic in user_topics:

        all_content.extend(
            fetch_google_news(topic)
        )

    return all_content


# =========================================================
# TOPIC MATCHER
# =========================================================

def topic_matches(content, topic):

    text = (
        content["title"] + " " +
        content["summary"]
    ).lower()

    topic = topic.lower()

    pattern = (
        r"\b" +
        re.escape(topic) +
        r"\b"
    )

    return (
        re.search(pattern, text)
        is not None
    )


# =========================================================
# FILTER FOR USERS
# =========================================================

def filter_for_users(
    all_content,
    users_data
):

    matched_results = {}


    for user_id, user_data in users_data.items():

        topics = user_data["topics"]

        matched_results[user_id] = {
            "items": [],
            "first_run": False
        }


        # =====================================
        # PROCESS ITEMS
        # =====================================

        for item in all_content:

            # duplicate prevention
            if link_exists(user_id, item["link"]):
                continue

            
            
            # =================================
            # TOPIC MATCHING
            # =================================

            for topic in topics:

                if topic_matches(
                    item,
                    topic
                ):

                    item_copy = item.copy()
                    item_copy["published_timestamp"] = (
                        item_copy["published_timestamp"]
                        .isoformat()
                    )

                    item_copy[
                        "matched_topic"
                    ] = topic

                    item_copy[
                        "published"
                    ] = format_date(
                        item_copy["published"]
                    )

                    matched_results[user_id]["items"].append(
                        item_copy
                    )

                    save_seen_link(
                        user_id,
                        item["link"]
                    )

                    break

        # =====================================
        # LIMIT PER TOPIC
        # =====================================

        topic_groups = {}

        for item in matched_results[user_id]["items"]:

            topic = item["matched_topic"]

            if topic not in topic_groups:

                topic_groups[topic] = []

            topic_groups[topic].append(item)

        limited_items = []

        for topic, topic_items in topic_groups.items():

            topic_items.sort(
                key=lambda x:
                datetime.fromisoformat(
                    x["published_timestamp"]
                ),
                reverse=True
            )

            limited_items.extend(
                topic_items[:MAX_ITEMS_PER_TOPIC]
            )

        # Final overall sort
        limited_items.sort(
            key=lambda x:
            datetime.fromisoformat(
                x["published_timestamp"]
            ),
            reverse=True
        )

        matched_results[user_id]["items"] = (
            limited_items
        )

    return matched_results


# =========================================================
# MAIN FETCH FUNCTION
# =========================================================

def get_updates():

    users_data = get_all_users_with_topics()

    all_topics = set()

    for user_data in users_data.values():

        for topic in user_data["topics"]:

            all_topics.add(topic)

    all_content = collect_global_content(
        list(all_topics)
    )

    filtered = filter_for_users(
        all_content,
        users_data
    )

    return filtered