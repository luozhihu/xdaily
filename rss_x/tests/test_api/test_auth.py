"""Tests for auth API."""
import pytest


class TestAuthAPI:
    """Tests for auth endpoints."""

    def test_register_first_user_becomes_admin(self, client):
        """First registered user should become admin."""
        resp = client.post('/api/auth/register', json={
            'username': 'admin',
            'password': 'admin123'
        })
        assert resp.status_code == 201
        assert resp.json['code'] == 0
        assert resp.json['data']['user']['role'] == 'admin'
        assert 'token' in resp.json['data']

    def test_register_second_user_becomes_user(self, client):
        """Second registered user should become user."""
        # First user
        client.post('/api/auth/register', json={
            'username': 'admin',
            'password': 'admin123'
        })

        # Second user
        resp = client.post('/api/auth/register', json={
            'username': 'user',
            'password': 'user123'
        })
        assert resp.json['data']['user']['role'] == 'user'

    def test_register_duplicate_username(self, client):
        """Register with duplicate username should fail."""
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'test123'
        })

        resp = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'test456'
        })
        assert resp.json['code'] == 3001

    def test_register_short_password(self, client):
        """Register with short password should fail."""
        resp = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': '123'
        })
        assert resp.json['code'] == 3006

    def test_login_success(self, client):
        """Login with correct credentials should succeed."""
        # Register first
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'test123'
        })

        # Login
        resp = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'test123'
        })
        assert resp.json['code'] == 0
        assert 'token' in resp.json['data']

    def test_login_wrong_password(self, client):
        """Login with wrong password should fail."""
        # Register first
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'test123'
        })

        # Login with wrong password
        resp = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        assert resp.json['code'] == 3002

    def test_login_nonexistent_user(self, client):
        """Login with nonexistent user should fail."""
        resp = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'test123'
        })
        assert resp.json['code'] == 3002
