# RSS Feed URLs to monitor
FEEDS = {
    "https://feeds.feedburner.com/Freightwaves": "FreightWaves",
    "https://rss.cnn.com/rss/edition": "CNN",
    "https://onlabor.org/feed": "On Labor",
    "https://teamster.org/feed/": "Teamsters",
    "https://about.ups.com/newsroom": "UPS Newsroom",
    "https://server5.unionactive.com/dynadocs/unionactive_newswire.xml": "Union Active",
    "https://www.thetrucker.com/feed": "The Trucker",
    "https://www.ttnews.com/rss.xml": "Transportation Topics",
    "https://cdllife.com/feed/": "CDL Life",
    "https://tdu.org/news/": "TDU News"
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


