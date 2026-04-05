"""Tests for parser service."""
import pytest
from app.services.parser import (
    extract_tweet_id,
    clean_content,
    detect_retweet,
    detect_reply,
    parse_entry
)


class MockEntry:
    """Mock RSS entry."""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.title = kwargs.get('title', '')
        self.summary = kwargs.get('summary', '')
        self.link = kwargs.get('link', '')
        self.published = kwargs.get('published', '')
        self.published_parsed = kwargs.get('published_parsed', None)
        self.author = kwargs.get('author', '')


class TestExtractTweetId:
    """Tests for extract_tweet_id."""

    def test_from_id_with_tag_format(self):
        """Test extracting ID from tag:twitter.com:123 format."""
        entry = MockEntry(id='tag:twitter.com:1234567890')
        assert extract_tweet_id(entry) == '1234567890'

    def test_from_id_plain(self):
        """Test extracting plain ID."""
        entry = MockEntry(id='1234567890')
        assert extract_tweet_id(entry) == '1234567890'

    def test_from_link(self):
        """Test extracting ID from status link."""
        entry = MockEntry(link='https://x.com/elonmusk/status/1234567890123456789')
        assert extract_tweet_id(entry) == '1234567890123456789'

    def test_from_nitter_link(self):
        """Test extracting ID from nitter link."""
        entry = MockEntry(link='https://nitter.net/elonmusk/status/9876543210')
        assert extract_tweet_id(entry) == '9876543210'

    def test_fallback_to_hash(self):
        """Test fallback to content hash."""
        entry = MockEntry(title='Test tweet content')
        result = extract_tweet_id(entry)
        assert len(result) == 16  # MD5 hash truncated to 16 chars


class TestCleanContent:
    """Tests for clean_content."""

    def test_remove_html_tags(self):
        """Test removing HTML tags."""
        html = '<p>Hello <a href="http://example.com">world</a>!</p>'
        assert clean_content(html) == 'Hello world!'

    def test_decode_html_entities(self):
        """Test decoding HTML entities."""
        text = 'Hello &amp; world &lt;3'
        assert clean_content(text) == 'Hello & world <3'

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        text = 'Hello    world\n\n\ntest'
        result = clean_content(text)
        assert '  ' not in result
        assert '\n' not in result

    def test_empty_string(self):
        """Test empty string."""
        assert clean_content('') == ''
        assert clean_content(None) == ''


class TestDetectRetweet:
    """Tests for detect_retweet."""

    def test_rt_in_title(self):
        """Test RT detection in title."""
        entry = MockEntry(title='RT @someone: This is a retweet')
        assert detect_retweet(entry) is True

    def test_rtin_summary(self):
        """Test RT detection in summary."""
        entry = MockEntry(summary='RT @user123 some content')
        assert detect_retweet(entry) is True

    def test_not_retweet(self):
        """Test non-retweet."""
        entry = MockEntry(title='This is a normal tweet')
        assert detect_retweet(entry) is False


class TestDetectReply:
    """Tests for detect_reply."""

    def test_reply_link(self):
        """Test reply detection from link."""
        entry = MockEntry(link='https://x.com/user/status/123/rto/456')
        assert detect_reply(entry) is True

    def test_not_reply(self):
        """Test non-reply."""
        entry = MockEntry(link='https://x.com/user/status/123')
        assert detect_reply(entry) is False


class TestParseEntry:
    """Tests for parse_entry."""

    def test_parse_basic_entry(self):
        """Test parsing a basic entry."""
        entry = MockEntry(
            id='tag:twitter.com:123456',
            title='Test tweet',
            summary='This is the tweet content',
            link='https://x.com/user/status/123456',
            author='TestUser'
        )
        tweet = parse_entry(entry, 'testuser', 'TestUser')

        assert tweet.id == '123456'
        assert tweet.twitter_username == 'testuser'
        assert tweet.author == 'TestUser'
        assert 'tweet content' in tweet.content

    def test_parse_retweet(self):
        """Test parsing a retweet."""
        entry = MockEntry(
            id='tag:twitter.com:789',
            title='RT @original: Original tweet',
            summary='RT @original: Original tweet',
            link='https://x.com/user/status/789'
        )
        tweet = parse_entry(entry, 'testuser')
        assert tweet.is_retweet is True

    def test_parse_with_hashtags(self):
        """Test parsing tweet with hashtags."""
        entry = MockEntry(
            id='tag:twitter.com:111',
            title='#Python #Testing is great',
            summary='Loving <a href="#">#Python</a> and <a href="#">#Testing</a>!',
            link='https://x.com/user/status/111'
        )
        tweet = parse_entry(entry, 'testuser')
        assert '#Python' in tweet.content or 'Python' in tweet.content
