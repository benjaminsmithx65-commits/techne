/**
 * Techne Protocol - Filter Credits System
 * Manages credits for advanced filtering
 * 
 * Model:
 * - 25 credits = 1 filter search (via Apply Filters button)
 * - 100 credits = 0.1 USDC
 * - Premium = 3000 credits/day
 */

const CreditsManager = {
    STORAGE_KEY: 'techne_credits',
    CREDITS_PER_PURCHASE: 100,
    FILTER_COST: 25,
    PRICE_USDC: 0.1,
    PREMIUM_DAILY_CREDITS: 3000,

    // Get current credits
    getCredits() {
        const stored = localStorage.getItem(this.STORAGE_KEY);
        if (stored) {
            const data = JSON.parse(stored);
            return data.credits || 0;
        }
        return 0;
    },

    // Set credits
    setCredits(amount) {
        const data = {
            credits: Math.max(0, amount),
            lastUpdated: Date.now()
        };
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
        this.updateDisplay();
        return data.credits;
    },

    // Add credits
    addCredits(amount) {
        const current = this.getCredits();
        return this.setCredits(current + amount);
    },

    // Use credits for filter search (25 credits per filter)
    useCredit() {
        const current = this.getCredits();
        if (current < this.FILTER_COST) {
            return false;
        }
        this.setCredits(current - this.FILTER_COST);
        return true;
    },

    // Check if can filter (need at least FILTER_COST credits)
    canFilter() {
        return this.getCredits() >= this.FILTER_COST;
    },

    // Update credits display in UI
    updateDisplay() {
        const countEl = document.getElementById('creditsCount');
        if (countEl) {
            countEl.textContent = this.getCredits();
        }

        // Update apply button state
        const applyBtn = document.getElementById('applyFiltersBtn');
        if (applyBtn) {
            const textEl = applyBtn.querySelector('.apply-text');
            if (this.getCredits() < this.FILTER_COST) {
                applyBtn.disabled = true;
                if (textEl) textEl.textContent = 'Need 25 Credits';
            } else {
                applyBtn.disabled = false;
                if (textEl) textEl.textContent = `Apply (${this.FILTER_COST} credits)`;
            }
        }
    },

    // Show buy credits modal
    showBuyModal() {
        document.getElementById('buyCreditsModal')?.remove();

        const modal = document.createElement('div');
        modal.id = 'buyCreditsModal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-container" style="max-width: 400px;">
                <button class="modal-close" onclick="document.getElementById('buyCreditsModal').remove()">✕</button>
                <h2 style="margin-bottom: 16px;">⚡ Buy Filter Credits</h2>
                
                <div style="background: var(--bg-elevated); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px;">
                    <div style="font-size: 3rem; margin-bottom: 8px;">100</div>
                    <div style="color: var(--text-muted);">filter credits</div>
                    <div style="color: var(--gold); font-size: 0.85rem; margin-top: 8px;">= 4 filter searches</div>
                </div>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 20px; color: var(--text-secondary);">
                    <span>Price:</span>
                    <span style="color: var(--gold); font-weight: 700;">0.10 USDC</span>
                </div>
                
                <button id="confirmBuyCreditsBtn" class="btn-apply-filters" style="width: 100%;">
                    <span>Pay with Wallet</span>
                </button>
                
                <p style="text-align: center; margin-top: 16px; font-size: 0.8rem; color: var(--text-muted);">
                    Payment via x402 protocol
                </p>
                
                <hr style="border: none; border-top: 1px solid var(--border); margin: 20px 0;">
                
                <div style="text-align: center;">
                    <p style="color: var(--gold); font-weight: 600; margin-bottom: 8px;">👑 Go Premium</p>
                    <p style="color: var(--text-muted); font-size: 0.85rem;">Get 3000 free credits every day!</p>
                    <a href="#premium" onclick="document.getElementById('buyCreditsModal').remove()" 
                       style="color: var(--gold); font-size: 0.8rem;">Learn more →</a>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        document.getElementById('confirmBuyCreditsBtn').addEventListener('click', () => {
            this.processPurchase();
        });
    },

    // Process purchase - Real x402 USDC payment
    async processPurchase() {
        const btn = document.getElementById('confirmBuyCreditsBtn');
        if (!btn) return;

        // Check wallet connection
        if (!window.connectedWallet) {
            alert('Please connect your wallet first');
            if (typeof connectWallet === 'function') connectWallet();
            return;
        }

        btn.innerHTML = '<span>⏳</span> Connecting...';
        btn.disabled = true;

        try {
            // Get provider and signer
            if (!window.ethereum) {
                throw new Error('No wallet detected. Please install MetaMask.');
            }

            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();

            // Payment details - 0.1 USDC for 100 credits
            const RECIPIENT = '0x542c3b6cb5c93c4e4b4c20de48ee87dd79efdfec'; // Techne treasury
            const AMOUNT = '100000'; // 0.10 USDC (6 decimals)

            // USDC contract on Base
            const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
            const USDC_ABI = [
                'function transfer(address to, uint256 amount) returns (bool)',
                'function balanceOf(address account) view returns (uint256)'
            ];

            const usdcContract = new ethers.Contract(USDC_ADDRESS, USDC_ABI, signer);

            // Check balance
            btn.innerHTML = '<span>⏳</span> Checking balance...';
            const balance = await usdcContract.balanceOf(window.connectedWallet);

            if (BigInt(balance) < BigInt(AMOUNT)) {
                alert('Insufficient USDC balance. You need at least 0.1 USDC on Base.');
                btn.innerHTML = '<span>💳</span> Pay with Wallet';
                btn.disabled = false;
                return;
            }

            // Execute transfer
            btn.innerHTML = '<span>⏳</span> Confirm in wallet...';
            const tx = await usdcContract.transfer(RECIPIENT, AMOUNT);

            btn.innerHTML = '<span>⏳</span> Confirming...';

            // Wait for confirmation
            const receipt = await tx.wait();

            console.log('[Credits] Payment successful, txHash:', receipt.hash);

            // Add credits
            this.addCredits(this.CREDITS_PER_PURCHASE);

            btn.innerHTML = '<span>✓</span> 100 Credits Added!';
            btn.style.background = 'var(--success)';

            // Show toast if available
            if (window.Toast) {
                Toast.show('✅ 100 Filter Credits added!', 'success');
            }

            // Close modal after delay
            setTimeout(() => {
                document.getElementById('buyCreditsModal')?.remove();
            }, 2000);

        } catch (e) {
            console.error('[Credits] Payment error:', e);
            alert('Payment failed: ' + (e.reason || e.message));

            btn.innerHTML = '<span>💳</span> Pay with Wallet';
            btn.disabled = false;
        }
    },

    // Handle Apply Filters click
    handleApplyFilters() {
        if (!this.canFilter()) {
            this.showBuyModal();
            return;
        }

        this.useCredit();
        console.log('[Credits] Used 25 credits, remaining:', this.getCredits());

        // Set flag and call original loadPools
        window._creditsApprovedLoad = true;
        if (window._originalLoadPools) {
            window._originalLoadPools();
        }
    },

    // Initialize system
    init() {
        this.updateDisplay();

        document.getElementById('buyCreditsBtn')?.addEventListener('click', () => {
            this.showBuyModal();
        });

        document.getElementById('applyFiltersBtn')?.addEventListener('click', () => {
            this.handleApplyFilters();
        });

        console.log('[Credits] System initialized, balance:', this.getCredits());
    }
};

