"""Twitter GraphQL API client with cookie authentication."""
import logging
import time
import random
import sys
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

import os
import yaml
from pathlib import Path
from curl_cffi import requests as cffi_requests

logger = logging.getLogger(__name__)


# Twitter GraphQL Query IDs (hardcoded fallback)
TWITTER_QUERY_IDS = {
    'HomeTimeline': 'L8Lb9oomccM012S7fQ-QKA',
    'HomeLatestTimeline': 'tzmrSIWxyV4IRrh9nij6TQ',
    'UserTweets': 'O0epvwaQPUx-bT9YlqlL6w',
    'TweetDetail': 'xIYgDwjboktoFeXe_fgacw',
    'Likes': 'RozqFzI4CilQzrcuU0NY5w',
    'SearchTimeline': 'rkp6b4vtR9u7v3naGoOzUQ',
    'Bookmarks': 'uzboyXSHSJrR-mGJqep0TQ',
    'UserByScreenName': 'IGgvgiOx4QZndDHuD3x9TQ',
}

# Bearer token for Twitter API
BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

# Chrome version for impersonation
_CHROME_VERSION = "133"

# curl_cffi session (shared)
_cffi_session = None
_best_chrome_target = "chrome133a"  # fallback default


def _detect_best_chrome_target():
    """Detect the best available Chrome impersonation target at runtime."""
    try:
        from curl_cffi.requests import BrowserType
        available = {e.value for e in BrowserType}
    except Exception:
        return "chrome133a"  # fallback

    # Preference order: suffixed variants first (more complete), then exact versions
    preferred = ["chrome133a", "chrome136", "chrome133", "chrome131", "chrome124", "chrome123"]
    for target in preferred:
        if target in available:
            return target

    # Fallback: pick highest chrome version
    chrome_targets = sorted(
        [v for v in available if v.startswith("chrome") and v[6:].isdigit()],
        key=lambda x: int(x.replace("chrome", "")),
        reverse=True,
    )
    return chrome_targets[0] if chrome_targets else "chrome133a"


def _get_cffi_session():
    """Get or create curl_cffi session with Chrome impersonation."""
    global _cffi_session, _best_chrome_target
    if _cffi_session is None:
        _best_chrome_target = _detect_best_chrome_target()
        logger.info(f"Using Chrome impersonation: {_best_chrome_target}")
        _cffi_session = cffi_requests.Session(impersonate=_best_chrome_target)
    return _cffi_session


def _sync_chrome_version(impersonate_target):
    """Sync chrome version based on impersonate target."""
    global _CHROME_VERSION
    match = re.search(r"(\d+)", impersonate_target)
    if match:
        _CHROME_VERSION = match.group(1)


def _get_user_agent():
    """Get User-Agent string."""
    if sys.platform == "darwin":
        platform = "Macintosh; Intel Mac OS X 10_15_7"
    elif sys.platform.startswith("win"):
        platform = "Windows NT 10.0; Win64; x64"
    else:
        platform = "X11; Linux x86_64"
    return (
        "Mozilla/5.0 (%s) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/%s.0.0.0 Safari/537.36" % (platform, _CHROME_VERSION)
    )


def _get_sec_ch_ua():
    return '"Chromium";v="%s", "Not(A:Brand";v="99", "Google Chrome";v="%s"' % (
        _CHROME_VERSION, _CHROME_VERSION,
    )


def _get_sec_ch_ua_full_version():
    return '"%s.0.0.0"' % _CHROME_VERSION


def _get_sec_ch_ua_full_version_list():
    return '"Google Chrome";v="%s.0.0.0", "Chromium";v="%s.0.0.0", "Not.A/Brand";v="99.0.0.0"' % (
        _CHROME_VERSION, _CHROME_VERSION,
    )


def _get_sec_ch_ua_platform():
    if sys.platform == "darwin":
        return '"macOS"'
    if sys.platform.startswith("win"):
        return '"Windows"'
    return '"Linux"'


def _get_sec_ch_ua_arch():
    machine = (getattr(os, 'uname', lambda: None)() or []).machine.lower() if hasattr(os, 'uname') else ""
    if "arm" in machine or "aarch" in machine:
        return '"arm"'
    if "86" in machine or "amd64" in machine or "x64" in machine:
        return '"x86"'
    return '""'


def _get_sec_ch_ua_platform_version():
    if sys.platform == "darwin":
        return '"15.0.0"'
    if sys.platform.startswith("win"):
        return '"10.0.0"'
    return '""'


