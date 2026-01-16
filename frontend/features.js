/**
 * Techne Protocol - Premium Features
 * $1B Protocol Quality Components
 */

// ============================================
// DEMO POOLS - Static preview data
// ============================================
const DEMO_POOLS = [
    {
        id: 'demo-1',
        project: 'Aerodrome',
        symbol: 'USDC-USDT',
        chain: 'Base',
        apy: 12.45,
        tvl: 45000000,
        risk_score: 'Low',
        stablecoin: true,
        airdrop: false,
        verified: true
    },
    {
        id: 'demo-2',
        project: 'Aave',
        symbol: 'USDC',
        chain: 'Base',
        apy: 8.32,
        tvl: 120000000,
        risk_score: 'Low',
        stablecoin: true,
        airdrop: false,
        verified: true
    },
    {
        id: 'demo-3',
        project: 'Morpho',
        symbol: 'USDC-ETH',
        chain: 'Base',
        apy: 18.75,
        tvl: 28000000,
        risk_score: 'Medium',
        stablecoin: false,
        airdrop: true,
        verified: true
    },
    {
        id: 'demo-4',
        project: 'Compound',
        symbol: 'USDC',
        chain: 'Ethereum',
        apy: 6.89,
        tvl: 850000000,
        risk_score: 'Low',
        stablecoin: true,
        airdrop: false,
        verified: true
    },
    {
        id: 'demo-5',
        project: 'Pendle',
        symbol: 'PT-stETH',
        chain: 'Ethereum',
        apy: 24.50,
        tvl: 156000000,
        risk_score: 'Medium',
        stablecoin: false,
        airdrop: true,
        verified: true
    },
    {
        id: 'demo-6',
        project: 'Curve',
        symbol: '3pool',
        chain: 'Ethereum',
        apy: 4.25,
        tvl: 420000000,
        risk_score: 'Low',
        stablecoin: true,
        airdrop: false,
        verified: true
    },
    {
        id: 'demo-7',
        project: 'Kamino',
        symbol: 'USDC-SOL',
        chain: 'Solana',
        apy: 32.15,
        tvl: 89000000,
        risk_score: 'Medium',
        stablecoin: false,
        airdrop: true,
        verified: true
    },
    {
        id: 'demo-8',
        project: 'Marinade',
        symbol: 'mSOL',
        chain: 'Solana',
        apy: 7.82,
        tvl: 340000000,
        risk_score: 'Low',
        stablecoin: false,
        airdrop: false,
        verified: true
    }
];

// ============================================
// APY CALCULATOR
// ============================================
const APYCalculator = {
    container: null,

    init() {
        this.createWidget();
    },

    createWidget() {
        const widget = document.createElement('div');
        widget.id = 'apyCalculator';
        widget.className = 'apy-calculator-widget';
        widget.innerHTML = `
            <div class="calc-header">
                <span>📊</span>
                <h3>Yield Calculator</h3>
            </div>
            <div class="calc-body">
                <div class="calc-input-group">
                    <label>Investment Amount</label>
                    <div class="input-with-currency">
                        <input type="number" id="calcAmount" value="10000" min="0">
                        <span>USD</span>
                    </div>
                </div>
                <div class="calc-input-group">
                    <label>APY</label>
                    <div class="input-with-currency">
                        <input type="number" id="calcApy" value="12.5" min="0" max="500" step="0.1">
                        <span>%</span>
                    </div>
                </div>
                <div class="calc-input-group">
                    <label>Duration</label>
                    <select id="calcDuration">
                        <option value="30">1 Month</option>
                        <option value="90">3 Months</option>
                        <option value="180">6 Months</option>
                        <option value="365" selected>1 Year</option>
                    </select>
                </div>
                <div class="calc-results">
                    <div class="result-row">
                        <span>Total Return</span>
                        <span class="result-value" id="calcReturn">$0</span>
                    </div>
                    <div class="result-row">
                        <span>Profit</span>
                        <span class="result-value profit" id="calcProfit">+$0</span>
                    </div>
                    <div class="result-row small">
                        <span>Daily</span>
                        <span id="calcDaily">$0/day</span>
                    </div>
                </div>
            </div>
        `;

        // Add to sidebar
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.appendChild(widget);
            this.bindEvents();
            this.calculate();
        }
    },

    bindEvents() {
        ['calcAmount', 'calcApy', 'calcDuration'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', () => this.calculate());
        });
    },

    calculate() {
        const amount = parseFloat(document.getElementById('calcAmount')?.value) || 0;
        const apy = parseFloat(document.getElementById('calcApy')?.value) || 0;
        const days = parseInt(document.getElementById('calcDuration')?.value) || 365;

        // Compound daily
        const dailyRate = apy / 100 / 365;
        const totalReturn = amount * Math.pow(1 + dailyRate, days);
        const profit = totalReturn - amount;
        const daily = profit / days;

        document.getElementById('calcReturn').textContent = `$${totalReturn.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
        document.getElementById('calcProfit').textContent = `+$${profit.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
        document.getElementById('calcDaily').textContent = `$${daily.toFixed(2)}/day`;
    }
};

