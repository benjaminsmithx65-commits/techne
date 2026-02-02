/**
 * Premium Subscription UI for Techne.finance
 * Handles subscription state, Telegram integration, and search limits
 */

// Constants
const PREMIUM_CONFIG = {
    TREASURY_ADDRESS: '0x742d35Cc6634C0532925a3b844Bc9e7595f8fE00', // Replace with actual treasury
    USDC_ADDRESS_BASE: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', // USDC on Base
    SUBSCRIPTION_PRICE: 99 * 1e6, // 99 USDC (6 decimals) - Artisan Bot
    CREDIT_PACK_PRICE: 0.1 * 1e6, // 0.10 USDC (6 decimals)
    CREDIT_PACK_SEARCHES: 15, // 15 searches per pack
    PREMIUM_DAILY_LIMIT: 200, // 200 searches/day for premium
    TELEGRAM_BOT: 'TechneArtisanBot',
    SUBSCRIPTION_DAYS: 30
};

// State
let premiumState = {
    isPremium: false,
    subscriptionExpires: null,
    searchCredits: 0, // Pay-per-use credits
    searchesToday: 0, // For premium daily counter
    telegramConnected: false,
    telegramChatId: null,
    alertPreferences: {
        minApy: 10,
        minTvl: 100000,
        riskLevel: 'medium',
        protocols: [],
        chains: []
    }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    loadPremiumState();
    initPremiumUI();
    updateSearchCounter();
});

/**
 * Load premium state from localStorage
 */
function loadPremiumState() {
    const saved = localStorage.getItem('techne_premium_state');
    if (saved) {
        try {
            const parsed = JSON.parse(saved);
            premiumState = { ...premiumState, ...parsed };

            // Reset daily search count if new day
            const lastSearchDate = localStorage.getItem('techne_last_search_date');
            const today = new Date().toDateString();
            if (lastSearchDate !== today) {
                premiumState.searchesToday = 0;
                localStorage.setItem('techne_last_search_date', today);
            }

            // Check if subscription expired
            if (premiumState.subscriptionExpires && new Date(premiumState.subscriptionExpires) < new Date()) {
                premiumState.isPremium = false;
                premiumState.subscriptionExpires = null;
            }
        } catch (e) {
            console.error('Failed to parse premium state:', e);
        }
    }
    savePremiumState();
}

/**
 * Save premium state to localStorage
 */
function savePremiumState() {
    localStorage.setItem('techne_premium_state', JSON.stringify(premiumState));
}

/**
 * Initialize Premium UI elements
 */
function initPremiumUI() {
    // Subscribe button
    const subscribeBtn = document.getElementById('subscribe-btn');
    if (subscribeBtn) {
        subscribeBtn.addEventListener('click', handleSubscribe);
    }

    // Buy credits button
    const buyCreditsBtn = document.getElementById('buy-credits-btn');
    if (buyCreditsBtn) {
        buyCreditsBtn.addEventListener('click', handleBuyCredits);
    }

    // Telegram connect button
    const telegramBtn = document.getElementById('connect-telegram-btn');
    if (telegramBtn) {
        telegramBtn.addEventListener('click', handleTelegramConnect);
    }

    // Update UI based on current state
    updatePremiumUI();
}

/**
 * Update all Premium UI elements
 */
