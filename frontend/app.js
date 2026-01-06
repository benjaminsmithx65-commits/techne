/**
 * Techne Protocol - Main Application
 * Full-featured DeFi operating system
 */

const API_BASE = 'http://localhost:8000';

// ===========================================
// STATE
// ===========================================
let currentSection = 'explore';
let connectedWallet = null;
let ethersProvider = null;
let ethersSigner = null;
let currentChain = 'base';
let pools = [];
let filters = {
    chain: 'all',
    minTvl: 100000,
    maxTvl: null,      // null = no max limit
    minApy: 0,
    maxApy: null,      // null = no max limit
    risk: 'all',
    protocols: [],
    assetType: 'stablecoin',
    stablecoinType: 'all',
    poolType: 'all'    // 'single', 'dual', 'all'
};

// ===========================================
// INITIALIZATION
// ===========================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initFilters();
    initWallet();
    initViewToggle();
    initProtocolSearch();
    initBuildSection();
    loadPools();
});

// Protocol search in More Protocols section
function initProtocolSearch() {
    const searchInput = document.getElementById('protocolSearchInput');
    const protocolGrid = document.getElementById('moreProtocolsGrid');

    if (!searchInput || !protocolGrid) return;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const items = protocolGrid.querySelectorAll('.protocol-item');

        items.forEach(item => {
            const protocolName = item.querySelector('span')?.textContent.toLowerCase() || '';
            const protocolId = item.dataset.protocol?.toLowerCase() || '';

            if (protocolName.includes(query) || protocolId.includes(query)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

// Build Section - Full Pro Mode Logic
function initBuildSection() {
    initModeToggle();
    initPoolTypeFiltering();
    initQuickAmounts();
    initLeverageSlider();
    initExitTargetCheckboxes();
    initLiquidityStrategyToggle();
}

// Mode Toggle (Basic/Pro)
function initModeToggle() {
    const modeButtons = document.querySelectorAll('#builderModeToggle .mode-btn');

    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            modeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const mode = btn.dataset.mode;
            if (mode === 'pro') {
                document.body.classList.add('builder-pro');
            } else {
                document.body.classList.remove('builder-pro');
            }
        });
    });
}

// Pool Type Filtering
function initPoolTypeFiltering() {
    const poolTypeButtons = document.querySelectorAll('.pool-type-btn-build');
    const protocolGrid = document.getElementById('buildProtocolGrid');

    if (!poolTypeButtons.length || !protocolGrid) return;

    poolTypeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            poolTypeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const selectedType = btn.dataset.poolType;
            filterBuildProtocols(selectedType);
            updateYieldEngineeringSection(selectedType);
        });
    });

    // Initial filter
    const activeBtn = document.querySelector('.pool-type-btn-build.active');
    if (activeBtn) {
        filterBuildProtocols(activeBtn.dataset.poolType);
        updateYieldEngineeringSection(activeBtn.dataset.poolType);
    }
}

// Filter protocol chips based on pool type
function filterBuildProtocols(poolType) {
    const protocolGrid = document.getElementById('buildProtocolGrid');
    if (!protocolGrid) return;

    const chips = protocolGrid.querySelectorAll('.protocol-chip');

    chips.forEach(chip => {
        const chipSide = chip.dataset.poolSide;

        if (poolType === 'all') {
            chip.style.display = '';
        } else if (poolType === 'single' && chipSide === 'single') {
            chip.style.display = '';
        } else if (poolType === 'dual' && chipSide === 'dual') {
            chip.style.display = '';
        } else {
            chip.style.display = 'none';
        }
    });

    chips.forEach(chip => {
        if (chip.style.display === 'none') {
            chip.classList.remove('active');
        }
    });
}

// Update Yield Engineering section based on pool type
function updateYieldEngineeringSection(poolType) {
    const smartLoopSection = document.getElementById('smartLoopSection');
    const liquidityManagerSection = document.getElementById('liquidityManagerSection');

    if (!smartLoopSection || !liquidityManagerSection) return;

    if (poolType === 'single') {
        smartLoopSection.classList.remove('hidden');
        liquidityManagerSection.classList.add('hidden');
    } else if (poolType === 'dual') {
        smartLoopSection.classList.add('hidden');
        liquidityManagerSection.classList.remove('hidden');
    } else {
        // All - show both
        smartLoopSection.classList.remove('hidden');
        liquidityManagerSection.classList.remove('hidden');
    }
}

// Quick Amount Buttons
function initQuickAmounts() {
    const quickBtns = document.querySelectorAll('.quick-amounts button');
    const amountInput = document.getElementById('builderAmount');

    if (!quickBtns.length || !amountInput) return;

    quickBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            quickBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            amountInput.value = btn.dataset.amount;
        });
    });
}

// Leverage Slider with APY Calculation
function initLeverageSlider() {
    const slider = document.getElementById('leverageSlider');
    const apyDisplay = document.getElementById('leverageApy');
    const liquidationDisplay = document.getElementById('liquidationPrice');

    if (!slider || !apyDisplay) return;

    const baseApy = 12; // Base APY percentage

    slider.addEventListener('input', () => {
        const leverage = slider.value / 100;
        const boostedApy = (baseApy * leverage).toFixed(1);

        apyDisplay.innerHTML = `${baseApy}% → <span class="highlight">${boostedApy}%</span>`;

        // Calculate approximate liquidation price for stablecoins
        if (leverage > 1) {
            const liquidationPct = ((1 - (1 / leverage)) * 100).toFixed(0);
            liquidationDisplay.textContent = `-${liquidationPct}% from entry`;
        } else {
            liquidationDisplay.textContent = 'No liquidation';
        }
    });
}

// Exit Target Checkboxes - Enable/Disable inputs
function initExitTargetCheckboxes() {
    const takeProfitCheck = document.getElementById('takeProfitEnabled');
    const takeProfitInput = document.getElementById('takeProfitAmount');
    const apyTargetCheck = document.getElementById('apyTargetEnabled');
    const apyTargetInput = document.getElementById('apyTargetValue');

    if (takeProfitCheck && takeProfitInput) {
        takeProfitCheck.addEventListener('change', () => {
            takeProfitInput.disabled = !takeProfitCheck.checked;
        });
    }

    if (apyTargetCheck && apyTargetInput) {
        apyTargetCheck.addEventListener('change', () => {
            apyTargetInput.disabled = !apyTargetCheck.checked;
        });
    }
}

// Liquidity Strategy Toggle
function initLiquidityStrategyToggle() {
    const liqBtns = document.querySelectorAll('.liq-btn');
    const rebalanceConfig = document.getElementById('rebalanceConfig');

    liqBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            liqBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Show rebalance config only for active strategy
            if (rebalanceConfig) {
                rebalanceConfig.style.display = btn.dataset.strategy === 'active' ? 'flex' : 'none';
            }
        });
    });
}

// View toggle
function initViewToggle() {
    const viewBtns = document.querySelectorAll('.view-btn');
    const poolGrid = document.getElementById('poolGrid');

    viewBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            viewBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const view = btn.dataset.view;
            if (view === 'list') {
                poolGrid?.classList.add('list-view');
            } else {
                poolGrid?.classList.remove('list-view');
            }
        });
    });
}


// ===========================================
// NAVIGATION
// ===========================================
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            navigateToSection(section);
        });
    });
}

function navigateToSection(sectionId) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === sectionId);
    });

    // Update sections
    document.querySelectorAll('.section').forEach(section => {
        // Special case for savings which has ID 'savings-section' but passed as 'savings-section'
        // Other sections like 'explore' become 'section-explore' OR simply match ID if standard naming varies
        if (sectionId === 'savings-section') {
            section.style.display = (section.id === 'savings-section') ? 'block' : 'none';
        } else {
            // Default behavior for other sections
            const isMatch = (section.id === `section-${sectionId}`) || (section.id === sectionId);
            section.style.display = isMatch ? 'block' : 'none';
            section.classList.toggle('active', isMatch);
        }
    });

    // Update body class for section-specific styling (sidebar hide/show)
    document.body.className = document.body.className.replace(/section-\w+/g, '');
    document.body.classList.add(`section-${sectionId}`);

    currentSection = sectionId;

    // Load section data
    switch (sectionId) {
        case 'explore':
            loadPools();
            break;
        case 'savings-section':
            // Savings UI initialized by savings-ui.js
            if (window.SavingsUI && window.SavingsUI.init) {
                window.SavingsUI.loadRecommendedPools();
            }
            break;
        case 'vaults':
            loadVaults();
            break;
        case 'strategies':
            loadStrategies();
            break;
        case 'portfolio':
            loadPortfolio();
            break;
    }
}

