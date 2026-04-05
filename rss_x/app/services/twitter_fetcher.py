"""Twitter API-based feed fetching service."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from app import db
from app.models import Feed, Tweet, FetchLog
from app.services.twitter_client import (
    TwitterClient, TwitterAuth, RateLimitError, TwitterAuthError, TwitterAPIError
)
from app.services.twitter_parser import parse_timeline_response

logger = logging.getLogger(__name__)


@dataclass
class ParsedTweet:
    """Parsed tweet data."""
    id: str
    author: str
    twitter_username: str
    content: str
    link: str
    published: Optional[datetime]
    is_retweet: bool
    is_reply: bool
    metadata: dict = field(default_factory=dict)


@dataclass
class FetchResult:
    """Result of a fetch operation."""
    feed_id: int
    feed_name: str
    status: str  # success/partial/failed
    items_new: int
    items_dup: int
    items_skipped: int  # 非昨天的推文数量
    rss_source: str
    error_message: Optional[str] = None


def get_yesterday_date():
    """Get yesterday's date."""
    return (datetime.utcnow() - timedelta(days=1)).date()


class TwitterFetchError(Exception):
    """Raised when Twitter fetch fails."""
    pass


def twitter_tweet_to_parsed_tweet(tweet, username: str) -> ParsedTweet:
    """Convert TwitterTweet to ParsedTweet for unified storage."""
    return ParsedTweet(
        id=tweet.id,
        author=tweet.author.display_name,
        twitter_username=username or tweet.author.username,
        content=tweet.text,
        link=tweet.link,
        published=tweet.created_at,
        is_retweet=tweet.is_retweet,
        is_reply=tweet.is_reply,
        metadata={
            'metrics': {
                'retweet': tweet.metrics.retweet_count,
                'reply': tweet.metrics.reply_count,
                'like': tweet.metrics.like_count,
                'quote': tweet.metrics.quote_count,
                'bookmark': tweet.metrics.bookmark_count,
                'view': tweet.metrics.view_count,
            },
            'lang': tweet.lang,
            'source': tweet.source,
            'media_count': len(tweet.media),
        }
    )