function updatePremiumUI() {
    // Update plan name
    const planName = document.getElementById('current-plan-name');
    if (planName) {
        if (premiumState.isPremium) {
            planName.innerHTML = '<span style="color: #d4af37;">🤖 Artisan Bot</span>';
        } else if (premiumState.searchCredits > 0) {
            planName.textContent = 'Pay-per-use';
        } else {
            planName.textContent = 'No Credits';
        }
    }

    // Update credits display
    const creditsEl = document.getElementById('search-credits');
    if (creditsEl) {
        creditsEl.textContent = premiumState.searchCredits;
    }

    // Update search count display
    updateSearchCounter();

    // Update subscribe button
    const subscribeBtn = document.getElementById('subscribe-btn');
    if (subscribeBtn) {
        if (premiumState.isPremium) {
            subscribeBtn.textContent = '✓ Subscribed';
            subscribeBtn.disabled = true;
            subscribeBtn.style.opacity = '0.7';
        } else {
            subscribeBtn.innerHTML = '💳 Subscribe with USDC';
            subscribeBtn.disabled = false;
            subscribeBtn.style.opacity = '1';
        }
    }

    // Update Telegram status
    const tgStatus = document.getElementById('tg-status');
    const tgBtn = document.getElementById('connect-telegram-btn');
    if (tgStatus && tgBtn) {
        if (premiumState.isPremium) {
            if (premiumState.telegramConnected) {
                tgStatus.innerHTML = '<span style="color: #10b981;">✓ Connected to Telegram</span>';
                tgBtn.innerHTML = '<span style="font-size: 18px;">✓</span> Telegram Connected';
                tgBtn.style.background = '#10b981';
            } else {
                tgStatus.textContent = 'Click to connect your Telegram for alerts';
                tgBtn.innerHTML = '<span style="font-size: 18px;">📲</span> Connect @TechneAlertBot';
            }
        } else {
            tgStatus.textContent = 'Premium subscription required for Telegram alerts';
            tgBtn.innerHTML = '<span style="font-size: 18px;">🔒</span> Premium Required';
        }
    }

    // Update subscription status banner
    const banner = document.getElementById('subscription-status-banner');
    if (banner && premiumState.isPremium) {
        banner.style.borderColor = '#d4af37';
        banner.style.background = 'linear-gradient(135deg, #1a1d29 0%, #2d2331 100%)';
    }
}

/**
 * Update search counter display
 */
function updateSearchCounter() {
    const countEl = document.getElementById('search-count');
    const limitEl = document.getElementById('search-limit');
    const displayEl = document.getElementById('search-count-display');

    if (premiumState.isPremium) {
        // Premium: show daily usage
        if (countEl) countEl.textContent = premiumState.searchesToday;
        if (limitEl) limitEl.textContent = PREMIUM_CONFIG.PREMIUM_DAILY_LIMIT;
        if (displayEl) displayEl.style.color = '#d4af37';
    } else {
        // Pay-per-use: show remaining credits
        if (countEl) countEl.textContent = premiumState.searchCredits;
        if (limitEl) limitEl.textContent = 'credits';

        if (displayEl) {
            displayEl.style.color = premiumState.searchCredits > 0 ? '#10b981' : '#ef4444';
        }
    }
}

/**
 * Check if user can perform a search (called from app.js)
 */
function canPerformSearch() {
    if (premiumState.isPremium) {
        return premiumState.searchesToday < PREMIUM_CONFIG.PREMIUM_DAILY_LIMIT;
    }
    return premiumState.searchCredits > 0;
}

/**
 * Increment search counter (called from app.js)
 */
function incrementSearchCount() {
    if (premiumState.isPremium) {
        premiumState.searchesToday++;
        // Show warning near daily limit
        const remaining = PREMIUM_CONFIG.PREMIUM_DAILY_LIMIT - premiumState.searchesToday;
        if (remaining === 20) {
            Toast?.show('⚠️ 20 searches remaining today', 'warning');
        }
    } else {
        // Deduct from credits
        if (premiumState.searchCredits > 0) {
            premiumState.searchCredits--;
            if (premiumState.searchCredits === 2) {
                Toast?.show('⚠️ Only 2 credits left! Buy more or subscribe.', 'warning');
            } else if (premiumState.searchCredits <= 0) {
                showUpgradeModal();
            }
        }
    }
    savePremiumState();
    updateSearchCounter();
    updatePremiumUI();
}

/**
 * Handle buy credits button click ($0.10 for 12 searches)
 */
/**
 * Handle buy credits button click - Redirect to Explore
 */
async function handleBuyCredits() {
    // Navigate to explore section
    const exploreNav = document.querySelector('[data-section="explore"]');
    if (exploreNav) {
        exploreNav.click();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        Toast?.show('View pools in Explore to unlock', 'info');
    } else if (typeof navigateToSection === 'function') {
        navigateToSection('explore');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        Toast?.show('View pools in Explore to unlock', 'info');
    } else {
        console.error('Navigation not found');
        Toast?.show('Please go to Explore page', 'info');
    }
}