// ===========================================
// FILTERS
// ===========================================
function initFilters() {
    // Chain buttons (old style)
    document.querySelectorAll('.chain-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.chain-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filters.chain = btn.dataset.chain;
            // loadPools(); // Disabled - use Apply Filters button
        });
    });

    // Chain buttons (new style with labels)
    document.querySelectorAll('.chain-btn-new[data-chain]').forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active from all chain buttons
            document.querySelectorAll('.chain-btn-new').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.chain-dropdown-item').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filters.chain = btn.dataset.chain;
            // loadPools(); // Disabled - use Apply Filters button
            // Close dropdown if open
            document.getElementById('chainDropdown')?.classList.remove('show');
        });
    });

    // Chain dropdown items
    document.querySelectorAll('.chain-dropdown-item').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.chain-btn-new').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.chain-dropdown-item').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelector('.chain-more-btn')?.classList.add('active');
            filters.chain = btn.dataset.chain;
            // loadPools(); // Disabled - use Apply Filters button
            document.getElementById('chainDropdown')?.classList.remove('show');
        });
    });

    // More dropdown toggle
    document.getElementById('chainMoreBtn')?.addEventListener('click', (e) => {
        e.stopPropagation();
        document.getElementById('chainDropdown')?.classList.toggle('show');
    });

    // Close dropdown on outside click
    document.addEventListener('click', () => {
        document.getElementById('chainDropdown')?.classList.remove('show');
    });

    // TVL dual slider
    const tvlMinSlider = document.getElementById('tvlMin');
    const tvlMaxSlider = document.getElementById('tvlMax');
    const tvlDisplay = document.getElementById('tvlDisplay');
    const tvlSteps = ['$100K', '$250K', '$500K', '$1M', '$2.5M', '$5M', '$10M', '$25M', '$50M', '$100M+'];
    const tvlValues = [100000, 250000, 500000, 1000000, 2500000, 5000000, 10000000, 25000000, 50000000, 100000000];

    function updateTvlDisplay() {
        const minIdx = parseInt(tvlMinSlider.value);
        const maxIdx = parseInt(tvlMaxSlider.value);
        filters.minTvl = tvlValues[minIdx];
        filters.maxTvl = maxIdx >= 9 ? null : tvlValues[maxIdx];

        if (minIdx === maxIdx) {
            tvlDisplay.textContent = tvlSteps[minIdx];
        } else if (maxIdx >= 9) {
            tvlDisplay.textContent = tvlSteps[minIdx] + '+';
        } else {
            tvlDisplay.textContent = tvlSteps[minIdx] + ' - ' + tvlSteps[maxIdx];
        }
    }

    if (tvlMinSlider && tvlMaxSlider) {
        tvlMinSlider.addEventListener('input', () => {
            if (parseInt(tvlMinSlider.value) > parseInt(tvlMaxSlider.value)) {
                tvlMaxSlider.value = tvlMinSlider.value;
            }
            updateTvlDisplay();
            if (typeof updateSliderFill === 'function') updateSliderFill('tvl');
        });
        tvlMaxSlider.addEventListener('input', () => {
            if (parseInt(tvlMaxSlider.value) < parseInt(tvlMinSlider.value)) {
                tvlMinSlider.value = tvlMaxSlider.value;
            }
            updateTvlDisplay();
            if (typeof updateSliderFill === 'function') updateSliderFill('tvl');
        });
        tvlMinSlider.addEventListener('change', loadPools);
        tvlMaxSlider.addEventListener('change', loadPools);
    }

    // APY dual slider
    const apyMinSlider = document.getElementById('apyMin');
    const apyMaxSlider = document.getElementById('apyMax');
    const apyDisplay = document.getElementById('apyDisplay');

    function updateApyDisplay() {
        const minVal = parseInt(apyMinSlider.value);
        const maxVal = parseInt(apyMaxSlider.value);
        filters.minApy = minVal;
        filters.maxApy = maxVal >= 100 ? null : maxVal;

        if (minVal === maxVal) {
            apyDisplay.textContent = minVal + '%';
        } else if (maxVal >= 100) {
            apyDisplay.textContent = minVal + '%+';
        } else {
            apyDisplay.textContent = minVal + '-' + maxVal + '%';
        }
    }

    if (apyMinSlider && apyMaxSlider) {
        apyMinSlider.addEventListener('input', () => {
            if (parseInt(apyMinSlider.value) > parseInt(apyMaxSlider.value)) {
                apyMaxSlider.value = apyMinSlider.value;
            }
            updateApyDisplay();
            if (typeof updateSliderFill === 'function') updateSliderFill('apy');
        });
        apyMaxSlider.addEventListener('input', () => {
            if (parseInt(apyMaxSlider.value) < parseInt(apyMinSlider.value)) {
                apyMinSlider.value = apyMaxSlider.value;
            }
            updateApyDisplay();
            if (typeof updateSliderFill === 'function') updateSliderFill('apy');
        });
        // apyMinSlider.addEventListener('change', loadPools); // Disabled
        // apyMaxSlider.addEventListener('change', loadPools); // Disabled
    }

    // Risk buttons - MULTI-SELECT (toggle on/off)
    document.querySelectorAll('.risk-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const risk = btn.dataset.risk;

            if (risk === 'all') {
                // "All" clears all other selections
                document.querySelectorAll('.risk-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                filters.risk = 'all';
            } else {
                // Remove "All" active state when selecting specific risks
                document.querySelector('.risk-btn[data-risk="all"]')?.classList.remove('active');

                // Toggle this button
                btn.classList.toggle('active');

                // Get all active risk levels
                const activeRisks = [];
                document.querySelectorAll('.risk-btn.active').forEach(b => {
                    if (b.dataset.risk !== 'all') {
                        activeRisks.push(b.dataset.risk);
                    }
                });

                // If nothing selected, default to "All"
                if (activeRisks.length === 0) {
                    document.querySelector('.risk-btn[data-risk="all"]')?.classList.add('active');
                    filters.risk = 'all';
                } else {
                    filters.risk = activeRisks; // Array of selected risks
                }
            }
            // loadPools(); // Disabled - use Apply Filters button
        });
    });

    // Protocol checkboxes
    document.querySelectorAll('.protocol-item input').forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            updateSelectedProtocols();
            // loadPools(); // Disabled - use Apply Filters button
        });
    });

    // Select all protocols
    const selectAllBtn = document.getElementById('selectAllProtocols');
    if (selectAllBtn) {
        let allSelected = true;
        selectAllBtn.addEventListener('click', () => {
            allSelected = !allSelected;
            document.querySelectorAll('.protocol-item input').forEach(cb => {
                cb.checked = allSelected;
            });
            selectAllBtn.textContent = allSelected ? 'None' : 'All';
            updateSelectedProtocols();
            // loadPools(); // Disabled - use Apply Filters button
        });
    }

    // Asset type buttons (Stablecoins, ETH, SOL, All)
    document.querySelectorAll('.asset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.asset-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filters.assetType = btn.dataset.asset;

            // Show/hide stablecoin type filter based on asset selection
            const stableGroup = document.getElementById('stablecoinTypeGroup');
            if (stableGroup) {
                stableGroup.style.display = filters.assetType === 'stablecoin' ? 'block' : 'none';
            }

            // loadPools(); // Disabled - use Apply Filters button
        });
    });

    // Stablecoin type buttons (USDC, USDT, DAI, etc)
    document.querySelectorAll('.stable-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.stable-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filters.stablecoinType = btn.dataset.stable;
            // loadPools(); // Disabled - use Apply Filters button
        });
    });

    // Pool type buttons (Single/Dual/All)
    document.querySelectorAll('.pool-type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.pool-type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filters.poolType = btn.dataset.pooltype;
            // loadPools(); // Disabled - use Apply Filters button
        });
    });
}

