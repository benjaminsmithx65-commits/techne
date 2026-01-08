/**
 * Techne Protocol - Verify Pools Module
 * Verify any pool by address/URL and get risk analysis
 * Cost: 10 credits per verification
 */

const VerifyPools = {
    VERIFY_COST: 10,
    STORAGE_KEY: 'techne_verify_history',

    // Initialize module
    init() {
        this.bindEvents();
        this.loadHistory();
        this.updateCreditsDisplay();
        console.log('[VerifyPools] Module initialized');
    },

    // Bind UI events
    bindEvents() {
        const verifyBtn = document.getElementById('verifyPoolBtn');
        const input = document.getElementById('verifyPoolInput');

        if (verifyBtn) {
            verifyBtn.addEventListener('click', () => this.handleVerify());
        }

        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.handleVerify();
            });
        }
    },

    // Update credits display
    updateCreditsDisplay() {
        const costEl = document.getElementById('verifyCreditCost');
        if (costEl) {
            costEl.textContent = this.VERIFY_COST;
        }
    },

    // Handle verify button click
    async handleVerify() {
        const input = document.getElementById('verifyPoolInput');
        const address = input?.value?.trim();

        if (!address) {
            Toast?.show('Please enter a pool address or URL', 'warning');
            return;
        }

        // Check credits
        if (typeof CreditsManager !== 'undefined') {
            const credits = CreditsManager.getCredits();
            if (credits < this.VERIFY_COST) {
                Toast?.show(`Need ${this.VERIFY_COST} credits to verify. You have ${credits}.`, 'warning');
                CreditsManager.showBuyModal?.();
                return;
            }
        }

        // Show loading
        const btn = document.getElementById('verifyPoolBtn');
        const originalText = btn?.innerHTML;
        if (btn) {
            btn.innerHTML = '<span class="loading-spinner"></span> Verifying...';
            btn.disabled = true;
        }

        try {
            // Parse input to get pool identifier
            const poolId = this.parseInput(address);

            // Fetch pool data
            const poolData = await this.fetchPoolData(poolId);

            if (!poolData) {
                throw new Error('Pool not found');
            }

            // Deduct credits
            if (typeof CreditsManager !== 'undefined') {
                CreditsManager.setCredits(CreditsManager.getCredits() - this.VERIFY_COST);
                Toast?.show(`✓ Used ${this.VERIFY_COST} credits`, 'success');
            }

            // Save to history
            this.saveToHistory(poolData);

            // Normalize data for PoolDetailModal (DefiLlama uses different field names)
            const normalizedPool = this.normalizePoolData(poolData);

            // Show modal
            this.showVerificationModal(normalizedPool);

            // Clear input
            if (input) input.value = '';

        } catch (error) {
            console.error('[VerifyPools] Error:', error);
            Toast?.show(`Verification failed: ${error.message}`, 'error');
        } finally {
            if (btn) {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }
    },

    // Parse input (address or URL) - supports multiple protocols
    parseInput(input) {
        console.log('[VerifyPools] Parsing input:', input);

        // DefiLlama URL: https://defillama.com/yields/pool/UUID
        if (input.includes('defillama.com')) {
            const match = input.match(/pool\/([a-f0-9-]+)/i);
            if (match) {
                console.log('[VerifyPools] Parsed DefiLlama pool ID:', match[1]);
                return { type: 'defillama', id: match[1] };
            }
        }

        // Aerodrome URL: https://aerodrome.finance/deposit?token0=0x...&token1=0x...
        // or: https://aerodrome.finance/liquidity/0x...
        if (input.includes('aerodrome.finance')) {
            // Try to extract pool address from liquidity path
            const liquidityMatch = input.match(/liquidity\/(0x[a-fA-F0-9]{40})/i);
            if (liquidityMatch) {
                console.log('[VerifyPools] Parsed Aerodrome pool address:', liquidityMatch[1]);
                return { type: 'address', id: liquidityMatch[1].toLowerCase(), protocol: 'aerodrome' };
            }

            // Extract BOTH tokens from deposit URL for pair matching
            const token0Match = input.match(/token0=(0x[a-fA-F0-9]{40})/i);
            const token1Match = input.match(/token1=(0x[a-fA-F0-9]{40})/i);
            const typeMatch = input.match(/type=(\d+)/i);
            const factoryMatch = input.match(/factory=(0x[a-fA-F0-9]{40})/i);

            if (token0Match && token1Match) {
                // Determine if stable pool from type param (10 = stable slipstream)
                const poolType = typeMatch ? parseInt(typeMatch[1]) : 0;
                const isStable = poolType === 10 || poolType === 1;

                console.log('[VerifyPools] Parsed Aerodrome pair:', token0Match[1], token1Match[1], 'stable:', isStable);
                return {
                    type: 'pair',
                    token0: token0Match[1].toLowerCase(),
                    token1: token1Match[1].toLowerCase(),
                    protocol: 'aerodrome',
                    chain: 'Base',
                    stable: isStable,
                    factory: factoryMatch ? factoryMatch[1].toLowerCase() : null,
                    original: input  // Preserve for InputResolver
                };
            }

            // Fallback to single token if only one found
            if (token0Match) {
                console.log('[VerifyPools] Parsed Aerodrome token0:', token0Match[1]);
                return { type: 'address', id: token0Match[1].toLowerCase(), protocol: 'aerodrome' };
            }
        }

        // Velodrome URL (similar to Aerodrome): https://velodrome.finance/deposit?token0=...&token1=...
        if (input.includes('velodrome.finance')) {
            const token0Match = input.match(/token0=(0x[a-fA-F0-9]{40})/i);
            const token1Match = input.match(/token1=(0x[a-fA-F0-9]{40})/i);

            if (token0Match && token1Match) {
                console.log('[VerifyPools] Parsed Velodrome pair:', token0Match[1], token1Match[1]);
                return {
                    type: 'pair',
                    token0: token0Match[1].toLowerCase(),
                    token1: token1Match[1].toLowerCase(),
                    protocol: 'velodrome',
                    chain: 'Optimism'
                };
            }
        }

        // PancakeSwap URLs
        if (input.includes('pancakeswap.finance')) {
            const token0Match = input.match(/token0=(0x[a-fA-F0-9]{40})/i);
            const token1Match = input.match(/token1=(0x[a-fA-F0-9]{40})/i);

            if (token0Match && token1Match) {
                console.log('[VerifyPools] Parsed PancakeSwap pair');
                return {
                    type: 'pair',
                    token0: token0Match[1].toLowerCase(),
                    token1: token1Match[1].toLowerCase(),
                    protocol: 'pancakeswap'
                };
            }
        }

        // Uniswap URL: https://app.uniswap.org/pools/POOL_ID or /pool/CHAIN/0x...
        if (input.includes('uniswap.org') || input.includes('uniswap.com')) {
            // Check for token pair in URL params first
            const token0Match = input.match(/token0=(0x[a-fA-F0-9]{40})/i);
            const token1Match = input.match(/token1=(0x[a-fA-F0-9]{40})/i);

            if (token0Match && token1Match) {
                console.log('[VerifyPools] Parsed Uniswap pair');
                return {
                    type: 'pair',
                    token0: token0Match[1].toLowerCase(),
                    token1: token1Match[1].toLowerCase(),
                    protocol: 'uniswap-v3'
                };
            }

            const poolMatch = input.match(/pool[s]?\/([\\w]+)\/(0x[a-fA-F0-9]{40})/i);
            if (poolMatch) {
                console.log('[VerifyPools] Parsed Uniswap pool:', poolMatch[2]);
                return { type: 'address', id: poolMatch[2].toLowerCase(), protocol: 'uniswap' };
            }
            const simpleMatch = input.match(/(0x[a-fA-F0-9]{40})/i);
            if (simpleMatch) {
                return { type: 'address', id: simpleMatch[1].toLowerCase(), protocol: 'uniswap' };
            }
        }

        // Curve URL: https://curve.fi/#/ethereum/pools/...
        if (input.includes('curve.fi')) {
            const poolMatch = input.match(/pools\/([a-zA-Z0-9-]+)/i);
            if (poolMatch) {
                console.log('[VerifyPools] Parsed Curve pool:', poolMatch[1]);
                return { type: 'name', id: poolMatch[1], protocol: 'curve' };
            }
        }

        // UNIVERSAL: Any URL with token0 & token1 query params
        if (input.includes('token0=') && input.includes('token1=')) {
            const token0Match = input.match(/token0=(0x[a-fA-F0-9]{40})/i);
            const token1Match = input.match(/token1=(0x[a-fA-F0-9]{40})/i);

            if (token0Match && token1Match) {
                console.log('[VerifyPools] Parsed generic pair URL');
                return {
                    type: 'pair',
                    token0: token0Match[1].toLowerCase(),
                    token1: token1Match[1].toLowerCase()
                };
            }
        }

        // Contract address (0x...)
        if (input.startsWith('0x') && input.length === 42) {
            console.log('[VerifyPools] Parsed contract address:', input);
            return { type: 'address', id: input.toLowerCase() };
        }

        // UUID format (DefiLlama pool ID)
        if (/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(input)) {
            console.log('[VerifyPools] Parsed UUID:', input);
            return { type: 'defillama', id: input };
        }

        // Return as-is for other formats
        console.log('[VerifyPools] Unknown format, using as-is');
        return { type: 'unknown', id: input };
    },

    // Normalize DefiLlama pool data to match our PoolDetailModal expected format
    normalizePoolData(pool) {
        console.log('[VerifyPools] Normalizing pool data:', pool);

        // Calculate risk data
        const riskScore = this.calculateRiskScore(pool);
        const riskLevel = this.getRiskLevel(pool);

        // Format volume
        const volume = pool.volumeUsd1d || pool.volumeUsd7d || 0;
        const volumeFormatted = this.formatNumber(volume);

        // Generate premium insights based on pool data
        const premiumInsights = this.generateInsights(pool);

        // Generate risk reasons
        const riskReasons = this.generateRiskReasons(pool);

        // Get reward token name
        const rewardTokens = pool.rewardTokens || [];
        const rewardToken = rewardTokens.length > 0 ? rewardTokens[0] : pool.project;

        return {
            // Identity
            id: pool.pool || pool.id,
            pool: pool.pool,
            symbol: pool.symbol,
            project: pool.project,
            chain: pool.chain,

            // TVL & Volume (DefiLlama uses tvlUsd)
            tvl: pool.tvlUsd || pool.tvl || 0,
            tvlUsd: pool.tvlUsd || pool.tvl || 0,
            tvl_formatted: '$' + this.formatNumber(pool.tvlUsd || pool.tvl || 0),
            tvl_change_7d: pool.apyPct7D || 0, // Use APY change as proxy for TVL trend
            volume_24h: volume,
            volume_24h_formatted: volume > 0 ? ('$' + volumeFormatted) : 'N/A',

            // APY breakdown - if apyBase/apyReward not available, treat total APY as base
            apy: pool.apy || 0,
            apy_base: this.getApyBase(pool),
            apy_reward: this.getApyReward(pool),
            apyBase: pool.apyBase || pool.apy || 0,
            apyReward: pool.apyReward || 0,

            // Reward token source
            reward_token: rewardToken,
            rewardTokens: rewardTokens,

            // Pool characteristics - SNAKE_CASE
            pool_type: pool.stablecoin ? 'stable' : 'volatile',
            isStable: pool.stablecoin === true,
            stablecoin: pool.stablecoin,

            // Risk metrics from DefiLlama
            ilRisk: pool.ilRisk || 'unknown',
            il_risk: pool.ilRisk === 'no' ? 'none' : (pool.ilRisk || 'unknown'),
            impermanentLoss: pool.ilRisk === 'no' ? 'None' : (pool.ilRisk || 'Unknown'),
            exposure: pool.exposure || null,

            // Risk scoring
            risk_score: riskScore,
            risk_level: riskLevel,
            riskScore: riskScore,
            riskLevel: riskLevel,

            // IMPORTANT: Flag for showing verdict banner in modal
            isVerified: true,

            // Additional metrics
            underlyingTokens: pool.underlyingTokens || [],

            // Historical data (if available)
            apyPct1D: pool.apyPct1D || 0,
            apyPct7D: pool.apyPct7D || 0,
            apyPct30D: pool.apyPct30D || 0,
            apyMean30d: pool.apyMean30d || pool.apy || 0,

            // IMPORTANT: Fields for Market Dynamics section
            premium_insights: premiumInsights,
            risk_reasons: riskReasons,

            // Smart insights for rich analysis
            smart_insights: premiumInsights,

            // Data source indicator
            dataSource: pool.dataSource || pool.source || 'defillama',

            // Keep original data for reference
            _raw: pool
        };
    },

    // Generate premium insights based on pool data
    generateInsights(pool) {
        const insights = [];
        const tvl = pool.tvlUsd || pool.tvl || 0;
        const apy = pool.apy || 0;
        const apyBase = pool.apyBase || 0;
        const apyReward = pool.apyReward || 0;

        // TVL insight
        if (tvl > 100000000) {
            insights.push({ type: 'positive', icon: '✅', text: `High TVL ($${this.formatNumber(tvl)}) indicates strong liquidity and reduced slippage risk` });
        } else if (tvl > 10000000) {
            insights.push({ type: 'neutral', icon: '📊', text: `Moderate TVL ($${this.formatNumber(tvl)}) - adequate liquidity for most trades` });
        } else if (tvl < 1000000) {
            insights.push({ type: 'warning', icon: '⚠️', text: `Low TVL ($${this.formatNumber(tvl)}) - potential liquidity issues and higher slippage` });
        }

        // APY composition insight
        if (apyReward > apyBase && apyReward > 5) {
            insights.push({ type: 'warning', icon: '⚠️', text: `${((apyReward / apy) * 100).toFixed(0)}% of APY comes from reward emissions - may decrease over time` });
        } else if (apyBase > apyReward) {
            insights.push({ type: 'positive', icon: '✅', text: `Majority of yield (${apyBase.toFixed(1)}%) is from trading fees - more sustainable` });
        }

        // IL risk insight
        if (pool.ilRisk === 'no') {
            insights.push({ type: 'positive', icon: '✅', text: 'No impermanent loss risk (single-sided or stable pair)' });
        } else if (pool.ilRisk === 'yes') {
            insights.push({ type: 'warning', icon: '⚠️', text: 'Volatile pair - subject to impermanent loss during price movements' });
        }

        // Stablecoin insight
        if (pool.stablecoin) {
            insights.push({ type: 'positive', icon: '✅', text: 'Stablecoin pool - lower volatility and predictable returns' });
        }

        // High APY warning
        if (apy > 50) {
            insights.push({ type: 'warning', icon: '⚠️', text: `High APY (${apy.toFixed(1)}%) - verify emission sustainability and token value` });
        }

        return insights;
    },

    // Generate risk reasons list
    generateRiskReasons(pool) {
        const reasons = [];
        const tvl = pool.tvlUsd || pool.tvl || 0;
        const apy = pool.apy || 0;

        if (tvl < 1000000) reasons.push('Low TVL may cause liquidity issues');
        if (apy > 100) reasons.push('Extremely high APY may be unsustainable');
        if (pool.ilRisk === 'yes') reasons.push('Impermanent loss risk for volatile pairs');
        if (pool.apyReward > pool.apyBase * 2) reasons.push('Heavy reliance on reward emissions');

        return reasons;
    },

    // Calculate basic risk score (0-100, higher = safer)
    calculateRiskScore(pool) {
        let score = 50; // Base score

        // TVL factor
        const tvl = pool.tvlUsd || pool.tvl || 0;
        if (tvl > 100000000) score += 20; // >100M
        else if (tvl > 10000000) score += 15; // >10M
        else if (tvl > 1000000) score += 10; // >1M
        else if (tvl < 100000) score -= 15; // <100K risky

        // APY factor (very high APY = risky)
        const apy = pool.apy || 0;
        if (apy > 100) score -= 20;
        else if (apy > 50) score -= 10;
        else if (apy < 20) score += 5;

        // Stablecoin bonus
        if (pool.stablecoin) score += 10;

        // IL risk
        if (pool.ilRisk === 'no') score += 10;
        else if (pool.ilRisk === 'yes') score -= 10;

        return Math.max(0, Math.min(100, score));
    },

    // Get risk level label
    getRiskLevel(pool) {
        const score = this.calculateRiskScore(pool);
        if (score >= 75) return 'Low';
        if (score >= 50) return 'Medium';
        if (score >= 25) return 'High';
        return 'Critical';
    },

    // Get APY base - if not available, use total APY (assume all from trading fees)
    getApyBase(pool) {
        if (pool.apyBase !== null && pool.apyBase !== undefined) {
            return pool.apyBase.toFixed(2);
        }
        // If no breakdown available, total APY is treated as base yield
        return (pool.apy || 0).toFixed(2);
    },

    // Get APY reward - if not available, return 0
    getApyReward(pool) {
        if (pool.apyReward !== null && pool.apyReward !== undefined) {
            return pool.apyReward.toFixed(2);
        }
        return '0.00';
    },

    // Search for pool by token pair (e.g., from Aerodrome deposit URLs)
    async searchByPair(parsed) {
        const { token0, token1, protocol, chain, stable } = parsed;
        console.log('[VerifyPools] Searching for pair:', token0, token1, 'on', protocol, 'stable:', stable);

        Toast?.show('🧠 Analyzing pool with SmartRouter...', 'info');

        try {
            // Call backend API for pair search
            const response = await fetch(
                `http://localhost:8000/api/scout/pool-pair?token0=${encodeURIComponent(token0)}&token1=${encodeURIComponent(token1)}&protocol=${encodeURIComponent(protocol || '')}&chain=${encodeURIComponent(chain || '')}&stable=${stable ? 'true' : 'false'}`
            );

            if (response.ok) {
                const data = await response.json();
                if (data && data.pool) {
                    console.log('[VerifyPools] Found pair pool:', data.pool);
                    Toast?.show('Pool found!', 'success');
                    return data.pool;
                }
            }

            // Fallback: try to find in local pools
            if (typeof pools !== 'undefined' && Array.isArray(pools) && pools.length > 0) {
                const found = pools.find(p => {
                    const poolLower = (p.pool || '').toLowerCase();
                    const underlying = p.underlyingTokens || [];

                    // Check if both tokens are in the pool
                    const hasToken0 = poolLower.includes(token0) ||
                        underlying.some(t => t?.toLowerCase().includes(token0));
                    const hasToken1 = poolLower.includes(token1) ||
                        underlying.some(t => t?.toLowerCase().includes(token1));

                    // If protocol specified, filter by it
                    if (protocol && p.project?.toLowerCase() !== protocol.toLowerCase()) {
                        return false;
                    }

                    return hasToken0 && hasToken1;
                });

                if (found) {
                    console.log('[VerifyPools] Found pair in local pools:', found);
                    Toast?.show('Pool found!', 'success');
                    return found;
                }
            }

            Toast?.show('Pool not found - try pasting the pool contract address directly', 'warning');
            return null;
        } catch (error) {
            console.error('[VerifyPools] Pair search error:', error);
            Toast?.show('Error searching for token pair', 'error');
            return null;
        }
    },

    // Fetch pool data from API
    async fetchPoolData(parsed) {
        console.log('[VerifyPools] Searching for pool:', parsed);

        const poolId = parsed.id;
        const searchType = parsed.type;
        const protocol = parsed.protocol;

        try {
            // Handle 'pair' type search (e.g., from Aerodrome deposit URL)
            if (searchType === 'pair') {
                return await this.searchByPair(parsed);
            }

            // Try to find in existing pools first (already loaded from backend)
            if (typeof pools !== 'undefined' && Array.isArray(pools) && pools.length > 0) {
                console.log('[VerifyPools] Searching in', pools.length, 'local pools');

                const found = pools.find(p => {
                    // Match by different criteria based on type
                    if (searchType === 'defillama') {
                        return p.pool === poolId;
                    }
                    if (searchType === 'address') {
                        const addr = p.address?.toLowerCase() || p.pool?.toLowerCase();
                        // Also check if pool ID contains this address
                        return addr?.includes(poolId) || p.pool?.includes(poolId);
                    }
                    // For protocol-specific searches
                    if (protocol && p.project?.toLowerCase() === protocol.toLowerCase()) {
                        return p.symbol?.toLowerCase().includes(poolId.toLowerCase()) ||
                            p.pool?.includes(poolId);
                    }
                    // Fallback: generic search
                    return p.pool === poolId ||
                        p.pool_id === poolId ||
                        p.address?.toLowerCase() === poolId?.toLowerCase();
                });

                if (found) {
                    console.log('[VerifyPools] Found in local pools:', found);
                    return found;
                }
            }

            // Use our backend API scout endpoint
            Toast?.show('Fetching pool data...', 'info');

            try {
                // STEP 1: Use InputResolver for universal input handling
                // Works with: raw address, Aerodrome URL, Uniswap URL, DexScreener, etc.
                let poolAddress = null;
                const rawInput = parsed.original || poolId;

                // If it looks like a URL or contains multiple addresses, use /resolve
                if (rawInput.includes('http') || rawInput.includes('token0') || rawInput.includes('token1')) {
                    console.log('[VerifyPools] Using InputResolver for:', rawInput.substring(0, 50) + '...');
                    Toast?.show('🧠 Resolving input...', 'info');

                    const resolveResponse = await fetch(
                        `http://localhost:8000/api/scout/resolve?input=${encodeURIComponent(rawInput)}&chain=base`
                    );

                    if (resolveResponse.ok) {
                        const resolveData = await resolveResponse.json();
                        if (resolveData.success && resolveData.pool_address) {
                            poolAddress = resolveData.pool_address;
                            console.log('[VerifyPools] Resolved to pool:', poolAddress);
                        }
                    }
                }

                // Use resolved address or original poolId
                const addressToVerify = poolAddress || poolId;

                // STEP 2: Verify the pool with full data enrichment
                const searchUrl = `http://localhost:8000/api/scout/verify-any?pool_address=${encodeURIComponent(addressToVerify)}&chain=base`;

                const response = await fetch(searchUrl);
                if (response.ok) {
                    const data = await response.json();
                    // Handle verify-any response format
                    if (data && data.success && data.pool) {
                        const pool = data.pool;
                        // Add risk analysis if available
                        if (data.risk_analysis) {
                            pool.risk_score = data.risk_analysis.risk_score;
                            pool.risk_level = data.risk_analysis.risk_level;
                            pool.risk_reasons = data.risk_analysis.risk_reasons;
                        }
                        pool.dataSource = data.source;
                        console.log('[VerifyPools] Found via verify-any:', pool);
                        Toast?.show('Pool found!', 'success');
                        return pool;
                    } else if (data && data.pool) {
                        console.log('[VerifyPools] Found via backend:', data.pool);
                        Toast?.show('Pool found!', 'success');
                        return data.pool;
                    }
                } else if (response.status === 404) {
                    console.log('[VerifyPools] Pool not found');
                }
            } catch (backendError) {
                console.error('[VerifyPools] Backend error:', backendError);
            }

            Toast?.show('Pool not found', 'warning');
            console.log('[VerifyPools] Pool not found');
            return null;
        } catch (error) {
            console.error('[VerifyPools] Fetch error:', error);
            return null;
        }
    },

    // Show verification modal (reuse Pool Detail style)
    showVerificationModal(pool) {
        // Use existing PoolDetailModal if available (same as Explore modal)
        if (typeof PoolDetailModal !== 'undefined' && PoolDetailModal.show) {
            console.log('[VerifyPools] Using PoolDetailModal.show()');
            PoolDetailModal.show(pool);
            return;
        }

        // Fallback simple modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'verifyResultModal';
        modal.innerHTML = `
            <div class="modal-container" style="max-width: 600px;">
                <button class="modal-close" onclick="document.getElementById('verifyResultModal').remove()">✕</button>
                <h2 style="margin-bottom: 16px;">✅ Pool Verified</h2>
                
                <div style="background: var(--bg-elevated); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                    <h3 style="font-size: 1.2rem; margin-bottom: 8px;">${pool.symbol || pool.pool}</h3>
                    <p style="color: var(--text-muted); font-size: 0.9rem;">${pool.project || 'Unknown Protocol'}</p>
                </div>

                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px;">
                    <div style="background: var(--bg-surface); padding: 12px; border-radius: 8px;">
                        <div style="color: var(--text-muted); font-size: 0.75rem;">TVL</div>
                        <div style="font-size: 1.1rem; font-weight: 600;">$${this.formatNumber(pool.tvlUsd)}</div>
                    </div>
                    <div style="background: var(--bg-surface); padding: 12px; border-radius: 8px;">
                        <div style="color: var(--text-muted); font-size: 0.75rem;">APY</div>
                        <div style="font-size: 1.1rem; font-weight: 600; color: var(--success);">${pool.apy?.toFixed(2) || 0}%</div>
                    </div>
                    <div style="background: var(--bg-surface); padding: 12px; border-radius: 8px;">
                        <div style="color: var(--text-muted); font-size: 0.75rem;">Chain</div>
                        <div style="font-size: 1.1rem;">${pool.chain || 'Unknown'}</div>
                    </div>
                    <div style="background: var(--bg-surface); padding: 12px; border-radius: 8px;">
                        <div style="color: var(--text-muted); font-size: 0.75rem;">Pool Type</div>
                        <div style="font-size: 1.1rem;">${pool.stablecoin ? 'Stable' : 'Volatile'}</div>
                    </div>
                </div>

                <div style="background: var(--bg-surface); padding: 16px; border-radius: 8px;">
                    <h4 style="margin-bottom: 12px; color: var(--gold);">Risk Analysis</h4>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        <li style="padding: 6px 0; color: var(--text-secondary);">
                            ${pool.ilRisk === 'no' ? '✅' : '⚠️'} IL Risk: ${pool.ilRisk || 'Unknown'}
                        </li>
                        <li style="padding: 6px 0; color: var(--text-secondary);">
                            ${pool.tvlUsd > 1000000 ? '✅' : '⚠️'} TVL: ${pool.tvlUsd > 1000000 ? 'Healthy' : 'Low'}
                        </li>
                        <li style="padding: 6px 0; color: var(--text-secondary);">
                            ${pool.apy < 50 ? '✅' : '⚠️'} APY: ${pool.apy < 50 ? 'Sustainable' : 'High (check source)'}
                        </li>
                    </ul>
                </div>

                <button onclick="document.getElementById('verifyResultModal').remove()" 
                        style="width: 100%; margin-top: 20px; padding: 12px; background: var(--gold); color: black; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                    Close
                </button>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    },

    // Format number with K/M/B suffix
    formatNumber(num) {
        if (!num) return '0';
        if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
        return num.toFixed(0);
    },

    // Save to history
    saveToHistory(pool) {
        const history = this.getHistory();

        // Generate consistent ID from pool_address or pool field
        const poolId = pool.pool_address || pool.address || pool.pool || pool.pool_id || `${pool.symbol}-${pool.chain}`;

        const entry = {
            id: poolId,
            pool_address: pool.pool_address || pool.address,
            address: pool.pool_address || pool.address,
            symbol: pool.symbol,
            project: pool.project,
            chain: pool.chain,
            apy: pool.apy,
            tvlUsd: pool.tvlUsd,
            verifiedAt: Date.now()
        };

        // Add to front, limit to 20 items
        history.unshift(entry);
        if (history.length > 20) history.pop();

        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(history));
        this.renderHistory(history);
    },

    // Get history from localStorage
    getHistory() {
        try {
            return JSON.parse(localStorage.getItem(this.STORAGE_KEY)) || [];
        } catch {
            return [];
        }
    },

    // Clear history
    clearHistory() {
        localStorage.removeItem(this.STORAGE_KEY);
        this.renderHistory([]);
        Toast?.show('History cleared', 'success');
    },

    // Load and render history
    loadHistory() {
        const history = this.getHistory();
        this.renderHistory(history);
    },

    // Render history grid
    renderHistory(history) {
        const grid = document.getElementById('verifyHistoryGrid');
        if (!grid) return;

        if (history.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">
                    <div style="font-size: 2rem; margin-bottom: 8px;">🔍</div>
                    <p>No verified pools yet. Enter an address above to verify.</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = history.map(pool => `
            <div class="verify-history-card" onclick="VerifyPools.openFromHistory('${pool.id}')">
                <div class="verify-card-header">
                    <span class="verify-pool-name">${pool.symbol || 'Unknown'}</span>
                    <span class="verify-pool-apy ${pool.apy > 0 ? 'positive' : ''}">${pool.apy?.toFixed(1) || 0}%</span>
                </div>
                <div class="verify-card-meta">
                    <span>${pool.project || 'Protocol'}</span>
                    <span>•</span>
                    <span>${pool.chain || 'Chain'}</span>
                </div>
                <div class="verify-card-footer">
                    <span class="verify-tvl">$${this.formatNumber(pool.tvlUsd)}</span>
                    <span class="verify-date">${this.formatDate(pool.verifiedAt)}</span>
                </div>
            </div>
        `).join('');
    },

    // Format date
    formatDate(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    },

    // Open pool from history - refetch fresh data
    async openFromHistory(poolId) {
        console.log('[VerifyPools] Opening from history:', poolId);
        const history = this.getHistory();

        // Match by id, pool_address, or address
        const cached = history.find(p =>
            p.id === poolId ||
            p.pool_address === poolId ||
            p.address === poolId
        );

        if (cached) {
            // Get fresh data using verify-any endpoint
            const poolAddress = cached.pool_address || cached.address || poolId;
            const chain = (cached.chain || 'base').toLowerCase();

            Toast?.show('Refreshing pool data...', 'info');

            try {
                const response = await fetch(
                    `http://localhost:8000/api/scout/verify-any?pool_address=${poolAddress}&chain=${chain}`
                );

                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.pool) {
                        // Merge fresh data with cached
                        const freshPool = {
                            ...cached,
                            ...data.pool,
                            risk_score: data.risk_analysis?.risk_score,
                            risk_level: data.risk_analysis?.risk_level,
                            risk_reasons: data.risk_analysis?.risk_reasons || [],
                            dataSource: data.source
                        };
                        const normalized = this.normalizePoolData(freshPool);
                        this.showVerificationModal(normalized);
                        return;
                    }
                }
            } catch (error) {
                console.log('[VerifyPools] Fresh fetch failed, using cached:', error);
            }

            // Fallback to cached data
            const normalized = this.normalizePoolData(cached);
            this.showVerificationModal(normalized);
        } else {
            Toast?.show('Pool not found in history', 'warning');
        }
    }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    VerifyPools.init();
});
