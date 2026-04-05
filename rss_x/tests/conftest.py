"""Pytest configuration and fixtures."""
import pytest
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope='function')
def app():
    """Create application for testing."""
    from flask import Flask
    from app import db

    # Create a minimal Flask app for testing
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(test_app)

    # Register blueprints
    from app.api import feeds, categories, tweets, auth, users, summaries
    test_app.register_blueprint(feeds.bp)
    test_app.register_blueprint(categories.bp)
    test_app.register_blueprint(tweets.bp)
    test_app.register_blueprint(auth.bp)
    test_app.register_blueprint(users.bp)
    test_app.register_blueprint(summaries.bp)

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def get_admin_token(client):
    """Helper to get admin token."""
    # Register admin user (first user becomes admin)
    client.post('/api/auth/register', json={
        'username': 'admin',
        'password': 'admin123'
    })
    # Login
    resp = client.post('/api/auth/login', json={
        'username': 'admin',
        'password': 'admin123'
    })
    return resp.json['data']['token']


def get_user_token(client):
    """Helper to get user token."""
    # Register admin first
    client.post('/api/auth/register', json={
        'username': 'admin',
        'password': 'admin123'
    })
    # Register regular user
    client.post('/api/auth/register', json={
        'username': 'user',
        'password': 'user123'
    })
    # Login as regular user
    resp = client.post('/api/auth/login', json={
        'username': 'user',
        'password': 'user123'
    })
    return resp.json['data']['token']
