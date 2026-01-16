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
        const credits = this.getCredits();

        // Update sidebar credits count
        const countEl = document.getElementById('creditsCount');
        if (countEl) {
            countEl.textContent = credits;
        }

        // Update header credits balance
        const headerAmount = document.getElementById('creditsAmount');
        if (headerAmount) {
            headerAmount.textContent = credits;
        }

        // Update apply button state
        const applyBtn = document.getElementById('applyFiltersBtn');
        if (applyBtn) {
            const textEl = applyBtn.querySelector('.apply-text');
            if (credits < this.FILTER_COST) {
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
        modal.className = 'credits-modal';
        modal.innerHTML = `
            <div class="modal-overlay"></div>
            <div class="modal-content" onclick="event.stopPropagation()">
                <button class="modal-close-btn" id="modalCloseBtn">✕</button>
                
                <div class="modal-header">
                    <svg width="32" height="32" viewBox="0 0 16 16" fill="none" class="modal-icon">
                        <path d="M9 1L3 9H8L7 15L13 7H8L9 1Z" stroke="#d4a853" stroke-width="1.5" fill="rgba(212,168,83,0.15)" stroke-linejoin="round"/>
                    </svg>
                    <h2>Buy Filter Credits</h2>
                </div>

                <div class="modal-body">
                    <div class="credits-package">
                        <div class="package-amount">100</div>
                        <div class="package-label">filter credits</div>
                        <div class="package-info">= 4 filter searches</div>
                    </div>

                    <div class="price-row">
                        <span class="price-label">Price:</span>
                        <span class="price-value">0.10 USDC</span>
                    </div>

                    <button id="confirmBuyCreditsBtn" class="btn-pay-wallet">
                        Pay with Wallet
                    </button>

                    <p class="payment-method" style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                        <img src="/meridian-logo.png" alt="Meridian" style="width: 18px; height: 18px;">
                        Payment via Meridian x402 protocol
                    </p>

                    <div class="premium-cta">
                        <div class="premium-icon">⚡</div>
                        <div class="premium-text">
                            <strong>Go Premium</strong>
                            <p>Get 3000 free credits every day!</p>
                        </div>
                        <a href="#premium" class="premium-link" id="premiumLink">Learn more →</a>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);

        // Close on overlay click (not content)
        const overlay = modal.querySelector('.modal-overlay');
        overlay.addEventListener('click', () => modal.remove());

        // Close button
        document.getElementById('modalCloseBtn').addEventListener('click', (e) => {
            e.stopPropagation();
            modal.remove();
        });

        // Premium link
        document.getElementById('premiumLink').addEventListener('click', () => {
            modal.remove();
        });

        // Pay button
        document.getElementById('confirmBuyCreditsBtn').addEventListener('click', (e) => {
            e.stopPropagation();
            this.processPurchase();
        });
    },

    // Process purchase - Meridian x402 Payment
    async processPurchase() {
        const btn = document.getElementById('confirmBuyCreditsBtn');
        if (!btn) return;

        // Check wallet provider exists
        if (!window.ethereum) {
            alert('No Web3 wallet detected. Please install MetaMask.');
            return;
        }

        // Check wallet is connected
        if (!window.connectedWallet) {
            alert('Please connect your wallet first');
            if (typeof connectWallet === 'function') connectWallet();
            return;
        }

        // Check ethers library is loaded
        if (typeof ethers === 'undefined') {
            alert('Payment library not loaded. Please refresh the page.');
            console.error('[Credits] ethers.js not loaded');
            return;
        }

        btn.innerHTML = '<span>⏳</span> Preparing...';
        btn.disabled = true;

        try {
            // Step 1: Get payment requirements from backend
            const reqResponse = await fetch('/api/meridian/payment-requirements');
            if (!reqResponse.ok) throw new Error('Failed to get payment requirements');
            const paymentReq = await reqResponse.json();

            console.log('[Credits] Payment requirements:', paymentReq);

            // Step 2: Build EIP-712 typed data for TransferWithAuthorization
            const USDC_ADDRESS = paymentReq.usdcAddress;
            const recipient = paymentReq.recipientAddress;
            const amount = paymentReq.amount; // "100000" = 0.10 USDC
            const validAfter = 0;
            const validBefore = Math.floor(Date.now() / 1000) + 3600; // 1 hour
            const nonce = '0x' + [...crypto.getRandomValues(new Uint8Array(32))].map(b => b.toString(16).padStart(2, '0')).join('');

            const domain = {
                name: 'USD Coin',
                version: '2',
                chainId: 8453, // Base
                verifyingContract: USDC_ADDRESS
            };

            const types = {
                TransferWithAuthorization: [
                    { name: 'from', type: 'address' },
                    { name: 'to', type: 'address' },
                    { name: 'value', type: 'uint256' },
                    { name: 'validAfter', type: 'uint256' },
                    { name: 'validBefore', type: 'uint256' },
                    { name: 'nonce', type: 'bytes32' }
                ]
            };

            const message = {
                from: window.connectedWallet,
                to: recipient,
                value: amount,
                validAfter: validAfter,
                validBefore: validBefore,
                nonce: nonce
            };

            // Step 3: Request signature from wallet
            btn.innerHTML = '<span>✍️</span> Sign in wallet...';

            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();

            // Sign typed data using EIP-712
            const signature = await signer.signTypedData(domain, types, message);

            console.log('[Credits] Signature obtained:', signature.substring(0, 20) + '...');

            // Step 4: Build payment payload for Meridian
            const paymentPayload = {
                authorization: {
                    from: window.connectedWallet,
                    to: recipient,
                    value: amount,
                    validAfter: validAfter.toString(),
                    validBefore: validBefore.toString(),
                    nonce: nonce
                },
                signature: signature,
                asset: USDC_ADDRESS,
                network: 'base'
            };

            // Step 5: Submit to backend for verification and settlement
            btn.innerHTML = '<span>⏳</span> Processing...';

            const settleResponse = await fetch('/api/meridian/settle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ paymentPayload })
            });

            const settleData = await settleResponse.json();
            console.log('[Credits] Settle response:', settleData);

            if (settleData.success) {
                // Add credits
                this.addCredits(settleData.credits || this.CREDITS_PER_PURCHASE);

                btn.innerHTML = '<span>✓</span> 100 Credits Added!';
                btn.style.background = 'var(--success)';

                if (window.Toast) {
                    Toast.show('✅ 100 Filter Credits added via Meridian!', 'success');
                }

                // Close modal after delay
                setTimeout(() => {
                    document.getElementById('buyCreditsModal')?.remove();
                }, 2000);
            } else {
                throw new Error(settleData.error || 'Payment failed');
            }

        } catch (e) {
            console.error('[Credits] Payment error:', e);

            // User-friendly error messages
            let errorMsg = e.message;
            if (e.code === 4001 || e.message.includes('rejected')) {
                errorMsg = 'Transaction cancelled';
            } else if (e.message.includes('insufficient')) {
                errorMsg = 'Insufficient USDC balance (need 0.10 USDC on Base)';
            }

            alert('Payment failed: ' + errorMsg);
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

        // Header credits balance click
        const balanceEl = document.getElementById('creditsBalance');
        if (balanceEl) {
            console.log('[Credits] creditsBalance element found, adding click listener');
            balanceEl.addEventListener('click', () => {
                console.log('[Credits] Balance clicked, opening modal');
                this.showBuyModal();
            });
        } else {
            console.error('[Credits] creditsBalance element NOT found!');
        }

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
