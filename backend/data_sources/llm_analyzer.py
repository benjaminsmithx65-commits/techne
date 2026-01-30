"""
LLM Pool Analyzer
Tiered LLM analysis for DeFi pool risk assessment.

Tier 1: Groq (Llama) - Fast, cheap, routine analysis
Tier 2: Gemini - Expensive, critical decisions only
"""
import asyncio
import os
import httpx
from typing import Dict, Optional
from datetime import datetime

# Import pool enricher for DefiLlama data
try:
    from data_sources.pool_enricher import enrich_pool
except ImportError:
    from pool_enricher import enrich_pool

# Try to load dotenv at import
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API endpoints
GROQ_API = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"


class LLMAnalyzer:
    """
    Tiered LLM analysis for DeFi pools.
    
    Usage:
        analyzer = LLMAnalyzer()
        result = await analyzer.analyze_pool({
            "symbol": "WETH-USDC",
            "apy": 150,
            "tvl": 5000000,
            "protocol": "aerodrome"
        })
    """
    
    def __init__(self):
        # Load API keys (after dotenv is loaded)
        # Groq keys as ordered list for failover
        self.groq_keys = [
            os.getenv("GROQ_API_KEY", ""),
            os.getenv("GROQ_API_KEY_FALLBACK", ""),
            os.getenv("GROQ_API_KEY_FALLBACK_2", ""),
            os.getenv("GROQ_API_KEY_FALLBACK_3", ""),  # Ready for future
        ]
        # Filter out empty keys
        self.groq_keys = [k for k in self.groq_keys if k]
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.cache: Dict[str, Dict] = {}
        self.cache_ttl = 3600  # 1 hour
        
    async def analyze_pool(self, pool: Dict, use_gemini: bool = False, trading_style: str = "moderate") -> Dict:
        """
        Analyze pool risk using LLM.
        
        Args:
            pool: Pool data with symbol, apy, tvl, protocol
            use_gemini: Force Gemini for critical analysis (default: Groq)
            trading_style: 'conservative', 'moderate', or 'aggressive' - affects evaluation strictness
            
        Returns:
            {
                "risk_score": 1-10,
                "risk_factors": [...],
                "recommendation": "INVEST" | "CAUTION" | "AVOID",
                "reasoning": str,
                "llm_provider": "groq" | "gemini"
            }
        """
        # Cache key includes trading style
        cache_key = f"{pool.get('symbol', '')}_{pool.get('apy', 0)}_{trading_style}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now().timestamp() - cached["time"]) < self.cache_ttl:
                return cached["result"]
        
        # Enrich pool with DefiLlama data (APY history, age, volume, IL risk)
        enriched_pool = await enrich_pool(pool)
        
        # Build prompt with enriched data and trading style
        prompt = self._build_analysis_prompt(enriched_pool, trading_style)
        
        # =====================================================
        # TIERING: Groq (all keys) → Gemini → Rules
        # =====================================================
        # Try all Groq keys in order, then Gemini as last resort
        # =====================================================
        
        result = None
        
        # Try all Groq keys in order
        for i, key in enumerate(self.groq_keys):
            result = await self._call_groq(prompt, key)
            if result and result.get("risk_score", 0) > 0:
                result["llm_provider"] = f"groq_{i+1}" if i > 0 else "groq"
                break
            result = None  # Reset for next attempt
        
        # Gemini ONLY if ALL Groq keys failed
        if result is None and self.gemini_key:
            result = await self._call_gemini(prompt)
            if result:
                result["llm_provider"] = "gemini"
        
        # Fallback to rules if ALL LLMs failed
        if result is None:
            result = self._rule_based_analysis(pool)
            result["llm_provider"] = "rules"
        
        # Cache
        self.cache[cache_key] = {"result": result, "time": datetime.now().timestamp()}
        
        return result
    
    def _build_analysis_prompt(self, pool: Dict, trading_style: str = "moderate") -> str:
        """Build enriched analysis prompt for LLM with style-dependent criteria"""
        
        # Define thresholds per trading style
        style_thresholds = {
            "conservative": {
                "min_tvl": "$1M", "max_apy": 100, "min_age": 14, 
                "tokens": "stablecoins and blue chips only", "audited": "required"
            },
            "moderate": {
                "min_tvl": "$500k", "max_apy": 300, "min_age": 7,
                "tokens": "stablecoins and major alts", "audited": "preferred"
            },
            "aggressive": {
                "min_tvl": "$100k", "max_apy": 9999, "min_age": 0,
                "tokens": "any including memecoins/alts", "audited": "not required"
            }
        }
        thresholds = style_thresholds.get(trading_style, style_thresholds["moderate"])
        
        # Core data
        symbol = pool.get("symbol", "Unknown")
        apy = pool.get("apy", 0)
        tvl = pool.get("tvl", 0) / 1e6 if pool.get("tvl", 0) > 0 else 0
        protocol = pool.get("protocol", "unknown")
        pool_type = pool.get("pool_type", "unknown")
        
        # Enhanced data
        volatility = pool.get("volatility_7d", 0)
        il_estimate = pool.get("il_estimate", 0)
        volume_24h = pool.get("volume_24h", 0) / 1e6 if pool.get("volume_24h", 0) > 0 else 0
        fee_tier = pool.get("fee", pool.get("fee_tier", 0))
        pool_address = pool.get("address", pool.get("id", "unknown"))[:10] + "..." if pool.get("address") or pool.get("id") else "unknown"
        token0 = pool.get("token0_symbol", pool.get("token0", {}).get("symbol", "?"))
        token1 = pool.get("token1_symbol", pool.get("token1", {}).get("symbol", "?"))
        
        # Trust signals
        is_verified = pool.get("is_verified", pool.get("verified", "unknown"))
        holder_count = pool.get("holder_count", 0)
        pool_age_days = pool.get("age_days", pool.get("created_days_ago", 0))
        reserve0 = pool.get("reserve0", 0)
        reserve1 = pool.get("reserve1", 0)
        
        # DefiLlama enriched data
        apy_mean_30d = pool.get("apy_mean_30d", 0)
        il_risk_llama = pool.get("il_risk", "unknown")  # DefiLlama IL assessment
        prediction = pool.get("prediction", "unknown")  # DefiLlama trend prediction
        
        # Previous APY for stability check
        apy_7d_ago = pool.get("apy_7d_ago", pool.get("previous_apy", 0))
        apy_change = ((apy - apy_7d_ago) / apy_7d_ago * 100) if apy_7d_ago > 0 else 0
        
        return f"""You are a veteran DeFi trader with sharp intuition. Analyze this pool like you're protecting your own money.

POOL: {symbol} on {protocol}
Tokens: {token0}/{token1} | Type: {pool_type}

NUMBERS:
• APY: {apy:.1f}% (7d ago: {apy_7d_ago:.1f}%, 30d avg: {apy_mean_30d:.1f}%)
• TVL: ${tvl:.2f}M | Volume 24h: ${volume_24h:.2f}M
• Age: {pool_age_days} days | Fee: {fee_tier}%

SIGNALS:
• DefiLlama IL Risk: {il_risk_llama}
• DefiLlama Trend: {prediction}
• 7d Volatility: {volatility:.1f}%

USER STYLE: {trading_style.upper()}
Thresholds: TVL>{thresholds['min_tvl']}, APY<{thresholds['max_apy']}%, Age>{thresholds['min_age']}d

🔍 USE YOUR INTUITION - CHECK FOR:
1. RUG SIGNALS: New pool + insane APY + low TVL = honeypot?
2. APY SUSTAINABILITY: Is {apy:.0f}% realistic for {protocol}? Compare to 30d avg
3. SMART MONEY: High volume/TVL = real usage or wash trading?
4. TOKEN QUALITY: {token0}/{token1} - blue chips or shitcoins?
5. PROTOCOL TRUST: {protocol} track record? Exploits? Audits?
6. TIMING: APY spiking/dumping? Why now?
7. GUT FEELING: Would YOU put money here with {trading_style} mindset?

RESPOND JSON ONLY:
{{"risk_score": 1-10, "risk_factors": ["max 3 key factors"], "recommendation": "INVEST|CAUTION|AVOID", "reasoning": "2-3 sentences - be specific, not generic"}}"""
    
    async def _call_groq(self, prompt: str, api_key: str = None) -> Dict:
        """Call Groq API (Llama)"""
        key = api_key or self.groq_key
        if not key:
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    GROQ_API,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {"role": "system", "content": "You are a DeFi risk analyst. Respond only in valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 500
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return self._parse_llm_response(content)
                else:
                    print(f"[LLM] Groq error: {resp.status_code}")
                    
        except Exception as e:
            print(f"[LLM] Groq exception: {e}")
        
        return self._default_response()
    
    async def _call_gemini(self, prompt: str) -> Dict:
        """Call Gemini API"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{GEMINI_API}?key={self.gemini_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": 300
                        }
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    return self._parse_llm_response(content)
                else:
                    print(f"[LLM] Gemini error: {resp.status_code}")
                    
        except Exception as e:
            print(f"[LLM] Gemini exception: {e}")
        
        return self._default_response()
    
    def _parse_llm_response(self, content: str) -> Dict:
        """Parse LLM JSON response"""
        import json
        try:
            # Clean response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            data = json.loads(content)
            return {
                "risk_score": int(data.get("risk_score", 5)),
                "risk_factors": data.get("risk_factors", []),
                "recommendation": data.get("recommendation", "CAUTION"),
                "reasoning": data.get("reasoning", "")
            }
        except Exception as e:
            print(f"[LLM] Parse error: {e}")
            return self._default_response()
    
    def _rule_based_analysis(self, pool: Dict) -> Dict:
        """Fallback rule-based analysis"""
        symbol = pool.get("symbol", "").upper()
        apy = pool.get("apy", 0)
        tvl = pool.get("tvl", 0)
        
        risk_score = 5
        risk_factors = []
        
        # APY check
        if apy > 500:
            risk_score += 3
            risk_factors.append("Extremely high APY (>500%)")
        elif apy > 200:
            risk_score += 1
            risk_factors.append("High APY (>200%)")
        
        # TVL check
        if tvl < 100000:
            risk_score += 2
            risk_factors.append("Low TVL (<$100k)")
        elif tvl > 10000000:
            risk_score -= 1
        
        # Pair check
        safe_tokens = ["USDC", "USDT", "DAI", "WETH", "ETH", "CBBTC", "WBTC"]
        has_safe = any(t in symbol for t in safe_tokens)
        if not has_safe:
            risk_score += 2
            risk_factors.append("No major tokens in pair")
        
        risk_score = max(1, min(10, risk_score))
        
        if risk_score <= 3:
            recommendation = "INVEST"
        elif risk_score <= 6:
            recommendation = "CAUTION"
        else:
            recommendation = "AVOID"
        
        return {
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "recommendation": recommendation,
            "reasoning": f"Rule-based analysis: score {risk_score}/10"
        }
    
    def _default_response(self) -> Dict:
        """Default response on error"""
        return {
            "risk_score": 5,
            "risk_factors": ["Analysis unavailable"],
            "recommendation": "CAUTION",
            "reasoning": "Could not complete analysis"
        }


# Singleton
llm_analyzer = LLMAnalyzer()


async def analyze_pool_risk(pool: Dict, critical: bool = False) -> Dict:
    """Quick function to analyze pool risk"""
    return await llm_analyzer.analyze_pool(pool, use_gemini=critical)


# Test
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    async def test():
        analyzer = LLMAnalyzer()
        
        pools = [
            {"symbol": "WETH-USDC", "apy": 45, "tvl": 50000000, "protocol": "aerodrome"},
            {"symbol": "DEGEN-WETH", "apy": 850, "tvl": 500000, "protocol": "aerodrome"},
            {"symbol": "SCAM-USDC", "apy": 9999, "tvl": 10000, "protocol": "unknown"},
        ]
        
        print("\n" + "="*60)
        print("LLM POOL ANALYZER TEST")
        print("="*60)
        
        for pool in pools:
            print(f"\n📊 Analyzing {pool['symbol']}...")
            result = await analyzer.analyze_pool(pool)
            print(f"   Risk Score: {result['risk_score']}/10")
            print(f"   Recommendation: {result['recommendation']}")
            print(f"   Factors: {', '.join(result['risk_factors'])}")
            print(f"   Reasoning: {result['reasoning']}")
            print(f"   Provider: {result['llm_provider']}")
    
    asyncio.run(test())
