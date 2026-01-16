/**
 * Techne Protocol - Interactive Components
 * Deposit Modal, Strategy Builder, Portfolio
 */

// ===========================================
// DEPOSIT MODAL
// ===========================================
const DepositModal = {
    isOpen: false,
    selectedPool: null,
    selectedToken: null,
    amount: '',

    open(pool) {
        this.selectedPool = pool;
        this.amount = '';
        this.isOpen = true;
        this.render();
    },

    close() {
        this.isOpen = false;
        document.getElementById('depositModal')?.remove();
    },

    render() {
        const existing = document.getElementById('depositModal');
        if (existing) existing.remove();

        const pool = this.selectedPool;
        const protocolIcon = window.getProtocolIconUrl ? getProtocolIconUrl(pool?.project) : `/icons/protocols/${pool?.project?.toLowerCase().replace(/\s+/g, '-')}.png`;
        const chainIcon = window.getChainIconUrl ? getChainIconUrl(pool?.chain) : `/icons/protocols/${pool?.chain?.toLowerCase()}.png`;

        const modal = document.createElement('div');
        modal.id = 'depositModal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-container deposit-modal">
                <button class="modal-close" onclick="DepositModal.close()">✕</button>
                
                <div class="modal-header">
                    <img src="${protocolIcon}" class="modal-protocol-icon" onerror="this.style.display='none'">
                    <div>
                        <h2>${pool?.project || 'Vault'}</h2>
                        <span class="modal-subtitle">${pool?.symbol || ''}</span>
                    </div>
                </div>
                
                <div class="deposit-info">
                    <div class="info-row">
                        <span class="label">Chain</span>
                        <span class="value">
                            <img src="${chainIcon}" width="16" height="16" style="border-radius:50%">
                            ${pool?.chain || 'Base'}
                        </span>
                    </div>
                    <div class="info-row">
                        <span class="label">Current APY</span>
                        <span class="value apy">${pool?.apy?.toFixed(2) || '0'}%</span>
                    </div>
                    <div class="info-row">
                        <span class="label">TVL</span>
                        <span class="value">${formatTvl(pool?.tvl)}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Risk Level</span>
                        <span class="value risk-${(pool?.risk_level || 'medium').toLowerCase()}">${pool?.risk_level || 'Medium'}</span>
                    </div>
                </div>
                
                <div class="deposit-form">
                    <label class="form-label">Amount to Deposit</label>
                    <div class="input-with-token">
                        <input type="number" id="depositAmount" placeholder="0.00" value="${this.amount}" 
                               onchange="DepositModal.amount = this.value">
                        <button class="token-selector" onclick="DepositModal.showTokenSelector()">
                            <img src="https://icons.llama.fi/usdc.png" width="20" height="20">
                            <span>USDC</span>
                            <span class="arrow">▼</span>
                        </button>
                    </div>
                    <div class="balance-row">
                        <span>Balance: 0.00 USDC</span>
                        <button class="btn-max" onclick="DepositModal.setMax()">MAX</button>
                    </div>
                </div>
                
                <div class="deposit-preview">
                    <div class="preview-row">
                        <span>Estimated Daily Yield</span>
                        <span class="positive">+$${this.calculateDailyYield()}</span>
                    </div>
                    <div class="preview-row">
                        <span>Monthly Projection</span>
                        <span class="positive">+$${this.calculateMonthlyYield()}</span>
                    </div>
                </div>
                
                <div class="deposit-actions">
                    <button class="btn-go-protocol" onclick="DepositModal.goToProtocol()" style="
                        background: var(--bg-elevated);
                        border: 1px solid var(--border);
                        color: var(--text);
                        padding: 12px 16px;
                        border-radius: 10px;
                        cursor: pointer;
                        margin-bottom: 8px;
                        width: 100%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                    ">
                        <span>🔗</span> Go to ${pool?.project || 'Protocol'} Website
                    </button>
                    <button class="btn-deposit-full" onclick="DepositModal.executeDeposit()">
                        <span>⚡</span> Deposit & Open Protocol
                    </button>
                </div>
                
                <div class="deposit-disclaimer">
                    Click "Go to Protocol" to deposit directly on ${pool?.project}. 
                    Your wallet will connect to their official app.
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.close();
        });
    },

    calculateDailyYield() {
        const amount = parseFloat(this.amount) || 0;
        const apy = this.selectedPool?.apy || 0;
        return ((amount * apy / 100) / 365).toFixed(2);
    },

    calculateMonthlyYield() {
        const amount = parseFloat(this.amount) || 0;
        const apy = this.selectedPool?.apy || 0;
        return ((amount * apy / 100) / 12).toFixed(2);
    },

    setMax() {
        // Would get balance from wallet
        document.getElementById('depositAmount').value = '0';
    },

    showTokenSelector() {
        console.log('Token selector');
    },

    // Protocol deposit URLs
    getProtocolUrl(pool) {
        const protocols = {
            'aave': `https://app.aave.com/reserve-overview/?underlyingAsset=${pool?.symbol?.toLowerCase() || 'usdc'}&marketName=proto_${pool?.chain?.toLowerCase() || 'base'}_v3`,
            'aave v3': `https://app.aave.com/reserve-overview/?underlyingAsset=${pool?.symbol?.toLowerCase() || 'usdc'}&marketName=proto_${pool?.chain?.toLowerCase() || 'base'}_v3`,
            'compound': 'https://app.compound.finance/markets',
            'compound v3': 'https://app.compound.finance/markets',
            'morpho': 'https://app.morpho.org/earn',
            'morpho blue': 'https://app.morpho.org/earn',
            'curve': 'https://curve.fi/#/pools',
            'uniswap': 'https://app.uniswap.org/pool',
            'aerodrome': 'https://aerodrome.finance/liquidity',
            'moonwell': 'https://moonwell.fi/base/supply',
            'fluid': 'https://fluid.instadapp.io/',
            'euler': 'https://app.euler.finance/',
            'euler v2': 'https://app.euler.finance/',
            'spark': 'https://app.spark.fi/',
            'kamino': 'https://app.kamino.finance/lend',
            'marginfi': 'https://app.marginfi.com/',
            'drift': 'https://app.drift.trade/earn',
            'solend': 'https://solend.fi/dashboard',
            'lido': 'https://stake.lido.fi/',
            'pendle': 'https://app.pendle.finance/trade/pools',
            'gmx': 'https://app.gmx.io/#/earn',
            'yearn': 'https://yearn.fi/vaults',
            'convex': 'https://www.convexfinance.com/stake'
        };

        const projectKey = (pool?.project || '').toLowerCase();
        return protocols[projectKey] || `https://defillama.com/yields/pool/${pool?.id || ''}`;
    },

    async executeDeposit() {
        if (!window.connectedWallet) {
            window.Toast?.show('Please connect wallet first', 'warning');
            connectWallet?.();
            return;
        }

        const amount = parseFloat(this.amount);
        if (!amount || amount <= 0) {
            window.Toast?.show('Please enter a valid amount', 'warning');
            return;
        }

        const pool = this.selectedPool;
        const protocolUrl = this.getProtocolUrl(pool);

        window.Toast?.show(`Opening ${pool?.project || 'protocol'}...`, 'info');

        // Open protocol in new tab
        setTimeout(() => {
            window.open(protocolUrl, '_blank');
            this.close();
            window.Toast?.show(`✅ Deposit $${amount} into ${pool?.project} at ${pool?.apy?.toFixed(2)}% APY`, 'success');
        }, 500);
    },

    goToProtocol() {
        const pool = this.selectedPool;
        const protocolUrl = this.getProtocolUrl(pool);
        window.open(protocolUrl, '_blank');
        window.Toast?.show(`Opening ${pool?.project}...`, 'info');
    }
};