/**
 * Handle subscribe button click - x402 Meridian Payment ($99)
 */
async function handleSubscribe() {
    const btn = document.getElementById('subscribe-btn');

    // Must have wallet connected
    if (!window.connectedWallet) {
        Toast?.show('Please connect your wallet first', 'warning');
        if (typeof connectWallet === 'function') connectWallet();
        return;
    }

    // Check ethers library
    if (typeof ethers === 'undefined') {
        Toast?.show('Payment library not loaded. Please refresh.', 'error');
        return;
    }

    if (btn) {
        btn.innerHTML = '<span>⏳</span> Preparing...';
        btn.disabled = true;
    }

    try {
        // Check Base network
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        if (chainId !== '0x2105') {
            Toast?.show('Switching to Base network...', 'info');
            await window.ethereum.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: '0x2105' }]
            });
        }

        // Step 1: Get payment requirements from Meridian x402 (same as credits)
        const reqResponse = await fetch('/api/meridian/premium-requirements');
        if (!reqResponse.ok) throw new Error('Failed to get payment requirements');
        const paymentReq = await reqResponse.json();

        console.log('[Premium] Payment requirements:', paymentReq);

        // Step 2: Build EIP-712 typed data for TransferWithAuthorization
        const USDC_ADDRESS = paymentReq.usdcAddress || PREMIUM_CONFIG.USDC_ADDRESS_BASE;
        const recipient = paymentReq.recipientAddress || PREMIUM_CONFIG.TREASURY_ADDRESS;
        const amount = paymentReq.amount || String(PREMIUM_CONFIG.SUBSCRIPTION_PRICE); // $99 = 99000000
        const now = Math.floor(Date.now() / 1000);
        const validAfter = now - 3600;
        const validBefore = now + 3600;
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

        // Step 3: Request signature
        if (btn) btn.innerHTML = '<span>✍️</span> Sign in wallet...';
        Toast?.show('Please sign the payment in your wallet', 'info');

        const provider = new ethers.BrowserProvider(window.ethereum);
        const signer = await provider.getSigner();
        const signature = await signer.signTypedData(domain, types, message);

        console.log('[Premium] Signature obtained');

        // Step 4: Build x402 payment payload
        const paymentPayload = {
            x402Version: 1,
            scheme: "exact",
            network: "base",
            payload: {
                signature: signature,
                authorization: {
                    from: window.connectedWallet,
                    to: recipient,
                    value: amount,
                    validAfter: validAfter.toString(),
                    validBefore: validBefore.toString(),
                    nonce: nonce
                }
            }
        };

        // Step 5: Settle via Meridian (same as credits)
        if (btn) btn.innerHTML = '<span>⏳</span> Processing payment...';

        const settleResponse = await fetch('/api/meridian/settle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paymentPayload })
        });

        const settleResult = await settleResponse.json();
        console.log('[Premium] Meridian settle result:', settleResult);

        if (!settleResult.success) {
            throw new Error(settleResult.error || 'Payment settlement failed');
        }

        // Step 6: Create subscription in backend
        const subResponse = await fetch('/api/premium/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wallet_address: window.connectedWallet,
                paymentPayload,
                meridian_tx: settleResult.transaction
            })
        });

        const result = await subResponse.json();
        console.log('[Premium] Subscribe result:', result);

        if (result.success) {
            // Update local state
            premiumState.isPremium = true;
            premiumState.subscriptionExpires = result.expires_at;
            premiumState.telegramConnected = false;
            savePremiumState();
            updatePremiumUI();

            if (btn) {
                btn.innerHTML = '<span>✓</span> Subscribed!';
                btn.style.background = 'var(--success, #10b981)';
            }

            // Show activation code
            const activationCode = result.activation_code;
            Toast?.show(`🎉 Artisan Bot activated! Code: ${activationCode}`, 'success');

            // Show TG connect modal
            showActivationModal(activationCode);
        } else {
            throw new Error(result.error || 'Subscription failed');
        }

    } catch (error) {
        console.error('[Premium] Subscription error:', error);

        let errorMsg = error.message;
        if (error.code === 4001 || error.message.includes('rejected')) {
            errorMsg = 'Transaction cancelled';
        } else if (error.message.includes('insufficient')) {
            errorMsg = 'Insufficient USDC balance (need 99 USDC on Base)';
        }

        Toast?.show('Payment failed: ' + errorMsg, 'error');

        if (btn) {
            btn.innerHTML = '💳 Subscribe with USDC';
            btn.disabled = false;
            btn.style.background = '';
        }
    }
}

