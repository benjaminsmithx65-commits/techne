/**
 * Techne Agent Wallet UI
 * V4.3.2 - Production with Flash Loan Deleverage, Cross-Asset Swap, Sequencer Check
 */

const AgentWalletUI = {
    // Legacy Contract - V4.3.3 (for backward compatibility)
    contractAddress: '0xC83E01e39A56Ec8C56Dd45236E58eE7a139cCDD4',
    contractVersion: 'V4.3.3',

    // NEW: Smart Account Factory (Trustless Architecture)
    factoryAddress: '0x33f5e2F6d194869ACc60C965C2A24eDC5de8a216',

    // Factory ABI for creating Smart Accounts
    FACTORY_ABI: [
        'function createAccount(bytes32 salt) returns (address account)',
        'function getAddress(address owner, bytes32 salt) view returns (address)',
        'function getAccounts(address owner) view returns (address[])',
        'function getAccountCount(address owner) view returns (uint256)'
    ],

    // Smart Account ABI (for owner operations)
    SMART_ACCOUNT_ABI: [
        'function execute(address target, uint256 value, bytes data) returns (bytes)',
        'function owner() view returns (address)',
        'function addSessionKey(address key, uint48 validUntil, uint256 dailyLimitUSD)',
        'function revokeSessionKey(address key)',
        'function getSessionKeyInfo(address key) view returns (bool active, uint48 validUntil, uint256 dailyLimitUSD, uint256 spentTodayUSD)',
        'function revenueFee() view returns (uint256)',
        'function MAX_REVENUE_FEE_BPS() view returns (uint256)'
    ],

    // User's Smart Account address (populated after connection)
    userSmartAccount: null,

    // Supported tokens on Base
    TOKENS: {
        USDC: {
            address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            decimals: 6,
            symbol: 'USDC',
            name: 'USD Coin',
            icon: '💵'
        },
        ETH: {
            address: null,  // Native ETH - no contract address
            decimals: 18,
            symbol: 'ETH',
            name: 'Ether',
            icon: '⟠',
            isNative: true
        },
        WETH: {
            address: '0x4200000000000000000000000000000000000006',
            decimals: 18,
            symbol: 'WETH',
            name: 'Wrapped Ether',
            icon: '⟠'
        }
    },

    // Legacy (keep for compatibility)
    USDC_ADDRESS: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',

    // ERC20 ABI for read/write
    ERC20_ABI: [
        'function approve(address spender, uint256 amount) returns (bool)',
        'function balanceOf(address account) view returns (uint256)',
        'function allowance(address owner, address spender) view returns (uint256)',
        'function decimals() view returns (uint8)',
        'function symbol() view returns (string)'
    ],

    // Vault V4 ABI - Individual Model (no shares!)
    WALLET_ABI: [
        // Core functions
        'function deposit(uint256 amount)',
        'function withdraw(uint256 amount)',
        'function withdrawAll()',

        // View functions - Individual balances (no shares!)
        'function balances(address user) view returns (uint256)',
        'function investments(address user, address protocol) view returns (uint256)',
        'function totalInvested(address user) view returns (uint256)',
        'function getUserTotalValue(address user) view returns (uint256)',
        'function getUserFreeBalance(address user) view returns (uint256)',
        'function getUserInvestment(address user, address protocol) view returns (uint256)',
        'function getUserProtocols(address user) view returns (address[])',
        'function canWithdraw(address user) view returns (bool available, uint256 timeLeft)',
        'function isWhitelisted(address user) view returns (bool)',

        // V4 Security - Constants
        'function DEPOSIT_COOLDOWN() view returns (uint256)',
        'function MINIMUM_DEPOSIT() view returns (uint256)',
        'function MAX_SINGLE_WITHDRAW() view returns (uint256)',

        // V4 Access Control
        'function hasRole(bytes32 role, address account) view returns (bool)',

        // Emergency
        'function emergencyMode() view returns (bool)',
        'function paused() view returns (bool)'
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
    selectedToken: 'USDC', // Currently selected deposit token

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

    // ============================================
    // SMART ACCOUNT METHODS (Trustless Architecture)
    // ============================================

    /**
     * Check if user has a Smart Account
     * @returns {Promise<string|null>} Smart Account address or null
     */
    async checkSmartAccount() {
        if (!window.ethereum) {
            console.warn('[SmartAccount] No wallet connected');
            return null;
        }

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();
            const userAddress = await signer.getAddress();

            const factory = new ethers.Contract(
                this.factoryAddress,
                this.FACTORY_ABI,
                provider
            );

            const accounts = await factory.getAccounts(userAddress);

            if (accounts.length > 0) {
                this.userSmartAccount = accounts[0];
                console.log('[SmartAccount] Found:', this.userSmartAccount);
                return this.userSmartAccount;
            }

            console.log('[SmartAccount] No account found for', userAddress);
            return null;

        } catch (error) {
            console.error('[SmartAccount] Check failed:', error);
            return null;
        }
    },

    /**
     * Create a new Smart Account for the user
     * @returns {Promise<string>} Created account address
     */
    async createSmartAccount() {
        if (!window.ethereum) {
            throw new Error('Please connect your wallet first');
        }

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();

            const factory = new ethers.Contract(
                this.factoryAddress,
                this.FACTORY_ABI,
                signer
            );

            // Generate unique salt
            const salt = ethers.keccak256(
                ethers.solidityPacked(
                    ['address', 'uint256'],
                    [await signer.getAddress(), Date.now()]
                )
            );

            console.log('[SmartAccount] Creating with salt:', salt);

            const tx = await factory.createAccount(salt);
            console.log('[SmartAccount] TX sent:', tx.hash);

            const receipt = await tx.wait();
            console.log('[SmartAccount] Created in block:', receipt.blockNumber);

            // Get the created account address
            const accounts = await factory.getAccounts(await signer.getAddress());
            this.userSmartAccount = accounts[accounts.length - 1];

            console.log('[SmartAccount] Address:', this.userSmartAccount);
            return this.userSmartAccount;

        } catch (error) {
            console.error('[SmartAccount] Creation failed:', error);
            throw error;
        }
    },

    /**
     * Revoke a session key (emergency stop)
     * @param {string} sessionKeyAddress - Address of the session key to revoke
     */
    async revokeSessionKey(sessionKeyAddress) {
        if (!this.userSmartAccount) {
            throw new Error('No Smart Account found');
        }

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();

            const account = new ethers.Contract(
                this.userSmartAccount,
                this.SMART_ACCOUNT_ABI,
                signer
            );

            const tx = await account.revokeSessionKey(sessionKeyAddress);
            console.log('[SmartAccount] Revoking session key:', tx.hash);

            await tx.wait();
            console.log('[SmartAccount] Session key revoked successfully');

            return true;

        } catch (error) {
            console.error('[SmartAccount] Revoke failed:', error);
            throw error;
        }
    },

    /**
     * Get Smart Account info (fee, session keys)
     */
    async getSmartAccountInfo() {
        if (!this.userSmartAccount) {
            return null;
        }

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);

            const account = new ethers.Contract(
                this.userSmartAccount,
                this.SMART_ACCOUNT_ABI,
                provider
            );

            const [revenueFee, maxFee] = await Promise.all([
                account.revenueFee(),
                account.MAX_REVENUE_FEE_BPS()
            ]);

            return {
                address: this.userSmartAccount,
                revenueFeePercent: Number(revenueFee) / 100, // Convert BPS to %
                maxFeePercent: Number(maxFee) / 100
            };

        } catch (error) {
            console.error('[SmartAccount] Get info failed:', error);
            return null;
        }
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
                    <button class="btn-vault-deposit" onclick="window.AgentWalletUI.showDepositModal()">
                        <span class="techne-icon">${TechneIcons.deposit}</span> Deposit
                    </button>
                    <button class="btn-vault-withdraw" onclick="window.AgentWalletUI.showWithdrawModal()">
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
     * Show deposit modal - Premium styled
     */
    showDepositModal() {
        // Remove existing
        document.getElementById('vaultModal')?.remove();

        const modal = document.createElement('div');
        modal.id = 'vaultModal';
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(12px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.2s ease;
        `;

        modal.innerHTML = `
            <div class="vault-modal-premium" style="
                background: linear-gradient(180deg, rgba(26, 26, 30, 0.98), rgba(18, 18, 20, 0.99));
                border: 1px solid rgba(212, 168, 83, 0.25);
                border-radius: 20px;
                width: 420px;
                max-width: 95vw;
                overflow: hidden;
                box-shadow: 0 25px 80px rgba(0,0,0,0.5), 0 0 60px rgba(212, 168, 83, 0.1);
                animation: slideUp 0.3s ease;
            ">
                <!-- Header -->
                <div style="
                    background: linear-gradient(135deg, rgba(212, 168, 83, 0.12), transparent);
                    padding: 24px;
                    border-bottom: 1px solid rgba(212, 168, 83, 0.15);
                    display: flex;
                    align-items: center;
                    gap: 14px;
                ">
                    <div style="
                        width: 48px;
                        height: 48px;
                        background: linear-gradient(135deg, rgba(212, 168, 83, 0.2), rgba(212, 168, 83, 0.05));
                        border: 1px solid rgba(212, 168, 83, 0.3);
                        border-radius: 12px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    ">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                            <path d="M12 2L4 6v6c0 5.5 3.5 10.7 8 12 4.5-1.3 8-6.5 8-12V6l-8-4z" 
                                stroke="#d4a853" stroke-width="1.5" fill="rgba(212,168,83,0.1)"/>
                            <path d="M12 8v4m0 0v4m0-4h4m-4 0H8" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
                        </svg>
                    </div>
                    <div style="flex: 1;">
                        <h2 style="margin: 0; font-size: 1.2rem; color: #fff; font-weight: 600;">Fund Agent Vault</h2>
                        <p style="margin: 4px 0 0; font-size: 0.8rem; color: rgba(255,255,255,0.5);">Deposit USDC for autonomous yield optimization</p>
                    </div>
                    <button onclick="document.getElementById('vaultModal').remove()" style="
                        background: rgba(255,255,255,0.05);
                        border: 1px solid rgba(255,255,255,0.1);
                        border-radius: 8px;
                        width: 32px;
                        height: 32px;
                        color: rgba(255,255,255,0.5);
                        cursor: pointer;
                        font-size: 1rem;
                        transition: all 0.2s;
                    " onmouseover="this.style.background='rgba(255,255,255,0.1)'" 
                       onmouseout="this.style.background='rgba(255,255,255,0.05)'">✕</button>
                </div>

                <!-- Body -->
                <div style="padding: 24px;">
                    <!-- Agent Selector -->
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-size: 0.7rem; color: rgba(255,255,255,0.5); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Select Agent</label>
                        <select id="agentSelect" onchange="AgentWalletUI.onAgentSelect(this.value)" style="
                            width: 100%;
                            padding: 14px 16px;
                            background: rgba(0,0,0,0.4);
                            border: 1px solid rgba(255,255,255,0.12);
                            border-radius: 12px;
                            color: #fff;
                            font-size: 0.95rem;
                            font-weight: 500;
                            cursor: pointer;
                            appearance: none;
                            background-image: url('data:image/svg+xml;utf8,<svg fill=\"white\" height=\"24\" viewBox=\"0 0 24 24\" width=\"24\" xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M7 10l5 5 5-5z\"/></svg>');
                            background-repeat: no-repeat;
                            background-position: right 12px center;
                            background-size: 20px;
                        ">
                            <option value="">Loading agents...</option>
                        </select>
                    </div>

                    <!-- Token Selector -->
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-size: 0.7rem; color: rgba(255,255,255,0.5); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Select Token</label>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <button id="tokenSelectUSDC" onclick="AgentWalletUI.selectToken('USDC')" style="
                                padding: 14px 16px;
                                background: rgba(212, 168, 83, 0.12);
                                border: 2px solid #d4a853;
                                border-radius: 12px;
                                color: #fff;
                                font-weight: 600;
                                cursor: pointer;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                gap: 10px;
                                transition: all 0.2s;
                                font-size: 0.95rem;
                            ">
                                <img src="/icons/usdc.png" alt="USDC" style="width: 22px; height: 22px; border-radius: 50%;">
                                <span>USDC</span>
                            </button>
                            <button id="tokenSelectETH" onclick="AgentWalletUI.selectToken('ETH')" style="
                                padding: 14px 16px;
                                background: rgba(255,255,255,0.03);
                                border: 1px solid rgba(255,255,255,0.12);
                                border-radius: 12px;
                                color: rgba(255,255,255,0.7);
                                font-weight: 600;
                                cursor: pointer;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                gap: 10px;
                                transition: all 0.2s;
                                font-size: 0.95rem;
                            ">
                                <img src="/icons/ethereum.png" alt="ETH" style="width: 22px; height: 22px; border-radius: 50%;">
                                <span>ETH</span>
                                <span style="
                                    background: rgba(99, 102, 241, 0.2);
                                    color: #818cf8;
                                    padding: 2px 6px;
                                    border-radius: 4px;
                                    font-size: 0.65rem;
                                    font-weight: 700;
                                    text-transform: uppercase;
                                    letter-spacing: 0.5px;
                                ">Gas</span>
                            </button>
                        </div>
                    </div>

                    <!-- Amount Input -->
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-size: 0.75rem; color: rgba(255,255,255,0.6); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Amount (<span id="selectedTokenLabel">USDC</span>)</label>
                        <div style="
                            display: flex;
                            background: rgba(0,0,0,0.4);
                            border: 1px solid rgba(255,255,255,0.1);
                            border-radius: 12px;
                            overflow: hidden;
                            transition: border-color 0.2s;
                        " onfocus="this.style.borderColor='rgba(212,168,83,0.5)'">
                            <input type="number" id="depositAmount" placeholder="0.00" min="0.001" step="any" style="
                                flex: 1;
                                background: transparent;
                                border: none;
                                padding: 16px;
                                font-size: 1.3rem;
                                color: #fff;
                                outline: none;
                                font-weight: 500;
                            ">
                            <button onclick="AgentWalletUI.setMaxDeposit()" style="
                                background: linear-gradient(135deg, rgba(212, 168, 83, 0.2), rgba(212, 168, 83, 0.1));
                                border: none;
                                border-left: 1px solid rgba(255,255,255,0.1);
                                padding: 0 20px;
                                color: #d4a853;
                                font-weight: 600;
                                font-size: 0.8rem;
                                cursor: pointer;
                                transition: all 0.2s;
                            " onmouseover="this.style.background='rgba(212,168,83,0.3)'"
                               onmouseout="this.style.background='linear-gradient(135deg, rgba(212, 168, 83, 0.2), rgba(212, 168, 83, 0.1))'">MAX</button>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.75rem; color: rgba(255,255,255,0.4);">
                            <span>Balance: <span id="tokenBalance" style="color: #d4a853;">--</span> <span id="tokenSymbol">USDC</span></span>
                            <span id="minAmountHint">Min: 10 USDC</span>
                        </div>
                    </div>

                    <!-- Summary Card -->
                    <div style="
                        background: rgba(212, 168, 83, 0.05);
                        border: 1px solid rgba(212, 168, 83, 0.15);
                        border-radius: 12px;
                        padding: 16px;
                        margin-bottom: 20px;
                    ">
                        <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <span style="color: rgba(255,255,255,0.6); font-size: 0.85rem;">Estimated APY</span>
                            <span style="color: #22c55e; font-weight: 600;">${this.estimatedAPY || '--'}%</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <span style="color: rgba(255,255,255,0.6); font-size: 0.85rem;">Performance Fee</span>
                            <span style="color: rgba(255,255,255,0.8);">10% of yield</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 8px 0; align-items: center;">
                            <span style="color: rgba(255,255,255,0.6); font-size: 0.85rem;">Network</span>
                            <span style="
                                display: flex;
                                align-items: center;
                                gap: 6px;
                                color: #fff;
                                font-weight: 500;
                            ">
                                <span style="width: 16px; height: 16px; background: #0052ff; border-radius: 50%;"></span>
                                Base
                            </span>
                        </div>
                    </div>

                    <!-- CTA Button -->
                    <button id="depositBtn" onclick="AgentWalletUI.executeDeposit()" style="
                        width: 100%;
                        padding: 16px;
                        background: linear-gradient(135deg, #d4a853, #c49a48);
                        border: none;
                        border-radius: 12px;
                        color: #000;
                        font-size: 1rem;
                        font-weight: 600;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        transition: all 0.2s;
                        box-shadow: 0 4px 20px rgba(212, 168, 83, 0.3);
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 25px rgba(212, 168, 83, 0.4)'"
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 20px rgba(212, 168, 83, 0.3)'">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                            <path d="M12 2L4 6v6c0 5.5 3.5 10.7 8 12 4.5-1.3 8-6.5 8-12V6l-8-4z" stroke="currentColor" stroke-width="2"/>
                            <path d="M9 12l2 2 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                        Approve & Deposit
                    </button>

                    <!-- Disclaimer -->
                    <p style="
                        margin: 16px 0 0;
                        font-size: 0.7rem;
                        color: rgba(255,255,255,0.35);
                        text-align: center;
                        line-height: 1.5;
                    ">
                        By depositing, you authorize the Techne Agent to manage your funds across DeFi protocols.
                    </p>
                </div>
            </div>

            <style>
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
                #depositAmount::placeholder { color: rgba(255,255,255,0.3); }
                #depositAmount:focus { color: #fff; }
            </style>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        // Load USDC balance
        this.loadUSDCBalance();

        // Load agents for dropdown
        this.loadAgentsForSelect();
    },

    /**
     * Load deployed agents for the dropdown selector
     */
    async loadAgentsForSelect() {
        const select = document.getElementById('agentSelect');
        if (!select) return;

        try {
            // Get agents from localStorage or API
            const agents = JSON.parse(localStorage.getItem('techne_deployed_agents') || '[]');

            if (agents.length === 0) {
                select.innerHTML = '<option value="">No agents deployed</option>';
                return;
            }

            select.innerHTML = agents.map((agent, i) => `
                <option value="${agent.address || agent.smartAccount}" ${i === 0 ? 'selected' : ''}>
                    ${agent.name || agent.strategy || 'Agent'} - ${(agent.address || agent.smartAccount || '').slice(0, 10)}...
                </option>
            `).join('');

            // Auto-select first agent
            if (agents.length > 0) {
                this.selectedAgent = agents[0];
            }
        } catch (e) {
            console.warn('[AgentWallet] Failed to load agents:', e);
            select.innerHTML = '<option value="">Error loading agents</option>';
        }
    },

    /**
     * Handle agent selection change
     */
    onAgentSelect(address) {
        const agents = JSON.parse(localStorage.getItem('techne_deployed_agents') || '[]');
        this.selectedAgent = agents.find(a => (a.address || a.smartAccount) === address) || null;
        console.log('[AgentWallet] Selected agent:', this.selectedAgent);
    },

    /**
     * Show withdraw modal - Premium styled
     * @param {string} asset - Token symbol (USDC, ETH, WETH)
     */
    async showWithdrawModal(asset = 'USDC') {
        // CRITICAL: Refresh stats from contract BEFORE showing modal
        // This ensures userValue is populated with actual vault balance
        try {
            await this.refreshStats();
            console.log('[AgentWallet] Withdraw modal - userValue:', this.userValue);
        } catch (e) {
            console.warn('[AgentWallet] Failed to refresh stats before withdraw:', e);
            // Continue anyway - show modal with whatever data we have
        }

        // Store which token we're withdrawing
        this.withdrawToken = asset;
        document.getElementById('vaultModal')?.remove();

        const modal = document.createElement('div');
        modal.id = 'vaultModal';
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(12px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.2s ease;
        `;

        modal.innerHTML = `
            <div class="vault-modal-premium" style="
                background: linear-gradient(180deg, rgba(26, 26, 30, 0.98), rgba(18, 18, 20, 0.99));
                border: 1px solid rgba(212, 168, 83, 0.25);
                border-radius: 20px;
                width: 420px;
                max-width: 95vw;
                overflow: hidden;
                box-shadow: 0 25px 80px rgba(0,0,0,0.5), 0 0 60px rgba(212, 168, 83, 0.1);
                animation: slideUp 0.3s ease;
            ">
                <!-- Header -->
                <div style="
                    background: linear-gradient(135deg, rgba(212, 168, 83, 0.12), transparent);
                    padding: 24px;
                    border-bottom: 1px solid rgba(212, 168, 83, 0.15);
                    display: flex;
                    align-items: center;
                    gap: 14px;
                ">
                    <div style="
                        width: 48px;
                        height: 48px;
                        background: linear-gradient(135deg, rgba(212, 168, 83, 0.2), rgba(212, 168, 83, 0.05));
                        border: 1px solid rgba(212, 168, 83, 0.3);
                        border-radius: 12px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    ">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                            <path d="M3 12h6l2 3h2l2-3h6" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
                            <path d="M12 3v6m0 0l3-3m-3 3L9 6" stroke="#d4a853" stroke-width="1.5" stroke-linecap="round"/>
                            <rect x="4" y="12" width="16" height="9" rx="2" stroke="#d4a853" stroke-width="1.5" fill="rgba(212,168,83,0.05)"/>
                        </svg>
                    </div>
                    <div style="flex: 1;">
                        <h2 style="margin: 0; font-size: 1.2rem; color: #fff; font-weight: 600;">Withdraw Funds</h2>
                        <p style="margin: 4px 0 0; font-size: 0.8rem; color: rgba(255,255,255,0.5);">Withdraw ${asset} from your Agent Vault</p>
                    </div>
                    <button onclick="document.getElementById('vaultModal').remove()" style="
                        background: rgba(255,255,255,0.05);
                        border: 1px solid rgba(255,255,255,0.1);
                        border-radius: 8px;
                        width: 32px;
                        height: 32px;
                        color: rgba(255,255,255,0.5);
                        cursor: pointer;
                        font-size: 1rem;
                        transition: all 0.2s;
                    " onmouseover="this.style.background='rgba(255,255,255,0.1)'" 
                       onmouseout="this.style.background='rgba(255,255,255,0.05)'">✕</button>
                </div>

                <!-- Body -->
                <div style="padding: 24px;">
                    <!-- Position Info -->
                    <div style="
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 12px;
                        margin-bottom: 20px;
                    ">
                        <div style="
                            background: rgba(255,255,255,0.03);
                            border: 1px solid rgba(255,255,255,0.08);
                            border-radius: 12px;
                            padding: 16px;
                            text-align: center;
                        ">
                            <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-bottom: 6px;">Your Position</div>
                            <div style="font-size: 1.3rem; color: #22c55e; font-weight: 600;" id="withdrawPositionValue">$${(Number(this.userValue) / 1e6).toFixed(2)}</div>
                        </div>
                        <div style="
                            background: rgba(255,255,255,0.03);
                            border: 1px solid rgba(255,255,255,0.08);
                            border-radius: 12px;
                            padding: 16px;
                            text-align: center;
                        ">
                            <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-bottom: 6px;">Available</div>
                            <div style="font-size: 1.3rem; color: #fff; font-weight: 600;">${(Number(this.userValue) / 1e6).toFixed(2)} ${asset}</div>
                        </div>
                    </div>

                    <!-- Shares Input -->
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-size: 0.75rem; color: rgba(255,255,255,0.6); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">${asset} Amount to Withdraw</label>
                        <div style="
                            display: flex;
                            background: rgba(0,0,0,0.4);
                            border: 1px solid rgba(255,255,255,0.1);
                            border-radius: 12px;
                            overflow: hidden;
                        ">
                            <input type="number" id="withdrawShares" placeholder="0" min="1" max="${this.userShares}" style="
                                flex: 1;
                                background: transparent;
                                border: none;
                                padding: 16px;
                                font-size: 1.3rem;
                                color: #fff;
                                outline: none;
                                font-weight: 500;
                            ">
                            <button onclick="AgentWalletUI.setMaxWithdraw()" style="
                                background: linear-gradient(135deg, rgba(212, 168, 83, 0.2), rgba(212, 168, 83, 0.1));
                                border: none;
                                border-left: 1px solid rgba(255,255,255,0.1);
                                padding: 0 20px;
                                color: #d4a853;
                                font-weight: 600;
                                font-size: 0.8rem;
                                cursor: pointer;
                            ">MAX</button>
                        </div>
                        <div style="margin-top: 8px; font-size: 0.75rem; color: rgba(255,255,255,0.4);">
                            Available: ${(Number(this.userValue) / 1e6).toFixed(2)} ${asset}
                        </div>
                    </div>

                    <!-- Estimate -->
                    <div style="
                        background: rgba(34, 197, 94, 0.08);
                        border: 1px solid rgba(34, 197, 94, 0.2);
                        border-radius: 12px;
                        padding: 16px;
                        margin-bottom: 20px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    ">
                        <span style="color: rgba(255,255,255,0.7); font-size: 0.85rem;">You will receive:</span>
                        <span style="color: #22c55e; font-size: 1.2rem; font-weight: 600;" id="withdrawEstimate">$0.00</span>
                    </div>

                    <!-- CTA Button -->
                    <button id="withdrawBtn" onclick="AgentWalletUI.executeWithdraw()" style="
                        width: 100%;
                        padding: 16px;
                        background: linear-gradient(135deg, #d4a853, #c49a48);
                        border: none;
                        border-radius: 12px;
                        color: #000;
                        font-size: 1rem;
                        font-weight: 600;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        transition: all 0.2s;
                        box-shadow: 0 4px 20px rgba(212, 168, 83, 0.3);
                    " onmouseover="this.style.transform='translateY(-2px)'"
                       onmouseout="this.style.transform='translateY(0)'">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                            <path d="M3 12h6l2 3h2l2-3h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                            <path d="M12 3v6m0 0l3-3m-3 3L9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                        Withdraw ${asset}
                    </button>
                </div>
            </div>

            <style>
                @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
                #withdrawShares::placeholder { color: rgba(255,255,255,0.3); }
            </style>
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
     * Select deposit token (USDC or ETH)
     */
    selectToken(symbol) {
        this.selectedToken = symbol;
        const token = this.TOKENS[symbol];

        // Update UI
        const usdcBtn = document.getElementById('tokenSelectUSDC');
        const ethBtn = document.getElementById('tokenSelectETH');

        if (symbol === 'USDC') {
            usdcBtn.style.background = 'rgba(212, 168, 83, 0.15)';
            usdcBtn.style.border = '2px solid #d4a853';
            usdcBtn.style.color = '#fff';
            ethBtn.style.background = 'rgba(255,255,255,0.03)';
            ethBtn.style.border = '1px solid rgba(255,255,255,0.1)';
            ethBtn.style.color = 'rgba(255,255,255,0.7)';
        } else {
            ethBtn.style.background = 'rgba(212, 168, 83, 0.15)';
            ethBtn.style.border = '2px solid #d4a853';
            ethBtn.style.color = '#fff';
            usdcBtn.style.background = 'rgba(255,255,255,0.03)';
            usdcBtn.style.border = '1px solid rgba(255,255,255,0.1)';
            usdcBtn.style.color = 'rgba(255,255,255,0.7)';
        }

        // Update labels
        document.getElementById('selectedTokenLabel').textContent = symbol;
        document.getElementById('tokenSymbol').textContent = symbol;
        document.getElementById('minAmountHint').textContent =
            symbol === 'USDC' ? 'Min: 10 USDC' : 'Min: 0.001 ETH';

        // Clear and reload balance
        document.getElementById('depositAmount').value = '';
        this.loadTokenBalance();
    },

    /**
     * Load selected token balance
     */
    async loadTokenBalance() {
        if (!window.connectedWallet || !window.ethereum) return;

        const token = this.TOKENS[this.selectedToken];

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            let balance;

            // Handle native ETH differently
            if (token.isNative) {
                balance = await provider.getBalance(window.connectedWallet);
            } else {
                const contract = new ethers.Contract(token.address, this.ERC20_ABI, provider);
                balance = await contract.balanceOf(window.connectedWallet);
            }

            const formatted = (Number(balance) / Math.pow(10, token.decimals)).toFixed(
                token.decimals === 18 ? 4 : 2
            );

            document.getElementById('tokenBalance').textContent = formatted;
            this.currentBalance = formatted;
        } catch (e) {
            console.error('[AgentWallet] Error loading balance:', e);
            document.getElementById('tokenBalance').textContent = '--';
        }
    },

    /**
     * Legacy: Load user's USDC balance (for compatibility)
     */
    async loadUSDCBalance() {
        this.selectedToken = 'USDC';
        await this.loadTokenBalance();
    },

    /**
     * Set max deposit amount
     */
    setMaxDeposit() {
        const balanceText = document.getElementById('tokenBalance')?.textContent;
        if (balanceText && balanceText !== '--') {
            document.getElementById('depositAmount').value = balanceText;
        }
    },

    /**
     * Set max withdraw - V4.3.2 uses USDC amount!
     */
    setMaxWithdraw() {
        // userValue is in raw USDC units, convert to display
        const maxUsdc = (Number(this.userValue) / 1e6).toFixed(2);
        document.getElementById('withdrawShares').value = maxUsdc;
        this.updateWithdrawEstimate(maxUsdc);
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
        const estimate = (shares / Math.max(1, Number(this.userShares))) * Number(this.userValue);
        document.getElementById('withdrawEstimate').textContent =
            '$' + (estimate / 1e6).toFixed(2);
    },

    /**
     * Execute deposit transaction (multi-token support)
     * AUTO-WHITELIST: Now automatically whitelists user before deposit
     */
    async executeDeposit() {
        const amount = document.getElementById('depositAmount')?.value;
        const token = this.TOKENS[this.selectedToken];

        // Validate minimum amounts
        const minAmount = this.selectedToken === 'USDC' ? 10 : 0.001;
        if (!amount || parseFloat(amount) < minAmount) {
            alert(`Minimum deposit is ${minAmount} ${this.selectedToken}`);
            return;
        }

        if (!window.connectedWallet) {
            alert('Please connect your wallet');
            return;
        }

        const btn = document.getElementById('depositBtn');
        btn.disabled = true;

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();
            const userAddress = await signer.getAddress();

            // ============================================
            // AUTO-WHITELIST: Call backend to whitelist user first
            // ============================================
            btn.innerHTML = '<span>🔐</span> Checking whitelist...';

            try {
                const whitelistResp = await fetch(
                    `${window.API_BASE || 'http://localhost:8000'}/api/whitelist?user_address=${userAddress}`,
                    { method: 'POST' }
                );
                const whitelistResult = await whitelistResp.json();

                if (whitelistResult.success) {
                    if (whitelistResult.tx_hash) {
                        console.log('[AgentWallet] User whitelisted, TX:', whitelistResult.tx_hash);
                        btn.innerHTML = '<span>✓</span> Whitelisted! Approving...';
                        // Wait for tx to be mined
                        await new Promise(r => setTimeout(r, 3000));
                    } else {
                        console.log('[AgentWallet] User already whitelisted');
                    }
                } else {
                    console.warn('[AgentWallet] Whitelist warning:', whitelistResult.message);
                    // Continue anyway - user might be manually whitelisted
                }
            } catch (wlError) {
                console.warn('[AgentWallet] Whitelist service unavailable:', wlError);
                // Continue anyway - fallback to direct deposit attempt
            }

            // Calculate amount in token's decimals
            const amountWei = BigInt(Math.floor(parseFloat(amount) * Math.pow(10, token.decimals)));

            let depositTx;

            // Handle native ETH - send to user's Smart Account for gas
            if (token.isNative) {
                btn.innerHTML = '<span>⏳</span> Funding Agent Gas...';

                // Get user's Smart Account address (ERC-4337)
                let gasRecipient;
                try {
                    const saResult = await NetworkUtils.getSmartAccount(userAddress);
                    if (saResult.success && saResult.smartAccount) {
                        gasRecipient = saResult.smartAccount;
                        console.log('[AgentWallet] Sending ETH to Smart Account:', gasRecipient);
                    } else {
                        // Fallback to shared executor if no Smart Account
                        gasRecipient = '0xEe95B8114b144f48A742BA96Dc6c167a35829Fe1';
                        console.log('[AgentWallet] No Smart Account, using shared executor');
                    }
                } catch (e) {
                    // Fallback to shared executor
                    gasRecipient = '0xEe95B8114b144f48A742BA96Dc6c167a35829Fe1';
                    console.warn('[AgentWallet] Smart Account check failed, using fallback:', e);
                }

                // Send ETH to the appropriate address
                depositTx = await signer.sendTransaction({
                    to: gasRecipient,
                    value: amountWei
                });

                console.log('[AgentWallet] ETH sent to:', gasRecipient);
            } else {
                // For ERC20 tokens - different handling for USDC vs other tokens
                btn.innerHTML = '<span>⏳</span> Approving...';
                const tokenContract = new ethers.Contract(token.address, this.ERC20_ABI, signer);

                if (this.selectedToken === 'USDC') {
                    // USDC goes to V4 contract via approve+deposit
                    // This is where backend reads balance from: contract.balances(user)
                    const approveTx = await tokenContract.approve(this.contractAddress, amountWei);
                    await approveTx.wait();

                    btn.innerHTML = '<span>⏳</span> Depositing to V4...';
                    const wallet = new ethers.Contract(this.contractAddress, this.WALLET_ABI, signer);
                    depositTx = await wallet.deposit(amountWei);
                    console.log('[AgentWallet] USDC deposited to V4 contract:', this.contractAddress);
                } else {
                    // For WETH and other tokens - direct transfer to Smart Account
                    let recipient;
                    try {
                        const saResult = await NetworkUtils.getSmartAccount(userAddress);
                        if (saResult.success && saResult.smartAccount) {
                            recipient = saResult.smartAccount;
                        } else {
                            recipient = this.contractAddress;
                        }
                    } catch (e) {
                        recipient = this.contractAddress;
                    }

                    btn.innerHTML = '<span>⏳</span> Transferring...';
                    const TRANSFER_ABI = ['function transfer(address to, uint256 amount) returns (bool)'];
                    const tokenWithTransfer = new ethers.Contract(token.address, TRANSFER_ABI, signer);
                    depositTx = await tokenWithTransfer.transfer(recipient, amountWei);
                    console.log(`[AgentWallet] ${this.selectedToken} transferred to:`, recipient);
                }
            }
            await depositTx.wait();

            btn.innerHTML = '<span>✓</span> Deposited!';
            btn.style.background = '#22c55e';

            Toast?.show(`Successfully deposited ${amount} ${this.selectedToken}!`, 'success');

            // Refresh stats
            await this.refreshStats();

            // Auto-refresh portfolio dashboard if available
            if (window.portfolioDashboard?.loadOnChainData) {
                window.portfolioDashboard.loadOnChainData();
            }

            // Start polling for agent allocation (every 10s for 2 minutes)
            this.startAllocationPolling();

            setTimeout(() => {
                document.getElementById('vaultModal')?.remove();
            }, 2000);

        } catch (e) {
            console.error('[AgentWallet] Deposit error:', e);
            alert('Deposit failed: ' + (e.reason || e.message));
            btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24"><path d="M12 2L4 6v6c0 5.5 3.5 10.7 8 12 4.5-1.3 8-6.5 8-12V6l-8-4z" stroke="currentColor" stroke-width="2"/><path d="M9 12l2 2 4-4" stroke="currentColor" stroke-width="2"/></svg> Approve & Deposit';
            btn.disabled = false;
        }
    },

    /**
     * Execute withdraw transaction - V4.3.2 uses USDC amount!
     */
    async executeWithdraw() {
        // Input is in USDC display units (e.g. "10" means 10 USDC)
        const amountInput = document.getElementById('withdrawShares')?.value;
        if (!amountInput || parseFloat(amountInput) <= 0) {
            alert('Enter USDC amount to withdraw');
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

            // Convert to USDC units (6 decimals)
            const amountUsdc = BigInt(Math.floor(parseFloat(amountInput) * 1e6));
            console.log('[AgentWallet] Withdrawing:', amountInput, 'USDC (', amountUsdc.toString(), 'raw units)');

            const wallet = new ethers.Contract(this.contractAddress, this.WALLET_ABI, signer);
            const tx = await wallet.withdraw(amountUsdc);
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
     * Refresh vault stats from contract - V4.3.2 compatible
     */
    async refreshStats() {
        if (!this.contractAddress || !window.ethereum || typeof ethers === 'undefined') return;

        try {
            const provider = new ethers.BrowserProvider(window.ethereum);
            const wallet = new ethers.Contract(this.contractAddress, this.WALLET_ABI, provider);

            // V4.3.2 uses balances(user) and getUserTotalValue(user)
            if (window.connectedWallet) {
                try {
                    // Get user's available balance
                    const balance = await wallet.balances(window.connectedWallet);
                    // Get user's total value (balance + invested)
                    const totalValue = await wallet.getUserTotalValue(window.connectedWallet);
                    // Get total invested
                    const invested = await wallet.totalInvested(window.connectedWallet);

                    this.userValue = totalValue;
                    this.userBalance = balance;
                    this.userInvested = invested;

                    console.log('[AgentWallet] Stats:', {
                        balance: Number(balance) / 1e6,
                        invested: Number(invested) / 1e6,
                        total: Number(totalValue) / 1e6
                    });

                    // Update Portfolio Dashboard if elements exist
                    const totalValueEl = document.querySelector('[data-stat="total-value"]');
                    if (totalValueEl) {
                        totalValueEl.textContent = '$' + (Number(totalValue) / 1e6).toFixed(2);
                    }

                    // Update USDC row in Asset Holdings
                    const usdcBalanceEl = document.querySelector('[data-asset="usdc-balance"]');
                    if (usdcBalanceEl) {
                        usdcBalanceEl.textContent = (Number(balance) / 1e6).toFixed(2);
                    }

                    const usdcValueEl = document.querySelector('[data-asset="usdc-value"]');
                    if (usdcValueEl) {
                        usdcValueEl.textContent = '$' + (Number(balance) / 1e6).toFixed(2);
                    }

                } catch (contractErr) {
                    console.warn('[AgentWallet] Contract read error:', contractErr.message);
                }
            }

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
    },

    /**
     * Start WebSocket connection for real-time allocation updates
     * Replaces polling with WebSocket for instant notifications
     */
    startAllocationPolling() {
        // Close existing connection
        if (this._allocationWs) {
            this._allocationWs.close();
        }

        console.log('[AgentWallet] Connecting WebSocket for allocation updates...');

        // Connect to backend WebSocket using global WS_BASE
        const wsBase = window.WS_BASE || 'ws://localhost:8000';
        const wsUrl = `${wsBase}/ws/allocation/${window.connectedWallet}`;

        try {
            this._allocationWs = new WebSocket(wsUrl);

            this._allocationWs.onopen = () => {
                console.log('[AgentWallet] ✅ WebSocket connected');
                Toast?.show('⏳ Waiting for agent to allocate funds...', 'info');
            };

            this._allocationWs.onmessage = async (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[AgentWallet] WebSocket message:', data);

                    if (data.type === 'allocation_complete') {
                        console.log('[AgentWallet] ✅ Agent allocated funds!');
                        Toast?.show('🤖 Agent has invested your funds!', 'success');

                        // Refresh UI
                        await this.refreshStats();
                        if (window.portfolioDashboard?.loadOnChainData) {
                            await window.portfolioDashboard.loadOnChainData();
                        }

                        this._allocationWs.close();
                    } else if (data.type === 'allocation_pending') {
                        Toast?.show('⏳ Agent is processing your deposit...', 'info');
                    }
                } catch (e) {
                    console.warn('[AgentWallet] WS parse error:', e);
                }
            };

            this._allocationWs.onerror = (error) => {
                console.warn('[AgentWallet] WebSocket error, falling back to polling:', error);
                this._startPollingFallback();
            };

            this._allocationWs.onclose = () => {
                console.log('[AgentWallet] WebSocket closed');
            };

            // Timeout after 2 minutes
            setTimeout(() => {
                if (this._allocationWs?.readyState === WebSocket.OPEN) {
                    console.log('[AgentWallet] WebSocket timeout');
                    this._allocationWs.close();
                }
            }, 120000);

        } catch (e) {
            console.warn('[AgentWallet] WebSocket failed, using polling:', e);
            this._startPollingFallback();
        }
    },

    /**
     * Fallback polling if WebSocket unavailable
     */
    _startPollingFallback() {
        if (this._allocationPollInterval) {
            clearInterval(this._allocationPollInterval);
        }

        let pollCount = 0;
        const maxPolls = 12;

        console.log('[AgentWallet] Using polling fallback...');

        this._allocationPollInterval = setInterval(async () => {
            pollCount++;

            try {
                await this.refreshStats();

                if (window.portfolioDashboard?.loadOnChainData) {
                    await window.portfolioDashboard.loadOnChainData();
                }

                if (window.connectedWallet && window.ethereum) {
                    const provider = new ethers.BrowserProvider(window.ethereum);
                    const contract = new ethers.Contract(this.contractAddress, this.WALLET_ABI, provider);
                    const invested = await contract.totalInvested(window.connectedWallet);

                    if (invested > 0n) {
                        console.log('[AgentWallet] ✅ Funds invested:', Number(invested) / 1e6, 'USDC');
                        Toast?.show('🤖 Agent has invested your funds!', 'success');
                        clearInterval(this._allocationPollInterval);
                        return;
                    }
                }
            } catch (e) {
                console.warn('[AgentWallet] Poll error:', e.message);
            }

            if (pollCount >= maxPolls) {
                clearInterval(this._allocationPollInterval);
            }
        }, 10000);
    }
};

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    AgentWalletUI.init();
});

// Export
window.AgentWalletUI = AgentWalletUI;
