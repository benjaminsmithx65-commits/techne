/**
 * Portfolio Dashboard Logic
 * Manages portfolio data, holdings display, and agent status
 */

class PortfolioDashboard {
    constructor() {
        this.portfolio = {
            totalValue: 0,
            totalPnL: 0,
            pnlPercent: 0,
            avgApy: 0,
            holdings: [],
            positions: [],
            transactions: []
        };

        this.notifications = [];
        this.selectedAgentId = null;
        this.agents = [];
    }

    init() {
        this.bindEvents();
        this.loadAgents();
        this.loadPortfolioData();
        this.syncAgentStatus();
        console.log('[Portfolio] Dashboard initialized');
    }

    bindEvents() {
        // Refresh button
        document.getElementById('refreshPortfolio')?.addEventListener('click', () => {
            this.loadPortfolioData();
        });

        // Transaction filter
        document.getElementById('txFilter')?.addEventListener('change', (e) => {
            this.filterTransactions(e.target.value);
        });

        // Fund agent button
        document.getElementById('btnFundAgent')?.addEventListener('click', () => {
            this.openFundModal();
        });

        // Withdraw all button
        document.getElementById('btnWithdrawAll')?.addEventListener('click', () => {
            this.confirmWithdrawAll();
        });

        // Agent selector
        document.getElementById('agentSelector')?.addEventListener('change', (e) => {
            this.selectAgent(e.target.value);
        });

        // Delete agent button
        document.getElementById('btnDeleteAgent')?.addEventListener('click', () => {
            this.confirmDeleteAgent();
        });

        // Quick actions
        document.querySelectorAll('.quick-action').forEach(btn => {
            btn.addEventListener('click', () => {
                this.handleQuickAction(btn.dataset.action);
            });
        });
    }

    loadAgents() {
        // Load all agents from localStorage
        try {
            const saved = localStorage.getItem('techne_deployed_agents');
            this.agents = saved ? JSON.parse(saved) : [];

            // Fallback to old format
            if (this.agents.length === 0) {
                const oldFormat = localStorage.getItem('techne_deployed_agent');
                if (oldFormat) {
                    const agent = JSON.parse(oldFormat);
                    agent.id = agent.id || `agent_${Date.now()}`;
                    this.agents = [agent];
                }
            }

            this.updateAgentSelector();

            // Auto-select first active agent
            const activeAgent = this.agents.find(a => a.isActive);
            if (activeAgent) {
                this.selectedAgentId = activeAgent.id;
                document.getElementById('agentSelector').value = activeAgent.id;
            }
        } catch (e) {
            console.error('[Portfolio] Failed to load agents:', e);
            this.agents = [];
        }
    }

