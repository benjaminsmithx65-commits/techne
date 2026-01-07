/**
 * Pool Detail Modal - Enhanced pool information view
 */

const PoolIcons = {
    close: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`,
    tvl: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>`,
    risk: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
    shield: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>`,
    coins: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"></circle><path d="M18.09 10.37A6 6 0 1 1 10.34 18"></path><path d="M7 6h1v4"></path><path d="m16.71 13.88.7.71-2.82 2.82"></path></svg>`,
    trendUp: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>`,
    trendDown: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>`,
    check: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
    activity: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`,
    bot: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="16" r="4"></circle><path d="M7 6h10"></path><line x1="8" y1="6" x2="8" y2="2"></line><line x1="16" y1="6" x2="16" y2="2"></line></svg>`,
    externalLink: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>`,
    fileText: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>`
};

// Known token address to symbol mapping (Base mainnet)
const TOKEN_ADDRESS_MAP = {
    '0x194f7cd4da3514c7fb38f079d79e4b7200e98bf4': 'MERKL',
    '0x940181a94a35a4569e4529a3cdfb74e38fd98631': 'AERO',
    '0x4200000000000000000000000000000000000006': 'WETH',
    '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913': 'USDC',
    '0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca': 'USDbC',
    '0x50c5725949a6f0c72e6c4a641f24049a917db0cb': 'DAI',
    '0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22': 'cbETH',
    '0xc1cba3fcea344f92d9239c08c0568f6f2f0ee452': 'wstETH',
    '0xb6fe221fe9eef5aba221c348ba20a1bf5e73624c': 'rETH',
    '0x0578d8a44db98b23bf096a382e016e29a5ce0ffe': 'COMP',
    '0x4f604735c1cf31399c6e711d5962b2b3e0225ad3': 'MORPHO',
    '0x78a087d713be963bf3f1c1a8e73af1a31d9eb08d': 'ARB',
};

// Format reward token name - resolve addresses to symbols
function formatRewardTokenName(name) {
    if (!name) return 'TOKEN';

    // Check if it's a hex address (starts with 0x and has 42 chars)
    const addressMatch = name.match(/0x[a-fA-F0-9]{40}/i);
    if (addressMatch) {
        const address = addressMatch[0].toLowerCase();
        // Check mapping first
        if (TOKEN_ADDRESS_MAP[address]) {
            return TOKEN_ADDRESS_MAP[address];
        }
        // Return shortened address
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    }

    // Check if it's in format "Reward (0x...):" or similar
    if (name.match(/\(0x[a-fA-F0-9]+\)/)) {
        const innerMatch = name.match(/0x[a-fA-F0-9]{40}/i);
        if (innerMatch) {
            const addr = innerMatch[0].toLowerCase();
            if (TOKEN_ADDRESS_MAP[addr]) {
                return TOKEN_ADDRESS_MAP[addr];
            }
            return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
        }
    }

    return name;
}

// Get protocol website URL
function getProtocolWebsite(project) {
    const websites = {
        'aerodrome': 'https://aerodrome.finance',
        'velodrome': 'https://velodrome.finance',
        'aave': 'https://aave.com',
        'aave-v3': 'https://aave.com',
        'compound': 'https://compound.finance',
        'compound-v3': 'https://compound.finance',
        'morpho': 'https://morpho.org',
        'moonwell': 'https://moonwell.fi',
        'curve-dex': 'https://curve.fi',
        'curve': 'https://curve.fi',
        'uniswap': 'https://uniswap.org',
        'uniswap-v3': 'https://uniswap.org',
        'beefy': 'https://beefy.finance',
        'yearn': 'https://yearn.fi',
        'yearn-finance': 'https://yearn.fi',
        'seamless': 'https://seamlessprotocol.com',
        'seamless-protocol': 'https://seamlessprotocol.com',
        'sonne': 'https://sonne.finance',
        'sonne-finance': 'https://sonne.finance',
        'exactly': 'https://exactly.finance',
        'extra-finance': 'https://extra.finance',
        'merkl': 'https://merkl.angle.money',
        'pendle': 'https://pendle.finance',
        'radiant': 'https://radiant.capital',
        'radiant-v2': 'https://radiant.capital',
        'spark': 'https://spark.fi',
        'convex': 'https://convexfinance.com',
        'convex-finance': 'https://convexfinance.com',
        'lido': 'https://lido.fi',
        'gmx': 'https://gmx.io',
        'balancer': 'https://balancer.fi',
        'balancer-v2': 'https://balancer.fi',
        'stargate': 'https://stargate.finance',
        'origin': 'https://originprotocol.com',
        'origin-ether': 'https://originprotocol.com',
        'avantis': 'https://avantis.finance',
        'infinifi': 'https://infinifi.xyz'
    };
    const key = (project || '').toLowerCase().replace(/[^a-z0-9-]/g, '');
    return websites[key] || null;
}