def _get_accept_language():
    import os
    raw = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "en_US.UTF-8"
    tag = raw.split(".", 1)[0].replace("_", "-")
    language = tag.split("-", 1)[0] or "en"
    return "%s,%s;q=0.9,en;q=0.8" % (tag, language)


def _get_twitter_client_language():
    import os
    raw = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "en_US.UTF-8"
    tag = raw.split(".", 1)[0].replace("_", "-")
    return tag.split("-", 1)[0] or "en"


@dataclass
class TwitterUser:
    """Twitter user profile."""
    id: str
    username: str
    display_name: str
    description: Optional[str] = None
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    tweet_count: Optional[int] = None
    profile_image_url: Optional[str] = None
    verified: bool = False


@dataclass
class TweetMetrics:
    """Engagement metrics for a tweet."""
    retweet_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    quote_count: int = 0
    bookmark_count: int = 0
    view_count: Optional[int] = None


@dataclass
class TweetMedia:
    """Media attached to a tweet."""
    id: str
    type: str  # photo, video, animated_gif
    url: str
    alt_text: Optional[str] = None
    preview_image_url: Optional[str] = None
    variants: List[dict] = field(default_factory=list)


@dataclass
class TwitterTweet:
    """Parsed Twitter tweet."""
    id: str
    text: str
    author: TwitterUser
    created_at: datetime
    metrics: TweetMetrics
    media: List[TweetMedia] = field(default_factory=list)
    is_retweet: bool = False
    is_reply: bool = False
    is_quoted: bool = False
    reply_to_id: Optional[str] = None
    reply_to_username: Optional[str] = None
    quoted_tweet_id: Optional[str] = None
    conversation_id: Optional[str] = None
    lang: Optional[str] = None
    source: Optional[str] = None
    link: str = ""


@dataclass
class TimelineResult:
    """Result of timeline fetch."""
    tweets: List[TwitterTweet]
    next_cursor: Optional[str]
    has_more: bool


class TwitterAuthError(Exception):
    """Raised when Twitter authentication fails."""
    pass


class RateLimitError(Exception):
    """Raised when Twitter returns 429 Too Many Requests."""
    pass


class TemporaryError(Exception):
    """Raised on temporary Twitter errors (5xx)."""
    pass


class TwitterAPIError(Exception):
    """Raised on general Twitter API errors."""
    pass


class RateLimiter:
    """Exponential backoff rate limiter for Twitter API."""

    def __init__(self, base_delay: float = 2.5, max_delay: float = 60.0, max_retries: int = 5):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries

    def get_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = random.uniform(0, 0.3 * delay)
        return delay + jitter


def load_twitter_config() -> dict:
    """Load Twitter configuration from config.yaml."""
    project_root = Path(__file__).parent.parent.parent
    yaml_config = project_root / 'config.yaml'

    if not yaml_config.exists():
        return {}

    with open(yaml_config) as f:
        config = yaml.safe_load(f)
        return config.get('twitter', {})


class TwitterAuth:
    """Cookie-based Twitter authentication."""

    def __init__(
        self,
        auth_token: Optional[str] = None,
        ct0: Optional[str] = None,
    ):
        if auth_token is None or ct0 is None:
            twitter_config = load_twitter_config()
            auth_token = auth_token or twitter_config.get('auth_token')
            ct0 = ct0 or twitter_config.get('ct0')

        if not auth_token or not ct0:
            raise TwitterAuthError(
                "Twitter cookies not configured. "
                "Set twitter.auth_token and twitter.ct0 in config.yaml."
            )

        self.auth_token = auth_token
        self.ct0 = ct0

    def get_cookies(self) -> dict:
        return {
            'auth_token': self.auth_token,
            'ct0': self.ct0,
        }

    def get_headers(self) -> dict:
        return {
            'x-csrf-token': self.ct0,
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': 'en',
        }


