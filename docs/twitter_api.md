# Twitter 用户搜索接口文档

## 接口概述

根据 Twitter 用户名（handle）查询用户信息，包括简介、头像、显示名字和用户名。

## 基础信息

- **接口路径**: `GET /api/twitter/user-info/<username>`
- **认证方式**: Bearer Token (JWT)
- **是否需要登录**: 是

## 请求

### Path Parameters

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | Twitter 用户名（不含 @ 符号） |

### Headers

```
Authorization: Bearer <token>
Content-Type: application/json
```

## 响应

### 成功响应 (200 OK)

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "44196397",
    "username": "elonmusk",
    "display_name": "Elon Musk",
    "description": "https://t.co/dDtDyVssfm",
    "followers_count": 237867912,
    "following_count": 1308,
    "tweet_count": 100647,
    "profile_image_url": "https://pbs.twimg.com/profile_images/...",
    "verified": true
  }
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | Twitter 用户 ID |
| username | string | 用户名（handle） |
| display_name | string | 显示名称 |
| description | string | 用户简介 |
| followers_count | integer | 粉丝数 |
| following_count | integer | 关注数 |
| tweet_count | integer | 推文数 |
| profile_image_url | string | 头像 URL |
| verified | boolean | 是否认证 |

### 错误响应

```json
{
  "code": 6001,
  "message": "Could not resolve user ID for @nonexistentuser"
}
```

## 使用示例

### cURL

```bash
# 登录获取 Token
TOKEN=$(curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

# 查询用户信息
curl -s "http://localhost:8080/api/twitter/user-info/elonmusk" \
  -H "Authorization: Bearer $TOKEN"
```

### Python

```python
import requests

# 登录
login_resp = requests.post(
    "http://localhost:8080/api/auth/login",
    json={"username": "admin", "password": "admin123"}
)
token = login_resp.json()["data"]["token"]

# 查询用户信息
user_resp = requests.get(
    "http://localhost:8080/api/twitter/user-info/elonmusk",
    headers={"Authorization": f"Bearer {token}"}
)
user_data = user_resp.json()["data"]
print(f"{user_data['display_name']} (@{user_data['username']})")
```

### JavaScript

```javascript
// 登录获取 Token
const loginResp = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'admin', password: 'admin123' })
});
const { token } = (await loginResp.json()).data;

// 查询用户信息
const userResp = await fetch('/api/twitter/user-info/elonmusk', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const user = (await userResp.json()).data;
console.log(`${user.display_name} (@${user.username})`);
```

## 前端集成

### 添加到 API 客户端

```typescript
// lib/api.ts
export const api = {
  // ... 其他接口
  twitter: {
    searchUser: (username: string) =>
      request<TwitterUser>(`/api/twitter/user-info/${username}`),
  },
};

interface TwitterUser {
  id: string;
  username: string;
  display_name: string;
  description: string;
  followers_count: number;
  following_count: number;
  tweet_count: number;
  profile_image_url: string | null;
  verified: boolean;
}
```

### 使用示例

```typescript
async function searchTwitterUser(username: string) {
  try {
    const user = await api.twitter.searchUser(username);
    console.log(user.display_name);
    console.log(user.followers_count);
    console.log(user.description);
    return user;
  } catch (error) {
    console.error('Failed to search user:', error);
  }
}
```

## 注意事项

1. **频率限制**: Twitter API 有请求频率限制，搜索用户信息时建议添加防抖处理
2. **缓存**: 用户信息变化不频繁，建议前端缓存搜索结果
3. **错误处理**: 用户不存在时会返回错误，需要在前端做好错误提示
