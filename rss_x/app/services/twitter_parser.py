"""Twitter GraphQL response parsing."""
import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.services.twitter_client import (
    TwitterUser, TwitterTweet, TweetMetrics, TweetMedia,
    TimelineResult
)

logger = logging.getLogger(__name__)


def parse_twitter_datetime(date_str: str) -> datetime:
    """Parse Twitter's datetime format: 'Fri Apr 03 23:32:53 +0000 2026' or 'Sat Apr 04 2026 00:00:00 +0000'."""
    # Twitter uses year at the end: 'Fri Apr 03 23:32:53 +0000 2026'
    try:
        return datetime.strptime(date_str, '%a %b %d %H:%M:%S %z %Y')
    except ValueError:
        try:
            # Alternative format with year after day: 'Sat Apr 04 2026 00:00:00 +0000'
            return datetime.strptime(date_str, '%a %b %d %Y %H:%M:%S %z')
        except ValueError:
            logger.warning(f"Failed to parse datetime: {date_str}")
            return datetime.utcnow()


def parse_tweet_metrics(legacy: dict) -> TweetMetrics:
    """Parse engagement metrics from tweet legacy data."""
    view_count = None
    if 'views_count' in legacy:
        views = legacy['views_count']
        if isinstance(views, dict):
            view_count = views.get('count') or views.get('state')
        elif isinstance(views, (int, str)):
            view_count = views

    return TweetMetrics(
        retweet_count=legacy.get('retweet_count', 0) or 0,
        reply_count=legacy.get('reply_count', 0) or 0,
        like_count=legacy.get('favorite_count', 0) or 0,
        quote_count=legacy.get('quote_count', 0) or 0,
        bookmark_count=legacy.get('bookmark_count', 0) or 0,
        view_count=view_count,
    )


def parse_user(user_result: dict) -> TwitterUser:
    """Parse Twitter user from user_results."""
    if not user_result or user_result.get('result') is None:
        raise ValueError("Invalid user result")

    result = user_result['result']
    legacy = result.get('legacy', {})
    core = result.get('core', {})

    # screen_name is in core for new API, fallback to legacy
    username = core.get('screen_name') or legacy.get('screen_name', '')
    display_name = core.get('name') or legacy.get('name', '')

    return TwitterUser(
        id=result.get('rest_id', ''),
        username=username,
        display_name=display_name,
        description=legacy.get('description'),
        followers_count=legacy.get('followers_count'),
        following_count=legacy.get('friends_count'),
        tweet_count=legacy.get('statuses_count'),
        profile_image_url=legacy.get('profile_image_url_https'),
        verified=legacy.get('verified', False) or result.get('is_blue_verified', False),
    )


def parse_tweet_media(entities: dict) -> List[TweetMedia]:
    """Parse media from tweet entities."""
    media_list = []
    for media in entities.get('media', []):
        media_list.append(TweetMedia(
            id=media.get('id_str', ''),
            type=media.get('type', 'photo'),
            url=media.get('url', ''),
            alt_text=media.get('alt_text'),
            preview_image_url=media.get('preview_image_url'),
            variants=media.get('video_info', {}).get('variants', []),
        ))
    return media_list


def parse_tweet(tweet_data: dict, author: Optional[TwitterUser] = None) -> TwitterTweet:
    """Parse a tweet from Twitter API response."""
    if not tweet_data:
        raise ValueError("Empty tweet data")

    rest_id = tweet_data.get('rest_id') or tweet_data.get('id_str', '')
    legacy = tweet_data.get('legacy', {})

    # Parse author if not provided
    if author is None:
        core = tweet_data.get('core', {})
        user_results = core.get('user_results', {})
        try:
            author = parse_user(user_results)
        except (ValueError, KeyError) as e:
            logger.warning(f"Failed to parse user: {e}")
            author = TwitterUser(
                id='',
                username='',
                display_name='Unknown',
            )

    # Parse media
    entities = legacy.get('entities', {})
    media = parse_tweet_media(entities)

    # Parse source (strip HTML from <a href="...">Twitter Web App</a>)
    source_raw = legacy.get('source', '')
    source_match = re.search(r'>(.+?)</a>', source_raw)
    source = source_match.group(1) if source_match else source_raw

    # Check if retweet
    is_retweet = 'retweeted_status_result' in legacy

    # Check if reply
    in_reply_to = legacy.get('in_reply_to_status_id_str')
    is_reply = in_reply_to is not None

    # Check if quoted
    is_quoted = legacy.get('is_quote', False)

    # Build link
    link = f"https://x.com/{author.username}/status/{rest_id}" if author.username else f"https://x.com/i/status/{rest_id}"

    # Handle retweet: extract original tweet info
    quoted_tweet_id = None
    if is_quoted:
        quoted_tweet_id = legacy.get('quoted_status_id_str')

    return TwitterTweet(
        id=rest_id,
        text=legacy.get('full_text', ''),
        author=author,
        created_at=parse_twitter_datetime(legacy['created_at']),
        metrics=parse_tweet_metrics(legacy),
        media=media,
        is_retweet=is_retweet,
        is_reply=is_reply,
        is_quoted=is_quoted,
        reply_to_id=in_reply_to,
        reply_to_username=legacy.get('in_reply_to_screen_name'),
        quoted_tweet_id=quoted_tweet_id,
        conversation_id=legacy.get('conversation_id_str'),
        lang=legacy.get('lang'),
        source=source,
        link=link,
    )