// ============================================
// YIELD COMPARISON
// ============================================
const YieldComparison = {
    pools: [],

    init() {
        this.createModal();
    },

    addPool(pool) {
        if (this.pools.length >= 5) {
            alert('Maximum 5 pools for comparison');
            return;
        }
        if (this.pools.find(p => p.id === pool.id)) {
            return; // Already added
        }
        this.pools.push(pool);
        this.updateBadge();
    },

    removePool(poolId) {
        this.pools = this.pools.filter(p => p.id !== poolId);
        this.updateBadge();
    },

    updateBadge() {
        let badge = document.getElementById('compareBadge');
        if (!badge && this.pools.length > 0) {
            badge = document.createElement('button');
            badge.id = 'compareBadge';
            badge.className = 'compare-badge';
            badge.onclick = () => this.showComparison();
            document.body.appendChild(badge);
        }
        if (badge) {
            badge.innerHTML = `📊 Compare (${this.pools.length})`;
            badge.style.display = this.pools.length > 0 ? 'flex' : 'none';
        }
    },

    createModal() {
        // Modal created on demand
    },

    showComparison() {
        if (this.pools.length < 2) {
            alert('Add at least 2 pools to compare');
            return;
        }

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'compareModal';
        modal.innerHTML = `
            <div class="modal-container compare-modal">
                <button class="modal-close" onclick="document.getElementById('compareModal').remove()">✕</button>
                <h2>Pool Comparison</h2>
                
                <div class="compare-table">
                    <div class="compare-header">
                        <div class="compare-cell">Pool</div>
                        <div class="compare-cell">APY</div>
                        <div class="compare-cell">TVL</div>
                        <div class="compare-cell">Risk</div>
                        <div class="compare-cell">$10K/Year</div>
                    </div>
                    ${this.pools.map(pool => `
                        <div class="compare-row">
                            <div class="compare-cell">
                                <img src="${window.getProtocolIconUrl ? getProtocolIconUrl(pool.project) : '/icons/protocols/' + pool.project?.toLowerCase().replace(/\\s+/g, '-') + '.png'}" width="24" onerror="this.style.display='none'">
                                <div>
                                    <strong>${pool.project}</strong>
                                    <small>${pool.symbol}</small>
                                </div>
                            </div>
                            <div class="compare-cell apy">${pool.apy?.toFixed(2)}%</div>
                            <div class="compare-cell">${formatTvl(pool.tvl)}</div>
                            <div class="compare-cell risk-${pool.risk_score?.toLowerCase()}">${pool.risk_score}</div>
                            <div class="compare-cell profit">+$${(10000 * pool.apy / 100).toFixed(0)}</div>
                        </div>
                    `).join('')}
                </div>
                
                <div class="compare-summary">
                    <p>Best APY: <strong>${this.pools.reduce((max, p) => p.apy > max.apy ? p : max).project}</strong></p>
                    <p>Lowest Risk: <strong>${this.pools.find(p => p.risk_score === 'Low')?.project || 'N/A'}</strong></p>
                </div>
                
                <button class="btn-clear-compare" onclick="YieldComparison.clearAll()">Clear All</button>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    },

    clearAll() {
        this.pools = [];
        this.updateBadge();
        document.getElementById('compareModal')?.remove();
    }
};

// ============================================
// PORTFOLIO SIMULATOR
// ============================================
const PortfolioSimulator = {
    allocations: [],

    addAllocation(pool, percentage) {
        this.allocations.push({ pool, percentage });
    },

    simulate(totalAmount) {
        let totalReturn = 0;

        this.allocations.forEach(({ pool, percentage }) => {
            const allocated = totalAmount * (percentage / 100);
            const yearlyReturn = allocated * (pool.apy / 100);
            totalReturn += yearlyReturn;
        });

        return {
            invested: totalAmount,
            yearlyReturn: totalReturn,
            monthlyReturn: totalReturn / 12,
            dailyReturn: totalReturn / 365,
            effectiveApy: (totalReturn / totalAmount) * 100
        };
    }
};

// ============================================
// ALERTS SYSTEM
// ============================================
const AlertsSystem = {
    alerts: [],

    init() {
        this.loadAlerts();
        this.createWidget();
    },

    loadAlerts() {
        const saved = localStorage.getItem('techne_alerts');
        if (saved) {
            this.alerts = JSON.parse(saved);
        }
    },

    saveAlerts() {
        localStorage.setItem('techne_alerts', JSON.stringify(this.alerts));
    },

    addAlert(type, config) {
        const alert = {
            id: Date.now().toString(),
            type, // 'apy_above', 'apy_below', 'tvl_change', 'new_pool'
            config,
            created: new Date().toISOString(),
            triggered: false
        };
        this.alerts.push(alert);
        this.saveAlerts();
        return alert;
    },

    removeAlert(id) {
        this.alerts = this.alerts.filter(a => a.id !== id);
        this.saveAlerts();
    },

    createWidget() {
        // Add alerts button to header if not exists
        const header = document.querySelector('.header-actions');
        if (header && !document.getElementById('alertsBtn')) {
            const btn = document.createElement('button');
            btn.id = 'alertsBtn';
            btn.className = 'btn-alerts';
            btn.innerHTML = `🔔 <span class="alert-count">${this.alerts.length}</span>`;
            btn.onclick = () => this.showAlertsModal();
            header.insertBefore(btn, header.firstChild);
        }
    },

    showAlertsModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'alertsModal';
        modal.innerHTML = `
            <div class="modal-container alerts-modal">
                <button class="modal-close" onclick="document.getElementById('alertsModal').remove()">✕</button>
                <h2>🔔 Price Alerts</h2>
                
                <div class="alert-form">
                    <h3>Create Alert</h3>
                    <select id="alertType">
                        <option value="apy_above">APY Above</option>
                        <option value="apy_below">APY Below</option>
                        <option value="new_pool">New Pool</option>
                    </select>
                    <input type="number" id="alertValue" placeholder="Value %" min="0" max="500">
                    <button onclick="AlertsSystem.createAlertFromForm()">Create</button>
                </div>
                
                <div class="alerts-list">
                    <h3>Active Alerts (${this.alerts.length})</h3>
                    ${this.alerts.length === 0 ? '<p class="no-alerts">No active alerts</p>' : ''}
                    ${this.alerts.map(a => `
                        <div class="alert-item">
                            <span class="alert-type">${a.type.replace('_', ' ')}</span>
                            <span class="alert-value">${a.config.value || ''}${a.config.value ? '%' : ''}</span>
                            <button onclick="AlertsSystem.removeAlert('${a.id}')">✕</button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    },

    createAlertFromForm() {
        const type = document.getElementById('alertType')?.value;
        const value = parseFloat(document.getElementById('alertValue')?.value);

        if (type && (value || type === 'new_pool')) {
            this.addAlert(type, { value });
            document.getElementById('alertsModal')?.remove();
            this.showAlertsModal();
        }
    }
};

// ============================================
// LIVE STATS TICKER
// ============================================
const LiveStats = {
    init() {
        this.createTicker();
        this.startUpdates();
    },

    createTicker() {
        const ticker = document.createElement('div');
        ticker.id = 'liveTicker';
        ticker.className = 'live-ticker';
        ticker.innerHTML = `
            <div class="ticker-content">
                <div class="ticker-item">
                    <span class="ticker-label">Total TVL</span>
                    <span class="ticker-value" id="tickerTvl">$2.4B</span>
                </div>
                <div class="ticker-item">
                    <span class="ticker-label">24h Volume</span>
                    <span class="ticker-value" id="tickerVolume">$145M</span>
                </div>
                <div class="ticker-item">
                    <span class="ticker-label">Active Users</span>
                    <span class="ticker-value" id="tickerUsers">12.4K</span>
                </div>
                <div class="ticker-item">
                    <span class="ticker-label">Avg APY</span>
                    <span class="ticker-value" id="tickerApy">14.2%</span>
                </div>
                <div class="ticker-item">
                    <span class="ticker-label">Pools Tracked</span>
                    <span class="ticker-value" id="tickerPools">847</span>
                </div>
            </div>
        `;

        const header = document.querySelector('.header');
        if (header) {
            header.insertAdjacentElement('afterend', ticker);
        }
    },

    startUpdates() {
        // Simulate live updates
        setInterval(() => {
            const tvl = (2.3 + Math.random() * 0.2).toFixed(1);
            const volume = (140 + Math.random() * 20).toFixed(0);
            const users = (12 + Math.random() * 1).toFixed(1);
            const apy = (13 + Math.random() * 2).toFixed(1);

            document.getElementById('tickerTvl').textContent = `$${tvl}B`;
            document.getElementById('tickerVolume').textContent = `$${volume}M`;
            document.getElementById('tickerUsers').textContent = `${users}K`;
            document.getElementById('tickerApy').textContent = `${apy}%`;
        }, 5000);
    }
};

// ============================================
// INITIALIZE ALL FEATURES
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for main app to load
    setTimeout(() => {
        // APYCalculator.init(); // Disabled - removed yield calculator
        YieldComparison.init();
        AlertsSystem.init();
        // LiveStats.init(); // Disabled - removed ticker bar per user request
    }, 500);
});

// ============================================
// CSS FOR PREMIUM FEATURES
// ============================================
const premiumStyles = document.createElement('style');
premiumStyles.textContent = `
    /* APY Calculator Widget */
    .apy-calculator-widget {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        overflow: hidden;
        margin-top: var(--space-4);
    }
    
    .calc-header {
        display: flex;
        align-items: center;
        gap: var(--space-2);
        padding: var(--space-3) var(--space-4);
        background: var(--gold-subtle);
        border-bottom: 1px solid var(--border);
    }
    
    .calc-header h3 {
        font-size: 0.9rem;
        font-weight: 600;
        margin: 0;
    }
    
    .calc-body {
        padding: var(--space-4);
    }
    
    .calc-input-group {
        margin-bottom: var(--space-3);
    }
    
    .calc-input-group label {
        display: block;
        font-size: 0.75rem;
        color: var(--text-muted);
        margin-bottom: var(--space-1);
    }
    
    .input-with-currency {
        display: flex;
        align-items: center;
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        overflow: hidden;
    }
    
    .input-with-currency input {
        flex: 1;
        padding: var(--space-2) var(--space-3);
        border: none;
        background: transparent;
        color: var(--text);
        font-size: 0.9rem;
    }
    
    .input-with-currency span {
        padding: var(--space-2) var(--space-3);
        background: var(--bg-void);
        color: var(--text-muted);
        font-size: 0.75rem;
    }
    
    .calc-input-group select {
        width: 100%;
        padding: var(--space-2) var(--space-3);
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        color: var(--text);
        font-size: 0.9rem;
    }
    
    .calc-results {
        background: var(--bg-elevated);
        border-radius: var(--radius-md);
        padding: var(--space-3);
        margin-top: var(--space-3);
    }
    
    .result-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: var(--space-2) 0;
    }
    
    .result-row:not(:last-child) {
        border-bottom: 1px solid var(--border);
    }
    
    .result-row.small {
        font-size: 0.8rem;
        color: var(--text-muted);
    }
    
    .result-value {
        font-weight: 700;
        font-size: 1.1rem;
    }
    
    .result-value.profit {
        color: var(--success);
    }
    
    /* Live Ticker */
    .live-ticker {
        background: linear-gradient(90deg, var(--bg-card), var(--bg-elevated), var(--bg-card));
        border-bottom: 1px solid var(--border);
        padding: var(--space-2) var(--space-4);
        overflow: hidden;
    }
    
    .ticker-content {
        display: flex;
        justify-content: center;
        gap: var(--space-8);
        animation: ticker-scroll 30s linear infinite;
    }
    
    @keyframes ticker-scroll {
        0% { transform: translateX(0); }
        100% { transform: translateX(-10%); }
    }
    
    .ticker-item {
        display: flex;
        align-items: center;
        gap: var(--space-2);
        white-space: nowrap;
    }
    
    .ticker-label {
        font-size: 0.75rem;
        color: var(--text-muted);
    }
    
    .ticker-value {
        font-weight: 700;
        color: var(--gold);
    }
    
    /* Compare Badge */
    .compare-badge {
        position: fixed;
        bottom: var(--space-6);
        right: var(--space-6);
        display: flex;
        align-items: center;
        gap: var(--space-2);
        padding: var(--space-3) var(--space-5);
        background: var(--gradient-gold);
        border: none;
        border-radius: var(--radius-pill);
        color: var(--bg-void);
        font-weight: 700;
        cursor: pointer;
        box-shadow: var(--shadow-gold);
        z-index: 1000;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    
    /* Compare Modal */
    .compare-modal {
        max-width: 700px;
    }
    
    .compare-table {
        margin: var(--space-4) 0;
    }
    
    .compare-header {
        display: grid;
        grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
        gap: var(--space-3);
        padding: var(--space-2);
        background: var(--bg-elevated);
        border-radius: var(--radius-md);
        font-size: 0.75rem;
        color: var(--text-muted);
        font-weight: 600;
    }
    
    .compare-row {
        display: grid;
        grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
        gap: var(--space-3);
        padding: var(--space-3) var(--space-2);
        border-bottom: 1px solid var(--border);
        align-items: center;
    }
    
    .compare-cell {
        display: flex;
        align-items: center;
        gap: var(--space-2);
    }
    
    .compare-cell.apy {
        color: var(--gold);
        font-weight: 700;
    }
    
    .compare-cell.profit {
        color: var(--success);
        font-weight: 600;
    }
    
    .compare-summary {
        background: var(--bg-elevated);
        padding: var(--space-3);
        border-radius: var(--radius-md);
    }
    
    .btn-clear-compare {
        width: 100%;
        padding: var(--space-3);
        background: transparent;
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        color: var(--text-muted);
        cursor: pointer;
        margin-top: var(--space-3);
    }
    
    /* Alerts */
    .btn-alerts {
        display: flex;
        align-items: center;
        gap: var(--space-2);
        padding: var(--space-2) var(--space-3);
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        color: var(--text);
        cursor: pointer;
    }
    
    .alert-count {
        background: var(--gold);
        color: var(--bg-void);
        padding: 2px 6px;
        border-radius: var(--radius-pill);
        font-size: 0.7rem;
        font-weight: 700;
    }
    
    .alerts-modal {
        max-width: 400px;
    }
    
    .alert-form {
        background: var(--bg-elevated);
        padding: var(--space-4);
        border-radius: var(--radius-md);
        margin: var(--space-4) 0;
    }
    
    .alert-form h3 {
        font-size: 0.85rem;
        margin-bottom: var(--space-3);
    }
    
    .alert-form select,
    .alert-form input {
        width: 100%;
        padding: var(--space-2);
        margin-bottom: var(--space-2);
        background: var(--bg-void);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        color: var(--text);
    }
    
    .alert-form button {
        width: 100%;
        padding: var(--space-2);
        background: var(--gradient-gold);
        border: none;
        border-radius: var(--radius-md);
        color: var(--bg-void);
        font-weight: 600;
        cursor: pointer;
    }
    
    .alerts-list {
        max-height: 300px;
        overflow-y: auto;
    }
    
    .alert-item {
        display: flex;
        align-items: center;
        gap: var(--space-3);
        padding: var(--space-2);
        background: var(--bg-elevated);
        border-radius: var(--radius-md);
        margin-bottom: var(--space-2);
    }
    
    .alert-type {
        flex: 1;
        text-transform: capitalize;
    }
    
    .no-alerts {
        text-align: center;
        color: var(--text-muted);
        padding: var(--space-4);
    }
    
    /* Add compare button to pool cards */
    .btn-compare {
        padding: var(--space-1) var(--space-2);
        background: transparent;
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        color: var(--text-muted);
        font-size: 0.7rem;
        cursor: pointer;
    }
    
    .btn-compare:hover {
        border-color: var(--gold);
        color: var(--gold);
    }
`;
document.head.appendChild(premiumStyles);

// Export globals
window.DEMO_POOLS = DEMO_POOLS;
window.APYCalculator = APYCalculator;
window.YieldComparison = YieldComparison;
window.PortfolioSimulator = PortfolioSimulator;
window.AlertsSystem = AlertsSystem;
window.LiveStats = LiveStats;
