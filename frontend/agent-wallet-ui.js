/**
 * Techne Agent Wallet UI
 * Inspired by NeoX Agent Vaults - elegant deposit/withdraw interface
 */

const AgentWalletUI = {
    // Contract address - DEPLOYED ON BASE MAINNET
    contractAddress: '0x567D1Fc55459224132aB5148c6140E8900f9a607',

    // Base USDC
    USDC_ADDRESS: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',

    // ABI for read/write
    WALLET_ABI: [
        'function deposit(uint256 amount)',
        'function withdraw(uint256 shares)',
        'function totalValue() view returns (uint256)',
        'function totalShares() view returns (uint256)',
        'function getUserValue(address user) view returns (uint256)',
        'function getUserShares(address user) view returns (uint256)',
        'function estimatedAPY() view returns (uint256)'
    ],

    USDC_ABI: [
        'function approve(address spender, uint256 amount) returns (bool)',
        'function balanceOf(address account) view returns (uint256)',
        'function allowance(address owner, address spender) view returns (uint256)'
    ],

    // State
    userShares: 0,
    userValue: 0,
    totalVaultValue: 0,
    estimatedAPY: 0,

    /**
     * Initialize the Agent Wallet UI
     */
    init() {
        this.renderVaultCard();
        this.bindEvents();

        // DISABLED: Contract not deployed yet - uncomment when ready
        // setInterval(() => this.refreshStats(), 30000);

        console.log('[AgentWallet] UI initialized (contract refresh disabled)');
    },

    /**
     * Render the main vault card in Build section
     */
    renderVaultCard() {
        const container = document.getElementById('agentVaultContainer');
        if (!container) return;

        container.innerHTML = `
            <div class="agent-vault-card">
                <div class="vault-header">
                    <div class="vault-icon"><span class="techne-icon">${TechneIcons.get('robot', 24)}</span></div>
                    <div class="vault-title">
                        <h2>Techne Agent Vault</h2>
                        <span class="vault-badge">Base • Single-Sided</span>
                    </div>
                    <div class="vault-apy">
                        <span class="apy-value" id="vaultAPY">--</span>
                        <span class="apy-label">APY</span>
                    </div>
                </div>
                
                <div class="vault-stats">
                    <div class="stat">
                        <span class="stat-label">Total Vault Value</span>
                        <span class="stat-value" id="vaultTVL">$--</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Your Position</span>
                        <span class="stat-value" id="userPosition">$0.00</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Your Shares</span>
                        <span class="stat-value" id="userSharesDisplay">0</span>
                    </div>
                </div>
                
                <div class="vault-agent-status">
                    <div class="agent-indicator active"></div>
                    <span>Agent Active • Auto-optimizing yields</span>
                </div>
                
                <div class="vault-actions">
                    <button class="btn-vault-deposit" onclick="AgentWalletUI.showDepositModal()">
                        <span class="techne-icon">${TechneIcons.deposit}</span> Deposit
                    </button>
                    <button class="btn-vault-withdraw" onclick="AgentWalletUI.showWithdrawModal()">
                        <span class="techne-icon">${TechneIcons.withdraw}</span> Withdraw
                    </button>
                </div>
                
                <div class="vault-protocols">
                    <span class="protocols-label">Protocols:</span>
                    <div class="protocol-badges">
                        <span class="protocol-badge">Morpho</span>
                        <span class="protocol-badge">Aave</span>
                        <span class="protocol-badge">Moonwell</span>
                        <span class="protocol-badge">Compound</span>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Show deposit modal
     */
    showDepositModal() {
        // Remove existing
        document.getElementById('vaultModal')?.remove();

        const modal = document.createElement('div');
        modal.id = 'vaultModal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-container vault-modal">
                <button class="modal-close" onclick="document.getElementById('vaultModal').remove()">✕</button>
                
                <div class="vault-modal-header">
                    <span class="modal-icon techne-icon">${TechneIcons.get('deposit', 24)}</span>
                    <h2>Deposit to Agent Vault</h2>
                </div>
                
                <div class="vault-modal-body">
                    <div class="deposit-info">
                        <p>Your USDC will be automatically allocated to the highest-yield single-sided pools on Base.</p>
                    </div>
                    
                    <div class="input-group">
                        <label>Amount (USDC)</label>
                        <div class="amount-input-wrapper">
                            <input type="number" id="depositAmount" placeholder="0.00" min="10" step="0.01">
                            <button class="btn-max" onclick="AgentWalletUI.setMaxDeposit()">MAX</button>
                        </div>
                        <span class="balance-info">Balance: <span id="usdcBalance">--</span> USDC</span>
                    </div>
                    
                    <div class="deposit-summary">
                        <div class="summary-row">
                            <span>Estimated APY</span>
                            <span class="highlight">${this.estimatedAPY}%</span>
                        </div>
                        <div class="summary-row">
                            <span>Management Fee</span>
                            <span>10% of yield</span>
                        </div>
                        <div class="summary-row">
                            <span>Network</span>
                            <span>Base</span>
                        </div>
                    </div>
                    
                    <button class="btn-deposit-confirm" id="depositBtn" onclick="AgentWalletUI.executeDeposit()">
                        <span class="techne-icon">${TechneIcons.lock}</span> Approve & Deposit
                    </button>
                    
                    <p class="modal-disclaimer">
                        By depositing, you authorize the Techne Agent to manage your funds across DeFi protocols.
                    </p>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        // Load USDC balance
        this.loadUSDCBalance();
    },

    /**
     * Show withdraw modal
     */
    showWithdrawModal() {
        document.getElementById('vaultModal')?.remove();

        const modal = document.createElement('div');
        modal.id = 'vaultModal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-container vault-modal">
                <button class="modal-close" onclick="document.getElementById('vaultModal').remove()">✕</button>
                
                <div class="vault-modal-header">
                    <span class="modal-icon techne-icon">${TechneIcons.get('withdraw', 24)}</span>
                    <h2>Withdraw from Agent Vault</h2>
                </div>
                
                <div class="vault-modal-body">
                    <div class="position-info">
                        <div class="position-stat">
                            <span class="label">Your Position</span>
                            <span class="value" id="withdrawPositionValue">$${(this.userValue / 1e6).toFixed(2)}</span>
                        </div>
                        <div class="position-stat">
                            <span class="label">Your Shares</span>
                            <span class="value">${this.userShares}</span>
                        </div>
                    </div>
                    
                    <div class="input-group">
                        <label>Shares to Withdraw</label>
                        <div class="amount-input-wrapper">
                            <input type="number" id="withdrawShares" placeholder="0" min="1" max="${this.userShares}">
                            <button class="btn-max" onclick="AgentWalletUI.setMaxWithdraw()">MAX</button>
                        </div>
                        <span class="balance-info">Available: ${this.userShares} shares</span>
                    </div>
                    
                    <div class="withdraw-estimate">
                        <span>You will receive approximately:</span>
                        <span class="estimate-value" id="withdrawEstimate">$0.00</span>
                    </div>
                    
                    <button class="btn-withdraw-confirm" id="withdrawBtn" onclick="AgentWalletUI.executeWithdraw()">
                        <span class="techne-icon">${TechneIcons.coin}</span> Withdraw
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        // Bind estimate calculator
        document.getElementById('withdrawShares')?.addEventListener('input', (e) => {
            this.updateWithdrawEstimate(e.target.value);
        });
    },

    /**
     * Load user's USDC balance
     */
    async loadUSDCBalance() {
        if (!window.connectedWallet || !window.ethereum) return;

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            const usdc = new ethers.Contract(this.USDC_ADDRESS, this.USDC_ABI, provider);
            const balance = await usdc.balanceOf(window.connectedWallet);

            document.getElementById('usdcBalance').textContent =
                (Number(balance) / 1e6).toFixed(2);
        } catch (e) {
            console.error('[AgentWallet] Error loading balance:', e);
        }
    },

    /**
     * Set max deposit amount
     */
    setMaxDeposit() {
        const balanceText = document.getElementById('usdcBalance')?.textContent;
        if (balanceText && balanceText !== '--') {
            document.getElementById('depositAmount').value = balanceText;
        }
    },

    /**
     * Set max withdraw shares
     */
    setMaxWithdraw() {
        document.getElementById('withdrawShares').value = this.userShares;
        this.updateWithdrawEstimate(this.userShares);
    },

    /**
     * Update withdraw estimate
     */
    updateWithdrawEstimate(shares) {
        if (!shares || this.totalVaultValue === 0) {
            document.getElementById('withdrawEstimate').textContent = '$0.00';
            return;
        }

        // Estimate: (shares / totalShares) * totalValue
        // Simplified - in reality would call contract
        const estimate = (shares / Math.max(1, this.userShares)) * this.userValue;
        document.getElementById('withdrawEstimate').textContent =
            '$' + (estimate / 1e6).toFixed(2);
    },

    /**
     * Execute deposit transaction
     */
    async executeDeposit() {
        const amount = document.getElementById('depositAmount')?.value;
        if (!amount || amount < 10) {
            alert('Minimum deposit is 10 USDC');
            return;
        }

        if (!window.connectedWallet) {
            alert('Please connect your wallet');
            return;
        }

        const btn = document.getElementById('depositBtn');
        btn.innerHTML = '<span>⏳</span> Approving...';
        btn.disabled = true;

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();

            const amountWei = BigInt(Math.floor(parseFloat(amount) * 1e6));

            // Approve USDC
            const usdc = new ethers.Contract(this.USDC_ADDRESS, this.USDC_ABI, signer);
            const approveTx = await usdc.approve(this.contractAddress, amountWei);
            await approveTx.wait();

            btn.innerHTML = '<span>⏳</span> Depositing...';

            // Deposit
            const wallet = new ethers.Contract(this.contractAddress, this.WALLET_ABI, signer);
            const depositTx = await wallet.deposit(amountWei);
            await depositTx.wait();

            btn.innerHTML = '<span class="techne-icon">' + TechneIcons.success + '</span> Deposited!';
            btn.style.background = 'var(--success)';

            Toast?.show('Successfully deposited to Agent Vault!', 'success');

            // Refresh stats
            await this.refreshStats();

            setTimeout(() => {
                document.getElementById('vaultModal')?.remove();
            }, 2000);

        } catch (e) {
            console.error('[AgentWallet] Deposit error:', e);
            alert('Deposit failed: ' + (e.reason || e.message));
            btn.innerHTML = '<span class="techne-icon">' + TechneIcons.lock + '</span> Approve & Deposit';
            btn.disabled = false;
        }
    },

    /**
     * Execute withdraw transaction
     */
    async executeWithdraw() {
        const shares = document.getElementById('withdrawShares')?.value;
        if (!shares || shares <= 0) {
            alert('Enter shares to withdraw');
            return;
        }

        if (!window.connectedWallet) {
            alert('Please connect your wallet');
            return;
        }

        const btn = document.getElementById('withdrawBtn');
        btn.innerHTML = '<span>⏳</span> Withdrawing...';
        btn.disabled = true;

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();

            const wallet = new ethers.Contract(this.contractAddress, this.WALLET_ABI, signer);
            const tx = await wallet.withdraw(BigInt(shares));
            await tx.wait();

            btn.innerHTML = '<span class="techne-icon">' + TechneIcons.success + '</span> Withdrawn!';
            btn.style.background = 'var(--success)';

            Toast?.show('Successfully withdrawn from Agent Vault!', 'success');

            await this.refreshStats();

            setTimeout(() => {
                document.getElementById('vaultModal')?.remove();
            }, 2000);

        } catch (e) {
            console.error('[AgentWallet] Withdraw error:', e);
            alert('Withdraw failed: ' + (e.reason || e.message));
            btn.innerHTML = '<span class="techne-icon">' + TechneIcons.coin + '</span> Withdraw';
            btn.disabled = false;
        }
    },

    /**
     * Refresh vault stats from contract
     */
    async refreshStats() {
        if (!this.contractAddress || !window.ethereum || typeof ethers === 'undefined') return;

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            const wallet = new ethers.Contract(this.contractAddress, this.WALLET_ABI, provider);

            // Get stats
            this.totalVaultValue = await wallet.totalValue();
            this.estimatedAPY = Number(await wallet.estimatedAPY()) / 100;

            if (window.connectedWallet) {
                this.userValue = await wallet.getUserValue(window.connectedWallet);
                this.userShares = Number(await wallet.getUserShares(window.connectedWallet));
            }

            // Update UI
            document.getElementById('vaultTVL').textContent =
                '$' + (Number(this.totalVaultValue) / 1e6).toLocaleString();
            document.getElementById('vaultAPY').textContent =
                this.estimatedAPY.toFixed(1) + '%';
            document.getElementById('userPosition').textContent =
                '$' + (Number(this.userValue) / 1e6).toFixed(2);
            document.getElementById('userSharesDisplay').textContent =
                this.userShares.toLocaleString();

        } catch (e) {
            console.error('[AgentWallet] Error refreshing stats:', e);
        }
    },

    /**
     * Bind UI events
     */
    bindEvents() {
        // Wallet connect callback
        // DISABLED: Contract not deployed yet
        // window.addEventListener('walletConnected', () => {
        //     this.refreshStats();
        // });
    }
};

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    AgentWalletUI.init();
});

// Export
window.AgentWalletUI = AgentWalletUI;
