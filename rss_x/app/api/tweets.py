"""Tweet API endpoints."""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Feed, Tweet
from app.api.auth import login_required

bp = Blueprint('tweets', __name__, url_prefix='/api')


def make_response(code=0, message='success', data=None):
    """Standard API response."""
    resp = {'code': code, 'message': message}
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


@bp.route('/feeds/<int:feed_id>/tweets', methods=['GET'])
@login_required
def get_feed_tweets(feed_id):
    """Get tweets for a specific feed."""
    feed = Feed.query.get(feed_id)
    if not feed:
        return make_response(1003, 'feed not found')

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 100)  # Max 100 per page

    # Query tweets
    query = Tweet.query.filter_by(twitter_username=feed.twitter_username)
    query = query.order_by(Tweet.published.desc())

    # Date filter
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date:
        query = query.filter(Tweet.published_date >= start_date)
    if end_date:
        query = query.filter(Tweet.published_date <= end_date)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return make_response(data={
        'tweets': [t.to_dict() for t in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@bp.route('/tweets', methods=['GET'])
@login_required
def search_tweets():
    """Search tweets across all feeds."""
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 100)

    query = Tweet.query

    # Filter by feed
    feed_id = request.args.get('feed_id', type=int)
    if feed_id:
        feed = Feed.query.get(feed_id)
        if feed:
            query = query.filter_by(twitter_username=feed.twitter_username)

    # Filter by category
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.join(Feed).filter(Feed.category_id == category_id)

    # Date filter
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date:
        query = query.filter(Tweet.published_date >= start_date)
    if end_date:
        query = query.filter(Tweet.published_date <= end_date)

    # Search in content
    keyword = request.args.get('keyword')
    if keyword:
        query = query.filter(Tweet.content.like(f'%{keyword}%'))

    # Order
    order = request.args.get('order', 'desc')
    if order == 'asc':
        query = query.order_by(Tweet.published.asc())
    else:
        query = query.order_by(Tweet.published.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return make_response(data={
        'tweets': [t.to_dict() for t in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })
