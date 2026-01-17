/**
 * Techne Agent Wallet UI
 * V2 - Institutional Grade Security
 */

const AgentWalletUI = {
    // Contract address - V2 DEPLOYED ON BASE MAINNET
    contractAddress: '0x8df33b5b58212f16519ce86e810be2e8232df305',
    contractVersion: 'V2',

    // Supported tokens on Base
    TOKENS: {
        USDC: {
            address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            decimals: 6,
            symbol: 'USDC',
            name: 'USD Coin',
            icon: '💵'
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

    // Vault V2 ABI - Institutional Grade
    WALLET_ABI: [
        // Core functions
        'function deposit(uint256 amount)',
        'function depositToken(address token, uint256 amount)',
        'function withdraw(uint256 shares)',

        // View functions
        'function totalValue() view returns (uint256)',
        'function totalShares() view returns (uint256)',
        'function getUserValue(address user) view returns (uint256)',
        'function getUserShares(address user) view returns (uint256)',

        // V2 Security - Withdraw limits
        'function dailyWithdrawLimit() view returns (uint256)',
        'function maxSingleWithdraw() view returns (uint256)',
        'function getWithdrawLimitStatus() view returns (uint256 remaining, uint256 dailyLimit)',

        // V2 Security - De-peg check
        'function checkUSDCPeg() view returns (bool pegged, int256 price)',
        'function depegProtectionEnabled() view returns (bool)',

        // V2 Security - Circuit breaker
        'function circuitBreakerTriggered() view returns (bool)',

        // V2 Security - Emergency
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
                    <!-- Token Selector -->
                    <div style="margin-bottom: 16px;">
                        <label style="display: block; font-size: 0.75rem; color: rgba(255,255,255,0.6); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Select Token</label>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                            <button id="tokenSelectUSDC" onclick="AgentWalletUI.selectToken('USDC')" style="
                                padding: 12px;
                                background: rgba(212, 168, 83, 0.15);
                                border: 2px solid #d4a853;
                                border-radius: 10px;
                                color: #fff;
                                font-weight: 600;
                                cursor: pointer;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                gap: 8px;
                                transition: all 0.2s;
                            ">
                                💵 USDC
                            </button>
                            <button id="tokenSelectWETH" onclick="AgentWalletUI.selectToken('WETH')" style="
                                padding: 12px;
                                background: rgba(255,255,255,0.03);
                                border: 1px solid rgba(255,255,255,0.1);
                                border-radius: 10px;
                                color: rgba(255,255,255,0.7);
                                font-weight: 600;
                                cursor: pointer;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                gap: 8px;
                                transition: all 0.2s;
                            ">
                                ⟠ WETH
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
    },

    /**
     * Show withdraw modal - Premium styled
     */
    showWithdrawModal() {
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
                        <p style="margin: 4px 0 0; font-size: 0.8rem; color: rgba(255,255,255,0.5);">Withdraw USDC from your Agent Vault</p>
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
                            <div style="font-size: 1.3rem; color: #22c55e; font-weight: 600;" id="withdrawPositionValue">$${(this.userValue / 1e6).toFixed(2)}</div>
                        </div>
                        <div style="
                            background: rgba(255,255,255,0.03);
                            border: 1px solid rgba(255,255,255,0.08);
                            border-radius: 12px;
                            padding: 16px;
                            text-align: center;
                        ">
                            <div style="font-size: 0.7rem; color: rgba(255,255,255,0.5); text-transform: uppercase; margin-bottom: 6px;">Your Shares</div>
                            <div style="font-size: 1.3rem; color: #fff; font-weight: 600;">${this.userShares}</div>
                        </div>
                    </div>

                    <!-- Shares Input -->
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-size: 0.75rem; color: rgba(255,255,255,0.6); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px;">Shares to Withdraw</label>
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
                            Available: ${this.userShares} shares
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
                        Withdraw USDC
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
     * Select deposit token (USDC or WETH)
     */
    selectToken(symbol) {
        this.selectedToken = symbol;
        const token = this.TOKENS[symbol];

        // Update UI
        const usdcBtn = document.getElementById('tokenSelectUSDC');
        const wethBtn = document.getElementById('tokenSelectWETH');

        if (symbol === 'USDC') {
            usdcBtn.style.background = 'rgba(212, 168, 83, 0.15)';
            usdcBtn.style.border = '2px solid #d4a853';
            usdcBtn.style.color = '#fff';
            wethBtn.style.background = 'rgba(255,255,255,0.03)';
            wethBtn.style.border = '1px solid rgba(255,255,255,0.1)';
            wethBtn.style.color = 'rgba(255,255,255,0.7)';
        } else {
            wethBtn.style.background = 'rgba(212, 168, 83, 0.15)';
            wethBtn.style.border = '2px solid #d4a853';
            wethBtn.style.color = '#fff';
            usdcBtn.style.background = 'rgba(255,255,255,0.03)';
            usdcBtn.style.border = '1px solid rgba(255,255,255,0.1)';
            usdcBtn.style.color = 'rgba(255,255,255,0.7)';
        }

        // Update labels
        document.getElementById('selectedTokenLabel').textContent = symbol;
        document.getElementById('tokenSymbol').textContent = symbol;
        document.getElementById('minAmountHint').textContent =
            symbol === 'USDC' ? 'Min: 10 USDC' : 'Min: 0.005 WETH';

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
            const contract = new ethers.Contract(token.address, this.ERC20_ABI, provider);
            const balance = await contract.balanceOf(window.connectedWallet);

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
     * Execute deposit transaction (multi-token support)
     */
    async executeDeposit() {
        const amount = document.getElementById('depositAmount')?.value;
        const token = this.TOKENS[this.selectedToken];

        // Validate minimum amounts
        const minAmount = this.selectedToken === 'USDC' ? 10 : 0.005;
        if (!amount || parseFloat(amount) < minAmount) {
            alert(`Minimum deposit is ${minAmount} ${this.selectedToken}`);
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

            // Calculate amount in token's decimals
            const amountWei = BigInt(Math.floor(parseFloat(amount) * Math.pow(10, token.decimals)));

            // Approve token
            const tokenContract = new ethers.Contract(token.address, this.ERC20_ABI, signer);
            const approveTx = await tokenContract.approve(this.contractAddress, amountWei);
            await approveTx.wait();

            btn.innerHTML = '<span>⏳</span> Depositing...';

            // Deposit - use depositToken for non-USDC, deposit for USDC
            const wallet = new ethers.Contract(this.contractAddress, this.WALLET_ABI, signer);
            let depositTx;

            if (this.selectedToken === 'USDC') {
                depositTx = await wallet.deposit(amountWei);
            } else {
                // For WETH and other tokens, use depositToken
                depositTx = await wallet.depositToken(token.address, amountWei);
            }
            await depositTx.wait();

            btn.innerHTML = '<span>✓</span> Deposited!';
            btn.style.background = '#22c55e';

            Toast?.show(`Successfully deposited ${amount} ${this.selectedToken}!`, 'success');

            // Refresh stats
            await this.refreshStats();

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