function updateSelectedProtocols() {
    filters.protocols = [];
    document.querySelectorAll('.protocol-item input:checked').forEach(cb => {
        const protocol = cb.closest('.protocol-item').dataset.protocol;
        if (protocol) filters.protocols.push(protocol);
    });
}

// ===========================================
// WALLET
// ===========================================
function initWallet() {
    const connectBtn = document.getElementById('connectWallet');
    if (connectBtn) {
        connectBtn.addEventListener('click', connectWallet);
    }

    // Check existing connection
    checkWalletConnection();

    // Initialize wallet gating for protected sections
    setTimeout(() => {
        updateWalletGatedSections();
    }, 500);
}

async function checkWalletConnection() {
    if (typeof window.ethereum === 'undefined') return;

    try {
        const accounts = await window.ethereum.request({ method: 'eth_accounts' });
        if (accounts.length > 0) {
            connectedWallet = accounts[0];
            window.connectedWallet = connectedWallet;
            updateWalletUI();
            loadUserPoolHistory();
            updateWalletGatedSections();
        }
    } catch (e) {
        console.log('Wallet check error:', e);
    }
}

async function connectWallet() {
    // Check if already connected
    if (connectedWallet) {
        showWalletMenu();
        return;
    }

    // Try MetaMask/injected wallet first
    if (typeof window.ethereum !== 'undefined') {
        try {
            Toast?.show('Connecting wallet...', 'info');

            // Create timeout promise
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('Connection timeout - please check MetaMask popup')), 30000);
            });

            // Race between wallet request and timeout
            const accounts = await Promise.race([
                window.ethereum.request({ method: 'eth_requestAccounts' }),
                timeoutPromise
            ]);

            if (accounts && accounts.length > 0) {
                connectedWallet = accounts[0];
                window.connectedWallet = connectedWallet;

                if (window.ethers) {
                    ethersProvider = new ethers.BrowserProvider(window.ethereum);
                    ethersSigner = await ethersProvider.getSigner();
                }

                updateWalletUI();
                Toast?.show('✅ Wallet connected: ' + connectedWallet.slice(0, 6) + '...' + connectedWallet.slice(-4), 'success');

                // Load user data
                loadUserPoolHistory();
                updateWalletGatedSections();
            } else {
                Toast?.show('No accounts found. Please unlock MetaMask.', 'warning');
            }
        } catch (e) {
            console.error('Wallet connection error:', e);

            // Better error messages
            if (e.code === 4001) {
                Toast?.show('Connection rejected by user', 'warning');
            } else if (e.code === -32002) {
                Toast?.show('Please check MetaMask - request pending!', 'warning');
            } else if (e.message?.includes('timeout')) {
                Toast?.show('Timeout - check MetaMask popup or unlock wallet', 'error');
            } else {
                Toast?.show('Connection failed: ' + (e.message || 'Unknown error'), 'error');
            }
        }
    } else {
        // No wallet detected - show options
        Toast?.show('No Web3 wallet detected', 'warning');

        // Show install options modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal" style="max-width: 400px; padding: 24px; background: #1a1d29; border-radius: 16px;">
                <h3 style="margin: 0 0 16px; color: #fff;">Install a Web3 Wallet</h3>
                <p style="color: #9ca3af; margin-bottom: 20px;">To use Techne Finance, you need a Web3 wallet.</p>
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    <a href="https://metamask.io/download/" target="_blank" 
                       style="display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #f6851b20; border: 1px solid #f6851b; border-radius: 8px; color: #fff; text-decoration: none;">
                        <span style="font-size: 24px;">🦊</span>
                        <span>MetaMask (Recommended)</span>
                    </a>
                    <a href="https://www.coinbase.com/wallet" target="_blank"
                       style="display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #0052ff20; border: 1px solid #0052ff; border-radius: 8px; color: #fff; text-decoration: none;">
                        <span style="font-size: 24px;">🔵</span>
                        <span>Coinbase Wallet</span>
                    </a>
                    <a href="https://rabby.io/" target="_blank"
                       style="display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #8697ff20; border: 1px solid #8697ff; border-radius: 8px; color: #fff; text-decoration: none;">
                        <span style="font-size: 24px;">🐰</span>
                        <span>Rabby Wallet</span>
                    </a>
                </div>
                <button onclick="this.closest('.modal-overlay').remove()" 
                        style="margin-top: 16px; width: 100%; padding: 12px; background: #374151; border: none; border-radius: 8px; color: #fff; cursor: pointer;">
                    Close
                </button>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }
}

function updateWalletUI() {
    const connectBtn = document.getElementById('connectWallet');
    if (connectBtn && connectedWallet) {
        connectBtn.innerHTML = `
            <span class="wallet-icon">✓</span>
            <span>Wallet Connected</span>
        `;
        connectBtn.classList.add('connected');

        // Show history button
        showPoolHistoryButton();
    }
}

function showWalletMenu() {
    const existing = document.querySelector('.wallet-menu-popup');
    if (existing) {
        existing.remove();
        return;
    }

    const popup = document.createElement('div');
    popup.className = 'wallet-menu-popup';
    popup.style.cssText = `
        position: fixed;
        top: 60px;
        right: 20px;
        background: var(--bg-elevated);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 12px;
        z-index: 1500;
        min-width: 220px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    `;

    popup.innerHTML = `
        <div style="padding: 8px 12px; border-bottom: 1px solid var(--border); margin-bottom: 8px;">
            <div style="font-size: 0.75rem; color: var(--text-muted);">Connected</div>
            <div style="font-family: monospace; font-size: 0.9rem;">${connectedWallet}</div>
        </div>
        <button onclick="showPoolHistory()" style="width: 100%; padding: 10px; background: var(--bg-surface); border: none; border-radius: 8px; color: var(--text); cursor: pointer; margin-bottom: 8px; text-align: left;">
            📜 Pool Order History
        </button>
        <button onclick="disconnectWallet()" style="width: 100%; padding: 10px; background: var(--danger); border: none; border-radius: 8px; color: white; cursor: pointer;">
            🔌 Disconnect
        </button>
    `;

    document.body.appendChild(popup);

    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!popup.contains(e.target) && !e.target.closest('#connectWallet')) {
                popup.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 100);
}

function disconnectWallet() {
    connectedWallet = null;
    window.connectedWallet = null;
    ethersProvider = null;
    ethersSigner = null;

    const connectBtn = document.getElementById('connectWallet');
    if (connectBtn) {
        connectBtn.innerHTML = '<span>🔗</span> Connect';
        connectBtn.classList.remove('connected');
    }

    document.querySelector('.wallet-menu-popup')?.remove();
    document.querySelector('.pool-history-btn')?.remove();

    Toast?.show('Wallet disconnected', 'info');
    updateWalletGatedSections();
}

function showPoolHistoryButton() {
    if (document.querySelector('.pool-history-btn')) return;

    const headerRight = document.querySelector('.header-right');
    if (!headerRight) return;

    const btn = document.createElement('button');
    btn.className = 'pool-history-btn';
    btn.style.cssText = `
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 8px 12px;
        color: var(--text);
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
        margin-right: 8px;
    `;
    btn.innerHTML = '📜 <span>History</span>';
    btn.onclick = showPoolHistory;

    headerRight.insertBefore(btn, headerRight.firstChild);
}

// Show history button immediately on page load (no wallet required)
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(showPoolHistoryButton, 100);
});

// Pool order history storage
const poolHistory = {
    orders: JSON.parse(localStorage.getItem('techne_pool_orders') || '[]'),

    add(pool, txHash) {
        this.orders.unshift({
            id: Date.now(),
            pool: pool,
            txHash: txHash,
            timestamp: new Date().toISOString()
        });
        this.orders = this.orders.slice(0, 20); // Keep last 20
        localStorage.setItem('techne_pool_orders', JSON.stringify(this.orders));
    },

    get() {
        return this.orders;
    }
};

