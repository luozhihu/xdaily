# X (Twitter) RSS 抓取系统设计

## 一、目标

- 定时抓取 X 博主推文，去重持久化
- 博主通过 API 管理（仅管理员）
- 不做推送，仅存储
- 用户认证，角色权限控制

## 二、架构

```
┌─────────────────────────────────────────────────────┐
│                   Twitter/X API                      │
│         (GraphQL with Cookie Authentication)         │
│              + curl_cffi TLS 模拟                   │
└──────────────────────────┬──────────────────────────┘
                           ▼
                 ┌─────────────────┐
                 │  TwitterClient  │
                 │   GraphQL API   │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │     SQLite      │
                 └─────────────────┘
                          ▲
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
┌──────┴──────┐   ┌───────┴───────┐   ┌──────┴──────┐
│  API 服务    │   │   cron 调度   │   │   AI 总结   │
│  (Flask)    │   │   (可选)      │   │  (OpenAI)   │
└─────────────┘   └───────────────┘   └─────────────┘
```

**技术栈**：Python + curl_cffi + SQLite + Flask + JWT + OpenAI

### 2.1 fetch_with_retry

Twitter GraphQL API 使用 Cookie 认证（`auth_token` + `ct0`），需要：
1. 从浏览器登录 x.com 后获取 `auth_token` 和 `ct0` Cookie
2. 使用 `curl_cffi` 模拟 Chrome 浏览器 TLS/JA3 指纹，避免被 Twitter 识别为机器人
3. 调用 `UserByScreenName` 查询将用户名解析为 numeric `userId`
4. 使用 `userId` 调用 `UserTweets` 获取用户推文

## 三、数据模型

### users 表（用户）
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',  -- 'admin' or 'user'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### categories 表（分类）
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### feeds 表（博主）
```sql
CREATE TABLE feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    twitter_username TEXT UNIQUE NOT NULL,
    category_id INTEGER,
    enabled BOOLEAN DEFAULT 1,
    tags TEXT,
    last_fetch_at DATETIME,
    last_tweet_at DATETIME,
    tweets_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

### tweets 表
```sql
CREATE TABLE tweets (
    id TEXT PRIMARY KEY,
    author TEXT NOT NULL,
    twitter_username TEXT NOT NULL,
    content TEXT,
    link TEXT,
    published DATETIME,
    published_date DATE,
    fetched_date DATE NOT NULL,
    fetched_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    tags TEXT,
    is_retweet BOOLEAN DEFAULT 0,
    is_reply BOOLEAN DEFAULT 0,
    extra_data TEXT
);

CREATE INDEX idx_tweets_fetched ON tweets(fetched_date);
CREATE INDEX idx_tweets_published ON tweets(published);
CREATE INDEX idx_tweets_username ON tweets(twitter_username);
```

### fetch_logs 表
```sql
CREATE TABLE fetch_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL,
    started_at DATETIME NOT NULL,
    completed_at DATETIME,
    status TEXT NOT NULL,
    items_new INTEGER DEFAULT 0,
    items_dup INTEGER DEFAULT 0,
    error_message TEXT,
    rss_source TEXT,
    FOREIGN KEY (feed_id) REFERENCES feeds(id)
);
```

### summaries 表（AI 总结）
```sql
CREATE TABLE summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    summary_date DATE NOT NULL,           -- 总结的日期
    summary_text TEXT,                  -- AI 生成的总结
    tweets_count INTEGER DEFAULT 0,      -- 当天该分类的推文数
    status TEXT NOT NULL,               -- 'success' / 'failed'
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    UNIQUE(category_id, summary_date)  -- 每天每个分类只能有一条总结
);
```

## 四、用户认证

### 4.1 角色说明

| 角色 | 权限 |
|------|------|
| admin | 管理分类、博主、触发抓取、触发总结、查看所有数据 |
| user | 查看推文、搜索 |

### 4.2 认证流程

```
用户登录 → 验证用户名密码 → 生成 JWT Token → 返回 Token
```

### 4.3 JWT Token 结构

```json
{
  "sub": "user_id",
  "username": "admin",
  "role": "admin",
  "exp": 1234567890
}
```

**Token 有效期**：24 小时

### 4.4 密码加密

- 算法：bcrypt
- 存储：`password_hash` 字段

## 五、API 接口

### 5.1 认证接口（公开）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/auth/login` | 用户登录 | 公开 |
| POST | `/api/auth/register` | 用户注册 | 公开（首个用户自动设为管理员） |

