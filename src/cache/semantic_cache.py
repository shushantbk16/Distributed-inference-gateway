"""Semantic caching layer using Redis and sentence embeddings."""
import hashlib
import json
import redis
from typing import Optional, Dict, Any, List
import numpy as np
from src.utils.logger import setup_logger
from src.config import settings

# Optional import for sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False

logger = setup_logger(__name__)


class SemanticCache:
    """
    Semantic cache using Redis and sentence embeddings.
    
    Caches LLM responses and retrieves them based on semantic similarity
    rather than exact string matching. Production-grade optimization.
    
    Falls back to exact match caching if sentence-transformers is not available.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        similarity_threshold: float = 0.95,
        ttl: int = 3600
    ):
        self.init_error = None
        """
        Initialize semantic cache.
        
        Args:
            redis_url: Redis connection URL
            similarity_threshold: Cosine similarity threshold (0.95 = 95% similar)
            ttl: Time to live in seconds (default 1 hour)
        """
        try:
            kwargs = {"decode_responses": False}
            if redis_url.startswith("rediss://"):
                kwargs["ssl_cert_reqs"] = None
            
            self.redis_client = redis.from_url(redis_url, **kwargs)
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_url}")
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.redis_client = None
            self.init_error = str(e)
        
        self.similarity_threshold = similarity_threshold
        self.ttl = ttl
        
        # Load sentence transformer model (lightweight)
        self.model = None
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')  # 80MB, fast
                logger.info("Loaded sentence transformer model")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
        else:
            logger.warning("sentence-transformers not installed. Semantic caching disabled (fallback to exact match).")
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text."""
        if not self.model:
            return None
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def get(self, prompt: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response for semantically similar prompt.
        
        Args:
            prompt: User prompt
            provider: LLM provider name
            
        Returns:
            Cached response if found, None otherwise
        """
        if not self.redis_client:
            return None
        
        try:
            # 1. Try Exact Match First (Fastest)
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
            exact_key = f"cache:{provider}:exact:{prompt_hash}"
            
            response_bytes = self.redis_client.get(exact_key)
            if response_bytes:
                response = json.loads(response_bytes.decode('utf-8'))
                logger.info(f"Cache HIT (Exact) for {provider}")
                return response

            # 2. Try Semantic Match (if enabled)
            if self.model:
                # Get embedding for current prompt
                prompt_embedding = self._get_embedding(prompt)
                if prompt_embedding is None:
                    return None
                
                # Search for similar cached prompts
                pattern = f"cache:{provider}:semantic:*"
                keys = self.redis_client.keys(pattern)
                
                best_match = None
                best_similarity = 0.0
                
                for key in keys:
                    try:
                        # Get cached embedding
                        cached_embedding_bytes = self.redis_client.hget(key, b"embedding")
                        if not cached_embedding_bytes:
                            continue
                        
                        cached_embedding = np.frombuffer(cached_embedding_bytes, dtype=np.float32)
                        
                        # Calculate similarity
                        similarity = self._cosine_similarity(prompt_embedding, cached_embedding)
                        
                        if similarity > best_similarity and similarity >= self.similarity_threshold:
                            best_similarity = similarity
                            best_match = key
                    
                    except Exception as e:
                        logger.warning(f"Error checking cache key {key}: {e}")
                        continue
                
                if best_match:
                    # Cache hit!
                    response_bytes = self.redis_client.hget(best_match, b"response")
                    if response_bytes:
                        response = json.loads(response_bytes.decode('utf-8'))
                        logger.info(
                            f"Cache HIT (Semantic) for {provider} "
                            f"(similarity: {best_similarity:.3f})"
                        )
                        return response
            
            logger.debug(f"Cache MISS for {provider}")
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(
        self,
        prompt: str,
        provider: str,
        response: Dict[str, Any]
    ) -> bool:
        """
        Cache response for prompt.
        
        Args:
            prompt: User prompt
            provider: LLM provider name
            response: LLM response to cache
            
        Returns:
            True if cached successfully
        """
        if not self.redis_client:
            return False
        
        try:
            # 1. Store Exact Match
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
            exact_key = f"cache:{provider}:exact:{prompt_hash}"
            
            self.redis_client.setex(
                exact_key,
                self.ttl,
                json.dumps(response).encode('utf-8')
            )
            
            # 2. Store Semantic Match (if enabled)
            if self.model:
                # Generate embedding
                embedding = self._get_embedding(prompt)
                if embedding is not None:
                    # Create unique key for semantic entry
                    # We use a truncated hash just to distinguish entries, 
                    # but semantic search iterates keys anyway.
                    semantic_key = f"cache:{provider}:semantic:{prompt_hash[:8]}"
                    
                    # Store in Redis with hash
                    pipe = self.redis_client.pipeline()
                    pipe.hset(semantic_key, b"prompt", prompt.encode('utf-8'))
                    pipe.hset(semantic_key, b"embedding", embedding.astype(np.float32).tobytes())
                    pipe.hset(semantic_key, b"response", json.dumps(response).encode('utf-8'))
                    pipe.expire(semantic_key, self.ttl)
                    pipe.execute()
            
            logger.info(f"Cached response for {provider}")
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.redis_client:
            return {"enabled": False, "error": self.init_error}
        
        try:
            info = self.redis_client.info("stats")
            total_keys = self.redis_client.dbsize()
            
            return {
                "enabled": True,
                "semantic_enabled": self.model is not None,
                "total_keys": total_keys,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "similarity_threshold": self.similarity_threshold,
                "ttl_seconds": self.ttl
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {"enabled": False, "error": str(e)}
    
    def clear(self, provider: Optional[str] = None):
        """
        Clear cache.
        
        Args:
            provider: If specified, only clear cache for this provider
        """
        if not self.redis_client:
            return
        
        try:
            if provider:
                pattern = f"cache:{provider}:*"
            else:
                pattern = "cache:*"
            
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")


# Global cache instance
_cache_instance = None


def get_cache() -> SemanticCache:
    """Get global cache instance (singleton)."""
    global _cache_instance
    if _cache_instance is None:
        redis_url = getattr(settings, 'redis_url', 'redis://localhost:6379')
        _cache_instance = SemanticCache(redis_url=redis_url)
    return _cache_instance
