import feedparser
import os
import sqlite3
import time
import threading
import logging
import re
from datetime import datetime
from config import FEEDS, KEYWORDS


DB_PATH = "data/rss_feeds.db"
LOG_PATH = "data/rss_monitor.log"


class RSSMonitor:
    def __init__(self):
        print("Initializing RSS Monitor...")
        os.makedirs("data", exist_ok=True)

        self.conn = sqlite3.connect(
            DB_PATH,
            check_same_thread=False,
        )

        self.db_lock = threading.Lock()
        self.create_database()

        logging.basicConfig(
            filename=LOG_PATH,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

        # Keep DB from growing forever
        self.purge_old_articles(months=3)

        print("Initialization complete.")

    def create_database(self):
        with self.db_lock:
            cursor = self.conn.cursor()
            cursor.execute(
                """
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
                """
            )
            self.conn.commit()

    def purge_old_articles(self, months=3):
        """Delete articles older than `months` months and VACUUM to shrink DB size."""
        with self.db_lock:
            cursor = self.conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM articles")
            before_count = cursor.fetchone()[0]

            cursor.execute(
                f"DELETE FROM articles WHERE datetime(published) < datetime('now', '-{months} months')"
            )
            deleted = cursor.rowcount
            self.conn.commit()

            # Compact DB file size (optional but nice)
            try:
                cursor.execute("VACUUM")
            except Exception as e:
                logging.warning(f"VACUUM failed: {e}")

            cursor.execute("SELECT COUNT(*) FROM articles")
            after_count = cursor.fetchone()[0]
            self.conn.commit()

        print(f"DB purge complete: deleted {deleted} old rows (before={before_count}, after={after_count})")

    def is_strict_and_match(self, text: str) -> bool:
        """Strict AND + exact word match (UPS won't match CUPS), case-insensitive."""
        patterns = [
            re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
            for kw in KEYWORDS
        ]
        return all(p.search(text) for p in patterns)

    def _safe_pub_date_iso(self, entry) -> str:
        # Prefer published_parsed if present
        try:
            pp = getattr(entry, "published_parsed", None)
            if pp:
                return datetime.fromtimestamp(time.mktime(pp)).isoformat()
        except Exception:
            pass

        # Some feeds use updated_parsed
        try:
            up = getattr(entry, "updated_parsed", None)
            if up:
                return datetime.fromtimestamp(time.mktime(up)).isoformat()
        except Exception:
            pass

        return datetime.now().isoformat()

    def check_feed(self, feed_url, feed_name):
        try:
            print(f"Checking feed: {feed_name}")
            feed = feedparser.parse(feed_url)

            # feed.bozo == 1 means parse problems; don't crash, just log it
            if getattr(feed, "bozo", 0):
                logging.warning(f"Feed parse issue for {feed_name}: {getattr(feed, 'bozo_exception', '')}")

            entries = getattr(feed, "entries", []) or []
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
                        # Without a link we can't de-dupe reliably
                        continue

                    pub_iso = self._safe_pub_date_iso(entry)

                    # Skip if already exists
                    cursor.execute("SELECT id FROM articles WHERE link = ?", (link,))
                    if cursor.fetchone():
                        continue

                    new_articles += 1

                    content = f"{title} {description}"
                    matched_keywords = ""

                    if self.is_strict_and_match(content):
                        matched_articles += 1
                        matched_keywords = ",".join(KEYWORDS)
                        print(f"Match: {title} -> {KEYWORDS}")

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO articles
                        (title, link, description, published, feed_name, keywords_matched, processed_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            title,
                            link,
                            description,
                            pub_iso,
                            feed_name,
                            matched_keywords,
                            datetime.now().isoformat(),
                        ),
                    )

                self.conn.commit()

            print(f"{feed_name}: {new_articles} new, {matched_articles} matches")

        except Exception as e:
            print(f"Error processing {feed_name}: {e}")
            logging.exception(f"Error processing {feed_name}")

    def generate_html(self):
        with self.db_lock:
            cursor = self.conn.cursor()

            # ONLY matches: latest 50
            cursor.execute(
                """
                SELECT title, link, feed_name, published, keywords_matched
                FROM articles
                WHERE keywords_matched IS NOT NULL AND keywords_matched != ""
                ORDER BY datetime(published) DESC
                LIMIT 50
                """
            )
            matches_50 = cursor.fetchall()

        updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
  <p class="muted">Last updated: {updated}</p>
  <p class="muted">Feeds: {', '.join(FEEDS.values())}</p>
  <p class="muted">Strict AND keywords (exact words): {', '.join(KEYWORDS)}</p>

  <h2>Latest 50 Matches</h2>
  <table>
    <tr>
      <th>Title</th>
      <th>Feed</th>
      <th>Published</th>
      <th>Keywords</th>
    </tr>
"""

        if not matches_50:
            html += """
    <tr><td colspan="4">No matches found yet.</td></tr>
"""
        else:
            for title, link, feed_name, published, keywords_matched in matches_50:
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

    monitor.purge_old_articles(months=3)
    monitor.generate_html()
