"""AI Summarizer service."""
import os
import logging
from datetime import datetime, date, timedelta
from typing import Optional

from app import db
from app.models import Category, Tweet, Summary

logger = logging.getLogger(__name__)


def get_ai_config():
    """Get AI configuration from config.yaml."""
    try:
        import yaml
        from pathlib import Path
        config_file = Path('config.yaml')
        if config_file.exists():
            with open(config_file) as f:
                config = yaml.safe_load(f)
                settings = config.get('settings', {})
                return {
                    'provider': settings.get('ai_provider', 'openai'),
                    'model': settings.get('ai_model', 'gpt-4o-mini'),
                    'api_key': os.environ.get('xdaily_LLM_SUMMARIZER_APIKEY') or settings.get('ai_api_key', ''),
                    'base_url': settings.get('ai_base_url', '') or os.environ.get('OPENAI_BASE_URL'),
                    'max_tokens': settings.get('ai_max_tokens', 1000),
                    'temperature': settings.get('ai_temperature', 0.7),
                    'extra_body': settings.get('ai_extra_body', {})
                }
    except Exception as e:
        logger.warning(f"Failed to load AI config: {e}")
    return {}


def build_summary_prompt(tweets: list) -> str:
    """Build prompt for summarizing tweets."""
    if not tweets:
        return ""

    # Format tweets
    tweet_lines = []
    for i, tweet in enumerate(tweets, 1):
        author = tweet.get('author', 'Unknown')
        content = tweet.get('content', '')
        link = tweet.get('link', '')
        tweet_lines.append(f"{i}. [{author}] {content}")
        if link:
            tweet_lines.append(f"   Link: {link}")

    tweets_text = '\n'.join(tweet_lines)

    prompt = fprompt = f"""你是一个专业的社交媒体内容分析助手，擅长从碎片化推文中提炼高价值信息，并生成中文的结构化日报。

请基于以下推文生成一份“今日推文简报”。

推文列表：
{tweets_text}

请严格按照以下格式输出（不得增加或减少字段）：

# 标题（用一句话概括今日最核心的话题或趋势）

## 今日摘要
> 用 150-200 字总结今天的整体内容，包括：
> - 最重要的 2-3 个话题
> - 是否有热点/突发信息
> - 整体讨论氛围（乐观 / 悲观 / 分歧 / 中性）

## NOTES
- **小标题：** 用几句话总结该主题核心信息[原文](原文链接)

👉 要求：
- 链接必须来自提供的推文，不允许编造
- 如果某条推文没有链接，可以不提供链接

## 评论
- 用 100-150 字对今日内容进行“总结性评论”，包括：
  - 当前趋势判断（例如：某领域升温/降温）
  - 信息价值（噪音 vs 信号）
  - 是否值得持续关注

【整体要求】
- 不要重复原文
- 内容必须压缩和提炼
- 语言简洁、有洞察
- 保持专业感，像行业日报
- 不要输出分析过程
- 输出必须是中文

开始输出：
"""
    return prompt


def call_ai_api(prompt: str) -> str:
    """Call AI API to generate summary."""
    config = get_ai_config()

    if not config.get('api_key'):
        raise Exception("AI_API_KEY not configured")

    if config.get('provider') == 'openai':
        return call_openai(prompt, config)
    else:
        raise Exception(f"Unsupported AI provider: {config.get('provider')}")


def call_openai(prompt: str, config: dict) -> str:
    """Call OpenAI-compatible API."""
    try:
        from openai import OpenAI

        client_kwargs = {
            'api_key': config['api_key'],
        }

        # Add base_url if configured (for MiniMax and other OpenAI-compatible APIs)
        if config.get('base_url'):
            client_kwargs['base_url'] = config['base_url']

        client = OpenAI(**client_kwargs)

        create_kwargs = {
            'model': config['model'],
            'messages': [
                {"role": "system", "content": "你是一个社交媒体内容分析助手。"},
                {"role": "user", "content": prompt}
            ],
            'max_tokens': config['max_tokens'],
            'temperature': config['temperature']
        }

        # Add extra_body if configured (e.g., MiniMax's reasoning_split)
        if config.get('extra_body'):
            create_kwargs['extra_body'] = config['extra_body']

        response = client.chat.completions.create(**create_kwargs)

        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        raise