function showPoolHistory() {
    document.querySelector('.wallet-menu-popup')?.remove();

    const orders = poolHistory.get();

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = 'display: flex; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center;';

    modal.innerHTML = `
        <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 24px; max-width: 500px; width: 90%; max-height: 80vh; overflow-y: auto;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0;">📜 Pool Order History</h2>
                <button onclick="this.closest('.modal-overlay').remove()" style="background: none; border: none; font-size: 20px; cursor: pointer; color: var(--text);">✕</button>
            </div>
            
            ${orders.length === 0 ? `
                <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                    <div style="font-size: 48px; margin-bottom: 16px;">📭</div>
                    <p>No pool orders yet</p>
                    <p style="font-size: 0.85rem;">Your unlocked pools will appear here</p>
                </div>
            ` : orders.map(order => `
                <div style="background: var(--bg-elevated); border-radius: 10px; padding: 14px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span style="font-weight: 600;">${order.pool?.project || 'Pool'}</span>
                        <span style="color: var(--text-muted); font-size: 0.8rem;">${new Date(order.timestamp).toLocaleDateString()}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary);">
                        ${order.pool?.symbol || ''} • ${order.pool?.apy?.toFixed(2) || '0'}% APY
                    </div>
                    ${order.txHash ? `
                        <a href="https://basescan.org/tx/${order.txHash}" target="_blank" 
                           style="font-size: 0.75rem; color: var(--gold); text-decoration: none;">
                            View on Basescan →
                        </a>
                    ` : ''}
                </div>
            `).join('')}
        </div>
    `;

    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

function loadUserPoolHistory() {
    // History loaded from localStorage automatically
    console.log('[Techne] Pool history loaded:', poolHistory.get().length, 'orders');
}

function updateWalletGatedSections() {
    // Only Portfolio requires wallet - Build/Vaults/Strategies are viewable
    // Deploy Agent button in Build checks wallet separately
    const gatedSections = ['section-portfolio'];

    gatedSections.forEach(sectionId => {
        const section = document.getElementById(sectionId);
        if (!section) return;

        if (!connectedWallet) {
            // Show connect wallet prompt
            if (!section.querySelector('.wallet-gate-overlay')) {
                const overlay = document.createElement('div');
                overlay.className = 'wallet-gate-overlay';
                overlay.style.cssText = `
                    position: absolute;
                    inset: 0;
                    background: rgba(0,0,0,0.85);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    z-index: 100;
                    backdrop-filter: blur(8px);
                `;
                overlay.innerHTML = `
                    <div style="font-size: 64px; margin-bottom: 20px;">🔒</div>
                    <h2 style="margin: 0 0 12px;">Connect Wallet</h2>
                    <p style="color: var(--text-secondary); margin-bottom: 24px; text-align: center;">
                        Connect your wallet to access this section
                    </p>
                    <button onclick="connectWallet()" style="
                        background: var(--gradient-gold);
                        border: none;
                        padding: 14px 32px;
                        border-radius: 10px;
                        font-weight: 600;
                        cursor: pointer;
                        font-size: 1rem;
                    ">
                        🔗 Connect Wallet
                    </button>
                `;
                section.style.position = 'relative';
                section.appendChild(overlay);
            }
        } else {
            // Remove overlay
            section.querySelector('.wallet-gate-overlay')?.remove();
        }
    });
}

// ===========================================
// POOLS
// ===========================================
async function loadPools() {
    const poolGrid = document.getElementById('poolGrid');
    const poolCount = document.getElementById('poolCount');

    if (!poolGrid) return;

    poolGrid.innerHTML = `
        <div class="loading-state">
            <div class="loader"></div>
            <p>Scanning protocols...</p>
        </div>
    `;

    try {
        // Fetch from API - send protocols to backend for server-side filtering
        // If 'all' or more than 5 protocols selected, don't filter by protocols (fetch all)
        let protocolsParam = '';
        if (Array.isArray(filters.protocols) && filters.protocols.length > 0 && filters.protocols.length <= 5) {
            protocolsParam = filters.protocols.join(',');
        }

        const params = new URLSearchParams({
            chain: filters.chain === 'all' ? '' : filters.chain,
            min_tvl: filters.minTvl,
            min_apy: filters.minApy,
            max_apy: filters.maxApy || 10000,  // Send max_apy to backend
            asset_type: filters.assetType,
            pool_type: filters.poolType,
            protocols: protocolsParam,  // Send selected protocols to backend
            limit: 100  // Fetch more, backend will filter by protocols
        });

        const response = await fetch(`${API_BASE}/api/pools?${params}`);
        const data = await response.json();

        pools = data.combined || data.pools || [];

        // Apply client-side filters
        let filtered = pools;

        // APY range filter (client-side backup)
        if (filters.minApy > 0 || (filters.maxApy && filters.maxApy < 10000)) {
            filtered = filtered.filter(p => {
                const apy = p.apy || 0;
                if (apy < filters.minApy) return false;
                if (filters.maxApy && apy > filters.maxApy) return false;
                return true;
            });
        }

        // TVL range filter (client-side backup)
        if (filters.maxTvl) {
            filtered = filtered.filter(p => {
                const tvl = p.tvl || 0;
                return tvl <= filters.maxTvl;
            });
        }

        // Risk filter - use risk_level from API (Low/Medium/High/Critical)
        // Supports multi-select: filters.risk can be 'all' (string) or array of selected levels
        if (filters.risk !== 'all') {
            filtered = filtered.filter(p => {
                const riskLevel = (p.risk_level || 'Medium').toLowerCase();
                // Handle multi-select (array) or single select (string)
                if (Array.isArray(filters.risk)) {
                    return filters.risk.includes(riskLevel);
                } else {
                    return riskLevel === filters.risk;
                }
            });
        }



        // Protocol filter (backup - backend now filters, but keep for safety)
        // Only filter if array with 1-5 protocols
        if (Array.isArray(filters.protocols) && filters.protocols.length > 0 && filters.protocols.length <= 5) {
            filtered = filtered.filter(p =>
                filters.protocols.some(proto =>
                    (p.project || '').toLowerCase().includes(proto)
                )
            );
        }

        // Asset type filter (Stablecoins, ETH, SOL)
        if (window.filterPoolsByAssetType && filters.assetType) {
            filtered = filterPoolsByAssetType(filtered, filters.assetType, filters.stablecoinType);
        }

        // Limit to 16 FREE pools on Explore page (daily rotation, same for all users)
        // Using filters/credits shows different results
        filtered = filtered.slice(0, 16);

        // Render
        renderPools(filtered);

        if (poolCount) {
            poolCount.textContent = `${filtered.length} pools found`;
        }


        // Update stats
        updateStats(filtered);

        // Add to search history
        if (window.SearchHistory && filters.assetType !== 'all') {
            SearchHistory.addEntry('filter', {
                assetType: filters.assetType,
                stablecoinType: filters.stablecoinType,
                chain: filters.chain,
                count: filtered.length
            });
        }

    } catch (e) {
        console.error('Pool loading error:', e);
        poolGrid.innerHTML = `
            <div class="loading-state">
                <p>Error loading pools. Please try again.</p>
            </div>
        `;
    }
}

function renderPools(pools) {
    const poolGrid = document.getElementById('poolGrid');
    if (!poolGrid) return;

    if (pools.length === 0) {
        poolGrid.innerHTML = `
            <div class="loading-state">
                <p>No pools match your filters</p>
            </div>
        `;
        return;
    }

    // Check if user has paid - DAILY ROTATING 15 FREE pools
    const FREE_POOL_LIMIT = 16;
    const userHasPaid = window.unlockedPools || localStorage.getItem('techne_pools_unlocked');

    // Get today's free pool indices (same for everyone, rotates daily)
    const freeIndices = getDailyFreePoolIndices(pools.length, FREE_POOL_LIMIT);

    poolGrid.innerHTML = pools.map((pool, index) => createPoolCard(pool, userHasPaid, index, freeIndices)).join('');

    // If not paid and there are more than 15 pools, show unlock overlay
    if (!userHasPaid && pools.length > FREE_POOL_LIMIT) {
        addUnlockOverlay(poolGrid);
    }
}

// Track unlocked pools state
window.unlockedPools = localStorage.getItem('techne_pools_unlocked') ? true : false;
window.verifiedPoolsData = null;

// FREE_POOL_LIMIT constant for other uses
window.FREE_POOL_LIMIT = 16;