def fetch_twitter_feed(feed: Feed, max_entries: int = 30) -> FetchResult:
    """
    Fetch tweets for a single feed using Twitter API.
    Returns FetchResult with statistics.
    """
    log = FetchLog(
        feed_id=feed.id,
        started_at=datetime.utcnow(),
        status='failed'
    )
    db.session.add(log)
    db.session.commit()

    try:
        # Create Twitter client
        auth = TwitterAuth()
        client = TwitterClient(auth=auth)

        cursor = None
        items_new = 0
        items_dup = 0
        items_skipped = 0
        yesterday = get_yesterday_date()

        while items_new + items_dup < max_entries:
            # Fetch user tweets
            result = client.fetch_user_tweets(
                username=feed.twitter_username,
                count=min(100, max_entries - items_new - items_dup),
                cursor=cursor,
            )

            for tweet in result.tweets:
                # Skip retweets
                if tweet.is_retweet:
                    items_skipped += 1
                    continue

                # Filter by date
                if tweet.created_at:
                    tweet_date = tweet.created_at.date()
                    if tweet_date != yesterday:
                        if tweet_date < yesterday:
                            items_skipped += 1
                            continue
                        # Future dates - include anyway

                # Convert to ParsedTweet for unified storage
                parsed: ParsedTweet = twitter_tweet_to_parsed_tweet(tweet, feed.twitter_username)

                # Check if already exists
                existing = Tweet.query.get(parsed.id)
                if existing:
                    items_dup += 1
                    continue

                # Create new tweet
                tweet_record = Tweet(
                    id=parsed.id,
                    author=parsed.author,
                    twitter_username=parsed.twitter_username,
                    content=parsed.content,
                    link=parsed.link,
                    published=parsed.published,
                    published_date=parsed.published.date() if parsed.published else None,
                    fetched_date=datetime.utcnow().date(),
                    is_retweet=parsed.is_retweet,
                    is_reply=parsed.is_reply,
                    extra_data=str(parsed.metadata),
                )
                db.session.add(tweet_record)
                items_new += 1

            # Check if more pages available
            if not result.has_more or not result.next_cursor:
                break

            cursor = result.next_cursor

        # Update feed statistics
        feed.last_fetch_at = datetime.utcnow()
        feed.tweets_count = Tweet.query.filter_by(twitter_username=feed.twitter_username).count()

        latest_tweet = Tweet.query.filter_by(
            twitter_username=feed.twitter_username
        ).order_by(Tweet.published.desc()).first()
        if latest_tweet and latest_tweet.published:
            feed.last_tweet_at = latest_tweet.published

        # Update fetch log
        log.status = 'success' if items_new > 0 else 'partial'
        log.items_new = items_new
        log.items_dup = items_dup
        log.completed_at = datetime.utcnow()
        log.rss_source = 'twitter_api'
        db.session.commit()

        logger.info(f"Feed {feed.name}: new={items_new}, dup={items_dup}, skipped={items_skipped}")

        return FetchResult(
            feed_id=feed.id,
            feed_name=feed.name,
            status=log.status,
            items_new=items_new,
            items_dup=items_dup,
            items_skipped=items_skipped,
            rss_source='twitter_api',
        )

    except TwitterAuthError as e:
        log.status = 'failed'
        log.error_message = f"Twitter auth error: {e}"
        log.completed_at = datetime.utcnow()
        log.rss_source = 'twitter_api'
        db.session.commit()
        logger.error(f"Twitter auth failed for feed {feed.name}: {e}")

        return FetchResult(
            feed_id=feed.id,
            feed_name=feed.name,
            status='failed',
            items_new=0,
            items_dup=0,
            items_skipped=0,
            rss_source='twitter_api',
            error_message=str(e),
        )

    except RateLimitError as e:
        log.status = 'failed'
        log.error_message = f"Rate limited: {e}"
        log.completed_at = datetime.utcnow()
        log.rss_source = 'twitter_api'
        db.session.commit()
        logger.warning(f"Rate limited for feed {feed.name}: {e}")

        return FetchResult(
            feed_id=feed.id,
            feed_name=feed.name,
            status='failed',
            items_new=0,
            items_dup=0,
            items_skipped=0,
            rss_source='twitter_api',
            error_message=str(e),
        )

    except TwitterAPIError as e:
        log.status = 'failed'
        log.error_message = f"Twitter API error: {e}"
        log.completed_at = datetime.utcnow()
        log.rss_source = 'twitter_api'
        db.session.commit()
        logger.error(f"Twitter API error for feed {feed.name}: {e}")

        return FetchResult(
            feed_id=feed.id,
            feed_name=feed.name,
            status='failed',
            items_new=0,
            items_dup=0,
            items_skipped=0,
            rss_source='twitter_api',
            error_message=str(e),
        )

    except Exception as e:
        log.status = 'failed'
        log.error_message = str(e)
        log.completed_at = datetime.utcnow()
        log.rss_source = 'twitter_api'
        db.session.commit()

        logger.error(f"Failed to fetch feed {feed.name}: {e}")

        return FetchResult(
            feed_id=feed.id,
            feed_name=feed.name,
            status='failed',
            items_new=0,
            items_dup=0,
            items_skipped=0,
            rss_source='twitter_api',
            error_message=str(e),
        )


def fetch_all_twitter_feeds(max_entries: int = 30) -> list:
    """Fetch all enabled feeds using Twitter API."""
    feeds = Feed.query.filter_by(enabled=True).all()
    results = []

    logger.info(f"Starting Twitter API fetch for {len(feeds)} feeds")

    for feed in feeds:
        result = fetch_twitter_feed(feed, max_entries)
        results.append(result)
        logger.info(f"Feed {feed.name}: new={result.items_new}, dup={result.items_dup}, status={result.status}")

    return results
