-- Initial database schema
-- For SQLite

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Feeds table
CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    twitter_username TEXT NOT NULL UNIQUE,
    category_id INTEGER,
    enabled BOOLEAN DEFAULT 1,
    tags TEXT,
    last_fetch_at DATETIME,
    last_tweet_at DATETIME,
    tweets_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Tweets table
CREATE TABLE IF NOT EXISTS tweets (
    id TEXT PRIMARY KEY,
    author TEXT NOT NULL,
    twitter_username TEXT NOT NULL,
    content TEXT,
    link TEXT,
    published DATETIME,
    published_date DATE,
    fetched_date DATE NOT NULL,
    fetched_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    tags TEXT,
    is_retweet BOOLEAN DEFAULT 0,
    is_reply BOOLEAN DEFAULT 0,
    metadata TEXT
);

-- Fetch logs table
CREATE TABLE IF NOT EXISTS fetch_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL,
    started_at DATETIME NOT NULL,
    completed_at DATETIME,
    status TEXT NOT NULL,
    items_new INTEGER DEFAULT 0,
    items_dup INTEGER DEFAULT 0,
    error_message TEXT,
    rss_source TEXT,
    FOREIGN KEY (feed_id) REFERENCES feeds(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tweets_fetched ON tweets(fetched_date);
CREATE INDEX IF NOT EXISTS idx_tweets_published ON tweets(published);
CREATE INDEX IF NOT EXISTS idx_tweets_username ON tweets(twitter_username);
CREATE INDEX IF NOT EXISTS idx_feeds_category ON feeds(category_id);
CREATE INDEX IF NOT EXISTS idx_feeds_enabled ON feeds(enabled);
CREATE INDEX IF NOT EXISTS idx_fetch_logs_feed ON fetch_logs(feed_id);
