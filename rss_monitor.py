import feedparser
import os
import sqlite3
import time
import threading
import logging
from datetime import datetime
from config import FEEDS, KEYWORDS


class RSSMonitor:
    def __init__(self):
        print("Initializing RSS Monitor...")
        os.makedirs("data", exist_ok=True)

        self.conn = sqlite3.connect(
            "data/rss_feeds.db",
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )

        sqlite3.register_adapter(datetime, lambda x: x.isoformat())
        sqlite3.register_converter("datetime", lambda x: datetime.fromisoformat(x.decode()))

        self.db_lock = threading.Lock()
        self.create_database()

        logging.basicConfig(
            filename="data/rss_monitor.log",
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        print("Initialization complete.")

    def create_database(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    link TEXT UNIQUE,
                    description TEXT,
                    published datetime,
                    feed_name TEXT,
                    keywords_matched TEXT,
                    processed_date datetime
                )
            """)
            self.conn.commit()

    def check_feed(self, feed_url, feed_name):
        try:
            print(f"Checking feed: {feed_name}")
            feed = feedparser.parse(feed_url)

            entries = getattr(feed, "entries", [])
            print(f"Number of entries: {len(entries)}")

            new_articles = 0
            matched_articles = 0

            with self.db_lock:
                cursor = self.conn.cursor()

                for entry in entries:
                    pub_date = datetime.now()
                    try:
                        if getattr(entry, "published_parsed", None):
                            pub_date = datetime.fromtimestamp(
                                time.mktime(entry.published_parsed)
                            )
                    except Exception:
                        pass

                    link = getattr(entry, "link", None)
                    title = getattr(entry, "title", "(no title)")
                    description = getattr(entry, "description", "") or ""

                    if not link:
                        continue

                    cursor.execute(
                        "SELECT id FROM articles WHERE link = ?",
                        (link,)
                    )
                    if cursor.fetchone():
                        continue

                    new_articles += 1

                    content = f"{title} {description}".lower()
                    matched_keywords = [
                        kw for kw in KEYWORDS if kw.lower() in content
                    ]

                    if matched_keywords:
                        matched_articles += 1
                        print(f"Match found: {title} -> {matched_keywords}")

                    cursor.execute("""
                        INSERT OR IGNORE INTO articles
                        (title, link, description, published, feed_name, keywords_matched, processed_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        title,
                        link,
                        description,
                        pub_date,