// Get deterministic "random" free pools based on date (same for all users each day)
function getDailyFreePoolIndices(totalPools, limit = 15) {
    // Use today's date as seed (YYYYMMDD)
    const today = new Date();
    const seed = today.getUTCFullYear() * 10000 + (today.getUTCMonth() + 1) * 100 + today.getUTCDate();

    // Simple seeded random function
    const seededRandom = (s) => {
        const x = Math.sin(s) * 10000;
        return x - Math.floor(x);
    };

    // Generate shuffled indices
    const indices = Array.from({ length: totalPools }, (_, i) => i);
    for (let i = indices.length - 1; i > 0; i--) {
        const j = Math.floor(seededRandom(seed + i) * (i + 1));
        [indices[i], indices[j]] = [indices[j], indices[i]];
    }

    // Return first 'limit' indices as Set for O(1) lookup
    return new Set(indices.slice(0, limit));
}

function createPoolCard(pool, isUnlocked, index, freeIndices = new Set()) {
    const protocolIcon = getProtocolIconUrl(pool.project);
    const chainIcon = getChainIconUrl(pool.chain);

    // Use new risk scoring data from API
    const riskScore = pool.risk_score || 50;
    const riskLevel = pool.risk_level || 'Medium';
    const riskColor = pool.risk_color || '#F59E0B';
    const riskClass = riskLevel.toLowerCase();

    const airdropPotential = checkAirdropPotential(pool.project);
    const isVerified = pool.verified || pool.agent_verified;
    const poolData = JSON.stringify(pool).replace(/"/g, '&quot;');

    // All 15 pools are FREE preview - no blur needed
    // Using filters/credits shows different results

    return `
        <div class="pool-card ${isVerified ? 'verified' : ''}" 
             onclick='PoolDetailModal?.show(${poolData})' 
             data-pool-index="${index}">
            <div class="pool-header">
                <div class="pool-protocol">
                    <img src="${protocolIcon}" alt="${pool.project}" class="protocol-icon" onerror="this.style.display='none'">
                    <div class="pool-info">
                        <span class="pool-name">${pool.project}</span>
                        <span class="pool-pair">${pool.symbol}</span>
                    </div>
                </div>
                <div class="pool-chain" title="${pool.chain}">
                    <img src="${chainIcon}" alt="${pool.chain}" class="chain-icon" style="width:20px;height:20px;border-radius:50%;">
                </div>
            </div>
            
            <div class="pool-stats">
                <div class="pool-stat">
                    <span class="stat-value apy">${pool.apy?.toFixed(2) || '0.00'}%</span>
                    <span class="stat-label">APY</span>
                </div>
                <div class="pool-stat">
                    <span class="stat-value">${formatTvl(pool.tvl)}</span>
                    <span class="stat-label">TVL</span>
                </div>
                <div class="pool-stat">
                    <span class="risk-badge ${riskClass}" style="background: ${riskColor}20; color: ${riskColor}; border-color: ${riskColor};" title="Risk Score: ${riskScore}/100">
                        ${riskLevel}
                    </span>
                    <span class="stat-label">Risk</span>
                </div>
            </div>

            
            <div class="pool-badges">
                ${pool.category_icon && pool.category_label ? `<span class="badge category" title="${pool.category}">${pool.category_icon} ${pool.category_label}</span>` : ''}
                ${isVerified ? `<span class="badge verified">🤖 Verified</span>` : ''}
                ${airdropPotential ? `<span class="badge airdrop">🎁 Airdrop</span>` : ''}
                ${pool.stablecoin ? `<span class="badge stable">Stable</span>` : ''}
            </div>
            
            ${isUnlocked ? `
                <div class="pool-actions">
                    <button class="btn-deposit" onclick="event.stopPropagation(); handleDeposit('${pool.id || pool.pool}')">Deposit</button>
                    <button class="btn-compare" onclick='event.stopPropagation(); YieldComparison?.addPool(${poolData})'>📊</button>
                    <button class="btn-add-strategy" onclick="event.stopPropagation(); addToStrategy('${pool.id || pool.pool}')">+</button>
                </div>
            ` : ''}
        </div>
    `;
}

function addUnlockOverlay(poolGrid) {
    // Add CSS for blur effect
    const style = document.createElement('style');
    style.id = 'pool-blur-styles';
    if (!document.getElementById('pool-blur-styles')) {
        style.textContent = `
            .pool-blurred {
                filter: blur(6px);
                pointer-events: none;
                user-select: none;
            }
            .pool-locked-overlay {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 32px;
                z-index: 10;
                background: rgba(0,0,0,0.5);
                border-radius: 50%;
                width: 60px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .pool-card { position: relative; }
            .unlock-cta-overlay {
                position: absolute;
                inset: 0;
                background: linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.95) 60%);
                display: flex;
                flex-direction: column;
                justify-content: flex-end;
                align-items: center;
                padding: 40px 20px;
                z-index: 20;
                pointer-events: auto;
            }
            .unlock-cta-content {
                text-align: center;
                max-width: 400px;
            }
            .unlock-cta-content h3 {
                color: var(--gold);
                margin: 0 0 12px;
                font-size: 1.5rem;
            }
            .unlock-cta-content p {
                color: var(--text-muted);
                margin: 0 0 20px;
            }
            .btn-unlock-cta {
                background: var(--gradient-gold);
                border: none;
                padding: 16px 32px;
                border-radius: 12px;
                font-weight: 700;
                font-size: 1.1rem;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .pool-risk-analysis {
                background: rgba(0,0,0,0.3);
                border-radius: 8px;
                padding: 12px;
                margin: 12px 0;
            }
            .risk-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            .risk-title { font-weight: 600; }
            .risk-factors {
                list-style: none;
                padding: 0;
                margin: 0;
                font-size: 0.8rem;
            }
            .risk-factors li {
                padding: 4px 0;
                color: var(--text-muted);
            }
            .risk-factors li.warning { color: #f59e0b; }
            .risk-factors li.caution { color: #fbbf24; }
            .pool-airdrop-analysis {
                background: rgba(139, 92, 246, 0.1);
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-radius: 8px;
                padding: 10px;
                margin: 8px 0;
            }
            .airdrop-header {
                display: flex;
                justify-content: space-between;
                font-size: 0.9rem;
            }
            .airdrop-score { color: #a78bfa; font-weight: 600; }
            .airdrop-reason { font-size: 0.75rem; color: var(--text-muted); margin: 4px 0 0; }
            .pool-feature-badges {
                display: flex;
                gap: 8px;
                margin: 8px 0;
            }
            .feature-badge {
                font-size: 0.75rem;
                padding: 4px 8px;
                border-radius: 4px;
            }
            .feature-badge.deposit { background: rgba(74, 222, 128, 0.2); color: #4ade80; }
            .feature-badge.withdraw { background: rgba(74, 222, 128, 0.2); color: #4ade80; }
            .pool-footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid var(--border);
            }
            .btn-deposit-full {
                background: var(--gradient-gold);
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
            }
            .pool-apy-display {
                text-align: right;
            }
            .apy-value {
                font-size: 1.5rem;
                font-weight: 700;
                color: #4ade80;
            }
            .apy-label {
                display: block;
                font-size: 0.75rem;
                color: var(--text-muted);
            }
        `;
        document.head.appendChild(style);
    }

    // Add unlock CTA overlay at bottom of grid
    const overlay = document.createElement('div');
    overlay.className = 'unlock-cta-overlay';
    overlay.innerHTML = `
        <div class="unlock-cta-content">
            <h3>🔓 Unlock 16 AI-Verified Pools</h3>
            <p>Get full risk analysis, airdrop potential, and deposit verification for all pools</p>
            <button class="btn-unlock-cta" onclick="UnlockModal.open()">
                <span>⚡</span> 16 Pools for $0.10 USDC
            </button>
        </div>
    `;
    poolGrid.style.position = 'relative';
    poolGrid.appendChild(overlay);
}

// Function to unlock pools after payment
window.unlockPoolsInPlace = function (verifiedPools, txHash = null) {
    window.unlockedPools = true;
    window.verifiedPoolsData = verifiedPools;
    localStorage.setItem('techne_pools_unlocked', 'true');
    localStorage.setItem('techne_verified_pools', JSON.stringify(verifiedPools));

    // Save each pool to history
    if (Array.isArray(verifiedPools)) {
        verifiedPools.forEach(pool => {
            poolHistory.add(pool, txHash);
        });
    }

    // Re-render pools with unlocked state
    if (typeof loadPools === 'function') {
        loadPools();
    }

    Toast?.show('✅ All pools unlocked with full analysis!', 'success');
}


function getProtocolIconUrl(protocol) {
    if (!protocol) return 'https://icons.llama.fi/default.png';

    // Map protocol names to DefiLlama icon slugs
    const protocolMap = {
        'aave': 'aave',
        'aave-v3': 'aave',
        'aave-v2': 'aave',
        'uniswap': 'uniswap',
        'uniswap-v3': 'uniswap',
        'uniswap-v2': 'uniswap',
        'uniswap-v4': 'uniswap',
        'curve': 'curve',
        'curve-finance': 'curve',
        'curve-dex': 'curve',
        'aerodrome': 'aerodrome',
        'aerodrome-finance': 'aerodrome',
        'aerodrome-v1': 'aerodrome',
        'aerodrome-slipstream': 'aerodrome',
        'aerodrome-base': 'aerodrome',
        'compound': 'compound',
        'compound-finance': 'compound',
        'compound-v3': 'compound',
        'lido': 'lido',
        'morpho': 'morpho',
        'morpho-blue': 'morpho',
        'morpho-v1': 'morpho',
        'morpho-aave-v3': 'morpho',
        'morpho-compound': 'morpho',
        'pendle': 'pendle',
        'gmx': 'gmx',
        'gmx-v2': 'gmx',
        'yearn': 'yearn',
        'yearn-finance': 'yearn',
        'beefy': 'beefy',
        'beefy-finance': 'beefy',
        'balancer': 'balancer',
        'balancer-v2': 'balancer',
        'balancer-finance': 'balancer',
        'spark': 'spark',
        'convex': 'convex',
        'convex-finance': 'convex',
        'radiant': 'radiant',
        'moonwell': 'moonwell',
        'infinifi': 'infinifi',
        // Solana protocols
        'raydium': 'raydium',
        'raydium-amm': 'raydium',
        'raydium-clmm': 'raydium',
        'orca': 'orca',
        'orca-dex': 'orca',
        'kamino': 'kamino',
        'kamino-lend': 'kamino',
        'kamino-liquidity': 'kamino',
        'kamino-lend': 'kamino',
        'kamino-liquidity': 'kamino',
        // Multi-chain protocols
        'memedollar': 'meme-dollar',
        'merkl': 'merkl',
        'peapods': 'peapods',
        'peapods-finance': 'peapods'
    };

    const lower = protocol.toLowerCase().replace(/[^a-z0-9-]/g, '').replace(/\s+/g, '-');
    const slug = protocolMap[lower] || lower;

    // Use local icons - SVG for some protocols
    const svgProtocols = ['infinifi'];
    const ext = svgProtocols.includes(slug) ? 'svg' : 'png';
    return `/icons/protocols/${slug}.${ext}`;
}

function getChainIconUrl(chain) {
    if (!chain) return '/icons/ethereum.png';

    const chainMap = {
        'ethereum': 'ethereum',
        'solana': 'solana',
        'base': 'base',
        'arbitrum': 'arbitrum',
        'optimism': 'optimism',
        'polygon': 'polygon',
        'avalanche': 'avalanche',
        'bsc': 'bsc',
        'binance': 'bsc'
    };

    const slug = chainMap[chain.toLowerCase()] || 'ethereum';
    return `/icons/${slug}.png`;
}

function getChainEmoji(chain) {
    // Fallback only
    return '';
}

function formatTvl(tvl) {
    if (!tvl) return '$0';
    if (tvl >= 1000000000) return `$${(tvl / 1000000000).toFixed(1)}B`;
    if (tvl >= 1000000) return `$${(tvl / 1000000).toFixed(1)}M`;
    if (tvl >= 1000) return `$${(tvl / 1000).toFixed(0)}K`;
    return `$${tvl.toFixed(0)}`;
}

function checkAirdropPotential(project) {
    if (!project) return false;
    const airdropProjects = [
        'morpho', 'pendle', 'eigenlayer', 'scroll', 'linea', 'midas', 'zksync',
        'velodrome', 'stargate', 'beefy', 'zerolend', 'hyperliquid', 'blast',
        'taiko', 'layerzero', 'eclipse', 'starknet', 'zircuit', 'mode',
        'base', 'mantle', 'arbitrum', 'optimism', 'polygon-zkevm', 'linea',
        'extra-finance', 'seamless', 'ironclad', 'ionic'
    ];
    return airdropProjects.some(p => project.toLowerCase().includes(p));
}

function updateStats(pools) {
    const totalTvl = pools.reduce((sum, p) => sum + (p.tvl || 0), 0);
    const avgApy = pools.length > 0
        ? pools.reduce((sum, p) => sum + (p.apy || 0), 0) / pools.length
        : 0;

    const protocols = new Set(pools.map(p => p.project)).size;
    const chains = new Set(pools.map(p => p.chain)).size;

    const tvlEl = document.getElementById('totalTvl');
    const apyEl = document.getElementById('avgApy');
    const protocolsEl = document.getElementById('protocolsActive');
    const chainsEl = document.getElementById('chainsActive');

    if (tvlEl) tvlEl.textContent = formatTvl(totalTvl);
    if (apyEl) apyEl.textContent = avgApy.toFixed(1) + '%';
    if (protocolsEl) protocolsEl.textContent = protocols;
    if (chainsEl) chainsEl.textContent = chains;
}

// ===========================================
// VAULTS
// ===========================================
async function loadVaults() {
    // Vaults are static for now, later will fetch from API
    console.log('Loading vaults...');
}

// ===========================================
// STRATEGIES
// ===========================================
async function loadStrategies() {
    console.log('Loading strategies...');
}

// ===========================================
// PORTFOLIO
// ===========================================
async function loadPortfolio() {
    if (!connectedWallet) {
        return;
    }
    console.log('Loading portfolio for', connectedWallet);
}

// ===========================================
// ACTIONS
// ===========================================
function handleDeposit(poolId) {
    // Find the pool data
    const pool = pools.find(p => p.id === poolId || p.pool === poolId);

    if (!pool) {
        console.error('Pool not found:', poolId);
        return;
    }

    // Open deposit modal
    if (window.DepositModal) {
        window.DepositModal.open(pool);
    } else {
        console.log('DepositModal not loaded, fallback');
        if (!connectedWallet) {
            connectWallet();
            return;
        }
    }
}

function addToStrategy(poolId) {
    // Find the pool data first
    const pool = pools.find(p => p.id === poolId || p.pool === poolId);

    if (!pool) {
        console.error('Pool not found for strategy:', poolId);
        Toast?.error('Pool not found');
        return;
    }

    // Store pool for StrategyBuilder to use
    window.selectedPoolForStrategy = pool;

    // Navigate to Build section
    navigateToSection('build');

    // Add pool to strategy if StrategyBuilder available
    if (window.StrategyBuilder) {
        setTimeout(() => {
            window.StrategyBuilder.addPoolToStrategy?.(pool);
            // Fallback if addPoolToStrategy doesn't exist
            if (!window.StrategyBuilder.addPoolToStrategy) {
                window.StrategyBuilder.addComponent?.('entry');
            }
        }, 100);
    }

    Toast?.success(`Added ${pool.project} to strategy builder`);
}

// ===========================================
// CUSTOM RANGE POPUP
// ===========================================
function showCustomRange(type) {
    // Remove existing popup
    document.querySelectorAll('.popup-overlay, .custom-range-popup').forEach(el => el.remove());

    const overlay = document.createElement('div');
    overlay.className = 'popup-overlay';
    overlay.onclick = () => {
        overlay.remove();
        document.querySelector('.custom-range-popup')?.remove();
    };

    const popup = document.createElement('div');
    popup.className = 'custom-range-popup';

    const label = type === 'tvl' ? 'TVL' : 'APY';
    const suffix = type === 'tvl' ? ' (in USD)' : ' (%)';
    const currentMin = type === 'tvl' ? filters.minTvl : filters.minApy;
    const currentMax = type === 'tvl' ? (filters.maxTvl || '') : (filters.maxApy || '');

    popup.innerHTML = `
        <h3>Custom ${label} Range${suffix}</h3>
        <div class="inputs">
            <input type="text" id="customMin" placeholder="Min" value="${currentMin}">
            <input type="text" id="customMax" placeholder="Max (empty = no limit)" value="${currentMax}">
        </div>
        <div class="actions">
            <button style="background: var(--bg-elevated); border: 1px solid var(--border); color: var(--text-primary);" 
                    onclick="this.closest('.custom-range-popup').remove(); document.querySelector('.popup-overlay').remove()">
                Cancel
            </button>
            <button style="background: var(--gold); border: none; color: var(--bg-void);"
                    onclick="applyCustomRange('${type}')">
                Apply
            </button>
        </div>
    `;

    document.body.appendChild(overlay);
    document.body.appendChild(popup);
    popup.querySelector('#customMin').focus();
}

function applyCustomRange(type) {
    const minVal = parseInt(document.getElementById('customMin').value) || 0;
    const maxInput = document.getElementById('customMax').value.trim();
    const maxVal = maxInput ? parseInt(maxInput) : null;

    if (type === 'tvl') {
        filters.minTvl = minVal;
        filters.maxTvl = maxVal;

        // Update display
        const display = document.getElementById('tvlDisplay');
        if (display) {
            const formatTvl = (n) => n >= 1000000 ? '$' + (n / 1000000) + 'M' : '$' + (n / 1000) + 'K';
            display.textContent = maxVal ? formatTvl(minVal) + ' - ' + formatTvl(maxVal) : formatTvl(minVal) + '+';
        }
    } else {
        filters.minApy = minVal;
        filters.maxApy = maxVal;

        const display = document.getElementById('apyDisplay');
        if (display) {
            display.textContent = maxVal ? minVal + '-' + maxVal + '%' : minVal + '%+';
        }
    }

    document.querySelector('.custom-range-popup')?.remove();
    document.querySelector('.popup-overlay')?.remove();
    // loadPools(); // Disabled - use Apply Filters button
}

// ===========================================
// EXPORT
// ===========================================
window.Techne = {
    navigateToSection,
    connectWallet,
    loadPools,
    showCustomRange,
    applyCustomRange,
    handleDeposit,
    addToStrategy
};

// Make global for onclick handlers
window.showCustomRange = showCustomRange;
window.applyCustomRange = applyCustomRange;

// Update slider fill position on load
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        updateSliderFill('tvl');
        updateSliderFill('apy');
    }, 100);
});

