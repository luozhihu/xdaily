"""Feed API endpoints."""
import json
from flask import Blueprint, request, jsonify
from app import db
from app.models import Feed, Category, Tweet
from app.services.twitter_fetcher import fetch_twitter_feed
from app.api.auth import admin_required, login_required

bp = Blueprint('feeds', __name__, url_prefix='/api/feeds')


def make_response(code=0, message='success', data=None):
    """Standard API response."""
    resp = {'code': code, 'message': message}
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


@bp.route('', methods=['GET'])
@login_required
def get_feeds():
    """Get all feeds."""
    feeds = Feed.query.order_by(Feed.id.desc()).all()
    result = []
    for feed in feeds:
        feed_dict = feed.to_dict(include_category=True)
        result.append(feed_dict)
    return make_response(data=result)


@bp.route('/<int:feed_id>', methods=['GET'])
@login_required
def get_feed(feed_id):
    """Get a single feed."""
    feed = Feed.query.get(feed_id)
    if not feed:
        return make_response(1003, 'feed not found')

    return make_response(data=feed.to_dict(include_category=True))


@bp.route('', methods=['POST'])
@admin_required
def create_feed():
    """Create a new feed or update existing one."""
    data = request.get_json()

    if not data:
        return make_response(4001, 'no data')

    # Validate required fields
    if 'twitter_username' not in data:
        return make_response(4001, 'twitter_username is required')

    username = data['twitter_username'].strip().lstrip('@')
    if not username or len(username) > 50:
        return make_response(1002, 'invalid twitter_username')

    name = data.get('name', username).strip()
    if not name or len(name) > 100:
        return make_response(4002, 'invalid name')

    # Check if username already exists - update instead of creating new
    existing = Feed.query.filter_by(twitter_username=username).first()
    if existing:
        # Update existing feed
        existing.name = name
        existing.description = data.get('description', existing.description)
        existing.avatar_url = data.get('avatar_url', existing.avatar_url)
        existing.followers_count = data.get('followers_count', existing.followers_count)

        if 'category_id' in data:
            category_id = data['category_id']
            if category_id:
                category = Category.query.get(category_id)
                if not category:
                    return make_response(2002, 'category not found')
            existing.category_id = category_id

        db.session.commit()
        return make_response(data=existing.to_dict(include_category=True))

    # Validate category if provided
    category_id = data.get('category_id')
    if category_id:
        category = Category.query.get(category_id)
        if not category:
            return make_response(2002, 'category not found')

    # Parse tags
    tags = None
    if 'tags' in data and isinstance(data['tags'], list):
        tags = json.dumps(data['tags'])

    feed = Feed(
        name=name,
        twitter_username=username,
        category_id=category_id,
        enabled=data.get('enabled', True),
        tags=tags,
        description=data.get('description'),
        avatar_url=data.get('avatar_url'),
        followers_count=data.get('followers_count', 0)
    )
    db.session.add(feed)
    db.session.commit()

    return make_response(data=feed.to_dict(include_category=True)), 201


@bp.route('/<int:feed_id>', methods=['PUT'])
@admin_required
def update_feed(feed_id):
    """Update a feed."""
    feed = Feed.query.get(feed_id)
    if not feed:
        return make_response(1003, 'feed not found')

    data = request.get_json()
    if not data:
        return make_response(4001, 'no data')

    if 'name' in data:
        name = data['name'].strip()
        if not name or len(name) > 100:
            return make_response(4002, 'invalid name')
        feed.name = name

    if 'twitter_username' in data:
        username = data['twitter_username'].strip().lstrip('@')
        if not username or len(username) > 50:
            return make_response(1002, 'invalid twitter_username')
        # Check if username already taken by another feed
        existing = Feed.query.filter_by(twitter_username=username).first()
        if existing and existing.id != feed_id:
            return make_response(1001, 'username already exists')
        feed.twitter_username = username

    if 'category_id' in data:
        if data['category_id'] is None:
            feed.category_id = None
        else:
            category = Category.query.get(data['category_id'])
            if not category:
                return make_response(2002, 'category not found')
            feed.category_id = data['category_id']

    if 'enabled' in data:
        feed.enabled = bool(data['enabled'])

    if 'tags' in data:
        if isinstance(data['tags'], list):
            feed.tags = json.dumps(data['tags'])
        else:
            feed.tags = data['tags']

    db.session.commit()
    return make_response(data=feed.to_dict(include_category=True))


@bp.route('/<int:feed_id>', methods=['DELETE'])
@admin_required
def delete_feed(feed_id):
    """Delete a feed."""
    feed = Feed.query.get(feed_id)
    if not feed:
        return make_response(1003, 'feed not found')

    # Delete related fetch logs first
    from app.models import FetchLog
    FetchLog.query.filter_by(feed_id=feed_id).delete()

    db.session.delete(feed)
    db.session.commit()

    return make_response()


@bp.route('/<int:feed_id>/fetch', methods=['POST'])
@admin_required
def trigger_fetch(feed_id):
    """Manually trigger fetch for a feed."""
    feed = Feed.query.get(feed_id)
    if not feed:
        return make_response(1003, 'feed not found')

    # Get max_entries from config
    max_entries = 30
    try:
        import yaml
        from pathlib import Path
        config_file = Path('config.yaml')
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
                max_entries = config.get('settings', {}).get('max_entries', 30)
    except Exception:
        pass

    result = fetch_twitter_feed(feed, max_entries)

    return make_response(data={
        'status': result.status,
        'items_new': result.items_new,
        'items_dup': result.items_dup,
        'rss_source': result.rss_source,
        'error_message': result.error_message
    })
