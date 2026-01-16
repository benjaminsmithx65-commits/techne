/**
 * Subscription UI Module for Techne Finance
 * Handles subscription tiers, upgrades, and billing integration
 */

const SUB_API_BASE = window.API_BASE || 'http://localhost:8000';

// Subscription state
let currentSubscription = null;
let availableTiers = null;

const SubscriptionUI = {
    /**
     * Initialize subscription system
     */
    async init() {
        console.log('[Subscription] Initializing...');
        await this.loadTiers();
        await this.loadCurrentSubscription();
        this.bindEvents();
        this.updateUI();
    },

    /**
     * Load available subscription tiers
     */
    async loadTiers() {
        try {
            const response = await fetch(`${SUB_API_BASE}/api/revenue/tiers`);
            const data = await response.json();
            if (data.success) {
                availableTiers = data.tiers;
                console.log('[Subscription] Loaded tiers:', availableTiers.length);
            }
        } catch (error) {
            console.error('[Subscription] Failed to load tiers:', error);
            // Use fallback tiers
            availableTiers = [
                { tier: 'free', price_monthly: 0, features: { pools_visible: 20, ai_queries_per_day: 5 } },
                { tier: 'pro', price_monthly: 10, features: { pools_visible: 'Unlimited', ai_queries_per_day: 100 } },
                { tier: 'teams', price_monthly: 50, features: { pools_visible: 'Unlimited', ai_queries_per_day: 500 } },
                { tier: 'enterprise', price_monthly: 200, features: { pools_visible: 'Unlimited', ai_queries_per_day: 'Unlimited' } }
            ];
        }
    },

    /**
     * Load current user subscription
     */
    async loadCurrentSubscription() {
        const userId = this.getUserId();
        try {
            const response = await fetch(`${SUB_API_BASE}/api/revenue/subscriptions/${userId}`);
            const data = await response.json();
            if (data.success) {
                currentSubscription = data.subscription;
                console.log('[Subscription] Current:', currentSubscription?.tier || 'free');
            }
        } catch (error) {
            console.log('[Subscription] No subscription found, using free tier');
            currentSubscription = null;
        }
    },

    /**
     * Get user ID from wallet or localStorage
     */
    getUserId() {
        // Try to get from wallet
        if (window.walletState?.address) {
            return window.walletState.address;
        }
        // Fallback to localStorage
        let userId = localStorage.getItem('techne_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('techne_user_id', userId);
        }
        return userId;
    },

    /**
     * Bind UI events
     */
    bindEvents() {
        // Upgrade buttons
        document.querySelectorAll('[data-upgrade-tier]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tier = e.target.dataset.upgradeTier;
                this.showUpgradeModal(tier);
            });
        });

        // Subscribe buttons in pricing cards
        document.querySelectorAll('.pricing-card .btn-primary, .pricing-card .btn-subscribe').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const card = e.target.closest('.pricing-card');
                const tier = card?.dataset?.tier || this.detectTierFromCard(card);
                if (tier) {
                    this.showUpgradeModal(tier);
                }
            });
        });
    },

    /**
     * Detect tier from pricing card content
     */
    detectTierFromCard(card) {
        if (!card) return null;
        const title = card.querySelector('h3, .tier-name')?.textContent?.toLowerCase() || '';
        if (title.includes('enterprise')) return 'enterprise';
        if (title.includes('team')) return 'teams';
        if (title.includes('pro')) return 'pro';
        return 'free';
    },

    /**
     * Update UI based on current subscription
     */
    updateUI() {
        const tier = currentSubscription?.tier || 'free';
        const tierConfig = availableTiers?.find(t => t.tier === tier) || availableTiers?.[0];

        // Update plan name display
        const planDisplay = document.getElementById('current-plan-name');
        if (planDisplay) {
            const tierLabels = {
                'free': 'Free Tier',
                'pro': 'Pro',
                'teams': 'Teams',
                'enterprise': 'Enterprise'
            };
            planDisplay.textContent = tierLabels[tier] || 'Free Tier';
        }

        // Update search limits
        const searchLimit = document.getElementById('search-limit');
        if (searchLimit && tierConfig) {
            const limit = tierConfig.features?.ai_queries_per_day;
            searchLimit.textContent = limit === 'Unlimited' ? '∞' : limit;
        }

        // Update feature badges
        document.querySelectorAll('[data-requires-tier]').forEach(el => {
            const requiredTier = el.dataset.requiresTier;
            const hasAccess = this.hasTierAccess(tier, requiredTier);
            el.classList.toggle('locked', !hasAccess);
            el.classList.toggle('unlocked', hasAccess);
        });

        // Update pricing cards to show "Current" on active tier
        document.querySelectorAll('.pricing-card').forEach(card => {
            const cardTier = card.dataset?.tier || this.detectTierFromCard(card);
            const btn = card.querySelector('.btn-primary, .btn-subscribe');
            if (btn && cardTier === tier) {
                btn.textContent = 'Current Plan';
                btn.disabled = true;
                btn.classList.add('current-plan');
            }
        });
    },

    /**
     * Check if user has access to a tier feature
     */
    hasTierAccess(currentTier, requiredTier) {
        const tierOrder = ['free', 'pro', 'teams', 'enterprise'];
        const currentIndex = tierOrder.indexOf(currentTier || 'free');
        const requiredIndex = tierOrder.indexOf(requiredTier || 'free');
        return currentIndex >= requiredIndex;
    },

    /**
     * Show upgrade modal
     */
    showUpgradeModal(tier) {
        const tierConfig = availableTiers?.find(t => t.tier === tier);
        if (!tierConfig) {
            console.error('[Subscription] Tier not found:', tier);
            return;
        }

        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'upgrade-modal';
        modal.innerHTML = `
            <div class="modal subscription-modal">
                <button class="modal-close" onclick="SubscriptionUI.closeModal()">&times;</button>
                
                <div class="modal-header">
                    <h2>Upgrade to ${tier.charAt(0).toUpperCase() + tier.slice(1)}</h2>
                    <p style="color: #9ca3af;">Unlock premium features and unlimited access</p>
                </div>
                
                <div class="upgrade-details">
                    <div class="price-display">
                        <span class="price-currency">$</span>
                        <span class="price-amount">${tierConfig.price_monthly}</span>
                        <span class="price-period">/month</span>
                    </div>
                    
                    <ul class="feature-list">
                        <li>✅ ${tierConfig.features?.pools_visible === 'Unlimited' ? 'Unlimited' : tierConfig.features?.pools_visible} pool views</li>
                        <li>✅ ${tierConfig.features?.ai_queries_per_day === 'Unlimited' ? 'Unlimited' : tierConfig.features?.ai_queries_per_day} AI queries/day</li>
                        ${tierConfig.features?.ai_predictions ? '<li>✅ AI Yield Predictions</li>' : ''}
                        ${tierConfig.features?.custom_strategies ? '<li>✅ Custom Strategies</li>' : ''}
                        ${tierConfig.features?.priority_support ? '<li>✅ Priority Support</li>' : ''}
                        ${tierConfig.features?.white_label ? '<li>✅ White-label Access</li>' : ''}
                    </ul>
                </div>
                
                <div class="billing-options">
                    <label class="billing-option active" data-cycle="monthly">
                        <input type="radio" name="billing" value="monthly" checked>
                        <span class="option-label">Monthly</span>
                        <span class="option-price">$${tierConfig.price_monthly}/mo</span>
                    </label>
                    <label class="billing-option" data-cycle="yearly">
                        <input type="radio" name="billing" value="yearly">
                        <span class="option-label">Yearly</span>
                        <span class="option-price">$${tierConfig.price_yearly || tierConfig.price_monthly * 10}/yr</span>
                        <span class="save-badge">Save 17%</span>
                    </label>
                </div>
                
                <div class="payment-methods">
                    <button class="btn-payment" onclick="SubscriptionUI.processUpgrade('${tier}', 'x402')">
                        <span class="payment-icon">💳</span>
                        Pay with USDC (x402)
                    </button>
                    <button class="btn-payment secondary" onclick="SubscriptionUI.processUpgrade('${tier}', 'crypto')">
                        <span class="payment-icon">🔗</span>
                        Pay with Crypto
                    </button>
                </div>
                
                <p class="terms-note" style="font-size: 12px; color: #6b7280; text-align: center; margin-top: 16px;">
                    Cancel anytime. 7-day money-back guarantee.
                </p>
            </div>
        `;

        document.body.appendChild(modal);

        // Bind billing toggle
        modal.querySelectorAll('.billing-option').forEach(opt => {
            opt.addEventListener('click', () => {
                modal.querySelectorAll('.billing-option').forEach(o => o.classList.remove('active'));
                opt.classList.add('active');
            });
        });

        // Add styles if not present
        this.injectModalStyles();
    },

    /**
     * Close upgrade modal
     */
    closeModal() {
        const modal = document.getElementById('upgrade-modal');
        if (modal) {
            modal.remove();
        }
    },

    /**
     * Process subscription upgrade
     */
    async processUpgrade(tier, paymentMethod) {
        if (!window.ethereum) {
            this.showNotification('Please install MetaMask to pay with crypto', 'error');
            return;
        }

        const billingCycle = document.querySelector('.billing-option.active input')?.value || 'monthly';
        const tierConfig = availableTiers?.find(t => t.tier === tier);

        if (!tierConfig) {
            this.showNotification('Invalid tier configuration', 'error');
            return;
        }

        const price = billingCycle === 'yearly'
            ? (tierConfig.price_yearly || tierConfig.price_monthly * 10)
            : tierConfig.price_monthly;

        // USDC on Base
        const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
        const RECIPIENT = '0x542c3b6cb5c93c4e4b4c20de48ee87dd79efdfec'; // Treasury
        const amountWei = BigInt(Math.floor(price * 1000000)); // 6 decimals

        const btn = event.target.closest('button');
        if (btn) {
            btn.innerHTML = '<span class="spinner"></span> Processing x402...';
            btn.disabled = true;
        }

        try {
            // 1. Connect & Check Balance
            const provider = new ethers.BrowserProvider(window.ethereum);
            const signer = await provider.getSigner();
            const userAddress = await signer.getAddress();

            const usdcContract = new ethers.Contract(USDC_ADDRESS, [
                'function transfer(address to, uint256 amount) returns (bool)',
                'function balanceOf(address account) view returns (uint256)'
            ], signer);

            const balance = await usdcContract.balanceOf(userAddress);
            if (balance < amountWei) {
                throw new Error(`Insufficient USDC balance. Required: $${price}`);
            }

            // 2. Execute Transfer
            this.showNotification(`Please confirm payment of $${price} USDC...`, 'info');
            const tx = await usdcContract.transfer(RECIPIENT, amountWei);

            this.showNotification('Payment submitted! Waiting for confirmation...', 'info');
            const receipt = await tx.wait();

            // 3. Create Subscription on Backend
            this.showNotification('Payment confirmed! Activating plan...', 'success');

            const response = await fetch(`${SUB_API_BASE}/api/revenue/subscriptions/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: this.getUserId(),
                    tier: tier,
                    billing_cycle: billingCycle,
                    tx_hash: receipt.hash, // Link payment
                    payment_method: 'x402'
                })
            });

            const data = await response.json();

            if (data.success) {
                currentSubscription = data.subscription;
                this.showNotification(`🎉 Upgraded to ${tier}!`, 'success');
                this.closeModal();
                this.updateUI();
                if (typeof loadPools === 'function') loadPools();
            } else {
                throw new Error(data.error || 'Activation failed');
            }

        } catch (error) {
            console.error('[Subscription] Payment failed:', error);
            this.showNotification(error.message || 'Payment failed', 'error');
            if (btn) {
                btn.innerHTML = '<span class="payment-icon">💳</span> Pay with USDC (x402)';
                btn.disabled = false;
            }
        }
    },

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Use existing notification system if available
        if (window.showNotification) {
            window.showNotification(message, type);
            return;
        }

        // Fallback notification
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">×</button>
        `;
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 16px 24px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    },

    /**
     * Inject modal styles
     */
    injectModalStyles() {
        if (document.getElementById('subscription-modal-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'subscription-modal-styles';
        styles.textContent = `
            .modal-overlay {
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 9999;
                animation: fadeIn 0.2s ease;
            }
            
            .subscription-modal {
                background: linear-gradient(135deg, #1a1d29 0%, #22262f 100%);
                border: 1px solid #2d3343;
                border-radius: 16px;
                padding: 32px;
                max-width: 480px;
                width: 90%;
                position: relative;
            }
            
            .modal-close {
                position: absolute;
                top: 16px;
                right: 16px;
                background: none;
                border: none;
                color: #9ca3af;
                font-size: 24px;
                cursor: pointer;
            }
            
            .modal-header h2 {
                margin: 0;
                font-size: 24px;
                color: #fff;
            }
            
            .price-display {
                text-align: center;
                padding: 24px;
                background: rgba(99, 102, 241, 0.1);
                border-radius: 12px;
                margin: 24px 0;
            }
            
            .price-currency {
                font-size: 24px;
                color: #9ca3af;
                vertical-align: top;
            }
            
            .price-amount {
                font-size: 64px;
                font-weight: 700;
                color: #fff;
            }
            
            .price-period {
                font-size: 16px;
                color: #9ca3af;
            }
            
            .feature-list {
                list-style: none;
                padding: 0;
                margin: 24px 0;
            }
            
            .feature-list li {
                padding: 8px 0;
                color: #d1d5db;
                border-bottom: 1px solid #2d3343;
            }
            
            .billing-options {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                margin: 24px 0;
            }
            
            .billing-option {
                padding: 16px;
                border: 2px solid #2d3343;
                border-radius: 12px;
                cursor: pointer;
                text-align: center;
                transition: all 0.2s;
            }
            
            .billing-option.active {
                border-color: #6366f1;
                background: rgba(99, 102, 241, 0.1);
            }
            
            .billing-option input {
                display: none;
            }
            
            .option-label {
                display: block;
                font-weight: 600;
                color: #fff;
            }
            
            .option-price {
                display: block;
                color: #9ca3af;
                margin-top: 4px;
            }
            
            .save-badge {
                display: inline-block;
                background: #10b981;
                color: #fff;
                font-size: 10px;
                padding: 2px 6px;
                border-radius: 4px;
                margin-top: 8px;
            }
            
            .payment-methods {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            
            .btn-payment {
                padding: 16px;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                transition: all 0.2s;
            }
            
            .btn-payment:not(.secondary) {
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                border: none;
                color: #fff;
            }
            
            .btn-payment.secondary {
                background: transparent;
                border: 2px solid #2d3343;
                color: #fff;
            }
            
            .btn-payment:hover {
                transform: translateY(-2px);
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(styles);
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Small delay to ensure other scripts are loaded
    setTimeout(() => {
        SubscriptionUI.init();
    }, 500);
});

// Export for global access
window.SubscriptionUI = SubscriptionUI;