/**
 * Show activation code modal after successful payment
 */
function showActivationModal(activationCode) {
    const existing = document.querySelector('.activation-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.className = 'activation-modal';
    modal.innerHTML = `
        <div class="modal-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,0.8);display:flex;align-items:center;justify-content:center;z-index:9999;">
            <div class="modal-content" style="background:#1a1d29;border:1px solid #d4af37;border-radius:16px;padding:32px;max-width:420px;text-align:center;">
                <div style="font-size:48px;margin-bottom:16px;">🎉</div>
                <h2 style="color:#d4af37;margin-bottom:8px;">Artisan Bot Activated!</h2>
                <p style="color:#9ca3af;margin-bottom:24px;">Send this code to @TechneArtisanBot on Telegram:</p>
                
                <div style="background:#0f1117;border:2px dashed #d4af37;border-radius:8px;padding:16px;margin-bottom:24px;">
                    <code style="font-size:24px;letter-spacing:4px;color:#ffffff;font-weight:bold;">${activationCode}</code>
                </div>
                
                <button onclick="navigator.clipboard.writeText('${activationCode}');this.textContent='✓ Copied!';" 
                    style="background:#d4af37;color:#000;border:none;padding:12px 24px;border-radius:8px;cursor:pointer;font-weight:600;margin-bottom:16px;">
                    📋 Copy Code
                </button>
                
                <br>
                
                <a href="https://t.me/${PREMIUM_CONFIG.TELEGRAM_BOT}?start=${activationCode}" target="_blank"
                    style="display:inline-block;background:#0088cc;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;">
                    📱 Open Telegram
                </a>
                
                <p style="margin-top:24px;font-size:12px;color:#6b7280;">
                    After activation, choose your autonomy mode and start trading!
                </p>
                
                <button onclick="this.closest('.activation-modal').remove();" 
                    style="margin-top:16px;background:transparent;border:1px solid #4b5563;color:#9ca3af;padding:8px 16px;border-radius:6px;cursor:pointer;">
                    Close
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

/**
 * Handle Telegram connect button click
 */
function handleTelegramConnect() {
    if (!premiumState.isPremium) {
        Toast?.show('Premium subscription required for Telegram alerts', 'warning');
        // Scroll to subscribe button
        document.getElementById('subscribe-btn')?.scrollIntoView({ behavior: 'smooth' });
        return;
    }

    // Open Telegram bot with deep link containing wallet address
    const walletParam = window.connectedWallet ? `?start=${window.connectedWallet}` : '';
    const botUrl = `https://t.me/${PREMIUM_CONFIG.TELEGRAM_BOT}${walletParam}`;
    window.open(botUrl, '_blank');

    // Mark as connected (in real app, verify via backend)
    setTimeout(() => {
        premiumState.telegramConnected = true;
        savePremiumState();
        updatePremiumUI();
        Toast?.show('Telegram bot opened! Complete setup in the app.', 'success');
    }, 2000);
}

/**
 * Show upgrade modal when no credits
 */
function showUpgradeModal() {
    const existing = document.querySelector('.upgrade-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.className = 'upgrade-modal upgrade-modal-greek';
    modal.innerHTML = `
        <div class="upgrade-content-greek">
            <div class="upgrade-icon">🔒</div>
            <h2>No Search Credits</h2>
            <p>You need credits to search pools. Choose an option:</p>
            
            <button onclick="document.querySelector('.upgrade-modal').remove(); handleBuyCredits();" class="btn-greek-option">
                <div class="option-info">
                    <span class="option-title">💳 Buy 15 Searches</span>
                </div>
                <span class="option-price">$0.10</span>
            </button>
            
            <button onclick="document.querySelector('.upgrade-modal').remove(); document.querySelector('[data-section=premium]')?.click();" class="btn-greek-option premium">
                <div class="option-info">
                    <span class="option-title">🤖 Artisan Bot</span>
                    <span class="option-sub">AI Trading Agent + TG</span>
                </div>
                <span class="option-price">$99/mo</span>
            </button>
            
            <button onclick="document.querySelector('.upgrade-modal').remove();" class="btn-greek-cancel">
                Maybe later
            </button>
        </div>
    `;
    document.body.appendChild(modal);
}

// ============================================
// ARTISAN BOT SETTINGS (Portfolio Page)
// ============================================

/**
 * Initialize Artisan Bot settings in portfolio sidebar
 */
function initArtisanSettings() {
    const settingsCard = document.getElementById('artisanSettingsCard');
    if (!settingsCard) return;

    // Show card if user has premium
    if (premiumState.isPremium) {
        settingsCard.style.display = 'block';
    }

    // Max trade slider handler
    const slider = document.getElementById('maxTradeSlider');
    const valueDisplay = document.getElementById('maxTradeValue');
    if (slider && valueDisplay) {
        slider.addEventListener('input', (e) => {
            valueDisplay.textContent = '$' + parseInt(e.target.value).toLocaleString();
        });
    }

    // Save settings button
    const saveBtn = document.getElementById('saveArtisanSettings');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveArtisanSettings);
    }

    // Update TG status
    updateArtisanStatus();
}