#### 登录
```json
POST /api/auth/login
{ "username": "admin", "password": "xxx" }

Response:
{
  "code": 0,
  "data": {
    "token": "eyJ...",
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin"
    }
  }
}
```

#### 注册
```json
POST /api/auth/register
{ "username": "newuser", "password": "xxx" }
```

### 5.2 分类管理（仅管理员）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/categories` | 分类列表 | user+ |
| POST | `/api/categories` | 添加分类 | admin |
| PUT | `/api/categories/{id}` | 更新分类 | admin |
| DELETE | `/api/categories/{id}` | 删除分类 | admin |

### 5.3 博主管理（仅管理员）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/feeds` | 博主列表 | user+ |
| GET | `/api/feeds/{id}` | 博主详情 | user+ |
| POST | `/api/feeds` | 添加博主 | admin |
| PUT | `/api/feeds/{id}` | 更新博主 | admin |
| DELETE | `/api/feeds/{id}` | 删除博主 | admin |
| POST | `/api/feeds/{id}/fetch` | 手动抓取 | admin |

### 5.4 推文接口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/feeds/{id}/tweets` | 推文列表 | user+ |
| GET | `/api/tweets` | 全局推文搜索 | user+ |

### 5.5 Twitter 用户搜索（仅管理员）

根据 Twitter 用户名查询用户信息（头像、简介、粉丝数等）。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/twitter/user-info/<username>` | 查询用户信息 | admin |

```
GET /api/twitter/user-info/elonmusk

