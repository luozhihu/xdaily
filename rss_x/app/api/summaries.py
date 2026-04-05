"""Summary API endpoints."""
from datetime import date, datetime, timedelta

from flask import Blueprint, request, jsonify
from app import db
from app.models import Category, Summary
from app.api.auth import admin_required, login_required
from app.services.summarizer import summarize_category, summarize_all_categories

bp = Blueprint('summaries', __name__, url_prefix='/api/summaries')


def make_response(code=0, message='success', data=None):
    """Standard API response."""
    resp = {'code': code, 'message': message}
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


@bp.route('/generate', methods=['POST'])
@admin_required
def generate_all_summaries():
    """Generate summaries for all categories (admin only)."""
    # Get target date from request, default to today
    data = request.get_json() or {}
    target_date_str = data.get('date')

    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            return make_response(6004, 'invalid date format, use YYYY-MM-DD')
    else:
        target_date = date.today() - timedelta(days=1)

    results = summarize_all_categories(target_date)

    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = len(results) - success_count

    return make_response(data={
        'total': len(results),
        'success': success_count,
        'failed': failed_count,
        'results': results
    })


@bp.route('/generate/<int:category_id>', methods=['POST'])
@admin_required
def generate_category_summary(category_id):
    """Generate summary for a specific category (admin only)."""
    # Get target date from request, default to today
    data = request.get_json() or {}
    target_date_str = data.get('date')

    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            return make_response(6004, 'invalid date format, use YYYY-MM-DD')
    else:
        target_date = date.today() - timedelta(days=1)

    # Check if category exists
    category = Category.query.get(category_id)
    if not category:
        return make_response(2002, 'category not found')

    result = summarize_category(category_id, target_date)

    return make_response(data=result)


@bp.route('', methods=['GET'])
@admin_required
def get_summaries():
    """Get all summaries (admin only)."""
    # Filter by date if provided
    date_str = request.args.get('date')
    category_id = request.args.get('category_id', type=int)

    query = Summary.query

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter_by(summary_date=filter_date)
        except ValueError:
            pass

    if category_id:
        query = query.filter_by(category_id=category_id)

    summaries = query.order_by(Summary.summary_date.desc(), Summary.category_id).all()

    return make_response(data=[s.to_dict(include_category=True) for s in summaries])


@bp.route('/category/<int:category_id>', methods=['GET'])
@admin_required
def get_category_summary(category_id):
    """Get summary for a specific category and date (admin only)."""
    # Check if category exists
    category = Category.query.get(category_id)
    if not category:
        return make_response(2002, 'category not found')

    # Get target date from request, default to today
    date_str = request.args.get('date')
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return make_response(6004, 'invalid date format, use YYYY-MM-DD')
    else:
        target_date = date.today() - timedelta(days=1)

    # Get summary for this category and date
    summary = Summary.query.filter_by(
        category_id=category_id,
        summary_date=target_date
    ).first()

    if not summary:
        return make_response(6005, 'no summary found for this category and date')

    return make_response(data=summary.to_dict(include_category=True))
