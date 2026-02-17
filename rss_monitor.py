import feedparser
import os
import sqlite3
import time
import threading
import logging
import re
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

        # Purge old data so DB doesn't grow forever
        self.purge_old_articles(months=3)

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
                    published TEXT,
                    feed_name TEXT,
                    keywords_matched TEXT,
                    processed_date TEXT
                )
            """)
            self.conn.commit()

    def purge_old_articles(self, months=3):
        """
        Delete articles older than `months` months and VACUUM to shrink the DB file.
        """
        with self.db_lock:
            cursor = self.conn.cursor()

            # Count before
            cursor.execute("SELECT COUNT(*) FROM articles")
            before_count = cursor.fetchone()[0]

            # Delete old rows (works well with ISO datetime strings)
            cursor.execute(
                f"DELETE FROM articles WHERE datetime(published) < datetime('now', '-{months} months')"
            )
            deleted = cursor.rowcount

            self.conn.commit()

            # Compact DB file size
            try:
                cursor.execute("VACUUM")
            except Exception as e:
                # VACUUM can fail if DB is busy; in Actions it's usually fine.
                logging.warning(f"VACUUM failed: {e}")

            # Count after
            cursor.execute("SELECT COUNT(*) FROM articles")
            after_count = cursor.fetchone()[0]
            self.conn.commit()

        print(f"DB purge complete: deleted {deleted} old rows (before={before_count}, after={after_count})")

    def is_strict_and_match(self, text):
        """
        Strict AND match for all KEYWORDS, exact word match (UPS won't match CUPS).
        Case-insensitive.
        """
        patterns = [
            re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
            for kw in KEYWORDS
        ]
        return all(p.search(text) for p in patterns)

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
                    title = getattr(entry, "title", "(no title)")
                    link = getattr(entry, "link", None)
                    description = getattr(entry, "description", "") or ""

                    if not link:
                        continue

                    # published date
                    pub_date = datetime.now()
                    try:
                        if getattr(entry, "published_parsed", None):
                            pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    except Exception:
                        pass

                    # skip if already exists
                    cursor.execute("SELECT id FROM articles WHERE link = ?", (link,))
                    if cursor.fetchone():
                        continue

                    new_articles += 1

                    content = f"{title} {description}"
                    matched_keywords = []

                    if self.is_strict_and_match(content):
                        matched_keywords = KEYWORDS.copy()
                        matched_articles += 1
                        print(f"Match: {title} -> {matched_keywords}")

                    cursor.execute("""
                        INSERT OR IGNORE INTO articles
                        (title, link, description, published, feed_name, keywords_matched, processed_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        title,
                        link,
                        description,
                        pub_date.isoformat(),
                        feed_name,
                        ",".join(matched_keywords),
                        datetime.now().isoformat(),
                    ))

                self.conn.commit()

            print(f"{feed_name}: {new_articles} new, {matched_articles} matches")

        except Exception as e:
            print(f"Error processing {feed_name}: {e}")
            logging.exception(f"Error processing {feed_name}")

    def generate_html(self):
        with self.db_lock:
            cursor = self.conn.cursor()

            # Top section: last 50 articles (show match info too)
            cursor.execute("""
                SELECT title, link, feed_name, published, keywords_matched, processed_date
                FROM articles
                ORDER BY datetime(published) DESC
                LIMIT 50
            """)
            latest_50 = cursor.fetchall()

            # Matches section: last 50 matches
            cursor.execute("""
                SELECT title, link, feed_name, published, keywords_matched, processed_date
                FROM articles
                WHERE keywords_matched IS NOT NULL AND keywords_matched != ""
                ORDER BY datetime(published) DESC
                LIMIT 50
            """)
            matches_50 = cursor.fetchall()

        html = f"""
<html>
<head>
  <title>RSS Monitor</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 30px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
    tr:nth-child(even) {{ background-color: #f9f9f9; }}
    .match {{ font-weight: bold; }}
    .muted {{ color: #666; font-size: 0.9em; }}
  </style>
</head>
<body>
  <h1>RSS Feed Monitor</h1>
  <p class="muted">Feeds: {', '.join(FEEDS.values())}</p>
  <p class="muted">Strict AND keywords (exact words): {', '.join(KEYWORDS)}</p>

  <h2>Latest 50 Articles (Top)</h2>
  <table>
    <tr>
      <th>Title</th>
      <th>Feed</th>
      <th>Published</th>
      <th>Matched?</th>
      <th>Keywords</th>
    </tr>
"""

        for title, link, feed_name, published, keywords_matched, processed_date in latest_50:
            is_match = "YES" if (keywords_matched and keywords_matched.strip()) else ""
            match_class = "match" if is_match else ""
            html += f"""
    <tr>
      <td class="{match_class}"><a href="{link}" target="_blank">{title}</a></td>
      <td>{feed_name}</td>
      <td>{published}</td>
      <td class="{match_class}">{is_match}</td>
      <td>{keywords_matched or ""}</td>
    </tr>
"""

        html += """
  </table>

  <h2>Latest 50 Matches</h2>
  <table>
    <tr>
      <th>Title</th>
      <th>Feed</th>
      <th>Published</th>
      <th>Keywords</th>
    </tr>
"""

        for title, link, feed_name, published, keywords_matched, processed_date in matches_50:
            html += f"""
    <tr>
      <td class="match"><a href="{link}" target="_blank">{title}</a></td>
      <td>{feed_name}</td>
      <td>{published}</td>
      <td>{keywords_matched}</td>
    </tr>
"""

        html += """
  </table>

</body>
</html>
"""

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)


if __name__ == "__main__":
    monitor = RSSMonitor()

    for feed_url, feed_name in FEEDS.items():
        monitor.check_feed(feed_url, feed_name)

    # purge again after inserts (keeps DB clean even if it ran a long time)
    monitor.purge_old_articles(months=3)

    monitor.generate_html()