// ============================================
// DISABLE AUTO-FILTER EXECUTION
// ============================================

function disableAutoFilterExecution() {
    if (typeof loadPools === 'undefined') {
        setTimeout(disableAutoFilterExecution, 500);
        return;
    }

    // Store original function
    window._originalLoadPools = window.loadPools;
    window._initialLoadDone = false;

    // Wrap loadPools to block auto-execution
    window.loadPools = function (...args) {
        // Allow initial page load
        if (!window._initialLoadDone) {
            window._initialLoadDone = true;
            return window._originalLoadPools.apply(this, args);
        }

        // Only allow if triggered by Apply Filters button
        if (window._creditsApprovedLoad) {
            window._creditsApprovedLoad = false;
            return window._originalLoadPools.apply(this, args);
        }

        // Block auto-execution from filter changes
        console.log('[Credits] Filter change - click Apply Filters to search');
        return;
    };

    console.log('[Credits] Auto-filter execution disabled');
}

// ============================================
// INIT
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    CreditsManager.init();
    setTimeout(disableAutoFilterExecution, 1000);
});

// Give 50 free credits on first visit
(function () {
    const hasVisited = localStorage.getItem('techne_first_visit');
    if (!hasVisited) {
        localStorage.setItem('techne_first_visit', 'true');
        CreditsManager.setCredits(50);
        console.log('[Credits] Welcome bonus: 50 free credits!');
    }
})();