class TwitterClient:
    """Twitter GraphQL API client with cookie authentication."""

    BASE_URL = "https://x.com/i/api/graphql"

    def __init__(
        self,
        auth: Optional[TwitterAuth] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.auth = auth or TwitterAuth()
        self.rate_limiter = rate_limiter or RateLimiter()

    def _build_url(self, query_id: str, operation_name: str, variables: dict, features: dict = None) -> str:
        """Build GraphQL endpoint URL."""
        import json
        import urllib.parse
        variables_json = urllib.parse.quote(json.dumps(variables, separators=(',', ':')))
        url = f"{self.BASE_URL}/{query_id}/{operation_name}?variables={variables_json}"
        if features:
            features_json = urllib.parse.quote(json.dumps(features, separators=(',', ':')))
            url += f"&features={features_json}"
        return url

    def _build_headers(self, url: str = "", method: str = "GET") -> dict:
        """Build request headers with all necessary fields for Twitter API."""
        cookie_str = "auth_token=%s; ct0=%s" % (self.auth.auth_token, self.auth.ct0)
        headers = {
            "Authorization": "Bearer %s" % BEARER_TOKEN,
            "Cookie": cookie_str,
            "X-Csrf-Token": self.auth.ct0,
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": _get_twitter_client_language(),
            "User-Agent": _get_user_agent(),
            "Origin": "https://x.com",
            "Referer": "https://x.com/",
            "Accept": "*/*",
            "Accept-Language": _get_accept_language(),
            "sec-ch-ua": _get_sec_ch_ua(),
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": _get_sec_ch_ua_platform(),
            "sec-ch-ua-arch": _get_sec_ch_ua_arch(),
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": _get_sec_ch_ua_full_version(),
            "sec-ch-ua-full-version-list": _get_sec_ch_ua_full_version_list(),
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform-version": _get_sec_ch_ua_platform_version(),
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        return headers

    def _check_response(self, response) -> None:
        """Check response for errors and rate limiting."""
        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        if response.status_code >= 500:
            raise TemporaryError(f"Twitter server error: {response.status_code}")
        if response.status_code == 401:
            raise TwitterAuthError("Authentication failed - check your cookies")
        if response.status_code != 200:
            raise TwitterAPIError(f"API error: {response.status_code}")

    def _execute_request(self, url: str, headers: dict) -> dict:
        """Execute HTTP request with retry logic using curl_cffi."""
        last_exception = None
        session = _get_cffi_session()
        for attempt in range(self.rate_limiter.max_retries):
            try:
                response = session.get(url, headers=headers, timeout=30)
                status = response.status_code
                text = response.text
                if status != 200:
                    logger.warning(f"API returned status {status}")
                self._check_response(response)
                if not text:
                    return {}
                return response.json()
            except RateLimitError as e:
                last_exception = e
                if attempt < self.rate_limiter.max_retries - 1:
                    delay = self.rate_limiter.get_delay(attempt)
                    logger.warning(f"Rate limited, waiting {delay:.1f}s before retry {attempt + 1}")
                    time.sleep(delay)
            except TemporaryError as e:
                last_exception = e
                if attempt < self.rate_limiter.max_retries - 1:
                    delay = self.rate_limiter.get_delay(attempt)
                    time.sleep(delay)
            except Exception as e:
                last_exception = e
                break

        raise last_exception

    def _default_features(self) -> dict:
        """Default feature flags for Twitter GraphQL requests."""
        return {
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "longform_notetweets_consumption_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_containers_enabled": False,
            "longform_notetweets_richtext_consumption_enabled": True,
            "responsive_web_graphql_deduplicate_requests_enabled": True,
            "tweetypie_unmention_optimization_enabled": True,
        }

    def fetch_home_timeline(
        self,
        timeline_type: str = "ForYou",
        count: int = 20,
        cursor: Optional[str] = None,
    ) -> TimelineResult:
        """
        Fetch home timeline (For You or Following).

        Args:
            timeline_type: "ForYou" or "Following"
            count: Number of tweets to fetch (max 100)
            cursor: Pagination cursor for next page

        Returns:
            TimelineResult with tweets and pagination info
        """
        query_id = (
            TWITTER_QUERY_IDS['HomeTimeline']
            if timeline_type == "ForYou"
            else TWITTER_QUERY_IDS['HomeLatestTimeline']
        )
        operation = "HomeTimeline" if timeline_type == "ForYou" else "HomeLatestTimeline"

        variables = {
            "count": min(count, 100),
            "includePromotedContent": False,
            "latestControlAvailable": True,
            "requestContext": "launch",
        }
        if cursor:
            variables["cursor"] = cursor

        url = self._build_url(query_id, operation, variables, self._default_features())
        headers = self._build_headers()

        response = self._execute_request(url, headers)
        return self._parse_timeline_response(response, timeline_type)

    def resolve_user_id(self, username: str) -> str:
        """Resolve a username to numeric user ID."""
        variables = {
            "screen_name": username,
            "withSafetyModeUserFields": True,
        }
        url = self._build_url(TWITTER_QUERY_IDS['UserByScreenName'], 'UserByScreenName', variables, self._default_features())
        headers = self._build_headers()
        response = self._execute_request(url, headers)
        user_result = response.get('data', {}).get('user', {}).get('result', {})
        user_id = user_result.get('rest_id')
        if not user_id:
            raise TwitterAPIError(f"Could not resolve user ID for @{username}")
        return user_id

    def fetch_user_info(self, username: str) -> TwitterUser:
        """Fetch full user profile info by username."""
        variables = {
            "screen_name": username,
            "withSafetyModeUserFields": True,
        }
        url = self._build_url(TWITTER_QUERY_IDS['UserByScreenName'], 'UserByScreenName', variables, self._default_features())
        headers = self._build_headers()
        response = self._execute_request(url, headers)

        from app.services.twitter_parser import parse_user
        user_result = response.get('data', {}).get('user', {})
        return parse_user(user_result)

    def fetch_user_tweets(
        self,
        username: str,
        count: int = 20,
        cursor: Optional[str] = None,
        include_replies: bool = True,
        include_retweets: bool = True,
    ) -> TimelineResult:
        """Fetch tweets for a specific user."""
        # Resolve username to numeric userId (required by Twitter API)
        user_id = self.resolve_user_id(username)

        variables = {
            "userId": user_id,
            "count": min(count, 100),
            "includePromotedContent": False,
            "withQuickPromoteEligibilityTweetFields": False,
            "withVoice": True,
            "withV2Timeline": True,
        }
        if cursor:
            variables["cursor"] = cursor

        variables["withReplies"] = include_replies
        variables["withRetweets"] = include_retweets

        url = self._build_url(TWITTER_QUERY_IDS['UserTweets'], 'UserTweets', variables, self._default_features())
        headers = self._build_headers()

        response = self._execute_request(url, headers)
        return self._parse_timeline_response(response, f"UserTweets_{username}")

    def fetch_tweet_detail(self, tweet_id: str) -> TwitterTweet:
        """Fetch a single tweet by ID."""
        variables = {
            "tweetId": tweet_id,
            "withCommunity": True,
            "includePromotedContent": False,
            "withVoice": True,
        }

        url = self._build_url(TWITTER_QUERY_IDS['TweetDetail'], 'TweetDetail', variables, self._default_features())
        headers = self._build_headers()

        response = self._execute_request(url, headers)
        return self._parse_tweet_detail_response(response)

    def fetch_likes(
        self,
        username: str,
        count: int = 20,
        cursor: Optional[str] = None,
    ) -> TimelineResult:
        """Fetch likes for a user."""
        variables = {
            "userId": "",
            "screen_name": username,
            "count": min(count, 100),
            "includePromotedContent": False,
        }
        if cursor:
            variables["cursor"] = cursor

        url = self._build_url(TWITTER_QUERY_IDS['Likes'], 'Likes', variables, self._default_features())
        headers = self._build_headers()

        response = self._execute_request(url, headers)
        return self._parse_timeline_response(response, f"Likes_{username}")

    def fetch_search(
        self,
        query: str,
        count: int = 20,
        cursor: Optional[str] = None,
    ) -> TimelineResult:
        """Fetch search results."""
        variables = {
            "query": query,
            "count": min(count, 100),
            "includePromotedContent": False,
            "newTypeEnabled": True,
        }
        if cursor:
            variables["cursor"] = cursor

        url = self._build_url(TWITTER_QUERY_IDS['SearchTimeline'], 'SearchTimeline', variables, self._default_features())
        headers = self._build_headers()

        response = self._execute_request(url, headers)
        return self._parse_timeline_response(response, "SearchTimeline")

    def _parse_timeline_response(self, response: dict, timeline_type: str) -> TimelineResult:
        """Parse GraphQL timeline response into TimelineResult."""
        from app.services.twitter_parser import parse_timeline_response
        return parse_timeline_response(response, timeline_type)

    def _parse_tweet_detail_response(self, response: dict) -> TwitterTweet:
        """Parse GraphQL tweet detail response into TwitterTweet."""
        from app.services.twitter_parser import parse_tweet_detail_response
        return parse_tweet_detail_response(response)
