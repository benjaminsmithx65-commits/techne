/**
 * Techne Protocol - x402 Unlock Pools Payment
 * $0.10 USDC = 15 AI-verified stablecoin pools
 */

const UnlockModal = {
    isOpen: false,
    sessionData: null,

    // Open unlock modal
    async open() {
        this.isOpen = true;

        // First create session to get preview
        await this.createSession();
        this.render();
    },

    close() {
        this.isOpen = false;
        document.getElementById('unlockModal')?.remove();
    },

    async createSession() {
        if (!connectedWallet) {
            // Will prompt to connect
            return;
        }

        try {
            // Get current filter settings from app.js
            const currentFilters = window.filters || {};

            // Build URL with filter parameters
            const params = new URLSearchParams({
                wallet: connectedWallet,
                chain: currentFilters.chain || 'all',
                risk: currentFilters.risk || 'all',
                asset_type: currentFilters.assetType || 'stablecoin',
                stablecoin_type: currentFilters.stablecoinType || 'all',
                min_tvl: currentFilters.minTvl || 50000,
                min_apy: currentFilters.minApy || 1
            });

            const response = await fetch(`${API_BASE}/api/unlock-pools?${params}`, {
                method: 'POST'
            });
            this.sessionData = await response.json();
        } catch (e) {
            console.error('Session creation error:', e);
        }
    },

    render() {
        const existing = document.getElementById('unlockModal');
        if (existing) existing.remove();

        // V2 Modal - Greek Gaming Aesthetic
        const modal = document.createElement('div');
        modal.id = 'unlockModal';
        modal.className = 'modal-overlay';

        // Using predefined CSS classes where possible, inline for specific overrides
        modal.innerHTML = `
            <div class="unlock-modal-v2" style="
                background: linear-gradient(145deg, var(--bg-void) 0%, var(--bg-deep) 100%);
                border: 1px solid var(--gold);
                border-radius: var(--radius-xl);
                padding: 0;
                width: 90%;
                max-width: 420px;
                position: relative;
                box-shadow: 0 0 40px rgba(212, 168, 83, 0.1);
                overflow: hidden;
            ">
                <!-- Close Button -->
                <button onclick="UnlockModal.close()" style="
                    position: absolute;
                    top: 16px;
                    right: 16px;
                    background: transparent;
                    border: none;
                    color: var(--text-muted);
                    cursor: pointer;
                    font-size: 20px;
                    transition: var(--transition-base);
                    z-index: 10;
                " onmouseover="this.style.color=var(--gold)">✕</button>

                <!-- Header -->
                <div style="
                    padding: var(--space-6);
                    text-align: center;
                    border-bottom: 1px solid var(--border);
                    background: radial-gradient(circle at top, var(--gold-subtle) 0%, transparent 70%);
                ">
                    <div style="font-size: 48px; margin-bottom: var(--space-4); filter: drop-shadow(0 0 15px var(--gold));">🔓</div>
                    <h2 style="
                        font-family: var(--font-display);
                        font-size: 1.5rem;
                        color: var(--gold);
                        margin: 0 0 var(--space-2);
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
                    ">Unlock 15 Pools</h2>
                    <p style="color: var(--text-secondary); font-size: 0.9rem; margin: 0;">Instant access to high-yield stablecoin strategies</p>
                </div>

                <!-- Price Section -->
                <div style="padding: var(--space-6); text-align: center;">
                     <div style="
                        display: inline-flex;
                        align-items: center;
                        gap: var(--space-3);
                        background: var(--bg-elevated);
                        border: 1px solid var(--border-gold);
                        padding: var(--space-3) var(--space-5);
                        border-radius: 100px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                     ">
                        <img src="/icons/usdc.png" width="32" height="32" alt="USDC" style="border-radius: 50%;">
                        <div style="text-align: left;">
                            <div style="font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; color: #fff; line-height: 1;">0.10</div>
                            <div style="font-size: 0.75rem; color: var(--gold); font-weight: 600; letter-spacing: 0.5px;">USDC (Base)</div>
                        </div>
                     </div>
                </div>

                <!-- Features List -->
                <div style="padding: 0 var(--space-6) var(--space-6);">
                    <div style="
                        background: rgba(255,255,255,0.02);
                        border: 1px solid var(--border);
                        border-radius: var(--radius-lg);
                        padding: var(--space-4);
                    ">
                        <ul style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-3);">
                            <li style="display: flex; gap: var(--space-3); align-items: center; color: var(--text); font-size: 0.9rem;">
                                <span style="color: var(--gold);">✓</span> Agent-verified Safety Scores
                            </li>
                            <li style="display: flex; gap: var(--space-3); align-items: center; color: var(--text); font-size: 0.9rem;">
                                <span style="color: var(--gold);">✓</span> Deposit & Withdraw checks
                            </li>
                            <li style="display: flex; gap: var(--space-3); align-items: center; color: var(--text); font-size: 0.9rem;">
                                <span style="color: var(--gold);">✓</span> Airdrop Potential Analysis
                            </li>
                        </ul>
                    </div>
                </div>

                <!-- Footer / Action -->
                <div style="
                    padding: var(--space-6); 
                    border-top: 1px solid var(--border);
                    background: var(--bg-elevated);
                ">
                    <button class="btn-unlock" onclick="UnlockModal.pay()" style="
                        width: 100%;
                        background: var(--gradient-gold);
                        color: #000;
                        font-family: var(--font-display);
                        font-weight: 700;
                        font-size: 1rem;
                        padding: var(--space-4);
                        border: none;
                        border-radius: var(--radius-md);
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: var(--space-2);
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        transition: var(--transition-base);
                        box-shadow: var(--shadow-gold);
                    " onmouseover="this.style.transform='translateY(-2px)'"
                      onmouseout="this.style.transform='translateY(0)'">
                        <span>⚡</span> PAY & UNLOCK (x402)
                    </button>
                    <div style="
                        text-align: center; 
                        margin-top: var(--space-3); 
                        font-size: 0.75rem; 
                        color: var(--text-muted);
                        font-weight: 500;
                    ">
                        Secured by x402 Protocol | Meridian.finance
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) this.close();
        });
    },

    async pay() {
        if (!connectedWallet) {
            alert('Please connect your wallet first');
            if (typeof connectWallet === 'function') connectWallet();
            return;
        }

        const payBtn = document.querySelector('.btn-unlock');
        if (payBtn) {
            payBtn.innerHTML = '<span>⏳</span> Processing...';
            payBtn.disabled = true;
        }

        try {
            // Get provider and signer
            if (!window.ethereum) {
                throw new Error('No wallet detected. Please install MetaMask.');
            }

            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();

            // Execute USDC transfer
            const payment = this.sessionData?.payment || {
                recipient: '0x542c3b6cb5c93c4e4b4c20de48ee87dd79efdfec',
                amount: '100000' // 0.10 USDC
            };

            // USDC contract on Base
            const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
            const USDC_ABI = [
                'function transfer(address to, uint256 amount) returns (bool)',
                'function balanceOf(address account) view returns (uint256)'
            ];

            const usdcContract = new ethers.Contract(USDC_ADDRESS, USDC_ABI, signer);

            // Check balance
            const balance = await usdcContract.balanceOf(connectedWallet);
            if (BigInt(balance) < BigInt(payment.amount)) {
                alert('Insufficient USDC balance. You need at least $0.10 USDC.');
                if (payBtn) {
                    payBtn.innerHTML = '<span>⚡</span> Pay & Unlock';
                    payBtn.disabled = false;
                }
                return;
            }

            // Execute transfer
            const tx = await usdcContract.transfer(payment.recipient, payment.amount);

            if (payBtn) {
                payBtn.innerHTML = '<span>⏳</span> Confirming...';
            }

            // Wait for confirmation
            const receipt = await tx.wait();

            // Verify on backend and get verified pools
            await this.verifyAndShow(receipt.hash);

        } catch (e) {
            console.error('Payment error:', e);
            alert('Payment failed: ' + (e.reason || e.message));

            const payBtnRetry = document.querySelector('.btn-unlock');
            if (payBtnRetry) {
                payBtnRetry.innerHTML = '<span>⚡</span> Pay & Unlock';
                payBtnRetry.disabled = false;
            }
        }
    },

    async verifyAndShow(txHash) {
        this.lastTxHash = txHash;

        try {
            // Check if we have session data
            if (!this.sessionData?.session_id) {
                // If no session, show pools from initial response
                const pools = this.sessionData?.preview || [];
                this.showVerifiedPools(pools, txHash);
                return;
            }

            const response = await fetch(
                `${API_BASE}/api/verify-unlock?session_id=${this.sessionData.session_id}&tx_hash=${txHash}`,
                { method: 'POST' }
            );

            const result = await response.json();

            if (result.success && result.pools) {
                this.showVerifiedPools(result.pools, txHash);
            } else if (this.sessionData?.preview) {
                // Fallback to preview pools
                this.showVerifiedPools(this.sessionData.preview, txHash);
            } else {
                throw new Error(result.error || 'No pools returned');
            }
        } catch (e) {
            console.error('Verification error:', e);
            // Still show success with preview pools if available
            if (this.sessionData?.preview) {
                this.showVerifiedPools(this.sessionData.preview, txHash);
            } else {
                alert('Payment confirmed! Pools will be available shortly.');
                this.close();
            }
        }
    },

    showVerifiedPools(pools, txHash) {
        // Ensure pools is an array
        pools = Array.isArray(pools) ? pools : [];

        // Close the unlock modal
        document.getElementById('unlockModal')?.remove();
        document.querySelector('.unlock-modal')?.remove();

        // Save to localStorage for persistence
        localStorage.setItem('techne_pools_unlocked', 'true');
        localStorage.setItem('techne_verified_pools', JSON.stringify(pools));
        localStorage.setItem('techne_unlock_tx', txHash);

        // Add to history
        const history = JSON.parse(localStorage.getItem('techne_payment_history') || '[]');
        history.push({
            pools,
            txHash,
            timestamp: new Date().toISOString(),
            filters: window.filters || {}
        });
        localStorage.setItem('techne_payment_history', JSON.stringify(history));

        // Unlock pools in-place (in the Explore grid)
        if (typeof window.unlockPoolsInPlace === 'function') {
            window.unlockPoolsInPlace(pools, txHash);

        } else {
            // Fallback: reload pools manually
            window.unlockedPools = true;
            window.verifiedPoolsData = pools;
            if (typeof loadPools === 'function') {
                loadPools();
            }
        }

        Toast?.show('✅ Pools unlocked! View full analysis in the Explore grid.', 'success');
    }
};

// Helper to get pool URL
function getPoolUrl(pool) {
    const project = pool.project?.toLowerCase();
    if (project?.includes('aerodrome')) return 'https://aerodrome.finance/liquidity';
    if (project?.includes('aave')) return 'https://app.aave.com/';
    if (project?.includes('compound')) return 'https://app.compound.finance/';
    if (project?.includes('morpho')) return 'https://app.morpho.org/';
    return '#';
}

// CSS for unlock modal
const unlockStyles = document.createElement('style');
unlockStyles.textContent = `
        .unlock - modal {
    max - width: 480px;
}
    
    .unlock - header {
    text - align: center;
    padding: var(--space - 6);
    background: linear - gradient(135deg, var(--gold - subtle), transparent);
    border - bottom: 1px solid var(--border);
}
    
    .unlock - header.success {
    background: linear - gradient(135deg, var(--success - dim), transparent);
}
    
    .unlock - icon {
    font - size: 3rem;
    margin - bottom: var(--space - 3);
}
    
    .unlock - header h2 {
    font - family: var(--font - display);
    font - size: 1.5rem;
    margin - bottom: var(--space - 2);
}
    
    .unlock - price {
    display: flex;
    align - items: baseline;
    justify - content: center;
    gap: var(--space - 2);
}
    
    .price - amount {
    font - family: var(--font - display);
    font - size: 2.5rem;
    font - weight: 700;
    color: var(--gold);
}
    
    .price - usdc {
    font - size: 1rem;
    color: var(--text - muted);
}
    
    .unlock - features {
    padding: var(--space - 5);
    border - bottom: 1px solid var(--border);
}
    
    .unlock - features h3 {
    font - size: 0.85rem;
    color: var(--text - muted);
    margin - bottom: var(--space - 3);
}
    
    .unlock - features ul {
    list - style: none;
    display: flex;
    flex - direction: column;
    gap: var(--space - 2);
}
    
    .unlock - features li {
    font - size: 0.9rem;
    color: var(--text);
}
    
    .unlock - preview {
    padding: var(--space - 5);
    border - bottom: 1px solid var(--border);
}
    
    .unlock - preview h3 {
    font - size: 0.85rem;
    color: var(--text - muted);
    margin - bottom: var(--space - 3);
}
    
    .preview - list {
    display: flex;
    flex - direction: column;
    gap: var(--space - 2);
}
    
    .preview - pool {
    display: grid;
    grid - template - columns: 1fr auto auto auto;
    gap: var(--space - 3);
    align - items: center;
    padding: var(--space - 2);
    background: var(--bg - elevated);
    border - radius: var(--radius - md);
    font - size: 0.85rem;
}
    
    .pool - status.verified { color: var(--success); }
    .pool - status.pending { color: var(--text - muted); }
    
    .preview - more {
    text - align: center;
    color: var(--text - muted);
    font - size: 0.8rem;
    padding: var(--space - 2);
}
    
    .unlock - payment {
    padding: var(--space - 5);
}
    
    .token - display {
    display: flex;
    align - items: center;
    gap: var(--space - 3);
    padding: var(--space - 3);
    background: var(--bg - elevated);
    border - radius: var(--radius - md);
}
    
    .token - display div {
    display: flex;
    flex - direction: column;
}
    
    .token - display span {
    font - size: 0.75rem;
    color: var(--text - muted);
}
    
    .unlock - actions {
    padding: 0 var(--space - 5) var(--space - 5);
}
    
    .btn - unlock {
    width: 100 %;
    display: flex;
    align - items: center;
    justify - content: center;
    gap: var(--space - 2);
    padding: var(--space - 4);
    background: var(--gradient - gold);
    border: none;
    border - radius: var(--radius - md);
    color: var(--bg - void);
    font - size: 1.1rem;
    font - weight: 700;
    cursor: pointer;
    transition: var(--transition - base);
}
    
    .btn - unlock: hover: not(: disabled) {
    box - shadow: var(--shadow - gold);
    transform: translateY(-2px);
}
    
    .btn - unlock:disabled {
    opacity: 0.7;
    cursor: not - allowed;
}
    
    .unlock - security {
    text - align: center;
    padding: var(--space - 4);
    font - size: 0.75rem;
    color: var(--text - muted);
    border - top: 1px solid var(--border);
}

    /* Verified pools display */
    .verified - pools {
    padding: var(--space - 4);
    max - height: 400px;
    overflow - y: auto;
    display: flex;
    flex - direction: column;
    gap: var(--space - 3);
}
    
    .verified - pool {
    background: var(--bg - elevated);
    border: 1px solid var(--border);
    border - radius: var(--radius - md);
    padding: var(--space - 3);
}
    
    .pool - main {
    display: flex;
    align - items: center;
    gap: var(--space - 3);
    margin - bottom: var(--space - 2);
}
    
    .pool - main.pool - info {
    flex: 1;
    display: flex;
    flex - direction: column;
}
    
    .pool - main.pool - name {
    font - weight: 600;
}
    
    .pool - main.pool - symbol {
    font - size: 0.75rem;
    color: var(--text - muted);
}
    
    .pool - main.pool - apy {
    color: var(--gold);
    font - weight: 600;
}
    
    .agent - verification {
    display: flex;
    align - items: center;
    gap: var(--space - 3);
    padding: var(--space - 2);
    background: var(--success - dim);
    border - radius: var(--radius - sm);
    margin - bottom: var(--space - 2);
}
    
    .verification - badge {
    font - size: 0.75rem;
    font - weight: 600;
    color: var(--success);
}
    
    .verification - details {
    display: flex;
    gap: var(--space - 2);
    font - size: 0.7rem;
}
    
    .check.ok { color: var(--success); }
    .check.fail { color: var(--danger); }
    
    .risk - badge {
    padding: 2px 6px;
    border - radius: var(--radius - sm);
    font - size: 0.65rem;
    font - weight: 600;
}
    
    .risk - badge.risk - low { background: var(--success - dim); color: var(--success); }
    .risk - badge.risk - medium { background: var(--warning - dim); color: var(--warning); }
    .risk - badge.risk - high { background: var(--danger - dim); color: var(--danger); }
    
    .verified - pool.pool - actions {
    display: flex;
    justify - content: flex - end;
}
    
    .btn - deposit - small {
    padding: var(--space - 1) var(--space - 3);
    background: var(--gradient - gold);
    border - radius: var(--radius - sm);
    color: var(--bg - void);
    font - size: 0.75rem;
    font - weight: 600;
    text - decoration: none;
}
    
    .unlock - footer {
    padding: var(--space - 4);
    border - top: 1px solid var(--border);
    text - align: center;
}
    
    .btn -continue {
    padding: var(--space - 3) var(--space - 6);
    background: var(--bg - elevated);
    border: 1px solid var(--border);
    border - radius: var(--radius - md);
    color: var(--text);
    font - weight: 600;
    cursor: pointer;
}
`;
document.head.appendChild(unlockStyles);

// Export
window.UnlockModal = UnlockModal;