// Get explorer URL for contract
function getExplorerUrl(pool) {
    const chain = (pool.chain || 'base').toLowerCase();
    const explorers = {
        'base': 'https://basescan.org/address/',
        'ethereum': 'https://etherscan.io/address/',
        'arbitrum': 'https://arbiscan.io/address/',
        'optimism': 'https://optimistic.etherscan.io/address/',
        'polygon': 'https://polygonscan.com/address/'
    };
    const baseUrl = explorers[chain] || explorers['base'];
    const contractAddress = pool.pool_address || pool.contract || pool.id;
    if (contractAddress && contractAddress.startsWith('0x')) {
        return `${baseUrl}${contractAddress}`;
    }
    return null;
}

const PoolDetailModal = {
    currentPool: null,

    // Calculate time until next Aerodrome/Velodrome epoch (Wednesday 00:00 UTC)
    getEpochCountdown() {
        const now = new Date();
        const nextWed = new Date(now);
        nextWed.setUTCHours(0, 0, 0, 0);
        const currentDay = now.getUTCDay();
        const daysUntilWed = (3 - currentDay + 7) % 7 || 7;
        nextWed.setUTCDate(now.getUTCDate() + daysUntilWed);
        const diff = nextWed - now;
        const days = Math.floor(diff / 86400000);
        const hours = Math.floor((diff % 86400000) / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        return { days, hours, minutes, display: `${days}d ${hours}h ${minutes}m` };
    },

    // Check if protocol has epoch-based rewards
    isEpochProtocol(project) {
        const ep = (project || '').toLowerCase();
        return ep.includes('aerodrome') || ep.includes('velodrome');
    },

    // Keydown handler
    handleKeydown(e) {
        if (e.key === 'Escape') {
            PoolDetailModal.close();
        }
    },

    // Render Artisan Agent verdict banner for verified pools
    renderVerdictBanner(pool) {
        const riskScore = pool.riskScore || pool.risk_score || 50;
        const riskLevel = pool.riskLevel || pool.risk_level || 'Medium';
        const dataSource = pool.dataSource || 'defillama';

        let verdict, verdictClass, verdictIcon, verdictDesc;

        if (riskScore >= 70 || riskLevel === 'Low') {
            verdict = 'VERIFIED SAFE';
            verdictClass = 'verdict-safe';
            verdictIcon = '✅';
            verdictDesc = 'This pool has passed Artisan Agent risk assessment';
        } else if (riskScore >= 40 || riskLevel === 'Medium') {
            verdict = 'CAUTION';
            verdictClass = 'verdict-caution';
            verdictIcon = '⚠️';
            verdictDesc = 'This pool requires careful consideration before investing';
        } else {
            verdict = 'HIGH RISK';
            verdictClass = 'verdict-danger';
            verdictIcon = '❌';
            verdictDesc = 'This pool has significant risk factors - proceed with caution';
        }

        // Dynamic data source indicator
        let sourceLabel;
        if (dataSource === 'geckoterminal') {
            sourceLabel = '🦎 Real-time data via GeckoTerminal';
        } else if (dataSource === 'onchain') {
            sourceLabel = '⛓️ On-chain data (most accurate)';
        } else {
            sourceLabel = '📊 Data: DefiLlama (may differ from protocol)';
        }

        return `
            <div class="artisan-verdict ${verdictClass}">
                <div class="verdict-stamp">
                    <span class="verdict-icon">${verdictIcon}</span>
                    <span class="verdict-text">${verdict}</span>
                </div>
                <div class="verdict-details">
                    <span class="verdict-agent">🤖 Artisan Agent Analysis</span>
                    <span class="verdict-desc">${verdictDesc}</span>
                    <span class="verdict-score">Risk Score: ${riskScore}/100</span>
                    <span class="verdict-source">${sourceLabel}</span>
                </div>
            </div>
        `;
    },

    show(pool) {
        this.currentPool = pool;

        // Add to history
        if (window.SearchHistory) {
            SearchHistory.addEntry('pool_view', {
                project: pool.project,
                symbol: pool.symbol,
                apy: pool.apy
            });
        }

        // Add ESC listener
        document.addEventListener('keydown', this.handleKeydown);

        // Create modal if not exists
        let modal = document.getElementById('poolDetailModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'poolDetailModal';
            modal.className = 'pool-detail-overlay';
            // Click outside to close
            modal.onclick = (e) => {
                if (e.target === modal) PoolDetailModal.close();
            };
            document.body.appendChild(modal);
        } else {
            modal.style.display = 'flex';
        }

        const protocolIcon = window.getProtocolIconUrl ? getProtocolIconUrl(pool.project) :
            `https://icons.llama.fi/${(pool.project || '').toLowerCase()}.png`;
        const chainIcon = window.getChainIconUrl ? getChainIconUrl(pool.chain) :
            `https://icons.llama.fi/chains/rsz_${(pool.chain || 'base').toLowerCase()}.jpg`;

        const isNiche = window.NicheProtocols?.isNiche(pool.project);
        const nicheCategory = isNiche ? NicheProtocols.getCategory(pool.project) : null;

        const epoch = this.getEpochCountdown();

        modal.innerHTML = `
            <div class="pool-detail-modal">
                <button class="modal-close" onclick="PoolDetailModal.close()" title="Close (ESC)">${PoolIcons.close}</button>
                
                ${pool.isVerified ? this.renderVerdictBanner(pool) : ''}
                
                <!-- Trust Links -->
                <div class="trust-links">
                    ${getExplorerUrl(pool) ? `<a href="${getExplorerUrl(pool)}" target="_blank" title="View Contract on ${pool.chain || 'Base'} Explorer">${PoolIcons.fileText} Contract</a>` : ''}
                    ${getProtocolWebsite(pool.project) ? `<a href="${getProtocolWebsite(pool.project)}" target="_blank" title="Visit ${pool.project} website">${PoolIcons.externalLink} Protocol</a>` : ''}
                    ${pool.pool_link ? `<a href="${pool.pool_link}" target="_blank" title="View Pool on ${pool.project}">🏊 Pool</a>` : ''}
                </div>
                
                <div class="pool-detail-header">
                    <div class="pool-detail-icon">
                        <img src="${protocolIcon}" alt="${pool.project}" onerror="this.style.display='none'">
                    </div>
                    <div class="pool-detail-title">
                        <h2>${pool.project}</h2>
                        <div class="pool-detail-meta">
                            <span class="symbol">${pool.symbol}</span>
                            <img src="${chainIcon}" alt="${pool.chain}" class="chain-badge">
                            <span class="chain-name">${pool.chain || 'Base'}</span>
                            ${isNiche ? `<span class="niche-badge">🔮 ${nicheCategory}</span>` : ''}
                        </div>
                    </div>
                    <div class="pool-detail-apy">
                        <span class="apy-value">${pool.apy?.toFixed(2)}%</span>
                        <span class="apy-label">APY</span>
                    </div>
                </div>
                
                <div class="pool-detail-grid">
                    <div class="detail-card">
                        <div class="detail-label">TVL</div>
                         <div class="detail-icon-bg">${PoolIcons.tvl}</div>
                        <div class="detail-value">${formatTvl ? formatTvl(pool.tvl) : '$' + (pool.tvl / 1000000).toFixed(2) + 'M'}</div>
                    </div>
                    <div class="detail-card">
                        <div class="detail-label">Risk Level</div>
                        <div class="detail-icon-bg">${PoolIcons.risk}</div>
                        <span class="risk-badge ${(pool.risk_level || 'medium').toLowerCase()}">${pool.risk_level || 'Medium'}</span>
                    </div>
                    <div class="detail-card ${pool.il_risk === 'yes' ? 'il-high' : 'il-none'}">
                        <div class="detail-label">IL Risk</div>
                        <div class="detail-icon-bg">${PoolIcons.shield}</div>
                        <div class="detail-value ${pool.il_risk === 'yes' ? 'il-danger' : 'il-safe'}">
                            ${pool.il_risk === 'yes'
                ? '<span class="warn">🛡️ High</span>'
                : '<span class="good">🛡️ None</span>'}
                        </div>
                    </div>
                    <div class="detail-card">
                        <div class="detail-label">Type</div>
                        <div class="detail-icon-bg">${PoolIcons.coins}</div>
                        <div class="detail-value">${pool.pool_type === 'stable' ? '🟢 Stable' : '🟠 Volatile'}</div>
                    </div>
                </div>
                
                <div class="detail-section premium-analysis">
                    <div class="section-header">
                        <h3>📊 Market Dynamics</h3>
                        ${this.isEpochProtocol(pool.project) ? `
                            <div class="epoch-timer" title="${pool.project} rewards reset each epoch (Wednesday 00:00 UTC)">
                                ⏳ Epoch ends in: ${epoch.display}
                            </div>
                        ` : ''}
                    </div>
                    
                    ${pool.premium_insights?.length > 0 ? `
                        <div class="smart-insights">
                            ${pool.premium_insights.map(insight => `
                                <div class="insight-item ${insight.type}">
                                    <span class="insight-icon">${insight.icon === '🟢' || insight.icon === '✅' ? PoolIcons.check :
                        insight.icon === '🔴' || insight.icon === '⚠️' ? PoolIcons.risk :
                            PoolIcons.activity
                    }</span>
                                    <span class="insight-text">${insight.text}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    <div class="metrics-grid">
                        ${pool.apy_base !== undefined ? `
                            <div class="metric-card">
                                <span class="metric-label">APY Composition</span>
                                <div class="apy-breakdown">
                                    <div class="apy-part base" title="Base Yield">
                                        <span class="dot"></span> Base: ${pool.apy_base}%
                                    </div>
                                    <div class="apy-part reward" title="Reward Yield - paid in ${formatRewardTokenName(pool.reward_token)}">
                                        <span class="dot"></span> Reward (${formatRewardTokenName(pool.reward_token)}): ${pool.apy_reward}%
                                        ${pool.pool_type !== 'stable' ? '<span class="reward-warning" title="Rewards paid in volatile token">⚠️</span>' : ''}
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                        
                        ${pool.tvl_change_7d !== undefined ? `
                            <div class="metric-card">
                                <span class="metric-label">7D TVL Trend</span>
                                <span class="metric-value ${pool.tvl_change_7d >= 0 ? 'good' : 'bad'}">
                                    ${pool.tvl_change_7d >= 0 ? PoolIcons.trendUp : PoolIcons.trendDown}
                                    ${Math.abs(pool.tvl_change_7d)}%
                                </span>
                            </div>
                        ` : ''}

                        ${pool.volume_24h_formatted ? `
                            <div class="metric-card">
                                <span class="metric-label">24h Volume</span>
                                <span class="metric-value">${pool.volume_24h_formatted}</span>
                            </div>
                        ` : ''}
                    </div>

                    ${pool.risk_reasons?.length > 0 ? `
                        <div class="risk-factors">
                            <h4>Risk Factors:</h4>
                            <ul class="risk-list">
                                ${pool.risk_reasons.map(r => `<li>• ${r}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
                
                ${pool.verification ? `
                    <div class="detail-section verified">
                        <h3>${PoolIcons.bot} Agent Verification</h3>
                        <div class="verification-grid">
                            <div class="verify-item ${pool.verification.deposit_ok ? 'ok' : 'fail'}">
                                ${pool.verification.deposit_ok ? '✅' : '❌'} Deposit Check
                            </div>
                            <div class="verify-item ${pool.verification.withdraw_ok ? 'ok' : 'fail'}">
                                ${pool.verification.withdraw_ok ? '✅' : '❌'} Withdraw Check
                            </div>
                        </div>
                        ${pool.verification.guardian_notes?.length > 0 ? `
                            <div class="verify-notes">
                                <strong>Guardian Notes:</strong>
                                ${pool.verification.guardian_notes.map(n => `<p>• ${n}</p>`).join('')}
                            </div>
                        ` : ''}
                        ${pool.verification.airdrop_potential && pool.verification.airdrop_potential !== 'None' ? `
                            <div class="airdrop-info">
                                <span class="airdrop-badge">${pool.verification.airdrop_potential} Airdrop Potential</span>
                                ${pool.verification.airdrop_notes?.map(n => `<span class="note">• ${n}</span>`).join('')}
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
                
                <div class="pool-detail-actions">
                    <a href="${pool.pool_link || (getPoolUrl ? getPoolUrl(pool) : '#')}" target="_blank" class="btn-primary-large" onclick="event.stopPropagation();" title="Open pool on ${pool.project}">
                        💰 Deposit on ${pool.project}
                    </a>
                    <button class="btn-secondary-large" onclick="PoolDetailModal.addToStrategy()">
                        + Add to Strategy
                    </button>
                    <button class="btn-outline-large" onclick="YieldComparison?.addPool(PoolDetailModal.currentPool)">
                        📊 Compare
                    </button>
                </div>
            </div>
        `;

        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    },

    close() {
        const modal = document.getElementById('poolDetailModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    },

    addToStrategy() {
        if (this.currentPool && window.addToStrategy) {
            addToStrategy(this.currentPool.id || this.currentPool.pool);
        }
        this.close();
    }
};

// ============================================
// CSS FOR POOL DETAIL MODAL
// ============================================
const detailStyles = document.createElement('style');
detailStyles.textContent = `
    .pool-detail-overlay {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.8);
        backdrop-filter: blur(8px);
        z-index: 2000;
        justify-content: center;
        align-items: center;
        padding: var(--space-6);
    }
    
    .pool-detail-modal {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-xl);
        max-width: 650px;
        width: 100%;
        max-height: 95vh;
        overflow-y: auto;
        padding: var(--space-3);
        position: relative;
    }
    
    /* Trust Links */
    .trust-links {
        position: absolute;
        top: var(--space-4);
        right: 50px;
        display: flex;
        gap: var(--space-3);
        z-index: 10;
    }
    
    .trust-links a {
        font-size: 0.75rem;
        color: var(--text-muted);
        text-decoration: none;
        padding: 6px 10px;
        background: var(--bg-elevated);
        border-radius: var(--radius-sm);
        transition: var(--transition-base);
        display: flex;
        align-items: center;
        gap: 4px;
        cursor: pointer;
    }
    
    .trust-links a:hover {
        color: var(--gold);
        background: rgba(234, 179, 8, 0.15);
    }
    
    .trust-links a svg {
        width: 14px;
        height: 14px;
    }
    
    .modal-close {
        z-index: 20;
        position: relative;
    }
    
    /* Epoch Timer */
    .epoch-timer {
        font-size: 0.75rem;
        color: #FBBF24;
        background: rgba(251, 191, 36, 0.1);
        padding: 4px 10px;
        border-radius: var(--radius-sm);
        margin-left: auto;
    }
    
    .section-header {
        display: flex;
        align-items: center;
        gap: var(--space-3);
    }
    
    /* IL Risk Colors */
    .detail-card.il-high {
        border: 1px solid rgba(239, 68, 68, 0.3);
        background: rgba(239, 68, 68, 0.05);
    }
    
    .detail-card.il-none {
        border: 1px solid rgba(16, 185, 129, 0.3);
        background: rgba(16, 185, 129, 0.05);
    }
    
    .detail-value.il-danger { color: #EF4444; }
    .detail-value.il-safe { color: #10B981; }
    
    /* Reward Warning */
    .reward-warning {
        margin-left: 4px;
        cursor: help;
    }
    
    .pool-detail-header {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        margin-bottom: var(--space-3);
        padding-bottom: var(--space-3);
        border-bottom: 1px solid var(--border);
    }
    
    .pool-detail-icon img {
        width: 64px;
        height: 64px;
        border-radius: var(--radius-lg);
    }
    
    .pool-detail-title {
        flex: 1;
    }
    
    .pool-detail-title h2 {
        font-size: 1.5rem;
        margin: 0 0 var(--space-2);
    }
    
    .pool-detail-meta {
        display: flex;
        align-items: center;
        gap: var(--space-2);
        color: var(--text-muted);
    }
    
    .pool-detail-meta .symbol {
        font-weight: 500;
    }
    
    .pool-detail-meta .chain-badge {
        width: 18px;
        height: 18px;
        border-radius: 50%;
    }
    
    .niche-badge {
        background: rgba(139, 92, 246, 0.15);
        color: #A78BFA;
        padding: 2px 8px;
        border-radius: var(--radius-sm);
        font-size: 0.7rem;
        font-weight: 600;
    }
    
    .pool-detail-apy {
        text-align: right;
    }
    
    .pool-detail-apy .apy-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--gold);
        display: block;
    }
    
    .pool-detail-apy .apy-label {
        font-size: 0.8rem;
        color: var(--text-muted);
    }
    
    .pool-detail-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: var(--space-2);
        margin-bottom: var(--space-3);
    }
    
    .detail-card {
        background: var(--bg-elevated);
        border-radius: var(--radius-md);
        padding: var(--space-2);
        text-align: center;
    }
    
    .detail-label {
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-bottom: var(--space-1);
    }
    
    .detail-value {
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .detail-value.risk-low { color: var(--success); }
    .detail-value.risk-medium { color: #FBBF24; }
    .detail-value.risk-high { color: #EF4444; }
    
    .detail-section {
        background: var(--bg-elevated);
        border-radius: var(--radius-lg);
        padding: var(--space-3);
        margin-bottom: var(--space-3);
    }
    
    .detail-section h3 {
        font-size: 0.9rem;
        margin: 0 0 var(--space-3);
    }
    
    .detail-section.verified {
        border: 1px solid var(--success);
        background: rgba(16, 185, 129, 0.05);
    }
    
    .risk-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    
    .risk-list li {
        font-size: 0.85rem;
        color: var(--text-secondary);
        padding: var(--space-1) 0;
    }
    
    .verification-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: var(--space-2);
        margin-bottom: var(--space-3);
    }
    
    .verify-item {
        padding: var(--space-2);
        border-radius: var(--radius-sm);
        font-size: 0.85rem;
        text-align: center;
    }
    
    .verify-item.ok { background: rgba(16, 185, 129, 0.1); }
    .verify-item.fail { background: rgba(239, 68, 68, 0.1); }
    
    .verify-notes {
        font-size: 0.8rem;
        color: var(--text-secondary);
    }
    
    .verify-notes p {
        margin: var(--space-1) 0;
    }
    
    .airdrop-info {
        margin-top: var(--space-3);
        padding-top: var(--space-3);
        border-top: 1px solid var(--border);
    }
    
    .airdrop-info .airdrop-badge {
        background: rgba(236, 72, 153, 0.15);
        color: #EC4899;
        padding: var(--space-1) var(--space-2);
        border-radius: var(--radius-sm);
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .airdrop-info .note {
        display: block;
        font-size: 0.8rem;
        color: var(--text-muted);
        margin-top: var(--space-2);
    }
    
    .pool-detail-actions {
        display: flex;
        gap: var(--space-2);
        margin-top: var(--space-3);
    }
    
    .btn-primary-large {
        flex: 2;
        padding: var(--space-3) var(--space-4);
        background: var(--gradient-gold);
        border: none;
        border-radius: var(--radius-lg);
        color: var(--bg-void);
        font-weight: 700;
        font-size: 1rem;
        text-decoration: none;
        text-align: center;
        cursor: pointer;
        transition: var(--transition-base);
    }
    
    .btn-primary-large:hover {
        filter: brightness(1.1);
        transform: translateY(-2px);
    }
    
    .btn-secondary-large, .btn-outline-large {
        flex: 1;
        padding: var(--space-4) var(--space-3);
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        color: var(--text-primary);
        font-weight: 600;
        font-size: 0.9rem;
        cursor: pointer;
        transition: var(--transition-base);
    }
    
    .btn-secondary-large:hover, .btn-outline-large:hover {
        border-color: var(--gold);
        color: var(--gold);
    }
    
    @media (max-width: 600px) {
        .pool-detail-grid {
            grid-template-columns: repeat(2, 1fr);
        }
        
        .pool-detail-actions {
            flex-direction: column;
        }
    }
`;
document.head.appendChild(detailStyles);

// Export
window.PoolDetailModal = PoolDetailModal;