/**
 * Save Artisan Bot settings to backend
 */
async function saveArtisanSettings() {
    const btn = document.getElementById('saveArtisanSettings');
    const autonomyMode = document.getElementById('autonomyModeSelect')?.value || 'advisor';
    const maxTrade = document.getElementById('maxTradeSlider')?.value || 1000;

    if (btn) {
        btn.innerHTML = '⏳ Saving...';
        btn.disabled = true;
    }

    try {
        const response = await fetch('/api/premium/update-settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wallet_address: window.connectedWallet,
                autonomy_mode: autonomyMode,
                max_trade_size: parseInt(maxTrade)
            })
        });

        const result = await response.json();

        if (result.success) {
            Toast?.show('✅ Settings saved!', 'success');
            if (btn) btn.innerHTML = '✓ Saved!';
        } else {
            throw new Error(result.error || 'Failed to save');
        }
    } catch (error) {
        console.error('Save settings error:', error);
        Toast?.show('Failed to save settings', 'error');
        if (btn) btn.innerHTML = '💾 Save Settings';
    }

    if (btn) {
        btn.disabled = false;
        setTimeout(() => {
            btn.innerHTML = '💾 Save Settings';
        }, 2000);
    }
}

/**
 * Update Artisan status indicators
 */
function updateArtisanStatus() {
    const statusBadge = document.getElementById('artisanStatusBadge');
    const tgStatus = document.getElementById('tgConnectionStatus');

    if (statusBadge) {
        if (premiumState.isPremium) {
            statusBadge.textContent = 'Active';
            statusBadge.className = 'status-badge premium';
        } else {
            statusBadge.textContent = 'Inactive';
            statusBadge.className = 'status-badge inactive';
        }
    }

    if (tgStatus) {
        if (premiumState.telegramConnected) {
            tgStatus.textContent = 'Connected';
            tgStatus.style.color = '#10b981';
        } else {
            tgStatus.textContent = 'Not connected';
            tgStatus.style.color = '#ef4444';
        }
    }
}

// Initialize on portfolio section load
document.addEventListener('DOMContentLoaded', () => {
    // Small delay to ensure DOM is ready
    setTimeout(initArtisanSettings, 500);
});

// Expose functions globally
window.PremiumUI = {
    canPerformSearch,
    incrementSearchCount,
    isPremium: () => premiumState.isPremium,
    getState: () => ({ ...premiumState }),
    initArtisanSettings,
    updateArtisanStatus
};
