"""
Metrics API Router - Exposes API metrics and health status

Endpoints:
- GET /api/metrics - All API stats
- GET /api/metrics/{service} - Service-specific stats
- GET /api/metrics/errors - Recent errors
- GET /api/metrics/slow - Slow calls
- GET /api/health - Overall health check
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from infrastructure.api_metrics import api_metrics

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("")
async def get_all_metrics():
    """
    Get comprehensive metrics for all tracked API services
    
    Returns:
    - Uptime info
    - Per-service stats (success rate, response times, rate limits)
    - Total call counts
    """
    return api_metrics.get_all_stats()


@router.get("/summary")
async def get_metrics_summary():
    """
    Get a condensed summary for dashboard display
    """
    stats = api_metrics.get_all_stats()
    
    # Build summary
    services_summary = []
    for name, data in stats['services'].items():
        if data.get('total_calls', 0) > 0:
            services_summary.append({
                'service': name,
                'calls': data.get('total_calls', 0),
                'success_rate': data.get('success_rate', 0),
                'avg_ms': data.get('avg_response_ms', 0),
                'status': 'healthy' if data.get('success_rate', 0) > 95 else 'degraded' if data.get('success_rate', 0) > 80 else 'unhealthy'
            })
    
    # Sort by call count
    services_summary.sort(key=lambda x: x['calls'], reverse=True)
    
    return {
        'uptime': stats['uptime_human'],
        'total_calls': stats['total_api_calls'],
        'overall_success_rate': stats['overall_success_rate'],
        'services': services_summary
    }


@router.get("/service/{service}")
async def get_service_metrics(service: str):
    """
    Get detailed metrics for a specific service
    
    Services: supabase, alchemy, defillama, geckoterminal, thegraph, moralis, coingecko
    """
    stats = api_metrics.get_service_stats(service)
    if stats.get('status') == 'no_data':
        raise HTTPException(status_code=404, detail=f"No data for service: {service}")
    return stats


@router.get("/rate-limits")
async def get_rate_limits():
    """
    Get current rate limit status for all services
    """
    limits = {}
    for service in api_metrics.SERVICES.keys():
        limits[service] = api_metrics.check_rate_limit(service)
    return limits


@router.get("/errors")
async def get_recent_errors(limit: int = 20):
    """
    Get recent API errors
    """
    return {
        'count': len(api_metrics.get_recent_errors(limit)),
        'errors': api_metrics.get_recent_errors(limit)
    }


@router.get("/slow")
async def get_slow_calls(threshold_ms: float = 1000, limit: int = 20):
    """
    Get recent slow API calls (above threshold)
    """
    return {
        'threshold_ms': threshold_ms,
        'calls': api_metrics.get_slow_calls(threshold_ms, limit)
    }


@router.get("/health")
async def health_check():
    """
    Overall API health check
    """
    stats = api_metrics.get_all_stats()
    
    # Determine overall health
    health = "healthy"
    issues = []
    
    for name, data in stats['services'].items():
        if data.get('total_calls', 0) > 10:  # Only check if we have data
            success_rate = data.get('success_rate', 100)
            if success_rate < 80:
                health = "unhealthy"
                issues.append(f"{name}: {success_rate}% success rate")
            elif success_rate < 95:
                if health == "healthy":
                    health = "degraded"
                issues.append(f"{name}: {success_rate}% success rate")
            
            # Check average response time
            avg_ms = data.get('avg_response_ms', 0)
            if avg_ms > 5000:
                if health == "healthy":
                    health = "degraded"
                issues.append(f"{name}: {avg_ms:.0f}ms avg response")
    
    return {
        'status': health,
        'uptime': stats['uptime_human'],
        'total_calls': stats['total_api_calls'],
        'overall_success_rate': stats['overall_success_rate'],
        'issues': issues if issues else None
    }


@router.post("/persist")
async def persist_metrics():
    """
    Persist current metrics snapshot to Supabase
    """
    success = await api_metrics.persist_to_supabase()
    return {'persisted': success}