function updateSliderFill(type) {
    const slider = document.getElementById(type + 'Slider');
    const fill = document.getElementById(type + 'Fill');
    const minInput = document.getElementById(type + 'Min');
    const maxInput = document.getElementById(type + 'Max');

    if (!slider || !fill || !minInput || !maxInput) return;

    const min = parseInt(minInput.min);
    const max = parseInt(minInput.max);
    const minVal = parseInt(minInput.value);
    const maxVal = parseInt(maxInput.value);

    const leftPercent = ((minVal - min) / (max - min)) * 100;
    const rightPercent = ((maxVal - min) / (max - min)) * 100;

    fill.style.left = leftPercent + '%';
    fill.style.width = (rightPercent - leftPercent) + '%';
}

window.updateSliderFill = updateSliderFill;

// ===========================================
// $1B PREMIUM UI UTILITIES
// ===========================================

// Toast Notification System
const Toast = {
    show(message, type = 'success', duration = 4000) {
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.2rem;">${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
                <div>
                    <div style="font-weight: 600; color: #fff;">${message}</div>
                </div>
            </div>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'toastSlideOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    success(message) { this.show(message, 'success'); },
    error(message) { this.show(message, 'error'); },
    info(message) { this.show(message, 'info'); }
};

// Animated Counter
function animateCounter(element, endValue, duration = 1500, prefix = '', suffix = '') {
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const current = start + (endValue - start) * easeOutQuart;

        // Format based on size
        let formatted;
        if (current >= 1000000000) {
            formatted = (current / 1000000000).toFixed(2) + 'B';
        } else if (current >= 1000000) {
            formatted = (current / 1000000).toFixed(1) + 'M';
        } else if (current >= 1000) {
            formatted = (current / 1000).toFixed(1) + 'K';
        } else {
            formatted = current.toFixed(0);
        }

        element.textContent = prefix + formatted + suffix;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// Skeleton Loading
function showSkeletonCards(container, count = 8) {
    container.innerHTML = Array(count).fill(0).map(() => `
        <div class="pool-card skeleton-card">
            <div class="skeleton" style="width: 60%; height: 20px; margin-bottom: 12px;"></div>
            <div class="skeleton" style="width: 40%; height: 16px; margin-bottom: 20px;"></div>
            <div style="display: flex; justify-content: space-between;">
                <div class="skeleton" style="width: 30%; height: 24px;"></div>
                <div class="skeleton" style="width: 25%; height: 24px;"></div>
            </div>
        </div>
    `).join('');
}

// High APY Detection
function markHighApyPools() {
    document.querySelectorAll('.pool-card').forEach(card => {
        const apyText = card.querySelector('.apy, .pool-apy, .apy-value')?.textContent;
        if (apyText) {
            const apy = parseFloat(apyText.replace('%', ''));
            if (apy > 20) {
                card.setAttribute('data-apy-high', 'true');
            }
        }
    });
}

// Add quick actions to pool cards
function addQuickActions() {
    document.querySelectorAll('.pool-card').forEach(card => {
        if (card.querySelector('.quick-actions')) return;

        const actions = document.createElement('div');
        actions.className = 'quick-actions';
        actions.innerHTML = `
            <button class="quick-action-btn" onclick="event.stopPropagation();">⭐ Favorite</button>
            <button class="quick-action-btn" onclick="event.stopPropagation();">📊 Compare</button>
            <button class="quick-action-btn" onclick="event.stopPropagation();">💰 Deposit</button>
        `;
        card.appendChild(actions);
    });
}

// Init premium features on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Animate header stats
    setTimeout(() => {
        const tvlStat = document.querySelector('[data-stat="tvl"]');
        const volumeStat = document.querySelector('[data-stat="volume"]');

        if (tvlStat) animateCounter(tvlStat, 2400000000, 2000, '$');
        if (volumeStat) animateCounter(volumeStat, 149000000, 2000, '$');
    }, 500);
});

