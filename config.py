# RSS Feed URLs to monitor
FEEDS = {
    "https://feeds.feedburner.com/Freightwaves": "FreightWaves",
    "https://rss.cnn.com/rss/edition": "CNN",
    "https://news.google.com/rss/search?q=%22ups%22%20AND%20%22teamsters%22&hl=en-US&gl=US&ceid=US%3Aen": "Google News",
    "https://teamster.org/feed/": "Teamsters",
}

# Keywords to monitor (case insensitive)
KEYWORDS = ["UPS", "Teamsters"]

# How often to check feeds (in seconds)
# (Ignored when running in GitHub Actions — scheduling is handled in rss.yml)
CHECK_INTERVAL = 300  # 5 minutes


# Optional Email Notification Settings
# ⚠️ WARNING: Do NOT store real passwords in a public GitHub repo.
# Use GitHub Secrets instead.
EMAIL_SETTINGS = {
    "sender": "xxxxxxxx@gmail.com",
    "password": "xxxxxxxx",  # Use a Gmail App Password
    "recipient": "xxx@xxx.com",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465,
}

