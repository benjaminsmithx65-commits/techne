"""
API Metrics Tracker - Comprehensive monitoring for all external API calls

Tracks:
- Request counts (success/error)
- Response times
- Rate limit status
- Error details

Supports:
- Supabase
- Alchemy RPC
- DefiLlama
- GeckoTerminal
- The Graph
- Moralis
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class APICallMetric:
    """Single API call record"""
    service: str
    endpoint: str
    status: str  # 'success', 'error', 'timeout', 'rate_limited'
    response_time_ms: float
    timestamp: str
    error_message: Optional[str] = None
    status_code: Optional[int] = None


@dataclass
class ServiceMetrics:
    """Aggregated metrics for a service"""
    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    timeout_count: int = 0
    rate_limit_count: int = 0
    avg_response_time_ms: float = 0
    min_response_time_ms: float = float('inf')
    max_response_time_ms: float = 0
    last_error: Optional[str] = None
    last_error_time: Optional[str] = None
    last_success_time: Optional[str] = None
    
    # Track recent response times for rolling average
    _recent_times: list = field(default_factory=list)


class APIMetricsTracker:
    """
    Centralized API metrics tracking
    
    Usage:
        metrics = APIMetricsTracker()
        
        # Track a call
        start = time.time()
        response = await http_client.get(url)
        metrics.record_call('defillama', '/yields', 'success', time.time() - start)
        
        # Get metrics
        stats = metrics.get_all_stats()
    """
    
    # Known API services and their rate limits
    SERVICES = {
        'supabase': {'rate_limit': 1000, 'window': 60},  # per minute
        'alchemy': {'rate_limit': 330, 'window': 1},      # per second (free tier)
        'defillama': {'rate_limit': 300, 'window': 60},
        'geckoterminal': {'rate_limit': 30, 'window': 60},
        'thegraph': {'rate_limit': 1000, 'window': 60},
        'moralis': {'rate_limit': 25, 'window': 1},        # per second (free tier)
        'coingecko': {'rate_limit': 30, 'window': 60},
    }
    
    def __init__(self):
        self._metrics: Dict[str, ServiceMetrics] = defaultdict(ServiceMetrics)
        self._recent_calls: list = []  # Last 1000 calls for detailed logs
        self._max_recent_calls = 1000
        self._start_time = datetime.utcnow()
        
        # Rate limit windows
        self._rate_windows: Dict[str, list] = defaultdict(list)
        
        logger.info("[APIMetrics] Tracker initialized")
    
    def record_call(
        self,
        service: str,
        endpoint: str,
        status: str,
        response_time_s: float,
        error_message: str = None,
        status_code: int = None
    ):
        """Record an API call"""
        response_time_ms = response_time_s * 1000
        now = datetime.utcnow()
        
        # Create call record
        call = APICallMetric(
            service=service.lower(),
            endpoint=endpoint,
            status=status,
            response_time_ms=round(response_time_ms, 2),
            timestamp=now.isoformat(),
            error_message=error_message,
            status_code=status_code
        )
        
        # Store in recent calls
        self._recent_calls.append(asdict(call))
        if len(self._recent_calls) > self._max_recent_calls:
            self._recent_calls.pop(0)
        
        # Update service metrics
        m = self._metrics[service.lower()]
        m.total_calls += 1
        
        if status == 'success':
            m.success_count += 1
            m.last_success_time = now.isoformat()
        elif status == 'error':
            m.error_count += 1
            m.last_error = error_message
            m.last_error_time = now.isoformat()
        elif status == 'timeout':
            m.timeout_count += 1
            m.last_error = 'Timeout'
            m.last_error_time = now.isoformat()
        elif status == 'rate_limited':
            m.rate_limit_count += 1
            m.last_error = 'Rate limited'
            m.last_error_time = now.isoformat()
        
        # Update response times
        m._recent_times.append(response_time_ms)
        if len(m._recent_times) > 100:
            m._recent_times.pop(0)
        
        m.avg_response_time_ms = sum(m._recent_times) / len(m._recent_times)
        m.min_response_time_ms = min(m.min_response_time_ms, response_time_ms)
        m.max_response_time_ms = max(m.max_response_time_ms, response_time_ms)
        
        # Update rate limit window
        self._rate_windows[service.lower()].append(now)
        
        # Log slow calls
        if response_time_ms > 2000:
            logger.warning(f"[APIMetrics] Slow call: {service} {endpoint} took {response_time_ms:.0f}ms")
        
        # Persist to Supabase (fire-and-forget, non-blocking)
        try:
            import asyncio
            from infrastructure.supabase_client import supabase
            if supabase.is_available:
                asyncio.create_task(supabase.log_api_call(
                    service=service,
                    endpoint=endpoint,
                    status=status,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    status_code=status_code
                ))
        except Exception:
            pass  # Don't fail metrics tracking if Supabase fails
    
    def check_rate_limit(self, service: str) -> Dict[str, Any]:
        """Check current rate limit status for a service"""
        service = service.lower()
        config = self.SERVICES.get(service, {'rate_limit': 100, 'window': 60})
        window_seconds = config['window']
        limit = config['rate_limit']
        
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Clean old entries
        self._rate_windows[service] = [
            t for t in self._rate_windows[service] if t > cutoff
        ]
        
        current_count = len(self._rate_windows[service])
        remaining = max(0, limit - current_count)
        
        return {
            'service': service,
            'limit': limit,
            'window_seconds': window_seconds,
            'current_count': current_count,
            'remaining': remaining,
            'percentage_used': round((current_count / limit) * 100, 1) if limit > 0 else 0,
            'is_limited': current_count >= limit
        }
    
    def get_service_stats(self, service: str) -> Dict[str, Any]:
        """Get stats for a specific service"""
        m = self._metrics.get(service.lower())
        if not m:
            return {'service': service, 'status': 'no_data'}
        
        rate_status = self.check_rate_limit(service)
        
        return {
            'service': service,
            'total_calls': m.total_calls,
            'success_count': m.success_count,
            'error_count': m.error_count,
            'timeout_count': m.timeout_count,
            'rate_limit_count': m.rate_limit_count,
            'success_rate': round((m.success_count / m.total_calls) * 100, 1) if m.total_calls > 0 else 0,
            'avg_response_ms': round(m.avg_response_time_ms, 1),
            'min_response_ms': round(m.min_response_time_ms, 1) if m.min_response_time_ms != float('inf') else 0,
            'max_response_ms': round(m.max_response_time_ms, 1),
            'last_error': m.last_error,
            'last_error_time': m.last_error_time,
            'last_success_time': m.last_success_time,
            'rate_limit': rate_status
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive stats for all services"""
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        
        services = {}
        total_calls = 0
        total_errors = 0
        
        for service_name in set(list(self._metrics.keys()) + list(self.SERVICES.keys())):
            stats = self.get_service_stats(service_name)
            services[service_name] = stats
            total_calls += stats.get('total_calls', 0)
            total_errors += stats.get('error_count', 0)
        
        return {
            'uptime_seconds': round(uptime, 0),
            'uptime_human': str(timedelta(seconds=int(uptime))),
            'started_at': self._start_time.isoformat(),
            'total_api_calls': total_calls,
            'total_errors': total_errors,
            'overall_success_rate': round(((total_calls - total_errors) / total_calls) * 100, 1) if total_calls > 0 else 100,
            'services': services
        }
    
    def get_recent_errors(self, limit: int = 20) -> list:
        """Get recent error calls"""
        errors = [
            c for c in reversed(self._recent_calls) 
            if c['status'] in ('error', 'timeout', 'rate_limited')
        ]
        return errors[:limit]
    
    def get_slow_calls(self, threshold_ms: float = 1000, limit: int = 20) -> list:
        """Get recent slow calls"""
        slow = [
            c for c in reversed(self._recent_calls) 
            if c['response_time_ms'] > threshold_ms
        ]
        return slow[:limit]
    
    async def persist_to_supabase(self):
        """Persist current metrics snapshot to Supabase (called every 5 min)"""
        try:
            from infrastructure.supabase_client import supabase
            if not supabase.is_available:
                logger.debug("[APIMetrics] Supabase not available for persistence")
                return False
            
            stats = self.get_all_stats()
            saved_count = 0
            
            # Save snapshot for each service with data
            for service, data in stats['services'].items():
                if data.get('total_calls', 0) > 0:
                    m = self._metrics.get(service)
                    if m:
                        await supabase.save_api_metrics_snapshot(
                            service=service,
                            total_calls=m.total_calls,
                            success_count=m.success_count,
                            error_count=m.error_count,
                            timeout_count=m.timeout_count,
                            rate_limit_count=m.rate_limit_count,
                            success_rate=data.get('success_rate', 0),
                            avg_response_ms=m.avg_response_time_ms,
                            min_response_ms=m.min_response_time_ms,
                            max_response_ms=m.max_response_time_ms,
                            last_error=m.last_error,
                            last_error_time=m.last_error_time
                        )
                        saved_count += 1
            
            logger.info(f"[APIMetrics] Persisted {saved_count} service snapshots to Supabase")
            return True
        except Exception as e:
            logger.error(f"[APIMetrics] Supabase persist failed: {e}")
            return False
    
    async def log_error_to_supabase(
        self,
        service: str,
        endpoint: str,
        status: str,
        response_time_ms: float,
        error_message: str = None,
        status_code: int = None
    ):
        """Log an API error to Supabase in real-time"""
        try:
            from infrastructure.supabase_client import supabase
            if supabase.is_available:
                await supabase.log_api_error(
                    service=service,
                    endpoint=endpoint,
                    status=status,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    status_code=status_code
                )
        except Exception as e:
            logger.debug(f"[APIMetrics] Error logging to Supabase failed: {e}")