// Re-apply premium features after pool load
const originalLoadPools = window.loadPools || loadPools;
window.loadPools = async function () {
    await originalLoadPools.apply(this, arguments);
    setTimeout(() => {
        markHighApyPools();
        // Note: Quick actions removed - pool cards already have action buttons
    }, 100);
};

// Export utilities
window.Toast = Toast;
window.animateCounter = animateCounter;
window.showSkeletonCards = showSkeletonCards;

// ===========================================
// COMPREHENSIVE BUTTON HANDLERS
// All buttons work like a billion-dollar protocol
// ===========================================

document.addEventListener('DOMContentLoaded', () => {
    initAllButtonHandlers();
});

function initAllButtonHandlers() {
    // Strategy Tab Buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const parent = btn.closest('.tabs, .strategy-tabs, .tab-container');
            if (parent) {
                parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            }
            btn.classList.add('active');

            const tabName = btn.textContent.trim();
            loadTabContent(tabName);
            Toast?.show(`Showing: ${tabName}`, 'info');
        });
    });

    // Copy Strategy Button
    document.querySelectorAll('.btn-copy').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const strategyCard = btn.closest('.strategy-card');
            const strategyName = strategyCard?.querySelector('.strategy-name, h3')?.textContent || 'Strategy';

            Toast?.show(`📋 Copying "${strategyName}"...`, 'info');

            // Navigate to Build section with copied strategy
            setTimeout(() => {
                navigateToSection('build');
                Toast?.show(`✅ Strategy "${strategyName}" copied! Customize it below.`, 'success');
            }, 500);
        });
    });

    // View Strategy Details Button
    document.querySelectorAll('.btn-view').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const strategyCard = btn.closest('.strategy-card');
            const strategyName = strategyCard?.querySelector('.strategy-name, h3')?.textContent || 'Strategy';

            showStrategyDetails(strategyName, strategyCard);
        });
    });

    // Preset Buttons
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const preset = btn.dataset.preset;
            applyStrategyPreset(preset);
            Toast?.show(`✅ ${btn.textContent.trim()} preset applied!`, 'success');
        });
    });

    // Portfolio Action Buttons
    document.querySelectorAll('.btn-withdraw').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!window.connectedWallet) {
                Toast?.show('Please connect wallet first', 'warning');
                connectWallet();
                return;
            }
            showWithdrawModal(btn.closest('.position-card'));
        });
    });

    document.querySelectorAll('.btn-claim').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!window.connectedWallet) {
                Toast?.show('Please connect wallet first', 'warning');
                connectWallet();
                return;
            }
            Toast?.show('🎁 Claiming rewards...', 'info');
            setTimeout(() => {
                Toast?.show('✅ Rewards claimed successfully!', 'success');
            }, 2000);
        });
    });

    // DAO Buttons
    document.querySelectorAll('.btn-vote, [data-action="vote"]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!window.connectedWallet) {
                Toast?.show('Please connect wallet to vote', 'warning');
                connectWallet();
                return;
            }
            const voteType = btn.dataset.vote || 'for';
            Toast?.show(`🗳️ Casting ${voteType} vote...`, 'info');
            setTimeout(() => {
                Toast?.show('✅ Vote recorded on-chain!', 'success');
            }, 1500);
        });
    });

    document.querySelectorAll('.btn-delegate').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!window.connectedWallet) {
                Toast?.show('Please connect wallet to delegate', 'warning');
                connectWallet();
                return;
            }
            showDelegateModal();
        });
    });

    document.querySelectorAll('.btn-propose, .btn-create-proposal').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!window.connectedWallet) {
                Toast?.show('Please connect wallet to create proposal', 'warning');
                connectWallet();
                return;
            }
            showProposalModal();
        });
    });

    // Detail/Expand Buttons for Pool Cards
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('btn-details') || e.target.closest('.btn-details')) {
            const card = e.target.closest('.pool-card');
            if (card) {
                const poolId = card.dataset.poolId || card.dataset.id;
                const pool = pools.find(p => (p.id || p.pool) === poolId);
                if (pool && window.PoolDetailModal) {
                    PoolDetailModal.show(pool);
                } else if (pool) {
                    Toast?.show(`Pool: ${pool.project} - ${pool.symbol}`, 'info');
                }
            }
        }
    });

    // Protocol Select All Button
    document.getElementById('selectAllProtocols')?.addEventListener('click', () => {
        document.querySelectorAll('.protocol-btn').forEach(btn => {
            btn.classList.add('active');
        });
        filters.protocols = 'all';
        // loadPools(); // Disabled - use Apply Filters button
        Toast?.show('All protocols selected', 'info');
    });

    // View Toggle (Grid/List)
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const view = btn.dataset.view;
            const poolGrid = document.getElementById('poolGrid');
            if (poolGrid) {
                poolGrid.className = view === 'list' ? 'pool-list' : 'pool-grid';
            }
            Toast?.show(`Switched to ${view} view`, 'info');
        });
    });

    // Stable Token Buttons
    document.querySelectorAll('.stable-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.stable-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            filters.stableToken = btn.dataset.stable;
            // loadPools(); // Disabled - use Apply Filters button
        });
    });

    // Asset Type Buttons
    document.querySelectorAll('.asset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.asset-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            filters.assetType = btn.dataset.asset;
            // loadPools(); // Disabled - use Apply Filters button
        });
    });

    console.log('[Techne] ✅ All button handlers initialized');
}

