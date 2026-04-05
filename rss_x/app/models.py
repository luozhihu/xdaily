"""Database models."""
from datetime import datetime
from app import db


class User(db.Model):
    """User model."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Category(db.Model):
    """Category model."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    feeds = db.relationship('Feed', backref='category', lazy=True)
    summaries = db.relationship('Summary', backref='category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Feed(db.Model):
    """Feed (博主) model."""
    __tablename__ = 'feeds'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    twitter_username = db.Column(db.String(50), nullable=False, unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    enabled = db.Column(db.Boolean, default=True)
    tags = db.Column(db.Text, nullable=True)  # JSON string
    description = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    followers_count = db.Column(db.Integer, default=0)
    last_fetch_at = db.Column(db.DateTime, nullable=True)
    last_tweet_at = db.Column(db.DateTime, nullable=True)
    tweets_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Note: tweets relationship removed - Tweet links to Feed via twitter_username, not feed_id
    fetch_logs = db.relationship('FetchLog', backref='feed', lazy=True)

    def to_dict(self, include_category=False):
        result = {
            'id': self.id,
            'name': self.name,
            'twitter_username': self.twitter_username,
            'category_id': self.category_id,
            'enabled': self.enabled,
            'description': self.description,
            'avatar_url': self.avatar_url,
            'followers_count': self.followers_count,
            'tags': self.tags,
            'last_fetch_at': self.last_fetch_at.isoformat() if self.last_fetch_at else None,
            'last_tweet_at': self.last_tweet_at.isoformat() if self.last_tweet_at else None,
            'tweets_count': self.tweets_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_category and self.category:
            result['category_name'] = self.category.name
        return result


class Tweet(db.Model):
    """Tweet model."""
    __tablename__ = 'tweets'

    id = db.Column(db.String(50), primary_key=True)  # Twitter tweet ID
    author = db.Column(db.String(100), nullable=False)
    twitter_username = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(500), nullable=True)
    published = db.Column(db.DateTime, nullable=True)
    published_date = db.Column(db.Date, nullable=True)
    fetched_date = db.Column(db.Date, nullable=False)
    fetched_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tags = db.Column(db.Text, nullable=True)  # JSON string
    is_retweet = db.Column(db.Boolean, default=False)
    is_reply = db.Column(db.Boolean, default=False)
    extra_data = db.Column(db.Text, nullable=True)  # JSON string (renamed from metadata)

    __table_args__ = (
        db.Index('idx_tweets_fetched', 'fetched_date'),
        db.Index('idx_tweets_published', 'published'),
        db.Index('idx_tweets_username', 'twitter_username'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'author': self.author,
            'twitter_username': self.twitter_username,
            'content': self.content,
            'link': self.link,
            'published': self.published.isoformat() if self.published else None,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'fetched_date': self.fetched_date.isoformat() if self.fetched_date else None,
            'tags': self.tags,
            'is_retweet': self.is_retweet,
            'is_reply': self.is_reply,
            'extra_data': self.extra_data
        }


class FetchLog(db.Model):
    """Fetch log model."""
    __tablename__ = 'fetch_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('feeds.id'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False)  # success/partial/failed
    items_new = db.Column(db.Integer, default=0)
    items_dup = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    rss_source = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'feed_id': self.feed_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status,
            'items_new': self.items_new,
            'items_dup': self.items_dup,
            'error_message': self.error_message,
            'rss_source': self.rss_source
        }


class Summary(db.Model):
    """AI Summary model."""
    __tablename__ = 'summaries'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    summary_date = db.Column(db.Date, nullable=False)
    summary_text = db.Column(db.Text, nullable=True)
    tweets_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), nullable=False)  # success/failed
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint: one summary per category per day
    __table_args__ = (
        db.UniqueConstraint('category_id', 'summary_date', name='uq_category_summary_date'),
    )

    def to_dict(self, include_category=False):
        result = {
            'id': self.id,
            'category_id': self.category_id,
            'summary_date': self.summary_date.isoformat() if self.summary_date else None,
            'summary_text': self.summary_text,
            'tweets_count': self.tweets_count,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_category and self.category:
            result['category_name'] = self.category.name
        return result