# Global instance
api_metrics = APIMetricsTracker()


# Decorator for easy tracking
def track_api_call(service: str):
    """Decorator to automatically track API calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start = time.time()
            endpoint = kwargs.get('endpoint', func.__name__)
            
            try:
                result = await func(*args, **kwargs)
                api_metrics.record_call(
                    service=service,
                    endpoint=endpoint,
                    status='success',
                    response_time_s=time.time() - start
                )
                return result
            except asyncio.TimeoutError:
                api_metrics.record_call(
                    service=service,
                    endpoint=endpoint,
                    status='timeout',
                    response_time_s=time.time() - start,
                    error_message='Request timeout'
                )
                raise
            except Exception as e:
                error_msg = str(e)
                status = 'rate_limited' if '429' in error_msg or 'rate' in error_msg.lower() else 'error'
                api_metrics.record_call(
                    service=service,
                    endpoint=endpoint,
                    status=status,
                    response_time_s=time.time() - start,
                    error_message=error_msg[:200]
                )
                raise
        
        return wrapper
    return decorator


# Helper context manager
class APICallTimer:
    """Context manager for tracking API calls"""
    
    def __init__(self, service: str, endpoint: str = ''):
        self.service = service
        self.endpoint = endpoint
        self.start = None
        self.status = 'success'
        self.error_message = None
        self.status_code = None
    
    def __enter__(self):
        self.start = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start
        
        if exc_type:
            error_msg = str(exc_val)
            if '429' in error_msg or 'rate' in error_msg.lower():
                self.status = 'rate_limited'
            elif 'timeout' in error_msg.lower():
                self.status = 'timeout'
            else:
                self.status = 'error'
            self.error_message = error_msg[:200]
        
        api_metrics.record_call(
            service=self.service,
            endpoint=self.endpoint,
            status=self.status,
            response_time_s=duration,
            error_message=self.error_message,
            status_code=self.status_code
        )
        
        return False  # Don't suppress exceptions
