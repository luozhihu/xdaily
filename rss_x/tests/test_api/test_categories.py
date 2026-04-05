"""Tests for categories API."""
from tests.conftest import get_admin_token, get_user_token


class TestCategoriesAPI:
    """Tests for categories endpoints."""

    def test_get_categories_requires_auth(self, client):
        """Getting categories without auth should fail."""
        resp = client.get('/api/categories')
        assert resp.status_code == 401

    def test_get_categories_empty(self, client):
        """Test getting categories when none exist."""
        token = get_admin_token(client)
        resp = client.get('/api/categories', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        assert resp.json['code'] == 0
        assert resp.json['data'] == []

    def test_create_category(self, client):
        """Test creating a category."""
        token = get_admin_token(client)
        resp = client.post('/api/categories', json={
            'name': '科技',
            'sort_order': 1
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 201
        assert resp.json['code'] == 0
        assert resp.json['data']['name'] == '科技'
        assert resp.json['data']['sort_order'] == 1
        assert 'id' in resp.json['data']

    def test_create_category_duplicate(self, client):
        """Test creating duplicate category returns error."""
        token = get_admin_token(client)
        # Create first
        client.post('/api/categories', json={'name': '科技'}, headers={'Authorization': f'Bearer {token}'})

        # Try to create duplicate
        resp = client.post('/api/categories', json={'name': '科技'}, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        assert resp.json['code'] == 2001
        assert 'already exists' in resp.json['message']

    def test_create_category_missing_name(self, client):
        """Test creating category without name."""
        token = get_admin_token(client)
        resp = client.post('/api/categories', json={}, headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 4001

    def test_update_category(self, client):
        """Test updating a category."""
        token = get_admin_token(client)
        # Create
        create_resp = client.post('/api/categories', json={'name': '科技'}, headers={'Authorization': f'Bearer {token}'})
        category_id = create_resp.json['data']['id']

        # Update
        resp = client.put(f'/api/categories/{category_id}', json={
            'name': '科技更新',
            'sort_order': 2
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 0
        assert resp.json['data']['name'] == '科技更新'
        assert resp.json['data']['sort_order'] == 2

    def test_update_category_not_found(self, client):
        """Test updating non-existent category."""
        token = get_admin_token(client)
        resp = client.put('/api/categories/9999', json={'name': 'test'}, headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 2002

    def test_delete_category(self, client):
        """Test deleting a category."""
        token = get_admin_token(client)
        # Create
        create_resp = client.post('/api/categories', json={'name': '科技'}, headers={'Authorization': f'Bearer {token}'})
        category_id = create_resp.json['data']['id']

        # Delete
        resp = client.delete(f'/api/categories/{category_id}', headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 0

        # Verify deleted
        get_resp = client.get('/api/categories', headers={'Authorization': f'Bearer {token}'})
        assert len(get_resp.json['data']) == 0

    def test_delete_category_with_feeds_fails(self, client):
        """Test deleting category that has feeds fails."""
        token = get_admin_token(client)
        # Create category
        cat_resp = client.post('/api/categories', json={'name': '科技'}, headers={'Authorization': f'Bearer {token}'})
        category_id = cat_resp.json['data']['id']

        # Create feed in this category
        client.post('/api/feeds', json={
            'name': 'Test User',
            'twitter_username': 'testuser',
            'category_id': category_id
        }, headers={'Authorization': f'Bearer {token}'})

        # Try to delete category
        resp = client.delete(f'/api/categories/{category_id}', headers={'Authorization': f'Bearer {token}'})
        assert resp.json['code'] == 2003
        assert 'has feeds' in resp.json['message']

    def test_user_cannot_create_category(self, client):
        """Test that regular user cannot create category."""
        token = get_user_token(client)
        resp = client.post('/api/categories', json={'name': '科技'}, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 403
        assert resp.json['code'] == 4001
