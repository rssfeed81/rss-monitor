Python 3.14.2 (tags/v3.14.2:df79316, Dec  5 2025, 17:18:21) [MSC v.1944 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.
>>> # RSS Feed URLs to monitor
... FEEDS = {
...     "https://feeds.feedburner.com/Freightwaves": "FreightWaves",
...     "https://rss.cnn.com/rss/edition": "CNN",
...     "https://news.google.com/rss/search?q=%22ups%22%20AND%20%22teamsters%22&hl=en-US&gl=US&ceid=US%3Aen": "Google News",
...     "https://teamster.org/feed/": "Teamsters",
... }
... 
... # Keywords to monitor (case insensitive)
... KEYWORDS = ['UPS', 'Teamsters']
... 
... # How often to check feeds (in seconds)
... CHECK_INTERVAL = 300  # 5 minutes, ignored in this setup since GitHub Actions controls timing
... 
... # Notification settings (uncomment and configure the one you want to use)
... # Email Settings
... EMAIL_SETTINGS = {
...     'sender': 'xxxxxxxx@gmail.com',
...     'password': 'xxxxxxx',  # Gmail requires an App Password
...     'recipient': 'xxx@xxx.com',
...     'smtp_server': 'smtp.gmail.com',
...     'smtp_port': 465