// ===========================================
// STRATEGY BUILDER
// ===========================================
const StrategyBuilder = {
    components: [],
    selectedComponent: null,
    mode: 'visual', // 'visual' or 'code'

    strategyCode: `// Techne Strategy
// Define your custom yield strategy

const strategy = {
    name: "My Custom Strategy",
    
    // Entry conditions
    entryRules: {
        minApy: 10,
        maxRisk: "medium",
        chains: ["base", "arbitrum"],
        protocols: ["aave", "compound"]
    },
    
    // Allocation
    allocation: {
        type: "equal", // or "apy_weighted"
        maxPositions: 5,
        maxPerPosition: 25 // percent
    },
    
    // Exit conditions
    exitRules: {
        apyDropPercent: 20,
        maxDuration: 30, // days
        riskIncrease: true
    },
    
    // Rebalancing
    rebalance: {
        frequency: "weekly",
        minChange: 5 // percent
    }
};

module.exports = strategy;`,

    init() {
        this.setupDragDrop();
        this.setupModeToggle();
    },

    setupDragDrop() {
        const components = document.querySelectorAll('.component-item');
        const canvas = document.querySelector('.builder-canvas');

        if (!canvas) return;

        components.forEach(comp => {
            comp.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('type', comp.dataset.type);
                comp.classList.add('dragging');
            });

            comp.addEventListener('dragend', () => {
                comp.classList.remove('dragging');
            });
        });

        canvas.addEventListener('dragover', (e) => {
            e.preventDefault();
            canvas.classList.add('drag-over');
        });

        canvas.addEventListener('dragleave', () => {
            canvas.classList.remove('drag-over');
        });

        canvas.addEventListener('drop', (e) => {
            e.preventDefault();
            canvas.classList.remove('drag-over');

            const type = e.dataTransfer.getData('type');
            this.addComponent(type);
        });
    },

    setupModeToggle() {
        const modeBtn = document.querySelector('.btn-mode');
        if (modeBtn) {
            modeBtn.addEventListener('click', () => this.toggleMode());
        }
    },

    addComponent(type) {
        const component = {
            id: Date.now(),
            type,
            config: this.getDefaultConfig(type)
        };

        this.components.push(component);
        this.renderCanvas();
        this.selectComponent(component);
    },

    getDefaultConfig(type) {
        const defaults = {
            entry: { minApy: 10, maxRisk: 'medium', chains: ['base'] },
            filter: { stablecoinsOnly: false, minTvl: 1000000 },
            allocate: { type: 'equal', maxPositions: 5 },
            rebalance: { frequency: 'weekly' },
            exit: { apyDrop: 20, maxDays: 30 }
        };
        return defaults[type] || {};
    },

    selectComponent(component) {
        this.selectedComponent = component;
        this.renderConfig();
    },

    renderCanvas() {
        const canvas = document.querySelector('.builder-canvas');
        if (!canvas) return;

        if (this.components.length === 0) {
            canvas.innerHTML = `
                <div class="canvas-empty">
                    <p>Drag components here to build your strategy</p>
                    <span class="hint">or use Code Mode for advanced logic</span>
                </div>
            `;
            return;
        }

        canvas.innerHTML = `
            <div class="strategy-flow">
                ${this.components.map((comp, idx) => `
                    <div class="flow-node ${this.selectedComponent?.id === comp.id ? 'selected' : ''}"
                         onclick="StrategyBuilder.selectComponent(StrategyBuilder.components[${idx}])">
                        <span class="node-icon">${this.getComponentIcon(comp.type)}</span>
                        <span class="node-label">${this.getComponentLabel(comp.type)}</span>
                        <button class="node-delete" onclick="event.stopPropagation(); StrategyBuilder.removeComponent(${idx})">✕</button>
                    </div>
                    ${idx < this.components.length - 1 ? '<div class="flow-connector">↓</div>' : ''}
                `).join('')}
            </div>
        `;
    },

    getComponentIcon(type) {
        const icons = {
            entry: '📥',
            filter: '🔍',
            allocate: '⚖️',
            rebalance: '🔄',
            exit: '📤'
        };
        return icons[type] || '📦';
    },

    getComponentLabel(type) {
        const labels = {
            entry: 'Entry Condition',
            filter: 'Pool Filter',
            allocate: 'Allocation',
            rebalance: 'Rebalance',
            exit: 'Exit Condition'
        };
        return labels[type] || type;
    },

    removeComponent(idx) {
        this.components.splice(idx, 1);
        this.selectedComponent = null;
        this.renderCanvas();
        this.renderConfig();
    },

    renderConfig() {
        const configPanel = document.querySelector('.builder-config');
        if (!configPanel) return;

        if (!this.selectedComponent) {
            configPanel.innerHTML = `
                <h3>Configuration</h3>
                <p class="config-hint">Select a component to configure</p>
            `;
            return;
        }

        const comp = this.selectedComponent;
        const config = comp.config;

        let configHtml = `<h3>Configure ${this.getComponentLabel(comp.type)}</h3>`;

        switch (comp.type) {
            case 'entry':
                configHtml += `
                    <div class="config-field">
                        <label>Minimum APY</label>
                        <input type="number" value="${config.minApy}" 
                               onchange="StrategyBuilder.updateConfig('minApy', this.value)">
                    </div>
                    <div class="config-field">
                        <label>Max Risk Level</label>
                        <select onchange="StrategyBuilder.updateConfig('maxRisk', this.value)">
                            <option value="low" ${config.maxRisk === 'low' ? 'selected' : ''}>Low</option>
                            <option value="medium" ${config.maxRisk === 'medium' ? 'selected' : ''}>Medium</option>
                            <option value="high" ${config.maxRisk === 'high' ? 'selected' : ''}>High</option>
                        </select>
                    </div>
                    <div class="config-field">
                        <label>Chains</label>
                        <div class="chain-checkboxes">
                            <label><input type="checkbox" value="base" ${config.chains?.includes('base') ? 'checked' : ''} 
                                          onchange="StrategyBuilder.toggleChain('base')"> Base</label>
                            <label><input type="checkbox" value="arbitrum" ${config.chains?.includes('arbitrum') ? 'checked' : ''}
                                          onchange="StrategyBuilder.toggleChain('arbitrum')"> Arbitrum</label>
                            <label><input type="checkbox" value="ethereum" ${config.chains?.includes('ethereum') ? 'checked' : ''}
                                          onchange="StrategyBuilder.toggleChain('ethereum')"> Ethereum</label>
                        </div>
                    </div>
                `;
                break;

            case 'allocate':
                configHtml += `
                    <div class="config-field">
                        <label>Allocation Type</label>
                        <select onchange="StrategyBuilder.updateConfig('type', this.value)">
                            <option value="equal" ${config.type === 'equal' ? 'selected' : ''}>Equal Weight</option>
                            <option value="apy_weighted" ${config.type === 'apy_weighted' ? 'selected' : ''}>APY Weighted</option>
                            <option value="risk_adjusted" ${config.type === 'risk_adjusted' ? 'selected' : ''}>Risk Adjusted</option>
                        </select>
                    </div>
                    <div class="config-field">
                        <label>Max Positions</label>
                        <input type="number" value="${config.maxPositions}" min="1" max="20"
                               onchange="StrategyBuilder.updateConfig('maxPositions', parseInt(this.value))">
                    </div>
                `;
                break;

            case 'exit':
                configHtml += `
                    <div class="config-field">
                        <label>Exit when APY drops by (%)</label>
                        <input type="number" value="${config.apyDrop}" min="5" max="100"
                               onchange="StrategyBuilder.updateConfig('apyDrop', parseInt(this.value))">
                    </div>
                    <div class="config-field">
                        <label>Max Duration (days)</label>
                        <input type="number" value="${config.maxDays}" min="1" max="365"
                               onchange="StrategyBuilder.updateConfig('maxDays', parseInt(this.value))">
                    </div>
                `;
                break;

            default:
                configHtml += `<p class="config-hint">No configuration options</p>`;
        }

        configPanel.innerHTML = configHtml;
    },

    updateConfig(key, value) {
        if (this.selectedComponent) {
            this.selectedComponent.config[key] = value;
        }
    },

    toggleChain(chain) {
        if (!this.selectedComponent) return;

        const chains = this.selectedComponent.config.chains || [];
        const idx = chains.indexOf(chain);

        if (idx === -1) {
            chains.push(chain);
        } else {
            chains.splice(idx, 1);
        }

        this.selectedComponent.config.chains = chains;
    },

    toggleMode() {
        const canvas = document.querySelector('.builder-canvas');
        const modeBtn = document.querySelector('.btn-mode');

        if (this.mode === 'visual') {
            this.mode = 'code';
            modeBtn.innerHTML = '<span>📦</span> Visual Mode';
            canvas.innerHTML = `
                <div class="code-editor">
                    <textarea id="strategyCode" spellcheck="false">${this.strategyCode}</textarea>
                </div>
            `;
        } else {
            this.mode = 'visual';
            modeBtn.innerHTML = '<span>{ }</span> Code Mode';

            // Save code
            const codeEl = document.getElementById('strategyCode');
            if (codeEl) this.strategyCode = codeEl.value;

            this.renderCanvas();
        }
    },

    async runBacktest() {
        alert('Backtest functionality coming soon! This will simulate your strategy against historical data.');
    },

    async deployStrategy() {
        if (this.components.length === 0 && this.mode === 'visual') {
            alert('Please add at least one component to your strategy');
            return;
        }

        alert('Deploy functionality coming soon! Your strategy will be deployed as a vault.');
    }
};

