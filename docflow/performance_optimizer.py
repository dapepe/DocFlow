"""
Performance Optimization System
Provides caching, request batching, and performance monitoring
"""
import time
import hashlib
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)

class PerformanceCache:
    """Thread-safe LRU cache for model responses"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def _generate_key(self, text: str, model_name: str, schema: Dict[str, Any]) -> str:
        """Generate cache key from input parameters"""
        content = f"{text[:500]}:{model_name}:{json.dumps(schema, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, model_name: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired"""
        key = self._generate_key(text, model_name, schema)
        
        with self.lock:
            if key in self.cache:
                cached_time, result = self.cache[key]
                
                # Check if expired
                if datetime.now() - cached_time > timedelta(seconds=self.ttl_seconds):
                    del self.cache[key]
                    del self.access_times[key]
                    return None
                
                # Update access time for LRU
                self.access_times[key] = datetime.now()
                logger.debug(f"Cache hit for key: {key[:8]}...")
                return result
            
            return None
    
    def set(self, text: str, model_name: str, schema: Dict[str, Any], result: Dict[str, Any]):
        """Store result in cache with LRU eviction"""
        key = self._generate_key(text, model_name, schema)
        
        with self.lock:
            # Evict oldest entries if cache is full
            if len(self.cache) >= self.max_size:
                self._evict_oldest()
            
            self.cache[key] = (datetime.now(), result)
            self.access_times[key] = datetime.now()
            logger.debug(f"Cached result for key: {key[:8]}...")
    
    def _evict_oldest(self):
        """Evict least recently used entries"""
        if not self.access_times:
            return
        
        # Find oldest entries (evict 10% of cache)
        evict_count = max(1, self.max_size // 10)
        oldest_keys = sorted(self.access_times.items(), key=lambda x: x[1])[:evict_count]
        
        for key, _ in oldest_keys:
            del self.cache[key]
            del self.access_times[key]
        
        logger.debug(f"Evicted {len(oldest_keys)} cache entries")
    
    def clear(self):
        """Clear all cached entries"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
        logger.info("Performance cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds,
                'oldest_entry': min(self.access_times.values()) if self.access_times else None,
                'newest_entry': max(self.access_times.values()) if self.access_times else None
            }

class PerformanceMonitor:
    """Monitor and track performance metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.lock = threading.RLock()
    
    def record_request(self, model_name: str, duration: float, success: bool, text_length: int):
        """Record request metrics"""
        with self.lock:
            if model_name not in self.metrics:
                self.metrics[model_name] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'total_duration': 0.0,
                    'min_duration': float('inf'),
                    'max_duration': 0.0,
                    'total_text_length': 0,
                    'last_request': None
                }
            
            stats = self.metrics[model_name]
            stats['total_requests'] += 1
            stats['total_text_length'] += text_length
            stats['last_request'] = datetime.now()
            
            if success:
                stats['successful_requests'] += 1
                stats['total_duration'] += duration
                stats['min_duration'] = min(stats['min_duration'], duration)
                stats['max_duration'] = max(stats['max_duration'], duration)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        with self.lock:
            results = {}
            for model_name, stats in self.metrics.items():
                total_requests = stats['total_requests']
                successful_requests = stats['successful_requests']
                
                results[model_name] = {
                    'total_requests': total_requests,
                    'successful_requests': successful_requests,
                    'success_rate': successful_requests / total_requests if total_requests > 0 else 0,
                    'average_duration': stats['total_duration'] / successful_requests if successful_requests > 0 else 0,
                    'min_duration': stats['min_duration'] if stats['min_duration'] != float('inf') else 0,
                    'max_duration': stats['max_duration'],
                    'average_text_length': stats['total_text_length'] / total_requests if total_requests > 0 else 0,
                    'last_request': stats['last_request'].isoformat() if stats['last_request'] else None
                }
            
            return results

class BatchProcessor:
    """Process multiple documents concurrently"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def process_batch(self, documents: List[Dict[str, Any]], 
                     processor_func: Callable, **kwargs) -> List[Dict[str, Any]]:
        """Process multiple documents concurrently"""
        start_time = time.time()
        
        # Submit all tasks
        futures = []
        for doc in documents:
            future = self.executor.submit(processor_func, **doc, **kwargs)
            futures.append((doc, future))
        
        # Collect results
        results = []
        completed = 0
        
        for doc, future in futures:
            try:
                result = future.result(timeout=300)  # 5 minute timeout per document
                result['batch_processing'] = True
                result['document_id'] = doc.get('id', f'doc_{completed}')
                results.append(result)
                completed += 1
                
            except Exception as e:
                logger.error(f"Batch processing failed for document {doc.get('id', 'unknown')}: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'document_id': doc.get('id', f'doc_{completed}'),
                    'batch_processing': True
                })
                completed += 1
        
        total_time = time.time() - start_time
        logger.info(f"Batch processed {len(documents)} documents in {total_time:.2f}s")
        
        return results

# Global instances
performance_cache = PerformanceCache()
performance_monitor = PerformanceMonitor()
batch_processor = BatchProcessor()

def cached_model_response(func):
    """Decorator to cache model responses"""
    @wraps(func)
    def wrapper(self, text: str, image_path: Optional[str] = None, **kwargs):
        # Try cache first (only for text-based requests to avoid image caching complexity)
        if image_path is None:
            cached_result = performance_cache.get(text, self.__class__.__name__, self.schema)
            if cached_result:
                return cached_result
        
        # Execute function with performance monitoring
        start_time = time.time()
        try:
            result = func(self, text, image_path, **kwargs)
            duration = time.time() - start_time
            success = result.get('success', False)
            
            # Cache successful results (text-only)
            if success and image_path is None:
                performance_cache.set(text, self.__class__.__name__, self.schema, result)
            
            # Record metrics
            performance_monitor.record_request(
                model_name=self.__class__.__name__,
                duration=duration,
                success=success,
                text_length=len(text)
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            performance_monitor.record_request(
                model_name=self.__class__.__name__,
                duration=duration,
                success=False,
                text_length=len(text)
            )
            raise
    
    return wrapper

def optimize_text_extraction(text: str, max_length: int = 50000) -> str:
    """Optimize text for model processing"""
    if len(text) <= max_length:
        return text
    
    # Smart truncation - try to preserve important sections
    lines = text.split('\n')
    
    # Priority: keep beginning and end, remove middle repetitive content
    if len(lines) > 100:
        # Keep first 30% and last 20%, sample from middle
        keep_start = int(len(lines) * 0.3)
        keep_end = int(len(lines) * 0.2)
        middle_sample = lines[keep_start:-keep_end:3]  # Every 3rd line from middle
        
        optimized_lines = lines[:keep_start] + ['... [content truncated] ...'] + middle_sample + ['... [content truncated] ...'] + lines[-keep_end:]
        optimized_text = '\n'.join(optimized_lines)
    else:
        optimized_text = text
    
    # Final length check
    if len(optimized_text) > max_length:
        optimized_text = optimized_text[:max_length] + '... [truncated]'
    
    logger.debug(f"Text optimized from {len(text)} to {len(optimized_text)} characters")
    return optimized_text

def get_performance_report() -> Dict[str, Any]:
    """Get comprehensive performance report"""
    return {
        'cache_stats': performance_cache.get_stats(),
        'model_stats': performance_monitor.get_stats(),
        'timestamp': datetime.now().isoformat(),
        'optimization_features': [
            'Response caching with LRU eviction',
            'Concurrent batch processing',
            'Performance monitoring and metrics',
            'Smart text truncation',
            'Model-specific optimizations'
        ]
    }