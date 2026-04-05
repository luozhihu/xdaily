"""Tests for feeds API."""
from tests.conftest import get_admin_token, get_user_token


class TestFeedsAPI:
    """Tests for feeds endpoints."""

    def test_get_feeds_requires_auth(self, client):
        """Getting feeds without auth should fail."""
        resp = client.get('/api/feeds')
        assert resp.status_code == 401

    def test_get_feeds_empty(self, client):
        """Test getting feeds when none exist."""
        token = get_admin_token(client)
        resp = client.get('/api/feeds', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        assert resp.json['code'] == 0
        assert resp.json['data'] == []

    def test_create_feed(self, client):
        """Test creating a feed."""
        token = get_admin_token(client)
        resp = client.post('/api/feeds', json={
            'name': 'Elon Musk',
            'twitter_username': 'elonmusk'
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 201
        assert resp.json['code'] == 0
        assert resp.json['data']['name'] == 'Elon Musk'
        assert resp.json['data']['twitter_username'] == 'elonmusk'
        assert resp.json['data']['enabled'] is True

    def test_create_feed_with_category(self, client):
        """Test creating a feed with category."""
        token = get_admin_token(client)
        # Create category first
        cat_resp = client.post('/api/categories', json={'name': '科技'}, headers={'Authorization': f'Bearer {token}'})
        category_id = cat_resp.json['data']['id']

        # Create feed with category
        resp = client.post('/api/feeds', json={
            'name': 'Test User',
            'twitter_username': 'testuser',
            'category_id': category_id
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.json['data']['category_id'] == category_id
        assert resp.json['data']['category_name'] == '科技'

    def test_create_feed_with_tags(self, client):
        """Test creating a feed with tags."""
        token = get_admin_token(client)
        resp = client.post('/api/feeds', json={
            'name': 'Test User',
            'twitter_username': 'testuser',
            'tags': ['tech', 'business']
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.json['data']['tags'] is not None
        assert 'tech' in resp.json['data']['tags']

    def test_create_feed_duplicate_username(self, client):
        """Test creating feed with duplicate username."""
        token = get_admin_token(client)
        # Create first
        client.post('/api/feeds', json={
            'name': 'User 1',
            'twitter_username': 'testuser'
        }, headers={'Authorization': f'Bearer {token}'})

        # Try to create duplicate
        resp = client.post('/api/feeds', json={
            'name': 'User 2',
            'twitter_username': 'testuser'
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 1001

    def test_create_feed_missing_username(self, client):
        """Test creating feed without username."""
        token = get_admin_token(client)
        resp = client.post('/api/feeds', json={'name': 'Test'}, headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 4001

    def test_create_feed_invalid_username(self, client):
        """Test creating feed with invalid username."""
        token = get_admin_token(client)
        resp = client.post('/api/feeds', json={
            'name': 'Test',
            'twitter_username': 'a' * 100  # Too long
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 1002

    def test_get_feed(self, client):
        """Test getting a single feed."""
        token = get_admin_token(client)
        # Create
        create_resp = client.post('/api/feeds', json={
            'name': 'Test User',
            'twitter_username': 'testuser'
        }, headers={'Authorization': f'Bearer {token}'})
        feed_id = create_resp.json['data']['id']

        # Get
        resp = client.get(f'/api/feeds/{feed_id}', headers={'Authorization': f'Bearer {token}'})
        assert resp.json['data']['id'] == feed_id
        assert resp.json['data']['twitter_username'] == 'testuser'

    def test_get_feed_not_found(self, client):
        """Test getting non-existent feed."""
        token = get_admin_token(client)
        resp = client.get('/api/feeds/9999', headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 1003

    def test_update_feed(self, client):
        """Test updating a feed."""
        token = get_admin_token(client)
        # Create
        create_resp = client.post('/api/feeds', json={
            'name': 'Old Name',
            'twitter_username': 'olduser'
        }, headers={'Authorization': f'Bearer {token}'})
        feed_id = create_resp.json['data']['id']

        # Update
        resp = client.put(f'/api/feeds/{feed_id}', json={
            'name': 'New Name',
            'enabled': False
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.json['data']['name'] == 'New Name'
        assert resp.json['data']['enabled'] is False
        # Username should not change
        assert resp.json['data']['twitter_username'] == 'olduser'

    def test_update_feed_username(self, client):
        """Test updating feed username."""
        token = get_admin_token(client)
        # Create two feeds
        client.post('/api/feeds', json={'name': 'User 1', 'twitter_username': 'user1'}, headers={'Authorization': f'Bearer {token}'})
        resp2 = client.post('/api/feeds', json={'name': 'User 2', 'twitter_username': 'user2'}, headers={'Authorization': f'Bearer {token}'})
        feed_id = resp2.json['data']['id']

        # Try to update username to existing one
        resp = client.put(f'/api/feeds/{feed_id}', json={'twitter_username': 'user1'}, headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 1001

    def test_delete_feed(self, client):
        """Test deleting a feed."""
        token = get_admin_token(client)
        # Create
        create_resp = client.post('/api/feeds', json={
            'name': 'Test User',
            'twitter_username': 'testuser'
        }, headers={'Authorization': f'Bearer {token}'})
        feed_id = create_resp.json['data']['id']

        # Delete
        resp = client.delete(f'/api/feeds/{feed_id}', headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 0

        # Verify deleted
        get_resp = client.get(f'/api/feeds/{feed_id}', headers={'Authorization': f'Bearer {token}'})
        assert get_resp.json['code'] == 1003

    def test_delete_feed_not_found(self, client):
        """Test deleting non-existent feed."""
        token = get_admin_token(client)
        resp = client.delete('/api/feeds/9999', headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 1003

    def test_user_cannot_create_feed(self, client):
        """Test that regular user cannot create feed."""
        # First create admin so we have a user
        get_admin_token(client)
        token = get_user_token(client)
        resp = client.post('/api/feeds', json={
            'name': 'Test',
            'twitter_username': 'test'
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 403

    def test_user_can_read_feeds(self, client):
        """Test that regular user can read feeds."""
        # First create admin and a feed
        admin_token = get_admin_token(client)
        client.post('/api/feeds', json={
            'name': 'Test User',
            'twitter_username': 'testuser'
        }, headers={'Authorization': f'Bearer {admin_token}'})

        # User reads feeds
        user_token = get_user_token(client)
        resp = client.get('/api/feeds', headers={'Authorization': f'Bearer {user_token}'})
        assert resp.status_code == 200
        assert len(resp.json['data']) == 1