Response:
{
  "code": 0,
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

### 5.6 用户管理（仅管理员）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/users` | 用户列表 | admin |
| PUT | `/api/users/{id}/role` | 修改用户角色 | admin |
| DELETE | `/api/users/{id}` | 删除用户 | admin |

### 5.7 AI 总结（仅管理员）

管理员触发后，系统遍历所有分类，对每个分类下当天所有博主的推文进行 AI 总结。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/summaries/generate` | 触发全部分类总结 | admin |
| POST | `/api/summaries/generate/{category_id}` | 触发单个分类总结 | admin |
| GET | `/api/summaries` | 总结列表 | admin |
| GET | `/api/categories/{id}/summary` | 查看某分类当天的总结 | admin |

#### 触发全部分类总结
```json
POST /api/summaries/generate

Response:
{
  "code": 0,
  "data": {
    "total": 5,
    "success": 4,
    "failed": 1,
    "results": [
      {"category_id": 1, "category_name": "科技", "status": "success", "tweets_count": 12},
      {"category_id": 2, "category_name": "商业", "status": "failed", "error": "No tweets found"}
    ]
  }
}
```

#### 查看分类总结
```json
GET /api/categories/1/summary

Response:
{
  "code": 0,
  "data": {
    "category_id": 1,
    "category_name": "科技",
    "summary_date": "2024-01-15",
    "summary_text": "今日科技领域重要动态：...",
    "tweets_count": 12,
    "status": "success"
  }
}
```

## 六、权限装饰器

```python
def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'code': 401, 'message': 'Unauthorized'}), 401

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            if payload.get('role') != 'admin':
                return jsonify({'code': 403, 'message': 'Forbidden'}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({'code': 401, 'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'code': 401, 'message': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated
```

## 七、AI 总结服务

### 7.1 总结流程

```
1. 管理员触发总结任务
2. 遍历所有分类：
   a. 查询该分类下当天所有推文
   b. 拼接推文内容
   c. 调用 AI API 生成总结
   d. 保存总结结果到 summaries 表
3. 返回汇总结果
```

### 7.2 Prompt 模板

```
你是一个社交媒体内容分析助手。请总结以下推文的主要内容，提取关键信息和趋势。

推文列表：
{推文内容拼接}

请用 200-300 字总结今日内容，包括：
1. 主要话题
2. 关键事件或观点
3. 整体情绪倾向

总结：
```

### 7.3 错误处理

- 某分类总结失败不影响其他分类
- 失败的分类记录错误信息，可重试
- 无推文的分类跳过总结

## 八、错误码

### 认证错误
| 码 | 说明 |
|----|------|
| 3001 | 用户名已存在 |
| 3002 | 用户名或密码错误 |
| 3003 | Token 已过期 |
| 3004 | Token 无效 |

### 权限错误
| 码 | 说明 |
|----|------|
| 4001 | 无权限，需要管理员权限 |

### 业务错误
| 码 | 说明 |
|----|------|
| 1001 | 用户名已存在（博主） |
| 1002 | 用户名格式错误 |
| 1003 | 博主不存在 |
| 2001 | 分类名称已存在 |
| 2002 | 分类不存在 |
| 2003 | 分类下有博主，无法删除 |
| 6001 | 该分类当天没有推文 |
| 6002 | AI 总结失败 |
| 6003 | 总结任务进行中 |

## 八、配置 (config.yaml)

```yaml
settings:
  timeout: 15
  max_entries: 200
  retry_times: 3
  retry_delay: 5
  db_path: "data/tweets.db"
  db_backup_enabled: true
  db_backup_retention: 7
  log_level: "INFO"
  log_path: "logs/rss_job.log"

  api_host: "0.0.0.0"
  api_port: 8080

  # JWT 配置
  jwt_secret: "your-secret-key-change-in-production"
  jwt_expiry_hours: 24

  # AI 总结配置
  ai_provider: "openai"  # openai / anthropic / custom
  ai_model: "gpt-4o-mini"
  ai_api_key: "${AI_API_KEY}"  # 环境变量
  ai_max_tokens: 1000
  ai_temperature: 0.7

twitter:
  enabled: true
  auth_token: "${TWITTER_AUTH_TOKEN}"      # Twitter auth_token cookie (从 x.com 登录后获取)
  ct0: "${TWITTER_CT0}"                    # Twitter ct0 cookie
  rate_limit:
    base_delay: 2.5        # 请求间隔基础延迟(秒)
    max_retries: 5        # 最大重试次数
  default_count: 20        # 默认每次拉取推文数
  request_timeout: 30      # 请求超时(秒)
```

### 8.1 Twitter Cookie 获取方式

1. 在浏览器中登录 x.com
2. 打开开发者工具 (F12) → Application → Cookies → x.com
3. 复制 `auth_token` 和 `ct0` 的值
4. 设置环境变量或填入 config.yaml

> 注意：Cookie 有效期有限，过期后需要重新获取

## 九、部署结构

```
/opt/rss/
├── rss_job.py        # 抓取入口
├── api_server.py     # API 服务
├── config.yaml
├── requirements.txt
├── data/
│   ├── tweets.db
│   └── backups/
├── logs/
└── migrations/
```

**依赖**：curl_cffi, requests, PyYAML, flask, pyjwt, bcrypt, openai

### 9.1 Twitter API 实现细节

| 组件 | 说明 |
|------|------|
| `twitter_client.py` | GraphQL API 客户端，处理请求/重试/认证 |
| `twitter_parser.py` | 解析 Twitter API 响应，提取推文/用户信息 |
| `twitter_fetcher.py` | 抓取流程编排，日期过滤，去重，持久化 |

**API 端点**：
- `UserByScreenName` - 将用户名解析为 numeric userId
- `UserTweets` - 获取用户推文列表（支持分页）

**关键响应结构**：
```
timeline.timeline.instructions[]  # 替代旧的 timeline_v2.timeline
core.screen_name                 # 替代 legacy.screen_name
```

## 十、扩展方向

- [x] AI 总结推文
- [x] Twitter 官方 API 抓取（替代 RSSHub/Nitter）
- [ ] Web UI
- [ ] PostgreSQL 迁移
- [ ] 数据导出 (JSON/CSV)
- [ ] OAuth 第三方登录
