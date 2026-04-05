"""Category API endpoints."""
from flask import Blueprint, request, jsonify
from app import db
from app.models import Category, Feed
from app.api.auth import admin_required, login_required

bp = Blueprint('categories', __name__, url_prefix='/api/categories')


def make_response(code=0, message='success', data=None):
    """Standard API response."""
    resp = {'code': code, 'message': message}
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


@bp.route('', methods=['GET'])
@login_required
def get_categories():
    """Get all categories."""
    categories = Category.query.order_by(Category.sort_order, Category.id).all()
    return make_response(data=[c.to_dict() for c in categories])


@bp.route('', methods=['POST'])
@admin_required
def create_category():
    """Create a new category."""
    data = request.get_json()

    if not data or 'name' not in data:
        return make_response(4001, 'name is required')

    name = data['name'].strip()
    if not name or len(name) > 100:
        return make_response(4002, 'invalid name')

    # Check if exists
    existing = Category.query.filter_by(name=name).first()
    if existing:
        return make_response(2001, 'category name already exists')

    category = Category(
        name=name,
        description=data.get('description', ''),
        sort_order=data.get('sort_order', 0)
    )
    db.session.add(category)
    db.session.commit()

    return make_response(data=category.to_dict()), 201


@bp.route('/<int:category_id>', methods=['PUT'])
@admin_required
def update_category(category_id):
    """Update a category."""
    category = Category.query.get(category_id)
    if not category:
        return make_response(2002, 'category not found')

    data = request.get_json()
    if not data:
        return make_response(4001, 'no data')

    if 'name' in data:
        name = data['name'].strip()
        if not name or len(name) > 100:
            return make_response(4002, 'invalid name')
        # Check if name already taken by another category
        existing = Category.query.filter_by(name=name).first()
        if existing and existing.id != category_id:
            return make_response(2001, 'category name already exists')
        category.name = name

    if 'sort_order' in data:
        category.sort_order = data['sort_order']

    if 'description' in data:
        category.description = data['description']

    db.session.commit()
    return make_response(data=category.to_dict())


@bp.route('/<int:category_id>', methods=['DELETE'])
@admin_required
def delete_category(category_id):
    """Delete a category and all its feeds and summaries."""
    category = Category.query.get(category_id)
    if not category:
        return make_response(2002, 'category not found')

    # Delete related summaries first
    from app.models import Summary
    Summary.query.filter_by(category_id=category_id).delete()

    # Delete each feed individually to trigger cascade deletes
    feeds = Feed.query.filter_by(category_id=category_id).all()
    for feed in feeds:
        db.session.delete(feed)

    # Delete the category
    db.session.delete(category)
    db.session.commit()

    return make_response()