def parse_timeline_response(response: dict, timeline_type: str) -> TimelineResult:
    """Parse GraphQL timeline response into TimelineResult."""
    tweets = []
    next_cursor = None

    try:
        # Navigate to instructions
        instructions = []
        data = response.get('data', {})

        # Handle different timeline types
        if timeline_type.startswith('UserTweets_'):
            # Try timeline_v2 first, fall back to timeline
            user_data = data.get('user', {}).get('result', {})
            timeline_data = user_data.get('timeline_v2', {}).get('timeline', {})
            if not timeline_data:
                timeline_data = user_data.get('timeline', {}).get('timeline', {})
            instructions = timeline_data.get('instructions', [])
        elif timeline_type.startswith('Likes_'):
            timeline_data = data.get('user', {}).get('result', {}).get('likes', {})
            instructions = timeline_data.get('instructions', [])
        elif timeline_type == 'SearchTimeline':
            timeline_data = data.get('search_by_raw_query', {}).get('search_timeline', {}).get('timeline', {})
            instructions = timeline_data.get('instructions', [])
        else:
            # Home timelines - try different response structures
            home = data.get('home', {})
            timeline_data = (
                home.get('home_timeline_urt', {}) or
                home.get('home_timeline_v2', {}) or
                home.get('home_timeline', {})
            )
            instructions = timeline_data.get('instructions', [])

        for instruction in instructions:
            inst_type = instruction.get('type')

            if inst_type == 'TimelineAddEntries':
                entries = instruction.get('entries', [])
                for entry in entries:
                    entry_id = entry.get('entryId', '')

                    # Skip cursor entries
                    if 'cursor' in entry_id.lower():
                        continue

                    content = entry.get('content', {})
                    entry_type = content.get('entryType')
                    typename = content.get('__typename')

                    if entry_type == 'TimelineTweet' or typename == 'TimelineTimelineItem':
                        item_content = content.get('itemContent', {}) or content
                        tweet_display_type = item_content.get('tweetDisplayType')
                        tweet_data = item_content.get('tweet', {})

                        if not tweet_data:
                            # New structure: tweet_results.result
                            tweet_results = item_content.get('tweet_results', {})
                            if isinstance(tweet_results, dict):
                                tweet_data = tweet_results.get('result', {})

                        if not tweet_data and typename == 'TimelineTimelineItem':
                            # Alternative structure
                            tweet_results = content.get('tweetResults', {}).get('result', {})
                            if tweet_results:
                                tweet_data = tweet_results

                        if tweet_data and (tweet_display_type == 'Tweet' or tweet_display_type == 'SelfThread' or typename == 'TimelineTimelineItem'):
                            try:
                                tweet = parse_tweet(tweet_data)
                                tweets.append(tweet)
                            except Exception as e:
                                logger.warning(f"Failed to parse tweet: {e}")
                                continue

                    elif entry_type == 'TimelineCursor' or typename == 'TimelineCursor':
                        next_cursor = content.get('value')

            elif inst_type == 'TimelineReplaceEntry':
                entry = instruction.get('entry', {})
                entry_id = entry.get('entryId', '')
                if 'cursor-bottom' in entry_id or 'cursor' in entry_id.lower():
                    cursor_content = entry.get('content', {})
                    next_cursor = cursor_content.get('value')

        has_more = next_cursor is not None and next_cursor != ''

    except Exception as e:
        logger.error(f"Failed to parse timeline response: {e}")
        has_more = False

    return TimelineResult(
        tweets=tweets,
        next_cursor=next_cursor if next_cursor else None,
        has_more=has_more,
    )


def parse_tweet_detail_response(response: dict) -> TwitterTweet:
    """Parse GraphQL tweet detail response into TwitterTweet."""
    try:
        data = response.get('data', {})
        tweet_result = data.get('tweetResult', {}).get('result', {})

        if not tweet_result:
            raise TwitterAPIError("Tweet not found")

        return parse_tweet(tweet_result)
    except Exception as e:
        logger.error(f"Failed to parse tweet detail: {e}")
        raise


class TwitterAPIError(Exception):
    """Raised when Twitter API parsing fails."""
    pass
