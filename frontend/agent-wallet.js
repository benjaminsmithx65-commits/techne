/**
 * Agent Wallet Frontend Integration
 * Handles wallet creation, deposits, withdrawals, and security
 */

const API_BASE = window.API_BASE || 'http://localhost:8000';

// ===========================================
// AGENT WALLET MANAGER
// ===========================================

const AgentWallet = {
    // State
    agentAddress: null,
    balances: {},
    positions: [],
    is2FAEnabled: false,
    pendingMultiSig: [],

    // Initialize
    async init() {
        if (!window.connectedWallet) {
            console.log('[AgentWallet] No wallet connected');
            return;
        }

        try {
            const info = await this.getWalletInfo();
            if (info) {
                this.agentAddress = info.agent_address;
                this.balances = info.balances || {};
                this.is2FAEnabled = info['2fa_enabled'] || false;
                this.pendingMultiSig = info.pending_multisig || [];
                this.updateUI();
            }
        } catch (e) {
            console.log('[AgentWallet] No agent wallet found');
        }
    },

    // ===========================================
    // WALLET CREATION
    // ===========================================

    async createWallet() {
        if (!window.connectedWallet) {
            Toast?.show('Please connect wallet first', 'warning');
            return null;
        }

        try {
            Toast?.show('Creating agent wallet...', 'info');

            // Get signature from user as encryption key
            const message = `Create Techne Agent Wallet\n\nTimestamp: ${Date.now()}\n\nThis signature will be used to encrypt your agent wallet's private key.`;

            const signature = await window.ethereum.request({
                method: 'personal_sign',
                params: [message, window.connectedWallet]
            });

            const response = await fetch(`${API_BASE}/api/agent-wallet/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_address: window.connectedWallet,
                    signature: signature
                })
            });

            const data = await response.json();

            if (data.success) {
                this.agentAddress = data.agent_address;

                // Show private key modal - IMPORTANT
                this.showPrivateKeyModal(data.private_key, data.agent_address);

                Toast?.show('✅ Agent wallet created!', 'success');

                await this.init();
                return data;
            } else {
                Toast?.show('Failed to create wallet', 'error');
                return null;
            }
        } catch (e) {
            console.error('Create wallet error:', e);
            Toast?.show('Wallet creation cancelled', 'warning');
            return null;
        }
    },

    showPrivateKeyModal(privateKey, agentAddress) {
        const modal = document.createElement('div');
        modal.className = 'agent-wallet-modal';
        modal.style.cssText = `
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 3000;
        `;

        modal.innerHTML = `
            <div style="
                background: linear-gradient(135deg, #1a1a2e, #16213e);
                border: 2px solid var(--gold);
                border-radius: 20px;
                padding: 32px;
                max-width: 600px;
                width: 90%;
            ">
                <h2 style="color: var(--gold); margin: 0 0 20px; text-align: center;">
                    🔐 Agent Wallet Created
                </h2>
                
                <div style="
                    background: rgba(212, 175, 55, 0.1);
                    border: 1px solid var(--gold);
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 20px;
                ">
                    <p style="color: #ff6b6b; font-weight: 600; margin: 0 0 8px;">
                        ⚠️ SAVE THIS PRIVATE KEY NOW!
                    </p>
                    <p style="color: var(--text-muted); font-size: 0.85rem; margin: 0;">
                        This is your only chance to save it. You need this key to access funds directly.
                    </p>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="color: var(--text-muted); font-size: 0.8rem;">Agent Address:</label>
                    <div style="
                        background: #0a0a1a;
                        border-radius: 8px;
                        padding: 12px;
                        font-family: monospace;
                        font-size: 0.85rem;
                        color: #4ade80;
                        word-break: break-all;
                    ">${agentAddress}</div>
                </div>
                
                <div style="margin-bottom: 24px;">
                    <label style="color: var(--text-muted); font-size: 0.8rem;">Private Key:</label>
                    <div id="privateKeyDisplay" style="
                        background: #0a0a1a;
                        border-radius: 8px;
                        padding: 12px;
                        font-family: monospace;
                        font-size: 0.75rem;
                        color: #f59e0b;
                        word-break: break-all;
                        user-select: all;
                    ">${privateKey}</div>
                </div>
                
                <div style="display: flex; gap: 12px;">
                    <button onclick="AgentWallet.copyToClipboard('${privateKey}')" style="
                        flex: 1;
                        padding: 14px;
                        background: var(--bg-elevated);
                        border: 1px solid var(--border);
                        border-radius: 10px;
                        color: var(--text);
                        cursor: pointer;
                    ">📋 Copy Key</button>
                    
                    <button onclick="this.closest('.agent-wallet-modal').remove()" style="
                        flex: 1;
                        padding: 14px;
                        background: var(--gradient-gold);
                        border: none;
                        border-radius: 10px;
                        font-weight: 600;
                        cursor: pointer;
                    ">✓ I've Saved It</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    },

    copyToClipboard(text) {
        navigator.clipboard.writeText(text);
        Toast?.show('📋 Private key copied!', 'success');
    },

    // ===========================================
    // WALLET INFO
    // ===========================================

    async getWalletInfo() {
        if (!window.connectedWallet) return null;

        try {
            const response = await fetch(
                `${API_BASE}/api/agent-wallet/info?user_address=${window.connectedWallet}`
            );
            const data = await response.json();
            return data.success ? data.wallet : null;
        } catch (e) {
            console.error('Get wallet info error:', e);
            return null;
        }
    },

    async refreshBalances() {
        try {
            const response = await fetch(
                `${API_BASE}/api/agent-wallet/balances?user_address=${window.connectedWallet}`
            );
            const data = await response.json();
            if (data.success) {
                this.balances = data.balances;
                this.updateUI();
            }
        } catch (e) {
            console.error('Refresh balances error:', e);
        }
    },

    // ===========================================
    // DEPOSITS
    // ===========================================

    showDepositModal() {
        console.log('[AgentWallet] showDepositModal called');
        console.log('[AgentWallet] connectedWallet:', window.connectedWallet);
        console.log('[AgentWallet] agentAddress:', this.agentAddress);

        // First check if main wallet is connected
        if (!window.connectedWallet) {
            Toast?.show('Please connect your wallet first', 'warning');
            if (typeof connectWallet === 'function') {
                connectWallet();
            }
            return;
        }

        // Then check if agent wallet exists
        if (!this.agentAddress) {
            this.showCreateWalletPrompt();
            return;
        }

        const modal = document.createElement('div');
        modal.className = 'agent-wallet-modal';
        modal.style.cssText = `
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.85);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 3000;
        `;

        modal.innerHTML = `
            <div style="
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 20px;
                padding: 28px;
                max-width: 450px;
                width: 90%;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                    <h2 style="margin: 0;">💰 Deposit to Agent</h2>
                    <button onclick="this.closest('.agent-wallet-modal').remove()" style="
                        background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-muted);
                    ">×</button>
                </div>
                
                <div style="
                    background: var(--bg-elevated);
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 20px;
                ">
                    <label style="color: var(--text-muted); font-size: 0.8rem;">Agent Address</label>
                    <div style="font-family: monospace; font-size: 0.9rem; word-break: break-all;">
                        ${this.agentAddress}
                    </div>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px;">Token</label>
                    <select id="depositToken" style="
                        width: 100%; padding: 12px; background: var(--bg-elevated);
                        border: 1px solid var(--border); border-radius: 10px; color: var(--text);
                    ">
                        <option value="USDC">USDC</option>
                        <option value="USDT">USDT</option>
                        <option value="ETH">ETH</option>
                        <option value="WETH">WETH</option>
                    </select>
                </div>
                
                <div style="margin-bottom: 24px;">
                    <label style="display: block; margin-bottom: 8px;">Amount</label>
                    <input type="number" id="depositAmount" placeholder="0.00" style="
                        width: 100%; padding: 14px; background: var(--bg-elevated);
                        border: 1px solid var(--border); border-radius: 10px; color: var(--text);
                        font-size: 1.1rem;
                    ">
                </div>
                
                <button onclick="AgentWallet.executeDeposit()" style="
                    width: 100%; padding: 16px; background: var(--gradient-gold);
                    border: none; border-radius: 12px; font-weight: 600;
                    font-size: 1rem; cursor: pointer;
                ">
                    ⚡ Deposit to Agent
                </button>
                
                <p style="color: var(--text-muted); font-size: 0.8rem; text-align: center; margin: 16px 0 0;">
                    Send tokens directly to the agent address above,<br>
                    or click Deposit to transfer from your wallet.
                </p>
            </div>
        `;

        document.body.appendChild(modal);
    },

    async executeDeposit() {
        const token = document.getElementById('depositToken').value;
        const amount = parseFloat(document.getElementById('depositAmount').value);

        if (!amount || amount <= 0) {
            Toast?.show('Please enter a valid amount', 'warning');
            return;
        }

        try {
            Toast?.show('Preparing deposit...', 'info');

            // Get token contract and transfer
            let txHash;

            if (token === 'ETH') {
                // Native ETH transfer
                const value = BigInt(Math.floor(amount * 1e18));
                txHash = await window.ethereum.request({
                    method: 'eth_sendTransaction',
                    params: [{
                        from: window.connectedWallet,
                        to: this.agentAddress,
                        value: '0x' + value.toString(16)
                    }]
                });
            } else {
                // ERC20 transfer
                const tokenAddresses = {
                    'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
                    'USDT': '0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2',
                    'WETH': '0x4200000000000000000000000000000000000006'
                };

                const tokenAddress = tokenAddresses[token];
                const decimals = token === 'USDC' || token === 'USDT' ? 6 : 18;
                const amountWei = BigInt(Math.floor(amount * (10 ** decimals)));

                // Transfer data
                const transferData = '0xa9059cbb' +
                    this.agentAddress.slice(2).padStart(64, '0') +
                    amountWei.toString(16).padStart(64, '0');

                txHash = await window.ethereum.request({
                    method: 'eth_sendTransaction',
                    params: [{
                        from: window.connectedWallet,
                        to: tokenAddress,
                        data: transferData
                    }]
                });
            }

            Toast?.show('Transaction sent, confirming...', 'info');

            // Record deposit in backend
            await fetch(`${API_BASE}/api/agent-wallet/deposit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_address: window.connectedWallet,
                    token: token,
                    amount: amount,
                    tx_hash: txHash
                })
            });

            Toast?.show(`✅ Deposited ${amount} ${token} to agent!`, 'success');

            // Close modal and refresh
            document.querySelector('.agent-wallet-modal')?.remove();
            await this.refreshBalances();

        } catch (e) {
            console.error('Deposit error:', e);
            Toast?.show('Deposit failed: ' + (e.message || 'Unknown error'), 'error');
        }
    },

    // ===========================================
    // WITHDRAWALS
    // ===========================================

    showWithdrawModal() {
        if (!this.agentAddress) {
            Toast?.show('No agent wallet found', 'warning');
            return;
        }

        const modal = document.createElement('div');
        modal.className = 'agent-wallet-modal';
        modal.style.cssText = `
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.85);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 3000;
        `;

        const balanceHtml = Object.entries(this.balances)
            .map(([token, amount]) => `<div>${token}: ${amount?.toFixed(4) || 0}</div>`)
            .join('');

        modal.innerHTML = `
            <div style="
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 20px;
                padding: 28px;
                max-width: 450px;
                width: 90%;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                    <h2 style="margin: 0;">📤 Withdraw from Agent</h2>
                    <button onclick="this.closest('.agent-wallet-modal').remove()" style="
                        background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-muted);
                    ">×</button>
                </div>
                
                <div style="
                    background: var(--bg-elevated);
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 20px;
                ">
                    <div style="color: var(--text-muted); font-size: 0.8rem; margin-bottom: 8px;">Available Balances</div>
                    <div style="font-family: monospace;">${balanceHtml || 'No funds'}</div>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px;">Token</label>
                    <select id="withdrawToken" style="
                        width: 100%; padding: 12px; background: var(--bg-elevated);
                        border: 1px solid var(--border); border-radius: 10px; color: var(--text);
                    ">
                        ${Object.keys(this.balances).map(t => `<option value="${t}">${t}</option>`).join('')}
                    </select>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px;">Amount</label>
                    <input type="number" id="withdrawAmount" placeholder="0.00" style="
                        width: 100%; padding: 14px; background: var(--bg-elevated);
                        border: 1px solid var(--border); border-radius: 10px; color: var(--text);
                        font-size: 1.1rem;
                    ">
                </div>
                
                ${this.is2FAEnabled ? `
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 8px;">2FA Code (for large amounts)</label>
                        <input type="text" id="withdrawTOTP" placeholder="000000" maxlength="6" style="
                            width: 100%; padding: 14px; background: var(--bg-elevated);
                            border: 1px solid var(--border); border-radius: 10px; color: var(--text);
                            font-size: 1.2rem; text-align: center; letter-spacing: 8px;
                        ">
                    </div>
                ` : ''}
                
                <button onclick="AgentWallet.executeWithdraw()" style="
                    width: 100%; padding: 16px; background: var(--gradient-gold);
                    border: none; border-radius: 12px; font-weight: 600;
                    font-size: 1rem; cursor: pointer;
                ">
                    📤 Withdraw to My Wallet
                </button>
                
                <button onclick="AgentWallet.emergencyDrain()" style="
                    width: 100%; padding: 14px; background: #7f1d1d;
                    border: none; border-radius: 12px; font-weight: 600;
                    font-size: 0.9rem; cursor: pointer; margin-top: 12px;
                    color: #fca5a5;
                ">
                    🚨 Emergency: Withdraw ALL
                </button>
            </div>
        `;

        document.body.appendChild(modal);
    },

    async executeWithdraw() {
        const token = document.getElementById('withdrawToken').value;
        const amount = parseFloat(document.getElementById('withdrawAmount').value);
        const totpCode = document.getElementById('withdrawTOTP')?.value;

        if (!amount || amount <= 0) {
            Toast?.show('Please enter a valid amount', 'warning');
            return;
        }

        try {
            Toast?.show('Processing withdrawal...', 'info');

            const response = await fetch(`${API_BASE}/api/agent-wallet/withdraw`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_address: window.connectedWallet,
                    token: token,
                    amount: amount,
                    totp_code: totpCode || null
                })
            });

            const data = await response.json();

            if (data.success) {
                if (data.requires_multisig) {
                    Toast?.show(`⏳ Multi-sig required for large withdrawal. Request ID: ${data.request_id}`, 'warning');
                } else {
                    Toast?.show(`✅ Withdrawal of ${amount} ${token} initiated!`, 'success');
                    document.querySelector('.agent-wallet-modal')?.remove();
                    await this.refreshBalances();
                }
            } else {
                Toast?.show(data.detail || 'Withdrawal failed', 'error');
            }
        } catch (e) {
            console.error('Withdraw error:', e);
            Toast?.show('Withdrawal failed', 'error');
        }
    },

    async emergencyDrain() {
        if (!confirm('⚠️ This will withdraw ALL funds to your wallet. Continue?')) {
            return;
        }

        try {
            Toast?.show('🚨 Emergency drain initiated...', 'warning');

            const totpCode = document.getElementById('withdrawTOTP')?.value;

            const response = await fetch(`${API_BASE}/api/agent-wallet/emergency-drain`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_address: window.connectedWallet,
                    totp_code: totpCode || null
                })
            });

            const data = await response.json();

            if (data.success) {
                Toast?.show('✅ All funds withdrawn to your wallet!', 'success');
                document.querySelector('.agent-wallet-modal')?.remove();
                await this.refreshBalances();
            } else {
                Toast?.show(data.detail || 'Emergency drain failed', 'error');
            }
        } catch (e) {
            console.error('Emergency drain error:', e);
            Toast?.show('Emergency drain failed', 'error');
        }
    },

    // ===========================================
    // 2FA
    // ===========================================

    async setup2FA() {
        try {
            Toast?.show('Setting up 2FA...', 'info');

            const response = await fetch(`${API_BASE}/api/agent-wallet/2fa/setup`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_address: window.connectedWallet })
            });

            const data = await response.json();

            if (data.success) {
                this.show2FASetupModal(data);
            }
        } catch (e) {
            console.error('2FA setup error:', e);
            Toast?.show('2FA setup failed', 'error');
        }
    },

    show2FASetupModal(data) {
        const modal = document.createElement('div');
        modal.className = 'agent-wallet-modal';
        modal.style.cssText = `
            position: fixed; inset: 0; background: rgba(0,0,0,0.9);
            display: flex; align-items: center; justify-content: center; z-index: 3000;
        `;

        modal.innerHTML = `
            <div style="
                background: var(--bg-card); border: 1px solid var(--gold);
                border-radius: 20px; padding: 28px; max-width: 450px; width: 90%;
            ">
                <h2 style="margin: 0 0 20px; text-align: center;">🔐 Setup 2FA</h2>
                
                <p style="color: var(--text-muted); text-align: center; margin-bottom: 20px;">
                    Scan this QR code with Google Authenticator or similar app
                </p>
                
                <div style="
                    background: white; padding: 16px; border-radius: 12px;
                    text-align: center; margin-bottom: 20px;
                ">
                    <img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(data.qr_uri)}" 
                         alt="2FA QR Code" style="max-width: 200px;">
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="color: var(--text-muted); font-size: 0.8rem;">Manual Entry Key:</label>
                    <div style="
                        background: var(--bg-elevated); padding: 12px; border-radius: 8px;
                        font-family: monospace; font-size: 0.9rem; word-break: break-all;
                    ">${data.secret}</div>
                </div>
                
                <div style="margin-bottom: 24px;">
                    <label style="color: var(--text-muted); font-size: 0.8rem;">Recovery Codes (save these!):</label>
                    <div style="
                        background: #1a0a0a; padding: 12px; border-radius: 8px;
                        font-family: monospace; font-size: 0.85rem; color: #f59e0b;
                    ">${data.recovery_codes.join(' • ')}</div>
                </div>
                
                <button onclick="this.closest('.agent-wallet-modal').remove(); AgentWallet.is2FAEnabled = true;" style="
                    width: 100%; padding: 16px; background: var(--gradient-gold);
                    border: none; border-radius: 12px; font-weight: 600; cursor: pointer;
                ">✓ Done</button>
            </div>
        `;

        document.body.appendChild(modal);
    },

    // ===========================================
    // EXPORT KEY
    // ===========================================

    async exportPrivateKey() {
        if (!this.agentAddress) {
            Toast?.show('No agent wallet found', 'warning');
            return;
        }

        if (!confirm('⚠️ You are about to export your private key. Never share this with anyone!')) {
            return;
        }

        try {
            Toast?.show('Signing to export key...', 'info');

            // Get signature for decryption
            const message = `Export Techne Agent Private Key\n\nTimestamp: ${Date.now()}`;
            const signature = await window.ethereum.request({
                method: 'personal_sign',
                params: [message, window.connectedWallet]
            });

            // Get 2FA code if enabled
            let totpCode = null;
            if (this.is2FAEnabled) {
                totpCode = prompt('Enter your 2FA code:');
                if (!totpCode) return;
            }

            const response = await fetch(`${API_BASE}/api/agent-wallet/export-key`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_address: window.connectedWallet,
                    signature: signature,
                    totp_code: totpCode
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showPrivateKeyModal(data.private_key, this.agentAddress);
            } else {
                Toast?.show(data.detail || 'Failed to export key', 'error');
            }
        } catch (e) {
            console.error('Export key error:', e);
            Toast?.show('Export cancelled', 'warning');
        }
    },

    // ===========================================
    // UI HELPERS
    // ===========================================

    showCreateWalletPrompt() {
        const modal = document.createElement('div');
        modal.className = 'agent-wallet-modal';
        modal.style.cssText = `
            position: fixed; inset: 0; background: rgba(0,0,0,0.85);
            display: flex; align-items: center; justify-content: center; z-index: 3000;
        `;

        modal.innerHTML = `
            <div style="
                background: var(--bg-card); border: 1px solid var(--border);
                border-radius: 20px; padding: 32px; max-width: 400px; width: 90%; text-align: center;
            ">
                <div style="font-size: 64px; margin-bottom: 16px;">🤖</div>
                <h2 style="margin: 0 0 12px;">Create Agent Wallet</h2>
                <p style="color: var(--text-muted); margin-bottom: 24px;">
                    Your agent needs a wallet to manage yield strategies on your behalf.
                </p>
                
                <button onclick="AgentWallet.createWallet(); this.closest('.agent-wallet-modal').remove();" style="
                    width: 100%; padding: 16px; background: var(--gradient-gold);
                    border: none; border-radius: 12px; font-weight: 600;
                    font-size: 1rem; cursor: pointer; margin-bottom: 12px;
                ">🔐 Create Agent Wallet</button>
                
                <button onclick="this.closest('.agent-wallet-modal').remove()" style="
                    width: 100%; padding: 14px; background: transparent;
                    border: 1px solid var(--border); border-radius: 12px;
                    color: var(--text-muted); cursor: pointer;
                ">Cancel</button>
            </div>
        `;

        document.body.appendChild(modal);
    },

    updateUI() {
        // Update balance displays
        const balanceEl = document.getElementById('agentBalance');
        if (balanceEl && this.balances) {
            const total = Object.entries(this.balances)
                .reduce((sum, [token, amt]) => {
                    const prices = { USDC: 1, USDT: 1, ETH: 3500, WETH: 3500, DAI: 1 };
                    return sum + (amt || 0) * (prices[token] || 0);
                }, 0);
            balanceEl.textContent = `$${total.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
        }

        // Update agent address display
        const addrEl = document.getElementById('agentAddress');
        if (addrEl && this.agentAddress) {
            addrEl.textContent = `${this.agentAddress.slice(0, 6)}...${this.agentAddress.slice(-4)}`;
        }
    }
};

// Initialize when wallet connects
document.addEventListener('walletConnected', () => {
    AgentWallet.init();
});

// Also try on page load if wallet already connected
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        if (window.connectedWallet) {
            AgentWallet.init();
        }
    }, 1000);
});

// Export
window.AgentWallet = AgentWallet;
