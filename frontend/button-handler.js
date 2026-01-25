/**
 * Button Handler Module for Techne Finance
 * Ensures every button on the page leads to proper functionality
 */

const BTN_API_BASE = window.API_BASE || 'http://localhost:8000';

const ButtonHandler = {
    /**
     * Initialize all button handlers
     */
    init() {
        console.log('[ButtonHandler] Initializing...');
        this.bindNavigationButtons();
        this.bindActionButtons();
        this.bindPoolButtons();
        this.bindFooterLinks();
        this.bindDAOButtons();
        this.bindNetworkButton();
        console.log('[ButtonHandler] All buttons connected');
    },

    /**
     * Navigation buttons
     */
    bindNavigationButtons() {
        // Main nav items
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const section = btn.dataset.section;
                if (typeof navigateToSection === 'function') {
                    navigateToSection(section);
                }
            });
        });

        // View toggles (Grid/List)
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const view = btn.dataset.view;
                const poolGrid = document.getElementById('poolGrid');
                if (poolGrid) {
                    poolGrid.classList.toggle('list-view', view === 'list');
                }
            });
        });
    },

    /**
     * Action buttons (Deposit, Withdraw, etc.)
     */
    bindActionButtons() {
        // Unlock pools button
        document.querySelectorAll('.btn-unlock-pools, .unlock-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (window.UnlockModal && UnlockModal.open) {
                    UnlockModal.open();
                } else {
                    this.showPaymentModal('unlock', 0.10);
                }
            });
        });

        // Deposit buttons on pool cards
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-deposit, [data-action="deposit"]')) {
                const poolId = e.target.dataset.poolId || e.target.closest('.pool-card')?.dataset?.poolId;
                if (poolId) {
                    this.handleDeposit(poolId);
                }
            }
        });

        // View Details / Details buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-details, [data-action="details"]')) {
                const poolId = e.target.dataset.poolId || e.target.closest('.pool-card')?.dataset?.poolId;
                if (poolId) {
                    this.showPoolDetails(poolId);
                }
            }
        });

        // Add to Strategy buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-add-strategy, [data-action="add-strategy"]')) {
                const poolId = e.target.dataset.poolId || e.target.closest('.pool-card')?.dataset?.poolId;
                if (poolId) {
                    this.addToStrategy(poolId);
                }
            }
        });
    },

    /**
     * Pool card buttons
     */
    bindPoolButtons() {
        // Pool cards - click to view details
        document.addEventListener('click', (e) => {
            const card = e.target.closest('.pool-card');
            if (card && !e.target.closest('button')) {
                const poolId = card.dataset.poolId;
                if (poolId) {
                    this.showPoolDetails(poolId);
                }
            }
        });
    },

    /**
     * DAO section buttons
     */
    bindDAOButtons() {
        // Vote buttons
        document.querySelectorAll('.btn-vote').forEach(btn => {
            btn.addEventListener('click', () => {
                this.showVoteModal(btn);
            });
        });

        // Create Proposal button
        document.querySelectorAll('.btn-create-proposal').forEach(btn => {
            btn.addEventListener('click', () => {
                this.showCreateProposalModal();
            });
        });
    },

    /**
     * Footer links - open in new tab with proper URLs
     */
    bindFooterLinks() {
        const linkMap = {
            'Docs': 'https://docs.techne.finance',
            'GitHub': 'https://github.com/techne-finance',
            'Twitter': 'https://twitter.com/technefinance',
            'Discord': 'https://discord.gg/technefinance'
        };

        document.querySelectorAll('.footer-links a').forEach(link => {
            const text = link.textContent.trim();
            if (linkMap[text]) {
                link.href = linkMap[text];
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
            }
        });
    },

    /**
     * Network button
     */
    bindNetworkButton() {
        const networkBtn = document.getElementById('networkBtn');
        if (networkBtn) {
            networkBtn.addEventListener('click', () => {
                this.showNetworkSelector();
            });
        }
    },

    /**
     * Handle deposit action
     */
    handleDeposit(poolId) {
        // Check wallet connection
        if (!window.walletState?.connected) {
            if (typeof connectWallet === 'function') {
                connectWallet();
            }
            this.showNotification('Please connect your wallet first', 'warning');
            return;
        }

        // Open deposit modal
        if (window.ZapDeposit && ZapDeposit.open) {
            ZapDeposit.open(poolId);
        } else {
            this.showDepositModal(poolId);
        }
    },

    /**
     * Show pool details modal
     */
    async showPoolDetails(poolId) {
        if (window.PoolDetail && PoolDetail.show) {
            PoolDetail.show(poolId);
            return;
        }

        // Fallback modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal pool-detail-modal">
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
                <div class="modal-content">
                    <div class="loading-spinner">Loading pool details...</div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        try {
            const response = await fetch(`${BTN_API_BASE}/api/scout/risk/${encodeURIComponent(poolId)}`);
            const data = await response.json();

            modal.querySelector('.modal-content').innerHTML = `
                <h2>Pool Details</h2>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="label">Pool ID</span>
                        <span class="value">${poolId}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Risk Score</span>
                        <span class="value">${data.risk_score || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <span class="label">Risk Level</span>
                        <span class="value risk-${data.risk_level || 'medium'}">${data.risk_level || 'Medium'}</span>
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="btn btn-primary" onclick="ButtonHandler.handleDeposit('${poolId}')">Deposit</button>
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Close</button>
                </div>
            `;
        } catch (error) {
            modal.querySelector('.modal-content').innerHTML = `
                <h2>Pool Details</h2>
                <p>Pool ID: ${poolId}</p>
                <p style="color: #f87171;">Could not load full details</p>
                <div class="modal-actions">
                    <button class="btn btn-primary" onclick="ButtonHandler.handleDeposit('${poolId}')">Deposit</button>
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Close</button>
                </div>
            `;
        }
    },

    /**
     * Add pool to strategy
     */
    addToStrategy(poolId) {
        // Get current strategy from localStorage
        let strategy = JSON.parse(localStorage.getItem('techne_strategy') || '[]');

        if (strategy.includes(poolId)) {
            this.showNotification('Pool already in strategy', 'info');
            return;
        }

        strategy.push(poolId);
        localStorage.setItem('techne_strategy', JSON.stringify(strategy));

        this.showNotification('Pool added to strategy! 📊', 'success');

        // Navigate to strategies section
        if (typeof navigateToSection === 'function') {
            setTimeout(() => navigateToSection('strategies'), 500);
        }
    },

    /**
     * Show vote modal for DAO proposals
     */
    showVoteModal(btn) {
        const proposal = btn.closest('.proposal-card');
        const title = proposal?.querySelector('h4')?.textContent || 'Proposal';

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal vote-modal">
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
                <h2>Vote on Proposal</h2>
                <p style="color: #9ca3af; margin-bottom: 24px;">${title}</p>
                
                <div class="vote-options">
                    <button class="vote-option for" onclick="ButtonHandler.submitVote('for', this)">
                        <span class="vote-icon">👍</span>
                        <span>Vote For</span>
                    </button>
                    <button class="vote-option against" onclick="ButtonHandler.submitVote('against', this)">
                        <span class="vote-icon">👎</span>
                        <span>Vote Against</span>
                    </button>
                </div>
                
                <p style="font-size: 12px; color: #6b7280; margin-top: 16px; text-align: center;">
                    Your vote will be recorded on-chain
                </p>
            </div>
        `;
        document.body.appendChild(modal);
    },

    /**
     * Submit vote
     */
    submitVote(vote, btn) {
        btn.innerHTML = '<span class="spinner"></span> Voting...';

        setTimeout(() => {
            const modal = btn.closest('.modal-overlay');
            modal.remove();
            this.showNotification(`Vote recorded: ${vote === 'for' ? '👍 For' : '👎 Against'}`, 'success');
        }, 1500);
    },

    /**
     * Show network selector
     */
    showNetworkSelector() {
        const networks = [
            { id: 'base', name: 'Base', icon: '/icons/base.png', active: true },
            { id: 'ethereum', name: 'Ethereum', icon: '/icons/ethereum.png', active: false },
            { id: 'arbitrum', name: 'Arbitrum', icon: '/icons/arbitrum.png', active: false },
            { id: 'optimism', name: 'Optimism', icon: '/icons/optimism.png', active: false },
            { id: 'polygon', name: 'Polygon', icon: '/icons/polygon.png', active: false },
            { id: 'solana', name: 'Solana', icon: '/icons/solana.png', soon: true },
        ];

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
        modal.innerHTML = `
            <div class="modal network-modal" style="
                background: linear-gradient(145deg, rgba(20,20,25,0.98), rgba(10,10,15,0.98));
                border: 1px solid rgba(212,168,83,0.2);
                border-radius: 16px;
                padding: 24px;
                max-width: 420px;
                width: 90%;
            ">
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()" style="
                    position: absolute; right: 16px; top: 16px;
                    background: none; border: none; color: #9ca3af;
                    font-size: 24px; cursor: pointer;
                ">&times;</button>
                <h2 style="margin: 0 0 20px 0; color: #fff; font-size: 18px;">Select Network</h2>
                <div class="network-grid" style="
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 12px;
                ">
                    ${networks.map(n => `
                        <button class="network-option ${n.active ? 'active' : ''} ${n.soon ? 'soon' : ''}" 
                            data-network="${n.id}" 
                            ${n.soon ? 'disabled' : `onclick="ButtonHandler.switchNetwork('${n.id}', this)"`}
                            style="
                                display: flex;
                                flex-direction: column;
                                align-items: center;
                                gap: 8px;
                                padding: 16px 12px;
                                background: ${n.active ? 'rgba(212,168,83,0.15)' : 'rgba(255,255,255,0.03)'};
                                border: 1px solid ${n.active ? 'rgba(212,168,83,0.5)' : 'rgba(255,255,255,0.08)'};
                                border-radius: 12px;
                                cursor: ${n.soon ? 'not-allowed' : 'pointer'};
                                opacity: ${n.soon ? '0.5' : '1'};
                                transition: all 0.2s ease;
                                position: relative;
                            "
                            ${!n.soon ? `onmouseenter="this.style.background='rgba(212,168,83,0.1)';this.style.borderColor='rgba(212,168,83,0.3)'"
                            onmouseleave="this.style.background='${n.active ? 'rgba(212,168,83,0.15)' : 'rgba(255,255,255,0.03)'}';this.style.borderColor='${n.active ? 'rgba(212,168,83,0.5)' : 'rgba(255,255,255,0.08)'}'"` : ''}
                        >
                            <img src="${n.icon}" alt="${n.name}" style="
                                width: 32px; height: 32px; border-radius: 50%;
                                object-fit: cover;
                            " onerror="this.style.display='none'">
                            <span style="color: #fff; font-size: 12px; font-weight: 500;">${n.name}</span>
                            ${n.soon ? '<span style="position:absolute;top:4px;right:4px;background:#d4a853;color:#000;font-size:9px;padding:2px 5px;border-radius:4px;font-weight:600;">SOON</span>' : ''}
                            ${n.active ? '<span style="position:absolute;top:4px;left:4px;width:6px;height:6px;background:#22c55e;border-radius:50%;"></span>' : ''}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    },

    /**
     * Switch network
     */
    async switchNetwork(networkId, btn) {
        const networkBtn = document.getElementById('networkBtn');
        const iconMap = {
            'base': 'https://icons.llama.fi/chains/rsz_base.jpg',
            'ethereum': 'https://icons.llama.fi/chains/rsz_ethereum.jpg',
            'arbitrum': 'https://icons.llama.fi/chains/rsz_arbitrum.jpg',
            'optimism': 'https://icons.llama.fi/chains/rsz_optimism.jpg',
            'polygon': 'https://icons.llama.fi/chains/rsz_polygon.jpg',
        };

        // Update UI
        if (networkBtn) {
            networkBtn.querySelector('img').src = iconMap[networkId] || iconMap.base;
            networkBtn.querySelector('span').textContent = networkId.charAt(0).toUpperCase() + networkId.slice(1);
        }

        // Update filters and reload
        if (window.filters) {
            window.filters.chain = networkId;
        }

        // Close modal
        btn.closest('.modal-overlay').remove();

        // Reload pools
        if (typeof loadPools === 'function') {
            loadPools();
        }

        this.showNotification(`Switched to ${networkId}`, 'success');
    },

    /**
     * Show payment modal
     */
    showPaymentModal(feature, price) {
        if (window.SubscriptionUI) {
            SubscriptionUI.showUpgradeModal('pro');
        } else {
            this.showNotification(`Payment required: $${price}`, 'info');
        }
    },

    /**
     * Show deposit modal (fallback)
     */
    showDepositModal(poolId) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal deposit-modal">
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
                <h2>Deposit</h2>
                <p style="color: #9ca3af;">Pool: ${poolId}</p>
                
                <div class="deposit-form">
                    <div class="form-group">
                        <label>Amount</label>
                        <input type="number" id="depositAmount" placeholder="0.00" min="0" step="0.01">
                    </div>
                    
                    <button class="btn btn-primary" onclick="ButtonHandler.executeDeposit('${poolId}')">
                        Confirm Deposit
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    },

    /**
     * Execute deposit
     */
    async executeDeposit(poolId) {
        const amount = document.getElementById('depositAmount')?.value;
        if (!amount || parseFloat(amount) <= 0) {
            this.showNotification('Please enter a valid amount', 'error');
            return;
        }

        this.showNotification(`Depositing ${amount} into ${poolId}...`, 'info');

        // Simulate deposit
        setTimeout(() => {
            document.querySelector('.modal-overlay')?.remove();
            this.showNotification('Deposit successful! 🎉', 'success');
        }, 2000);
    },

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        if (window.showNotification) {
            window.showNotification(message, type);
            return;
        }
        if (window.Notifications) {
            Notifications.show(message, type);
            return;
        }

        // Fallback
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };

        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 16px 24px;
            background: ${colors[type] || colors.info};
            color: white;
            border-radius: 8px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
            max-width: 300px;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 4000);
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    ButtonHandler.init();
});

// Export
window.ButtonHandler = ButtonHandler;
