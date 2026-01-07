/**
 * Techne Protocol - Verify Pools Module
 * Verify any pool by address/URL and get risk analysis
 * Cost: 10 credits per verification
 */

const VerifyPools = {
    VERIFY_COST: 10,
    STORAGE_KEY: 'techne_verify_history',

    // Initialize module
    init() {
        this.bindEvents();
        this.loadHistory();
        this.updateCreditsDisplay();
        console.log('[VerifyPools] Module initialized');
    },

    // Bind UI events
    bindEvents() {
        const verifyBtn = document.getElementById('verifyPoolBtn');
        const input = document.getElementById('verifyPoolInput');

        if (verifyBtn) {
            verifyBtn.addEventListener('click', () => this.handleVerify());
        }

        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.handleVerify();
            });
        }
    },

    // Update credits display
    updateCreditsDisplay() {
        const costEl = document.getElementById('verifyCreditCost');
        if (costEl) {
            costEl.textContent = this.VERIFY_COST;
        }
    },

    // Handle verify button click
    async handleVerify() {
        const input = document.getElementById('verifyPoolInput');
        const address = input?.value?.trim();

        if (!address) {
            Toast?.show('Please enter a pool address or URL', 'warning');
            return;
        }

        // Check credits
        if (typeof CreditsManager !== 'undefined') {
            const credits = CreditsManager.getCredits();
            if (credits < this.VERIFY_COST) {
                Toast?.show(`Need ${this.VERIFY_COST} credits to verify. You have ${credits}.`, 'warning');
                CreditsManager.showBuyModal?.();
                return;
            }
        }

        // Show loading
        const btn = document.getElementById('verifyPoolBtn');
        const originalText = btn?.innerHTML;
        if (btn) {
            btn.innerHTML = '<span class="loading-spinner"></span> Verifying...';
            btn.disabled = true;
        }

        try {
            // Parse input to get pool identifier
            const poolId = this.parseInput(address);

            // Fetch pool data
            const poolData = await this.fetchPoolData(poolId);

            if (!poolData) {
                throw new Error('Pool not found');
            }

            // Deduct credits
            if (typeof CreditsManager !== 'undefined') {
                CreditsManager.setCredits(CreditsManager.getCredits() - this.VERIFY_COST);
                Toast?.show(`✓ Used ${this.VERIFY_COST} credits`, 'success');
            }

            // Save to history
            this.saveToHistory(poolData);

            // Show modal
            this.showVerificationModal(poolData);

            // Clear input
            if (input) input.value = '';

        } catch (error) {
            console.error('[VerifyPools] Error:', error);
            Toast?.show(`Verification failed: ${error.message}`, 'error');
        } finally {
            if (btn) {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }
    },

    // Parse input (address or URL)
    parseInput(input) {
        // DefiLlama URL: https://defillama.com/yields/pool/...
        if (input.includes('defillama.com')) {
            const match = input.match(/pool\/([a-f0-9-]+)/i);
            return match ? match[1] : input;
        }

        // Contract address
        if (input.startsWith('0x') && input.length === 42) {
            return input.toLowerCase();
        }

        // Return as-is for other formats
        return input;
    },

    // Fetch pool data from API
    async fetchPoolData(poolId) {
        try {
            // Try to find in existing pools first
            if (typeof pools !== 'undefined' && Array.isArray(pools)) {
                const found = pools.find(p =>
                    p.pool === poolId ||
                    p.pool_id === poolId ||
                    p.address?.toLowerCase() === poolId.toLowerCase()
                );
                if (found) return found;
            }

            // Fetch from DefiLlama
            const response = await fetch(`https://yields.llama.fi/pools`);
            if (!response.ok) throw new Error('API error');

            const data = await response.json();
            const pool = data.data?.find(p =>
                p.pool === poolId ||
                p.pool?.includes(poolId)
            );

            return pool || null;
        } catch (error) {
            console.error('[VerifyPools] Fetch error:', error);
            return null;
        }
    },

    // Show verification modal (reuse Pool Detail style)
    showVerificationModal(pool) {
        // Use existing PoolDetail if available
        if (typeof PoolDetail !== 'undefined' && PoolDetail.show) {
            PoolDetail.show(pool);
            return;
        }

        // Fallback simple modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = 'verifyResultModal';
        modal.innerHTML = `
            <div class="modal-container" style="max-width: 600px;">
                <button class="modal-close" onclick="document.getElementById('verifyResultModal').remove()">✕</button>
                <h2 style="margin-bottom: 16px;">✅ Pool Verified</h2>
                
                <div style="background: var(--bg-elevated); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                    <h3 style="font-size: 1.2rem; margin-bottom: 8px;">${pool.symbol || pool.pool}</h3>
                    <p style="color: var(--text-muted); font-size: 0.9rem;">${pool.project || 'Unknown Protocol'}</p>
                </div>

                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px;">
                    <div style="background: var(--bg-surface); padding: 12px; border-radius: 8px;">
                        <div style="color: var(--text-muted); font-size: 0.75rem;">TVL</div>
                        <div style="font-size: 1.1rem; font-weight: 600;">$${this.formatNumber(pool.tvlUsd)}</div>
                    </div>
                    <div style="background: var(--bg-surface); padding: 12px; border-radius: 8px;">
                        <div style="color: var(--text-muted); font-size: 0.75rem;">APY</div>
                        <div style="font-size: 1.1rem; font-weight: 600; color: var(--success);">${pool.apy?.toFixed(2) || 0}%</div>
                    </div>
                    <div style="background: var(--bg-surface); padding: 12px; border-radius: 8px;">
                        <div style="color: var(--text-muted); font-size: 0.75rem;">Chain</div>
                        <div style="font-size: 1.1rem;">${pool.chain || 'Unknown'}</div>
                    </div>
                    <div style="background: var(--bg-surface); padding: 12px; border-radius: 8px;">
                        <div style="color: var(--text-muted); font-size: 0.75rem;">Pool Type</div>
                        <div style="font-size: 1.1rem;">${pool.stablecoin ? 'Stable' : 'Volatile'}</div>
                    </div>
                </div>

                <div style="background: var(--bg-surface); padding: 16px; border-radius: 8px;">
                    <h4 style="margin-bottom: 12px; color: var(--gold);">Risk Analysis</h4>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        <li style="padding: 6px 0; color: var(--text-secondary);">
                            ${pool.ilRisk === 'no' ? '✅' : '⚠️'} IL Risk: ${pool.ilRisk || 'Unknown'}
                        </li>
                        <li style="padding: 6px 0; color: var(--text-secondary);">
                            ${pool.tvlUsd > 1000000 ? '✅' : '⚠️'} TVL: ${pool.tvlUsd > 1000000 ? 'Healthy' : 'Low'}
                        </li>
                        <li style="padding: 6px 0; color: var(--text-secondary);">
                            ${pool.apy < 50 ? '✅' : '⚠️'} APY: ${pool.apy < 50 ? 'Sustainable' : 'High (check source)'}
                        </li>
                    </ul>
                </div>

                <button onclick="document.getElementById('verifyResultModal').remove()" 
                        style="width: 100%; margin-top: 20px; padding: 12px; background: var(--gold); color: black; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                    Close
                </button>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    },

    // Format number with K/M/B suffix
    formatNumber(num) {
        if (!num) return '0';
        if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
        return num.toFixed(0);
    },

    // Save to history
    saveToHistory(pool) {
        const history = this.getHistory();

        const entry = {
            id: pool.pool || pool.pool_id,
            symbol: pool.symbol,
            project: pool.project,
            chain: pool.chain,
            apy: pool.apy,
            tvlUsd: pool.tvlUsd,
            verifiedAt: Date.now()
        };

        // Add to front, limit to 20 items
        history.unshift(entry);
        if (history.length > 20) history.pop();

        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(history));
        this.renderHistory(history);
    },

    // Get history from localStorage
    getHistory() {
        try {
            return JSON.parse(localStorage.getItem(this.STORAGE_KEY)) || [];
        } catch {
            return [];
        }
    },

    // Load and render history
    loadHistory() {
        const history = this.getHistory();
        this.renderHistory(history);
    },

    // Render history grid
    renderHistory(history) {
        const grid = document.getElementById('verifyHistoryGrid');
        if (!grid) return;

        if (history.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">
                    <div style="font-size: 2rem; margin-bottom: 8px;">🔍</div>
                    <p>No verified pools yet. Enter an address above to verify.</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = history.map(pool => `
            <div class="verify-history-card" onclick="VerifyPools.openFromHistory('${pool.id}')">
                <div class="verify-card-header">
                    <span class="verify-pool-name">${pool.symbol || 'Unknown'}</span>
                    <span class="verify-pool-apy ${pool.apy > 0 ? 'positive' : ''}">${pool.apy?.toFixed(1) || 0}%</span>
                </div>
                <div class="verify-card-meta">
                    <span>${pool.project || 'Protocol'}</span>
                    <span>•</span>
                    <span>${pool.chain || 'Chain'}</span>
                </div>
                <div class="verify-card-footer">
                    <span class="verify-tvl">$${this.formatNumber(pool.tvlUsd)}</span>
                    <span class="verify-date">${this.formatDate(pool.verifiedAt)}</span>
                </div>
            </div>
        `).join('');
    },

    // Format date
    formatDate(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    },

    // Open pool from history
    async openFromHistory(poolId) {
        const history = this.getHistory();
        const cached = history.find(p => p.id === poolId);

        if (cached) {
            // Try to get fresh data
            const fresh = await this.fetchPoolData(poolId);
            this.showVerificationModal(fresh || cached);
        }
    }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    VerifyPools.init();
});
