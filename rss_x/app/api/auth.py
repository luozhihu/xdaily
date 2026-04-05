"""Authentication API endpoints."""
from functools import wraps
from datetime import datetime, timedelta

import jwt
import bcrypt
from flask import Blueprint, request, jsonify, current_app

from app import db
from app.models import User

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def make_response(code=0, message='success', data=None):
    """Standard API response."""
    resp = {'code': code, 'message': message}
    if data is not None:
        resp['data'] = data
    return jsonify(resp)


def get_jwt_secret():
    """Get JWT secret from config."""
    try:
        import yaml
        from pathlib import Path
        config_file = Path('config.yaml')
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
                return config.get('settings', {}).get('jwt_secret', 'default-secret-key')
    except Exception:
        pass
    return 'default-secret-key'


def get_jwt_expiry_hours():
    """Get JWT expiry hours from config."""
    try:
        import yaml
        from pathlib import Path
        config_file = Path('config.yaml')
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
                return config.get('settings', {}).get('jwt_expiry_hours', 24)
    except Exception:
        pass
    return 24


def generate_token(user: User) -> str:
    """Generate JWT token for user."""
    payload = {
        'sub': str(user.id),  # JWT requires string subject
        'username': user.username,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(hours=get_jwt_expiry_hours())
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm='HS256')


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return make_response(401, 'Unauthorized'), 401

        token = auth_header.replace('Bearer ', '')

        try:
            payload = jwt.decode(token, get_jwt_secret(), algorithms=['HS256'])
            if payload.get('role') != 'admin':
                return make_response(4001, 'Admin permission required'), 403
        except jwt.ExpiredSignatureError:
            return make_response(3003, 'Token expired'), 401
        except jwt.InvalidTokenError:
            return make_response(3004, 'Invalid token'), 401

        return f(*args, **kwargs)
    return decorated


def login_required(f):
    """Decorator to require login (any valid token)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return make_response(401, 'Unauthorized'), 401

        token = auth_header.replace('Bearer ', '')

        try:
            payload = jwt.decode(token, get_jwt_secret(), algorithms=['HS256'])
            # Store user info in request context
            request.current_user = {
                'id': int(payload.get('sub')) if payload.get('sub') else None,
                'username': payload.get('username'),
                'role': payload.get('role')
            }
        except jwt.ExpiredSignatureError:
            return make_response(3003, 'Token expired'), 401
        except jwt.InvalidTokenError:
            return make_response(3004, 'Invalid token'), 401

        return f(*args, **kwargs)
    return decorated


@bp.route('/register', methods=['POST'])
def register():
    """Register a new user. First user becomes admin."""
    data = request.get_json()

    if not data:
        return make_response(4001, 'no data')

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or len(username) < 3 or len(username) > 50:
        return make_response(3005, 'username must be 3-50 characters')

    if not password or len(password) < 6:
        return make_response(3006, 'password must be at least 6 characters')

    # Check if username exists
    existing = User.query.filter_by(username=username).first()
    if existing:
        return make_response(3001, 'username already exists')

    # First user becomes admin
    is_first = User.query.count() == 0
    role = 'admin' if is_first else 'user'

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()

    token = generate_token(user)

    return make_response(data={
        'token': token,
        'user': user.to_dict()
    }), 201


@bp.route('/login', methods=['POST'])
def login():
    """Login with username and password."""
    data = request.get_json()

    if not data:
        return make_response(4001, 'no data')

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return make_response(3002, 'username or password error')

    user = User.query.filter_by(username=username).first()
    if not user or not verify_password(password, user.password_hash):
        return make_response(3002, 'username or password error')

    token = generate_token(user)

    return make_response(data={
        'token': token,
        'user': user.to_dict()
    })