    updateAgentSelector() {
        const selector = document.getElementById('agentSelector');
        const countEl = document.getElementById('agentCount');

        if (!selector) return;

        // Clear options
        selector.innerHTML = '<option value="">Select Agent...</option>';

        // Add agents
        this.agents.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.id;
            option.textContent = `${agent.name || 'Agent'} ${agent.isActive ? '🟢' : '⚫'}`;
            if (agent.id === this.selectedAgentId) {
                option.selected = true;
            }
            selector.appendChild(option);
        });

        // Update count
        if (countEl) {
            const activeCount = this.agents.filter(a => a.isActive).length;
            countEl.textContent = `${this.agents.length}/5 agents (${activeCount} active)`;
        }
    }

    selectAgent(agentId) {
        this.selectedAgentId = agentId;
        const agent = this.agents.find(a => a.id === agentId);

        if (agent) {
            this.updateAgentSidebarFromDeployed(agent);
            this.populateFromDeployedAgent(agent);
            this.updateUI();
        } else {
            this.showEmptyState();
        }
    }

    async confirmDeleteAgent() {
        const agent = this.agents.find(a => a.id === this.selectedAgentId);

        if (!agent) {
            alert('Please select an agent first');
            return;
        }

        const confirmed = confirm(
            `Are you sure you want to delete "${agent.name || 'Agent'}"?\n\n` +
            `Address: ${agent.address?.slice(0, 10)}...\n` +
            `Strategy: ${agent.preset}\n\n` +
            `This action cannot be undone.`
        );

        if (!confirmed) return;

        // Call backend to delete
        const API_BASE = window.API_BASE || '';
        try {
            const response = await fetch(
                `${API_BASE}/api/agent/delete/${window.connectedWallet}/${agent.id}`,
                { method: 'DELETE' }
            );
            const result = await response.json();
            console.log('[Portfolio] Delete result:', result);
        } catch (e) {
            console.warn('[Portfolio] Backend delete failed:', e);
        }

        // Remove from local storage
        this.agents = this.agents.filter(a => a.id !== agent.id);
        localStorage.setItem('techne_deployed_agents', JSON.stringify(this.agents));

        // Update UI
        this.selectedAgentId = null;
        this.updateAgentSelector();

        if (this.agents.length > 0) {
            this.selectAgent(this.agents[0].id);
        } else {
            this.showEmptyState();
        }

        console.log('[Portfolio] Agent deleted:', agent.id);
    }

    async loadPortfolioData() {
        // Show loading state
        this.showLoadingState();

        try {
            // Check localStorage for deployed agent first
            const deployedAgent = this.getDeployedAgent();

            // Also check VaultAgent for legacy compatibility
            const agentStatus = window.VaultAgent?.getStatus?.();

            if (deployedAgent?.isActive) {
                // Populate with deployed agent data
                await this.populateFromDeployedAgent(deployedAgent);
            } else if (agentStatus?.isActive && agentStatus.allocations?.length > 0) {
                // Legacy: Populate with agent data
                this.populateMockData(agentStatus);
            } else {
                // Show empty state
                this.showEmptyState();
            }

            this.updateUI();
        } catch (error) {
            console.error('[Portfolio] Failed to load data:', error);
        }
    }

    getDeployedAgent() {
        // Retrieve deployed agent from localStorage
        try {
            const saved = localStorage.getItem('techne_deployed_agent');
            return saved ? JSON.parse(saved) : null;
        } catch (e) {
            console.error('[Portfolio] Failed to load deployed agent:', e);
            return null;
        }
    }

    async populateFromDeployedAgent(agent) {
        // Populate portfolio data from deployed agent config
        console.log('[Portfolio] Loading from deployed agent:', agent);

        // Try to fetch recommendations from backend
        const API_BASE = window.API_BASE || '';
        let recommendedPools = [];

        if (window.connectedWallet) {
            try {
                const response = await fetch(`${API_BASE}/api/agent/recommendations/${window.connectedWallet}`);
                const data = await response.json();
                if (data.success && data.recommended_pools) {
                    recommendedPools = data.recommended_pools;
                    console.log('[Portfolio] Fetched recommendations:', recommendedPools.length);
                }
            } catch (e) {
                console.log('[Portfolio] Could not fetch recommendations:', e);
            }
        }

        // Generate positions from recommendations or config
        const numPositions = recommendedPools.length || agent.vaultCount || 3;
        const protocols = agent.protocols || ['morpho', 'aave'];
        const assets = agent.preferredAssets || ['USDC', 'WETH'];

        const positions = [];

        if (recommendedPools.length > 0) {
            // Use actual recommendations
            for (let i = 0; i < recommendedPools.length; i++) {
                const pool = recommendedPools[i];
                positions.push({
                    id: i,
                    vaultName: pool.symbol || `${pool.project} Vault`,
                    protocol: pool.project || 'Unknown',
                    deposited: 0,
                    current: 0,
                    apy: pool.apy || 0,
                    pnl: 0,
                    allocation: pool._allocation || Math.floor(100 / numPositions),
                    tvl: pool.tvl || 0,
                    chain: pool.chain || 'base'
                });
            }
        } else {
            // Fallback to mock positions
            for (let i = 0; i < numPositions; i++) {
                positions.push({
                    id: i,
                    vaultName: `${protocols[i % protocols.length]} ${assets[i % assets.length]} Vault`,
                    protocol: protocols[i % protocols.length],
                    deposited: 0,
                    current: 0,
                    apy: agent.minApy + Math.random() * (agent.maxApy - agent.minApy),
                    pnl: 0,
                    allocation: Math.floor(100 / numPositions)
                });
            }
        }

        // Calculate average APY from positions
        const avgApy = positions.length > 0
            ? positions.reduce((sum, p) => sum + (p.apy || 0), 0) / positions.length
            : (agent.minApy + agent.maxApy) / 2;

        this.portfolio = {
            totalValue: 0,
            totalPnL: 0,
            pnlPercent: 0,
            avgApy: avgApy,
            holdings: assets.slice(0, 3).map(asset => ({
                asset: asset,
                balance: 0,
                value: 0,
                change: 0
            })),
            positions: positions,
            transactions: [],
            recommendedPools: recommendedPools
        };

        // Update agent status in sidebar
        this.updateAgentSidebarFromDeployed(agent);
    }

    updateAgentSidebarFromDeployed(agent) {
        const badge = document.getElementById('agentStatusBadge');
        const addrEl = document.getElementById('agentAddrDisplay');
        const strategyEl = document.getElementById('agentStrategy');
        const lastActionEl = document.getElementById('agentLastAction');

        if (badge) {
            badge.textContent = 'Active';
            badge.className = 'status-badge active';
        }

        if (addrEl) {
            addrEl.textContent = agent.address ?
                `${agent.address.slice(0, 6)}...${agent.address.slice(-4)}` :
                'Not deployed';
        }

        if (strategyEl) {
            strategyEl.textContent = agent.preset?.replace(/-/g, ' ') || 'Custom';
        }

        if (lastActionEl) {
            const deployedTime = new Date(agent.deployedAt);
            const now = new Date();
            const diffMs = now - deployedTime;
            const diffMins = Math.floor(diffMs / 60000);

            if (diffMins < 1) {
                lastActionEl.textContent = 'Just deployed';
            } else if (diffMins < 60) {
                lastActionEl.textContent = `Deployed ${diffMins}m ago`;
            } else {
                lastActionEl.textContent = `Deployed ${Math.floor(diffMins / 60)}h ago`;
            }
        }
    }

    populateMockData(agentStatus) {
        // Mock portfolio data based on agent allocations
        const allocations = agentStatus.allocations || [];

        this.portfolio = {
            totalValue: 1250.00 + Math.random() * 500,
            totalPnL: 45.67 + Math.random() * 20,
            pnlPercent: 3.8,
            avgApy: 18.5,
            holdings: [
                { asset: 'USDC', balance: 500, value: 500, change: 0 },
                { asset: 'WETH', balance: 0.25, value: 750, change: 2.3 }
            ],
            positions: allocations.map((pos, i) => ({
                id: i,
                vaultName: pos.vaultName || `Vault ${i + 1}`,
                protocol: pos.platform || 'Unknown',
                deposited: 250 + Math.random() * 100,
                current: 260 + Math.random() * 110,
                apy: pos.apy || (10 + Math.random() * 20),
                pnl: 10 + Math.random() * 20
            })),
            transactions: [
                { type: 'deposit', vault: 'Aerodrome USDC/WETH', amount: 500, time: 'Today', hash: '0x123...' },
                { type: 'harvest', vault: 'Aave USDC', amount: 12.5, time: 'Yesterday', hash: '0x456...' }
            ]
        };
    }

    showEmptyState() {
        document.getElementById('holdingsEmpty').style.display = 'block';
        document.getElementById('positionsEmpty').style.display = 'block';
        document.getElementById('txEmpty').style.display = 'block';
    }

    showLoadingState() {
        // Could add skeleton loaders here
    }

    updateUI() {
        // Update stats cards
        document.getElementById('portfolioTotalValue').textContent =
            this.formatCurrency(this.portfolio.totalValue);

        document.getElementById('portfolioPnL').textContent =
            this.formatCurrency(this.portfolio.totalPnL);

        const changeEl = document.getElementById('portfolioChange');
        changeEl.textContent = `+${this.portfolio.pnlPercent}%`;
        changeEl.className = `stat-change ${this.portfolio.pnlPercent >= 0 ? 'positive' : 'negative'}`;

        document.getElementById('portfolioAvgApy').textContent =
            `${this.portfolio.avgApy.toFixed(1)}%`;

        document.getElementById('portfolioVaultCount').textContent =
            this.portfolio.positions.length;

        // Update positions count
        document.getElementById('positionsCount').textContent =
            `${this.portfolio.positions.length} Active`;

        // Render holdings
        this.renderHoldings();

        // Render positions
        this.renderPositions();

        // Render transactions
        this.renderTransactions();

        // Update allocation chart
        this.updateAllocationChart();
    }

    renderHoldings() {
        const container = document.getElementById('holdingsTable');
        const emptyEl = document.getElementById('holdingsEmpty');

        if (this.portfolio.holdings.length === 0) {
            emptyEl.style.display = 'block';
            return;
        }

        emptyEl.style.display = 'none';

        // Remove existing rows (keep header and empty)
        container.querySelectorAll('.holding-row').forEach(el => el.remove());

        this.portfolio.holdings.forEach(holding => {
            const row = document.createElement('div');
            row.className = 'holding-row';
            row.innerHTML = `
                <div class="holding-info">
                    <img src="https://icons.llama.fi/${holding.asset.toLowerCase()}.png" 
                         alt="${holding.asset}" class="asset-icon" onerror="this.style.display='none'">
                    <span>${holding.asset}</span>
                </div>
                <span>${holding.balance.toLocaleString()}</span>
                <span>${this.formatCurrency(holding.value)}</span>
                <span class="${holding.change >= 0 ? 'positive' : 'negative'}">
                    ${holding.change >= 0 ? '+' : ''}${holding.change.toFixed(2)}%
                </span>
                <div class="holding-actions">
                    <button class="btn-sm" onclick="PortfolioDash.withdraw('${holding.asset}')">Withdraw</button>
                </div>
            `;
            container.appendChild(row);
        });
    }

    renderPositions() {
        const container = document.getElementById('vaultPositions');
        const emptyEl = document.getElementById('positionsEmpty');

        if (this.portfolio.positions.length === 0) {
            emptyEl.style.display = 'block';
            return;
        }

        emptyEl.style.display = 'none';

        container.querySelectorAll('.position-card').forEach(el => el.remove());

        this.portfolio.positions.forEach(pos => {
            const card = document.createElement('div');
            card.className = 'position-card';
            card.innerHTML = `
                <div class="position-header">
                    <span class="position-name">${pos.vaultName}</span>
                    <span class="position-apy">${pos.apy.toFixed(1)}% APY</span>
                </div>
                <div class="position-body">
                    <div class="position-row">
                        <span class="label">Deposited</span>
                        <span class="value">${this.formatCurrency(pos.deposited)}</span>
                    </div>
                    <div class="position-row">
                        <span class="label">Current</span>
                        <span class="value">${this.formatCurrency(pos.current)}</span>
                    </div>
                    <div class="position-row">
                        <span class="label">P&L</span>
                        <span class="value positive">+${this.formatCurrency(pos.pnl)}</span>
                    </div>
                </div>
                <div class="position-actions">
                    <button class="btn-sm" onclick="PortfolioDash.withdrawFromVault(${pos.id})">Withdraw</button>
                    <button class="btn-sm" onclick="PortfolioDash.harvest(${pos.id})">Harvest</button>
                </div>
            `;
            container.appendChild(card);
        });
    }

    renderTransactions() {
        const container = document.getElementById('txHistory');
        const emptyEl = document.getElementById('txEmpty');

        if (this.portfolio.transactions.length === 0) {
            emptyEl.style.display = 'block';
            return;
        }

        emptyEl.style.display = 'none';

        container.querySelectorAll('.tx-row').forEach(el => el.remove());

        this.portfolio.transactions.forEach(tx => {
            const row = document.createElement('div');
            row.className = 'tx-row';
            row.innerHTML = `
                <div class="tx-type ${tx.type}">${this.getTxIcon(tx.type)} ${tx.type}</div>
                <div class="tx-info">
                    <span class="tx-vault">${tx.vault}</span>
                    <span class="tx-time">${tx.time}</span>
                </div>
                <div class="tx-amount">${tx.type === 'withdraw' ? '-' : '+'}${this.formatCurrency(tx.amount)}</div>
                <a href="https://basescan.org/tx/${tx.hash}" target="_blank" class="tx-link">View ↗</a>
            `;
            container.appendChild(row);
        });
    }

    getTxIcon(type) {
        const icons = {
            deposit: '💰',
            withdraw: '📤',
            harvest: '🌾',
            rebalance: '⚖️',
            swap: '🔄'
        };
        return icons[type] || '📝';
    }

    updateAllocationChart() {
        const chartEl = document.getElementById('allocationChart');
        const legendEl = document.getElementById('allocationLegend');

        if (this.portfolio.positions.length === 0) return;

        // Calculate allocation percentages
        const total = this.portfolio.positions.reduce((sum, p) => sum + p.current, 0);
        const colors = ['#D4AF37', '#10b981', '#3b82f6', '#ef4444', '#8b5cf6', '#f59e0b'];

        let gradientParts = [];
        let currentDeg = 0;

        this.portfolio.positions.forEach((pos, i) => {
            const percent = (pos.current / total) * 100;
            const deg = (percent / 100) * 360;
            const color = colors[i % colors.length];

            gradientParts.push(`${color} ${currentDeg}deg ${currentDeg + deg}deg`);
            currentDeg += deg;
        });

        // Update chart
        const donutChart = chartEl.querySelector('.donut-chart');
        if (donutChart) {
            donutChart.style.background = `conic-gradient(${gradientParts.join(', ')})`;
        }

        const donutLabel = chartEl.querySelector('.donut-label');
        if (donutLabel) {
            donutLabel.textContent = this.formatCurrency(total);
        }

        // Update legend
        legendEl.innerHTML = '';
        this.portfolio.positions.forEach((pos, i) => {
            const percent = ((pos.current / total) * 100).toFixed(1);
            const color = colors[i % colors.length];

            legendEl.innerHTML += `
                <div class="legend-item">
                    <span class="legend-color" style="background: ${color}"></span>
                    <span class="legend-name">${pos.vaultName}</span>
                    <span class="legend-value">${percent}%</span>
                </div>
            `;
        });
    }

    syncAgentStatus() {
        // Check agent status and update sidebar
        const agentStatus = window.VaultAgent?.getStatus?.();

        const badge = document.getElementById('agentStatusBadge');
        const addrEl = document.getElementById('agentAddrDisplay');
        const balEl = document.getElementById('agentBalDisplay');
        const strategyEl = document.getElementById('agentStrategy');
        const lastActionEl = document.getElementById('agentLastAction');

        if (agentStatus?.isActive) {
            badge.textContent = 'Active';
            badge.className = 'status-badge active';

            addrEl.textContent = agentStatus.agentAddress ?
                `${agentStatus.agentAddress.slice(0, 6)}...${agentStatus.agentAddress.slice(-4)}` :
                'Not deployed';

            strategyEl.textContent = agentStatus.config?.preset?.replace(/-/g, ' ') || 'Custom';

            if (agentStatus.lastAction) {
                lastActionEl.textContent = agentStatus.lastAction.action || '—';
            }
        } else {
            badge.textContent = 'Inactive';
            badge.className = 'status-badge inactive';
        }
    }

    filterTransactions(type) {
        const rows = document.querySelectorAll('.tx-row');
        rows.forEach(row => {
            if (type === 'all' || row.querySelector('.tx-type').textContent.toLowerCase().includes(type)) {
                row.style.display = 'flex';
            } else {
                row.style.display = 'none';
            }
        });
    }

    handleQuickAction(action) {
        switch (action) {
            case 'deposit':
                // Open Agent Wallet deposit modal
                if (window.AgentWalletUI) {
                    AgentWalletUI.showDepositModal();
                } else {
                    this.showToast('Agent Wallet not initialized', 'warning');
                }
                break;
            case 'withdraw':
                // Open Agent Wallet withdraw modal
                if (window.AgentWalletUI) {
                    AgentWalletUI.showWithdrawModal();
                } else {
                    this.showToast('Agent Wallet not initialized', 'warning');
                }
                break;
            case 'harvest':
                this.harvestAll();
                break;
            case 'rebalance':
                this.triggerRebalance();
                break;
        }
    }

    async harvestAll() {
        this.showToast('Harvesting all rewards...', 'info');
        // Simulate harvest
        await new Promise(r => setTimeout(r, 2000));
        this.showToast('Harvested $12.50 in rewards! 🌾', 'success');
        this.loadPortfolioData();
    }

    async triggerRebalance() {
        this.showToast('Rebalancing portfolio...', 'info');
        await new Promise(r => setTimeout(r, 2000));
        this.showToast('Portfolio rebalanced successfully! ⚖️', 'success');
        this.loadPortfolioData();
    }

    openFundModal() {
        // Open Agent Wallet deposit modal
        if (window.AgentWalletUI) {
            AgentWalletUI.showDepositModal();
        } else {
            this.showToast('Agent Wallet not initialized. Go to Build section first.', 'warning');
        }
    }

    confirmWithdrawAll() {
        if (!window.AgentWalletUI) {
            this.showToast('Agent Wallet not initialized', 'warning');
            return;
        }

        if (confirm('Are you sure you want to withdraw all funds from the Agent Vault?')) {
            AgentWalletUI.showWithdrawModal();
        }
    }

    addNotification(text, type = 'info') {
        this.notifications.unshift({ text, type, time: new Date() });
        this.renderNotifications();
    }

    renderNotifications() {
        const listEl = document.getElementById('notificationsList');
        const countEl = document.getElementById('notifCount');

        countEl.textContent = this.notifications.length;

        if (this.notifications.length === 0) {
            listEl.innerHTML = '<div class="notif-empty"><p>No new notifications</p></div>';
            return;
        }

        listEl.innerHTML = this.notifications.slice(0, 5).map(n => `
            <div class="notif-item ${n.type}">
                <span class="notif-text">${n.text}</span>
                <span class="notif-time">${this.formatTime(n.time)}</span>
            </div>
        `).join('');
    }

    formatCurrency(amount) {
        return '$' + amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    formatTime(date) {
        const now = new Date();
        const diff = now - date;
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    }

    showToast(message, type = 'info') {
        // Use existing toast system if available, or create a simple one
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }
}

// Initialize
const PortfolioDash = new PortfolioDashboard();
document.addEventListener('DOMContentLoaded', () => PortfolioDash.init());

// Export
window.PortfolioDash = PortfolioDash;
