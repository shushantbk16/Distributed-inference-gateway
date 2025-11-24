import pytest
from unittest.mock import MagicMock, patch
import json
import sys

# Mock sentence-transformers as missing
with patch.dict(sys.modules, {'sentence_transformers': None}):
    from src.cache.semantic_cache import SemanticCache

class TestCacheFallback:
    @pytest.fixture
    def mock_redis(self):
        return MagicMock()

    @pytest.fixture
    def cache(self, mock_redis):
        # Initialize cache with mocked Redis
        cache = SemanticCache(redis_url="redis://localhost:6379")
        cache.redis_client = mock_redis
        # Force model to None to simulate missing dependency
        cache.model = None
        return cache

    def test_init_without_sentence_transformers(self, cache):
        """Test that cache initializes correctly without sentence-transformers."""
        assert cache.model is None
        # Should still have redis client
        assert cache.redis_client is not None

    def test_set_exact_match(self, cache, mock_redis):
        """Test setting a value uses exact match key."""
        prompt = "test prompt"
        provider = "test_provider"
        response = {"text": "response"}
        
        # Call set
        result = cache.set(prompt, provider, response)
        
        assert result is True
        # Verify redis setex was called
        mock_redis.setex.assert_called_once()
        
        # Verify key format (should contain 'exact')
        call_args = mock_redis.setex.call_args
        key = call_args[0][0]
        assert "exact" in key
        assert f"cache:{provider}:exact:" in key

    def test_get_exact_match_hit(self, cache, mock_redis):
        """Test getting a value uses exact match key."""
        prompt = "test prompt"
        provider = "test_provider"
        expected_response = {"text": "response"}
        
        # Setup mock return value
        mock_redis.get.return_value = json.dumps(expected_response).encode('utf-8')
        
        # Call get
        result = cache.get(prompt, provider)
        
        assert result == expected_response
        # Verify redis get was called
        mock_redis.get.assert_called_once()
        
        # Verify key format
        call_args = mock_redis.get.call_args
        key = call_args[0][0]
        assert "exact" in key

    def test_get_exact_match_miss(self, cache, mock_redis):
        """Test cache miss with exact match."""
        prompt = "test prompt"
        provider = "test_provider"
        
        # Setup mock return value (None for miss)
        mock_redis.get.return_value = None
        
        # Call get
        result = cache.get(prompt, provider)
        
        assert result is None
