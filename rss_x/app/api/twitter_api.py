"""Twitter API endpoints for direct Twitter access."""
from flask import Blueprint, request, jsonify

from app.api.auth import login_required

bp = Blueprint('twitter_api', __name__, url_prefix='/api/twitter')


def make_response(code=0, message='success', data=None):
    resp = {'code': code, 'message': message}
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


def tweet_to_dict(tweet) -> dict:
    """Convert TwitterTweet to dictionary for JSON response."""
    return {
        'id': tweet.id,
        'text': tweet.text,
        'author': {
            'id': tweet.author.id,
            'username': tweet.author.username,
            'display_name': tweet.author.display_name,
            'verified': tweet.author.verified,
            'profile_image_url': tweet.author.profile_image_url,
        },
        'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
        'metrics': {
            'retweet': tweet.metrics.retweet_count,
            'reply': tweet.metrics.reply_count,
            'like': tweet.metrics.like_count,
            'quote': tweet.metrics.quote_count,
            'bookmark': tweet.metrics.bookmark_count,
            'view': tweet.metrics.view_count,
        },
        'is_retweet': tweet.is_retweet,
        'is_reply': tweet.is_reply,
        'is_quoted': tweet.is_quoted,
        'reply_to_id': tweet.reply_to_id,
        'reply_to_username': tweet.reply_to_username,
        'quoted_tweet_id': tweet.quoted_tweet_id,
        'lang': tweet.lang,
        'source': tweet.source,
        'link': tweet.link,
        'media': [
            {
                'id': m.id,
                'type': m.type,
                'url': m.url,
                'alt_text': m.alt_text,
            }
            for m in tweet.media
        ],
    }


@bp.route('/timeline', methods=['GET'])
@login_required
def get_timeline():
    """Fetch home timeline tweets."""
    timeline_type = request.args.get('type', 'ForYou')  # ForYou or Following
    count = request.args.get('count', 20, type=int)
    cursor = request.args.get('cursor')

    if timeline_type not in ('ForYou', 'Following'):
        return make_response(4001, 'type must be ForYou or Following')

    try:
        from app.services.twitter_client import TwitterClient, TwitterAuth
        auth = TwitterAuth()
        client = TwitterClient(auth=auth)
        result = client.fetch_home_timeline(
            timeline_type=timeline_type,
            count=min(count, 100),
            cursor=cursor,
        )

        return make_response(data={
            'tweets': [tweet_to_dict(t) for t in result.tweets],
            'next_cursor': result.next_cursor,
            'has_more': result.has_more,
        })
    except Exception as e:
        return make_response(6001, str(e))


@bp.route('/user/<username>', methods=['GET'])
@login_required
def get_user_tweets(username):
    """Fetch tweets for a specific user."""
    count = request.args.get('count', 20, type=int)
    cursor = request.args.get('cursor')
    include_replies = request.args.get('include_replies', 'true').lower() == 'true'
    include_retweets = request.args.get('include_retweets', 'true').lower() == 'true'

    try:
        from app.services.twitter_client import TwitterClient, TwitterAuth
        auth = TwitterAuth()
        client = TwitterClient(auth=auth)
        result = client.fetch_user_tweets(
            username=username,
            count=min(count, 100),
            cursor=cursor,
            include_replies=include_replies,
            include_retweets=include_retweets,
        )

        return make_response(data={
            'tweets': [tweet_to_dict(t) for t in result.tweets],
            'next_cursor': result.next_cursor,
            'has_more': result.has_more,
        })
    except Exception as e:
        return make_response(6001, str(e))


@bp.route('/tweets/<tweet_id>', methods=['GET'])
@login_required
def get_tweet(tweet_id):
    """Fetch a single tweet by ID."""
    try:
        from app.services.twitter_client import TwitterClient, TwitterAuth
        auth = TwitterAuth()
        client = TwitterClient(auth=auth)
        tweet = client.fetch_tweet_detail(tweet_id)

        return make_response(data=tweet_to_dict(tweet))
    except Exception as e:
        return make_response(6001, str(e))


@bp.route('/search', methods=['GET'])
@login_required
def search_tweets():
    """Search tweets by query."""
    query = request.args.get('q', '')
    if not query:
        return make_response(4001, 'query parameter "q" is required')

    count = request.args.get('count', 20, type=int)
    cursor = request.args.get('cursor')

    try:
        from app.services.twitter_client import TwitterClient, TwitterAuth
        auth = TwitterAuth()
        client = TwitterClient(auth=auth)
        result = client.fetch_search(
            query=query,
            count=min(count, 100),
            cursor=cursor,
        )

        return make_response(data={
            'tweets': [tweet_to_dict(t) for t in result.tweets],
            'next_cursor': result.next_cursor,
            'has_more': result.has_more,
        })
    except Exception as e:
        return make_response(6001, str(e))


@bp.route('/likes/<username>', methods=['GET'])
@login_required
def get_likes(username):
    """Fetch likes for a user."""
    count = request.args.get('count', 20, type=int)
    cursor = request.args.get('cursor')

    try:
        from app.services.twitter_client import TwitterClient, TwitterAuth
        auth = TwitterAuth()
        client = TwitterClient(auth=auth)
        result = client.fetch_likes(
            username=username,
            count=min(count, 100),
            cursor=cursor,
        )

        return make_response(data={
            'tweets': [tweet_to_dict(t) for t in result.tweets],
            'next_cursor': result.next_cursor,
            'has_more': result.has_more,
        })
    except Exception as e:
        return make_response(6001, str(e))


def user_to_dict(user) -> dict:
    """Convert TwitterUser to dictionary for JSON response."""
    return {
        'id': user.id,
        'username': user.username,
        'display_name': user.display_name,
        'description': user.description,
        'followers_count': user.followers_count,
        'following_count': user.following_count,
        'tweet_count': user.tweet_count,
        'profile_image_url': user.profile_image_url,
        'verified': user.verified,
    }


@bp.route('/user-info/<username>', methods=['GET'])
@login_required
def get_user_info(username):
    """Fetch user profile info by username."""
    try:
        from app.services.twitter_client import TwitterClient, TwitterAuth
        auth = TwitterAuth()
        client = TwitterClient(auth=auth)
        user = client.fetch_user_info(username)

        return make_response(data=user_to_dict(user))
    except Exception as e:
        return make_response(6001, str(e))