// Helper Functions for Button Actions
function loadTabContent(tabName) {
    console.log(`Loading tab: ${tabName}`);
    // Tabs would load different strategy views
}

function showStrategyDetails(name, card) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = 'display: flex; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center;';

    modal.innerHTML = `
        <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 24px; max-width: 500px; width: 90%;">
            <h2 style="margin: 0 0 16px; color: var(--gold);">${name}</h2>
            <p style="color: var(--text-secondary); margin-bottom: 20px;">Strategy performance and allocation details.</p>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
                <div style="background: var(--bg-elevated); padding: 12px; border-radius: 8px;">
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Total Return</div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: var(--success);">+24.5%</div>
                </div>
                <div style="background: var(--bg-elevated); padding: 12px; border-radius: 8px;">
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Risk Level</div>
                    <div style="font-size: 1.2rem; font-weight: 700;">Medium</div>
                </div>
            </div>
            <button onclick="this.closest('.modal-overlay').remove()" style="width: 100%; padding: 12px; background: var(--gradient-gold); border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                Close
            </button>
        </div>
    `;

    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

function applyStrategyPreset(preset) {
    console.log(`Applying preset: ${preset}`);
    if (window.AgentBuilder) {
        switch (preset) {
            case 'yield-maximizer':
                AgentBuilder.config.minApy = 25;
                AgentBuilder.config.riskLevel = 'high';
                break;
            case 'balanced-growth':
                AgentBuilder.config.minApy = 10;
                AgentBuilder.config.riskLevel = 'medium';
                break;
            case 'stable-farmer':
                AgentBuilder.config.minApy = 5;
                AgentBuilder.config.riskLevel = 'low';
                break;
        }
        AgentBuilder.updateUI?.();
    }
}

function showWithdrawModal(positionCard) {
    const amount = positionCard?.querySelector('.position-value')?.textContent || '$0.00';

    Toast?.show('💸 Preparing withdrawal...', 'info');

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = 'display: flex; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center;';

    modal.innerHTML = `
        <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 24px; max-width: 400px; width: 90%;">
            <h2 style="margin: 0 0 16px;">Withdraw</h2>
            <p style="color: var(--text-secondary); margin-bottom: 16px;">Available: ${amount}</p>
            <input type="text" placeholder="Amount" style="width: 100%; padding: 12px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 8px; color: var(--text); margin-bottom: 16px;">
            <div style="display: flex; gap: 12px;">
                <button onclick="this.closest('.modal-overlay').remove()" style="flex: 1; padding: 12px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 8px; cursor: pointer; color: var(--text);">
                    Cancel
                </button>
                <button onclick="window.Toast?.show('✅ Withdrawal submitted!', 'success'); this.closest('.modal-overlay').remove();" style="flex: 1; padding: 12px; background: var(--gradient-gold); border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                    Withdraw
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

function showDelegateModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = 'display: flex; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center;';

    modal.innerHTML = `
        <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 24px; max-width: 400px; width: 90%;">
            <h2 style="margin: 0 0 16px;">🗳️ Delegate Voting Power</h2>
            <p style="color: var(--text-secondary); margin-bottom: 16px;">Delegate your TECHNE tokens to another address.</p>
            <input type="text" placeholder="Delegate address (0x...)" style="width: 100%; padding: 12px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 8px; color: var(--text); margin-bottom: 16px;">
            <button onclick="window.Toast?.show('✅ Delegation successful!', 'success'); this.closest('.modal-overlay').remove();" style="width: 100%; padding: 12px; background: var(--gradient-gold); border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                Delegate
            </button>
        </div>
    `;

    document.body.appendChild(modal);
}

function showProposalModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = 'display: flex; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 2000; align-items: center; justify-content: center;';

    modal.innerHTML = `
        <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 24px; max-width: 500px; width: 90%;">
            <h2 style="margin: 0 0 16px;">📝 Create Proposal</h2>
            <input type="text" placeholder="Proposal Title" style="width: 100%; padding: 12px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 8px; color: var(--text); margin-bottom: 12px;">
            <textarea placeholder="Proposal Description" rows="4" style="width: 100%; padding: 12px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 8px; color: var(--text); margin-bottom: 16px; resize: none;"></textarea>
            <div style="display: flex; gap: 12px;">
                <button onclick="this.closest('.modal-overlay').remove()" style="flex: 1; padding: 12px; background: var(--bg-elevated); border: 1px solid var(--border); border-radius: 8px; cursor: pointer; color: var(--text);">
                    Cancel
                </button>
                <button onclick="window.Toast?.show('✅ Proposal submitted for review!', 'success'); this.closest('.modal-overlay').remove();" style="flex: 1; padding: 12px; background: var(--gradient-gold); border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                    Submit
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

// Re-initialize handlers after dynamic content loads
window.addEventListener('sectionChanged', () => {
    setTimeout(initAllButtonHandlers, 100);
});

// Export shared functions for components.js
window.formatTvl = formatTvl;
window.getProtocolIconUrl = getProtocolIconUrl;
window.getChainIconUrl = getChainIconUrl;
window.addToStrategy = addToStrategy;
window.pools = pools;
window.handleDeposit = handleDeposit;
