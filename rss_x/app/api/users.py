"""User API endpoints (admin only)."""
from flask import Blueprint, request, jsonify
from app import db
from app.models import User
from app.api.auth import admin_required, login_required

bp = Blueprint('users', __name__, url_prefix='/api/users')


def make_response(code=0, message='success', data=None):
    """Standard API response."""
    resp = {'code': code, 'message': message}
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


@bp.route('', methods=['GET'])
@admin_required
def get_users():
    """Get all users (admin only)."""
    users = User.query.order_by(User.id).all()
    return make_response(data=[u.to_dict() for u in users])


@bp.route('/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update a user (admin only)."""
    user = User.query.get(user_id)
    if not user:
        return make_response(5001, 'user not found')

    data = request.get_json()
    if not data:
        return make_response(4001, 'no data')

    if 'role' in data:
        role = data['role']
        if role not in ('admin', 'user'):
            return make_response(5002, 'invalid role')
        user.role = role

    db.session.commit()
    return make_response(data=user.to_dict())


@bp.route('/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)."""
    user = User.query.get(user_id)
    if not user:
        return make_response(5001, 'user not found')

    # Prevent self-deletion
    if hasattr(request, 'current_user') and request.current_user['id'] == user_id:
        return make_response(5003, 'cannot delete yourself')

    db.session.delete(user)
    db.session.commit()

    return make_response()