def summarize_category(category_id: int, target_date: date = None) -> dict:
    """
    Generate summary for a specific category and date.

    Returns dict with status, summary_text, tweets_count, error.
    """
    # Default to yesterday
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    # Get category
    category = Category.query.get(category_id)
    if not category:
        return {
            'category_id': category_id,
            'category_name': None,
            'status': 'failed',
            'summary_text': None,
            'tweets_count': 0,
            'error': 'Category not found'
        }

    # Get all feeds in this category
    feeds = Feed.query.filter_by(category_id=category_id, enabled=True).all()
    today = date.today()
    if not feeds:
        # Delete existing summary if any, then create new one
        Summary.query.filter_by(category_id=category_id, summary_date=today).delete()
        summary = Summary(
            category_id=category_id,
            summary_date=today,
            summary_text='该分类下暂无博主',
            tweets_count=0,
            status='success'
        )
        db.session.add(summary)
        db.session.commit()
        return {
            'category_id': category_id,
            'category_name': category.name,
            'status': 'success',
            'summary_text': '该分类下暂无博主',
            'tweets_count': 0,
            'error': None
        }

    usernames = [f.twitter_username for f in feeds]

    # Get tweets for these feeds on target date
    tweets = Tweet.query.filter(
        Tweet.twitter_username.in_(usernames),
        Tweet.published_date == target_date
    ).order_by(Tweet.published.desc()).all()

    # Always create a summary, even if no tweets
    if not tweets:
        # Delete existing summary if any
        Summary.query.filter_by(category_id=category_id, summary_date=today).delete()
        summary = Summary(
            category_id=category_id,
            summary_date=today,
            summary_text=f'昨日（{target_date}）该分类下暂无推文',
            tweets_count=0,
            status='success'
        )
        db.session.add(summary)
        db.session.commit()
        return {
            'category_id': category_id,
            'category_name': category.name,
            'status': 'success',
            'summary_text': f'昨日（{target_date}）该分类下暂无推文',
            'tweets_count': 0,
            'error': None
        }

    # Build prompt
    tweets_data = [t.to_dict() for t in tweets]
    prompt = build_summary_prompt(tweets_data)

    try:
        # Call AI API
        summary_text = call_ai_api(prompt)

        # Delete existing summary if any, then save new one
        Summary.query.filter_by(category_id=category_id, summary_date=today).delete()
        summary = Summary(
            category_id=category_id,
            summary_date=today,
            summary_text=summary_text,
            tweets_count=len(tweets),
            status='success'
        )
        db.session.add(summary)
        db.session.commit()

        return {
            'category_id': category_id,
            'category_name': category.name,
            'status': 'success',
            'summary_text': summary_text,
            'tweets_count': len(tweets),
            'error': None
        }

    except Exception as e:
        # Delete existing summary if any, then save failed one
        Summary.query.filter_by(category_id=category_id, summary_date=today).delete()
        summary = Summary(
            category_id=category_id,
            summary_date=today,
            summary_text=None,
            tweets_count=len(tweets),
            status='failed',
            error_message=str(e)
        )
        db.session.add(summary)
        db.session.commit()

        return {
            'category_id': category_id,
            'category_name': category.name,
            'status': 'failed',
            'summary_text': None,
            'tweets_count': len(tweets),
            'error': str(e)
        }


def summarize_all_categories(target_date: date = None) -> list:
    """
    Generate summaries for all categories.

    Returns list of results for each category.
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    categories = Category.query.all()
    results = []

    for category in categories:
        result = summarize_category(category.id, target_date)
        results.append(result)
        logger.info(f"Summary for {category.name}: {result['status']}")

    return results


# Need to import Feed here due to circular reference
from app.models import Feed