// ===========================================
// PORTFOLIO TRACKER
// ===========================================
const PortfolioTracker = {
    positions: [],

    async loadPositions() {
        if (!connectedWallet) return;

        // Fetch from API
        try {
            const response = await fetch(`${API_BASE}/api/portfolio/${connectedWallet}`);
            if (response.ok) {
                const data = await response.json();
                this.positions = data.positions || [];
                this.render();
            }
        } catch (e) {
            console.log('Portfolio load error:', e);
        }
    },

    render() {
        const container = document.querySelector('#section-portfolio .empty-state');
        if (!container) return;

        if (this.positions.length === 0) {
            return; // Keep empty state
        }

        // Replace empty state with positions
        // ...
    },

    calculateTotalValue() {
        return this.positions.reduce((sum, p) => sum + (p.value || 0), 0);
    },

    calculateTotalPnl() {
        return this.positions.reduce((sum, p) => sum + (p.pnl || 0), 0);
    }
};

// ===========================================
// INIT
// ===========================================
document.addEventListener('DOMContentLoaded', () => {
    StrategyBuilder.init();

    // Add backtest handler
    const backtestBtn = document.querySelector('.btn-backtest');
    if (backtestBtn) {
        backtestBtn.addEventListener('click', () => StrategyBuilder.runBacktest());
    }

    // Add deploy handler
    const deployBtn = document.querySelector('.btn-deploy');
    if (deployBtn) {
        deployBtn.addEventListener('click', () => StrategyBuilder.deployStrategy());
    }
});

// Export
window.DepositModal = DepositModal;
window.StrategyBuilder = StrategyBuilder;
window.PortfolioTracker = PortfolioTracker;
