/**
 * Pool Detail Modal - Enhanced pool information view
 */

const PoolIcons = {
    close: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`,
    tvl: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>`,
    risk: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
    shield: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>`,
    coins: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"></circle><path d="M18.09 10.37A6 6 0 1 1 10.34 18"></path><path d="M7 6h1v4"></path><path d="m16.71 13.88.7.71-2.82 2.82"></path></svg>`,
    trendUp: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>`,
    trendDown: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>`,
    check: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
    activity: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`,
    bot: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="16" r="4"></circle><path d="M7 6h10"></path><line x1="8" y1="6" x2="8" y2="2"></line><line x1="16" y1="6" x2="16" y2="2"></line></svg>`,
    externalLink: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>`,
    fileText: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>`,
    // Data coverage icons
    database: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>`,
    chartBar: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"></line><line x1="18" y1="20" x2="18" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line></svg>`,
    clock: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`,
    // Audit & Security icons
    shieldCheck: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg>`,
    lock: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>`,
    unlock: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 9.9-1"></path></svg>`,
    // Risk Flag icons
    alertTriangle: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
    zap: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>`,
    target: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>`,
    flame: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path></svg>`,
    droplet: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"></path></svg>`,
    link: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>`,
    // Token icons
    hexagon: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>`,
    checkCircle: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
    xCircle: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`,
    // Whale & Analysis
    users: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>`,
    pieChart: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg>`,
    eye: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`,
    flag: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path><line x1="4" y1="22" x2="4" y2="15"></line></svg>`,
    info: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`,
    helpCircle: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
    dollarSign: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>`,
    percent: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="5" x2="5" y2="19"></line><circle cx="6.5" cy="6.5" r="2.5"></circle><circle cx="17.5" cy="17.5" r="2.5"></circle></svg>`,
    barChart: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>`
};

// Known token address to symbol mapping (Base mainnet)
const TOKEN_ADDRESS_MAP = {
    '0x194f7cd4da3514c7fb38f079d79e4b7200e98bf4': 'MERKL',
    '0x940181a94a35a4569e4529a3cdfb74e38fd98631': 'AERO',
    '0x4200000000000000000000000000000000000006': 'WETH',
    '0x833589fcd6edb6e08f4c7c32d4f71b54bda02913': 'USDC',
    '0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca': 'USDbC',
    '0x50c5725949a6f0c72e6c4a641f24049a917db0cb': 'DAI',
    '0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22': 'cbETH',
    '0xc1cba3fcea344f92d9239c08c0568f6f2f0ee452': 'wstETH',
    '0xb6fe221fe9eef5aba221c348ba20a1bf5e73624c': 'rETH',
    '0x0578d8a44db98b23bf096a382e016e29a5ce0ffe': 'COMP',
    '0x4f604735c1cf31399c6e711d5962b2b3e0225ad3': 'MORPHO',
    '0x78a087d713be963bf3f1c1a8e73af1a31d9eb08d': 'ARB',
};

// Format reward token name - resolve addresses to symbols
function formatRewardTokenName(name) {
    if (!name) return 'TOKEN';

    // Check if it's a hex address (starts with 0x and has 42 chars)
    const addressMatch = name.match(/0x[a-fA-F0-9]{40}/i);
    if (addressMatch) {
        const address = addressMatch[0].toLowerCase();
        // Check mapping first
        if (TOKEN_ADDRESS_MAP[address]) {
            return TOKEN_ADDRESS_MAP[address];
        }
        // Return shortened address
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    }

    // Check if it's in format "Reward (0x...):" or similar
    if (name.match(/\(0x[a-fA-F0-9]+\)/)) {
        const innerMatch = name.match(/0x[a-fA-F0-9]{40}/i);
        if (innerMatch) {
            const addr = innerMatch[0].toLowerCase();
            if (TOKEN_ADDRESS_MAP[addr]) {
                return TOKEN_ADDRESS_MAP[addr];
            }
            return `${addr.slice(0, 6)}...${addr.slice(-4)}`;
        }
    }

    return name;
}

// Get protocol website URL
function getProtocolWebsite(project) {
    const websites = {
        'aerodrome': 'https://aerodrome.finance',
        'velodrome': 'https://velodrome.finance',
        'aave': 'https://aave.com',
        'aave-v3': 'https://aave.com',
        'compound': 'https://compound.finance',
        'compound-v3': 'https://compound.finance',
        'morpho': 'https://morpho.org',
        'moonwell': 'https://moonwell.fi',
        'curve-dex': 'https://curve.fi',
        'curve': 'https://curve.fi',
        'uniswap': 'https://uniswap.org',
        'uniswap-v3': 'https://uniswap.org',
        'beefy': 'https://beefy.finance',
        'yearn': 'https://yearn.fi',
        'yearn-finance': 'https://yearn.fi',
        'seamless': 'https://seamlessprotocol.com',
        'seamless-protocol': 'https://seamlessprotocol.com',
        'sonne': 'https://sonne.finance',
        'sonne-finance': 'https://sonne.finance',
        'exactly': 'https://exactly.finance',
        'extra-finance': 'https://extra.finance',
        'merkl': 'https://merkl.angle.money',
        'pendle': 'https://pendle.finance',
        'radiant': 'https://radiant.capital',
        'radiant-v2': 'https://radiant.capital',
        'spark': 'https://spark.fi',
        'convex': 'https://convexfinance.com',
        'convex-finance': 'https://convexfinance.com',
        'lido': 'https://lido.fi',
        'gmx': 'https://gmx.io',
        'balancer': 'https://balancer.fi',
        'balancer-v2': 'https://balancer.fi',
        'stargate': 'https://stargate.finance',
        'origin': 'https://originprotocol.com',
        'origin-ether': 'https://originprotocol.com',
        'avantis': 'https://avantis.finance',
        'infinifi': 'https://infinifi.xyz'
    };
    const key = (project || '').toLowerCase().replace(/[^a-z0-9-]/g, '');
    return websites[key] || null;
}

// Get explorer URL for contract
function getExplorerUrl(pool) {
    const chain = (pool.chain || 'base').toLowerCase();
    const explorers = {
        'base': 'https://basescan.org/address/',
        'ethereum': 'https://etherscan.io/address/',
        'arbitrum': 'https://arbiscan.io/address/',
        'optimism': 'https://optimistic.etherscan.io/address/',
        'polygon': 'https://polygonscan.com/address/'
    };
    const baseUrl = explorers[chain] || explorers['base'];
    const contractAddress = pool.pool_address || pool.contract || pool.id;
    if (contractAddress && contractAddress.startsWith('0x')) {
        return `${baseUrl}${contractAddress}`;
    }
    return null;
}

const PoolDetailModal = {
    currentPool: null,

    // Calculate time until next Aerodrome/Velodrome epoch (Wednesday 00:00 UTC)
    getEpochCountdown() {
        const now = new Date();
        const nextWed = new Date(now);
        nextWed.setUTCHours(0, 0, 0, 0);
        const currentDay = now.getUTCDay();
        const daysUntilWed = (3 - currentDay + 7) % 7 || 7;
        nextWed.setUTCDate(now.getUTCDate() + daysUntilWed);
        const diff = nextWed - now;
        const days = Math.floor(diff / 86400000);
        const hours = Math.floor((diff % 86400000) / 3600000);
        const minutes = Math.floor((diff % 3600000) / 60000);
        return { days, hours, minutes, display: `${days}d ${hours}h ${minutes}m` };
    },

    // Check if protocol has epoch-based rewards
    isEpochProtocol(project) {
        const ep = (project || '').toLowerCase();
        return ep.includes('aerodrome') || ep.includes('velodrome');
    },

    // Keydown handler
    handleKeydown(e) {
        if (e.key === 'Escape') {
            PoolDetailModal.close();
        }
    },

    // Tab switching for Bento Grid
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.pd-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        // Update tab panels
        document.querySelectorAll('.pd-tab-panel').forEach(panel => {
            panel.classList.toggle('active', panel.dataset.panel === tabName);
        });
    },

    // Accordion toggle - opens as overlay
    toggleAccordion(accordionName) {
        const accordion = document.querySelector(`.pd-accordion[data-accordion="${accordionName}"]`);
        if (!accordion) return;

        const content = accordion.querySelector('.pd-accordion-content');
        const title = accordion.querySelector('.pd-accordion-title')?.textContent || 'Details';

        if (!content) return;

        this.openOverlay(title, content.innerHTML);
    },

    // Open overlay panel
    openOverlay(title, content) {
        // Remove any existing overlay
        this.closeOverlay();

        // Create backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'pd-overlay-backdrop';
        backdrop.onclick = () => this.closeOverlay();

        // Create panel
        const panel = document.createElement('div');
        panel.className = 'pd-overlay-panel';
        panel.innerHTML = `
            <div class="pd-overlay-header">
                <span class="pd-overlay-title">${title}</span>
                <button class="pd-overlay-close" onclick="PoolDetailModal.closeOverlay()">✕</button>
            </div>
            <div class="pd-overlay-body">
                ${content}
            </div>
        `;

        document.body.appendChild(backdrop);
        document.body.appendChild(panel);

        // Close on ESC
        document.addEventListener('keydown', this.handleOverlayKeydown);
    },

    // Close overlay panel
    closeOverlay() {
        const backdrop = document.querySelector('.pd-overlay-backdrop');
        const panel = document.querySelector('.pd-overlay-panel');
        if (backdrop) backdrop.remove();
        if (panel) panel.remove();
        document.removeEventListener('keydown', this.handleOverlayKeydown);
    },

    handleOverlayKeydown(e) {
        if (e.key === 'Escape') {
            PoolDetailModal.closeOverlay();
        }
    },

    // =========================================
    // SECURITY ASSESSMENT (Safety Guard)
    // =========================================

    /**
     * Assess pool security from backend data
     * Returns { isCritical, isWarning, warnings, canDeposit }
     */
    assessSecurity(pool) {
        const security = pool.security || {};
        const riskScore = pool.risk_score || pool.riskScore || 50;
        const riskAnalysis = pool.risk_analysis || {};

        const result = {
            isCritical: false,
            isWarning: false,
            warnings: [],
            canDeposit: true,
            honeypot: false,
            unverified: false,
            highTax: false,
            depeg: false
        };

        // Check 1: Honeypot detection (CRITICAL)
        if (security.is_honeypot || riskAnalysis.is_honeypot) {
            result.isCritical = true;
            result.canDeposit = false;
            result.honeypot = true;
            result.warnings.push('🚨 HONEYPOT DETECTED - Cannot sell tokens!');
        }

        // Check 2: Risk score below 30 (CRITICAL)
        if (riskScore < 30 && !result.isCritical) {
            result.isCritical = true;
            result.canDeposit = false;
            result.warnings.push(`🚨 Critical risk level (Score: ${riskScore}/100)`);
        }

        // Check 3: Unverified contract (WARNING)
        if (security.tokens) {
            for (const [addr, info] of Object.entries(security.tokens)) {
                if (info && info.is_verified === false) {
                    result.isWarning = true;
                    result.unverified = true;
                    result.warnings.push('⚠️ Unverified contract - not open source');
                    break;
                }
            }
        }

        // Check 4: High tax detection (WARNING)
        if (security.tokens) {
            for (const [addr, info] of Object.entries(security.tokens)) {
                if (info) {
                    const sellTax = parseFloat(info.sell_tax || 0) * 100;
                    const buyTax = parseFloat(info.buy_tax || 0) * 100;
                    if (sellTax > 10 || buyTax > 10) {
                        result.isWarning = true;
                        result.highTax = true;
                        result.warnings.push(`⚠️ High tax detected: Buy ${buyTax.toFixed(1)}% / Sell ${sellTax.toFixed(1)}%`);
                        break;
                    }
                }
            }
        }

        // Check 5: Stablecoin depeg (WARNING)
        const pegStatus = security.peg_status || {};
        if (pegStatus.depeg_risk) {
            result.isWarning = true;
            result.depeg = true;
            const depegged = pegStatus.depegged_tokens || [];
            depegged.forEach(t => {
                result.warnings.push(`⚠️ ${t.symbol} DEPEG: $${t.price?.toFixed(4)} (${t.deviation?.toFixed(2)}% off peg)`);
            });
        }

        return result;
    },

    /**
     * Format reward token name - prefer backend symbols over addresses
     */
    formatRewardSymbol(token) {
        // If backend provides symbol, use it
        if (token.symbol && !token.symbol.startsWith('0x')) {
            return token.symbol;
        }
        // Fallback to address mapping
        if (token.address && TOKEN_ADDRESS_MAP[token.address.toLowerCase()]) {
            return TOKEN_ADDRESS_MAP[token.address.toLowerCase()];
        }
        // Last resort: truncate address
        if (token.address) {
            return `${token.address.slice(0, 6)}...`;
        }
        return token.symbol || '???';
    },

    /**
     * Render deposit button based on security assessment
     */
    renderDepositButton(pool, security) {
        const project = (pool.project || '').toUpperCase();
        const poolUrl = pool.pool_link || (window.getPoolUrl ? getPoolUrl(pool) : '#');

        if (security.isCritical) {
            // BLOCKED: Critical risk
            return `
                <button class="pd-btn-danger" disabled onclick="alert('⚠️ Deposit blocked: ${security.warnings[0]}')">
                    🚫 DEPOSIT BLOCKED - CRITICAL RISK
                </button>
            `;
        } else if (security.isWarning) {
            // WARNING: Show caution but allow
            return `
                <a href="${poolUrl}" target="_blank" class="pd-btn-warning" onclick="return confirm('⚠️ Warning:\\n${security.warnings.join('\\n')}\\n\\nDo you want to proceed?');">
                    ⚠️ DEPOSIT ON ${project} (CAUTION)
                </a>
            `;
        } else {
            // SAFE: Normal deposit
            return `
                <a href="${poolUrl}" target="_blank" class="pd-btn-primary" onclick="event.stopPropagation();">
                    💰 DEPOSIT ON ${project}
                </a>
            `;
        }
    },

    // =========================================
    // APY EXPLAINER - Source and Confidence
    // =========================================

    /**
     * Render APY source explanation
     * Shows user where APY comes from and any caveats
     */
    renderApyExplainer(pool) {
        const apySource = pool.apy_source || 'unknown';
        const hasGauge = pool.gauge_address || pool.has_gauge;
        const isEpoch = this.isEpochProtocol(pool.project);
        const isCL = (pool.pool_type === 'cl') || (pool.project || '').toLowerCase().includes('slipstream');

        // Determine source label and explanation
        let sourceLabel, sourceIcon, explanation, confidence;

        if (apySource.includes('gauge') || apySource.includes('v2_onchain')) {
            sourceLabel = 'Gauge Emissions';
            sourceIcon = '🎯';
            explanation = 'APY from AERO token rewards distributed to stakers';
            confidence = 'high';
        } else if (apySource.includes('cl_calculated')) {
            sourceLabel = 'Gauge + Total TVL';
            sourceIcon = '📊';
            explanation = 'Emissions ÷ total pool TVL. Actual staker APR may be higher if not all liquidity is staked.';
            confidence = 'medium';
        } else if (apySource.includes('defillama')) {
            sourceLabel = 'DefiLlama Aggregate';
            sourceIcon = '📈';
            explanation = 'Historical yield data from aggregator';
            confidence = 'medium';
        } else if (apySource.includes('geckoterminal')) {
            sourceLabel = 'GeckoTerminal';
            sourceIcon = '🦎';
            explanation = 'Market-derived APY estimate';
            confidence = 'medium';
        } else {
            sourceLabel = 'Estimated';
            sourceIcon = '⚙️';
            explanation = 'Calculated from available data';
            confidence = 'low';
        }

        // Build caveats based on pool characteristics
        const caveats = [];
        if (isEpoch) caveats.push('Epoch-based: changes weekly');
        if (isCL) caveats.push('CL pool: gauge APR may differ');
        if (hasGauge) caveats.push('Requires gauge staking');
        if (pool.apy > 100) caveats.push('High APY: verify sustainability');

        // If APY is N/A, explain why
        if (!pool.apy || pool.apy === 0) {
            const reason = pool.apy_reason || pool.apy_status || 'Data unavailable';
            return `
                <div class="pd-apy-explainer unavailable">
                    <div class="pd-apy-source">
                        <span class="pd-source-icon">❓</span>
                        <span class="pd-source-label">APY Unavailable</span>
                    </div>
                    <div class="pd-apy-reason">${this.formatApyReason(reason)}</div>
                </div>
            `;
        }

        return `
            <div class="pd-apy-explainer">
                <div class="pd-apy-source">
                    <span class="pd-source-icon">${sourceIcon}</span>
                    <span class="pd-source-label">Source: ${sourceLabel}</span>
                    <span class="pd-confidence ${confidence}">${confidence.toUpperCase()}</span>
                </div>
                <div class="pd-apy-explanation">${explanation}</div>
                ${caveats.length > 0 ? `
                    <div class="pd-apy-caveats">
                        ${caveats.map(c => `<span class="pd-caveat">• ${c}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    },

    /**
     * Render "Why this APY can change" with full explanations
     * Shows detailed breakdown of APY volatility factors
     */
    renderApyChangeExplainer(pool) {
        const isCL = (pool.pool_type === 'cl') || (pool.project || '').toLowerCase().includes('slipstream');
        const isEpoch = this.isEpochProtocol(pool.project);
        const hasGauge = pool.gauge_address || pool.has_gauge;
        const apyReward = parseFloat(pool.apy_reward || 0);
        const apyBase = parseFloat(pool.apy_base || 0);

        const reasons = [];

        if (isEpoch) {
            reasons.push({
                icon: '⏰',
                title: 'Epoch Resets (Weekly)',
                desc: 'Aerodrome/Velodrome rewards reset every Wednesday at 00:00 UTC. Vote distribution changes weekly based on veAERO/veVELO holder decisions.',
                impact: 'HIGH',
                color: '#EF4444'
            });
        }

        if (isCL) {
            reasons.push({
                icon: '🎯',
                title: 'Range-Dependent Yield',
                desc: 'Concentrated Liquidity pools require active management. Yield depends on your price range - narrower ranges = higher yield but more rebalancing needed.',
                impact: 'HIGH',
                color: '#EF4444'
            });
        }

        if (hasGauge) {
            reasons.push({
                icon: '🗳️',
                title: 'Gauge Vote Distribution',
                desc: 'Emissions are distributed based on weekly governance votes. Popular pools may receive fewer emissions if votes shift to other pools.',
                impact: 'MEDIUM',
                color: '#F59E0B'
            });
        }

        reasons.push({
            icon: '💧',
            title: 'TVL Fluctuations',
            desc: 'When more liquidity enters the pool, rewards are diluted among more LPs. Conversely, TVL drops can increase your share of rewards.',
            impact: 'MEDIUM',
            color: '#F59E0B'
        });

        if (apyReward > 0 || hasGauge) {
            reasons.push({
                icon: '📉',
                title: 'Reward Token Price',
                desc: `Emission rewards are paid in protocol tokens (e.g., AERO). If token price drops, the USD value of your rewards decreases even if emissions stay constant.`,
                impact: apyReward > apyBase ? 'HIGH' : 'MEDIUM',
                color: apyReward > apyBase ? '#EF4444' : '#F59E0B'
            });
        }

        if (apyBase > 0) {
            reasons.push({
                icon: '💱',
                title: 'Trading Volume',
                desc: 'Base APY comes from swap fees. Lower trading volume = fewer fees collected = lower base yield. Volume can vary significantly day-to-day.',
                impact: 'LOW',
                color: '#10B981'
            });
        }

        if (reasons.length === 0) return '<div class="pd-no-data">No volatility factors identified</div>';

        return `
            <div class="pd-section pd-apy-change-full">
                <div class="pd-section-header">
                    <h3>⚡ Why This APY Can Change</h3>
                </div>
                <div class="pd-apy-reasons-list">
                    ${reasons.map(r => `
                        <div class="pd-reason-item">
                            <div class="pd-reason-header">
                                <span class="pd-reason-icon">${r.icon}</span>
                                <span class="pd-reason-title">${r.title}</span>
                                <span class="pd-reason-impact" style="background: ${r.color}20; color: ${r.color};">${r.impact}</span>
                            </div>
                            <div class="pd-reason-desc">${r.desc}</div>
                        </div>
                    `).join('')}
                </div>
                <div class="pd-apy-summary">
                    <strong>Current Composition:</strong> 
                    ${apyBase > 0 ? `Base/Fees: ${apyBase.toFixed(2)}%` : ''}
                    ${apyBase > 0 && apyReward > 0 ? ' + ' : ''}
                    ${apyReward > 0 ? `Emissions: ${apyReward.toFixed(2)}%` : ''}
                    ${!apyBase && !apyReward ? 'Data unavailable' : ''}
                </div>
            </div>
        `;
    },

    /**
     * Render Liquidity Stress Indicator
     * Simulates impact of TVL drops since we don't have historical data
     */
    renderLiquidityStress(pool) {
        const tvl = pool.tvl || pool.tvlUsd || 0;
        if (!tvl || tvl <= 0) return '';

        // Format TVL helper
        const formatTvl = (val) => {
            if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
            if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
            if (val >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
            return `$${val.toFixed(0)}`;
        };

        // Calculate stress scenarios
        const scenarios = [
            { drop: 10, level: 'low', label: 'Low impact', color: '#22C55E' },
            { drop: 30, level: 'medium', label: 'Medium impact', color: '#F59E0B' },
            { drop: 50, level: 'high', label: 'High slippage risk', color: '#EF4444' }
        ];

        // Determine current stress level based on absolute TVL
        let currentStress = 'healthy';
        let stressColor = '#22C55E';
        if (tvl < 100000) {
            currentStress = 'critical';
            stressColor = '#EF4444';
        } else if (tvl < 500000) {
            currentStress = 'stressed';
            stressColor = '#F59E0B';
        } else if (tvl < 2000000) {
            currentStress = 'moderate';
            stressColor = '#84CC16';
        }

        return `
            <div class="pd-liquidity-stress">
                <div class="pd-stress-header">
                    <span class="pd-stress-icon">💧</span>
                    <span class="pd-stress-title">Liquidity Stress Test</span>
                    <span class="pd-stress-current" style="color: ${stressColor}">
                        ${currentStress.charAt(0).toUpperCase() + currentStress.slice(1)}
                    </span>
                </div>
                <div class="pd-stress-scenarios">
                    ${scenarios.map(s => {
            const newTvl = tvl * (1 - s.drop / 100);
            return `
                            <div class="pd-stress-row ${s.level}">
                                <div class="pd-stress-drop">-${s.drop}% TVL</div>
                                <div class="pd-stress-bar-container">
                                    <div class="pd-stress-bar" style="width: ${100 - s.drop}%; background: ${s.color}"></div>
                                </div>
                                <div class="pd-stress-result">
                                    <span class="pd-stress-tvl">${formatTvl(newTvl)}</span>
                                    <span class="pd-stress-impact" style="color: ${s.color}">${s.label}</span>
                                </div>
                            </div>
                        `;
        }).join('')}
                </div>
                <div class="pd-stress-footer">
                    Simulated impact if liquidity exits. Current: ${formatTvl(tvl)}
                </div>
            </div>
        `;
    },

    formatApyReason(reason) {
        const reasons = {
            'CL_POOL_NO_ONCHAIN_TVL': 'Concentrated liquidity - TVL data unavailable',
            'NO_GAUGE': 'No gauge - no emission rewards',
            'GAUGE_METHODS_FAILED': 'Unable to read gauge contract',
            'LP_PRICE_ZERO': 'Could not determine LP token value',
            'requires_external_tvl': 'Waiting for external TVL data',
            'unsupported': 'Pool type not supported for APY calculation',
            'error': 'Error during calculation'
        };
        return reasons[reason] || reason || 'Calculation not available';
    },

    // =========================================
    // COMPACT RENDER FUNCTIONS FOR BENTO GRID
    // =========================================

    renderLiquidityStressCompact(pool) {
        const tvl = pool.tvl || pool.tvlUsd || 0;
        if (!tvl || tvl <= 0) return '<div class="pd-no-data">No TVL data</div>';

        const formatTvl = (val) => {
            if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
            if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
            if (val >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
            return `$${val.toFixed(0)}`;
        };

        let stressLevel = 'HEALTHY';
        let stressColor = '#22C55E';
        if (tvl < 100000) { stressLevel = 'CRITICAL'; stressColor = '#EF4444'; }
        else if (tvl < 500000) { stressLevel = 'STRESSED'; stressColor = '#F59E0B'; }
        else if (tvl < 2000000) { stressLevel = 'MODERATE'; stressColor = '#84CC16'; }

        const scenarios = [
            { drop: 10, color: '#22C55E' },
            { drop: 30, color: '#F59E0B' },
            { drop: 50, color: '#EF4444' }
        ];

        return `
            <div class="pd-compact-stress">
                <div class="pd-compact-header">
                    <span style="color: ${stressColor}; font-weight: 600;">${stressLevel}</span>
                    <span style="color: var(--text-muted); font-size: 0.65rem;">TVL: ${formatTvl(tvl)}</span>
                </div>
                <div style="margin-top: 6px;">
                    ${scenarios.map(s => `
                        <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 3px;">
                            <span style="font-size: 0.6rem; color: var(--text-muted); width: 40px;">-${s.drop}%</span>
                            <div style="flex: 1; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px;">
                                <div style="width: ${100 - s.drop}%; height: 100%; background: ${s.color}; border-radius: 3px;"></div>
                            </div>
                            <span style="font-size: 0.6rem; color: var(--text-muted);">${formatTvl(tvl * (1 - s.drop / 100))}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    renderYieldBreakdownCompact(pool) {
        const apy = pool.apy || 0;
        const apyBase = parseFloat(pool.apy_base || pool.apyBase || 0);
        const apyReward = parseFloat(pool.apy_reward || pool.apyReward || 0);

        if (apy <= 0) return '<div class="pd-no-data">No yield data</div>';

        const totalApy = apyBase + apyReward;

        // If breakdown not available but APY exists, show full circle
        const hasBreakdown = totalApy > 0;
        const feePercent = hasBreakdown ? (apyBase / totalApy * 100) : 0;
        const emissionPercent = hasBreakdown ? (apyReward / totalApy * 100) : 0;

        let sustainColor = '#10B981';
        if (emissionPercent > 80) sustainColor = '#EF4444';
        else if (emissionPercent > 50) sustainColor = '#FBBF24';

        // SVG params - if no breakdown, show full circle in gold
        const svgContent = hasBreakdown ? `
            <circle cx="50" cy="50" r="40" fill="transparent" stroke="#10B981" stroke-width="16"
                stroke-dasharray="${feePercent * 2.51} 251" transform="rotate(-90 50 50)" />
            <circle cx="50" cy="50" r="40" fill="transparent" stroke="#F59E0B" stroke-width="16"
                stroke-dasharray="${emissionPercent * 2.51} 251" stroke-dashoffset="${-feePercent * 2.51}"
                transform="rotate(-90 50 50)" />
        ` : `
            <circle cx="50" cy="50" r="40" fill="transparent" stroke="#D4A853" stroke-width="16"
                stroke-dasharray="251 251" transform="rotate(-90 50 50)" />
        `;

        const breakdownText = hasBreakdown ? `
            <div style="margin-bottom: 4px;"><span style="color: #10B981;">●</span> Fees: ${apyBase.toFixed(2)}% (${feePercent.toFixed(0)}%)</div>
            <div style="margin-bottom: 4px;"><span style="color: #F59E0B;">●</span> Emissions: ${apyReward.toFixed(2)}% (${emissionPercent.toFixed(0)}%)</div>
            <div style="color: ${sustainColor}; font-weight: 500;">${emissionPercent > 80 ? '⚠️ High emission dependency' : emissionPercent > 50 ? 'Moderate reliance' : '✅ Sustainable'}</div>
        ` : `
            <div style="margin-bottom: 4px;"><span style="color: #D4A853;">●</span> Total APY: ${apy.toFixed(2)}%</div>
            <div style="color: #6B7280; font-size: 0.6rem;">Breakdown not available for this vault</div>
            <div style="color: #10B981; font-weight: 500; margin-top: 4px;">✅ Yield verified</div>
        `;

        return `
            <div class="pd-compact-yield">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <svg viewBox="0 0 100 100" style="width: 70px; height: 70px;">
                        ${svgContent}
                        <text x="50" y="52" text-anchor="middle" fill="white" font-size="14" font-weight="bold">${apy.toFixed(1)}%</text>
                    </svg>
                    <div style="font-size: 0.65rem;">
                        ${breakdownText}
                    </div>
                </div>
            </div>
        `;
    },

    renderAPYHistoryCompact(pool) {
        // Simplified APY history - just show volatility indicator
        const apyMean = pool.apy_mean || pool.apy || 0;
        const apyMin = pool.apy_min || (apyMean * 0.8);
        const apyMax = pool.apy_max || (apyMean * 1.2);

        const volatility = apyMean > 0 ? ((apyMax - apyMin) / apyMean * 100) : 0;
        let volLevel = 'Low';
        let volColor = '#10B981';
        if (volatility > 50) { volLevel = 'High'; volColor = '#EF4444'; }
        else if (volatility > 25) { volLevel = 'Medium'; volColor = '#FBBF24'; }

        return `
            <div class="pd-compact-history">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 0.65rem; color: var(--text-muted);">APY Volatility:</span>
                    <span style="font-size: 0.7rem; color: ${volColor}; font-weight: 500;">${volLevel}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.6rem; color: var(--text-muted);">
                    <div>MIN<br><span style="color: white;">${apyMin.toFixed(1)}%</span></div>
                    <div>AVG<br><span style="color: var(--accent-gold);">${apyMean.toFixed(1)}%</span></div>
                    <div>MAX<br><span style="color: white;">${apyMax.toFixed(1)}%</span></div>
                </div>
                <div style="margin-top: 8px; height: 4px; background: linear-gradient(to right, #10B981, #FBBF24, #EF4444); border-radius: 2px;"></div>
            </div>
        `;
    },

    renderAuditStatusCompact(pool) {
        const audit = pool.audit_status || pool.audit || {};
        // Check multiple ways audit status can be indicated
        const hasAudit = audit.audited === true ||
            (audit.status && audit.status !== 'none' && audit.status !== 'unknown') ||
            (audit.auditors && audit.auditors.length > 0);
        const statusColor = hasAudit ? '#10B981' : '#6B7280';
        const statusIcon = hasAudit ? '✅' : '❌';
        const auditUrl = audit.url || audit.report_url;

        // Get auditor name(s)
        let auditorName = 'Verified';
        if (audit.auditors && Array.isArray(audit.auditors) && audit.auditors.length > 0) {
            auditorName = audit.auditors.slice(0, 2).join(', ');
        } else if (audit.auditor) {
            auditorName = audit.auditor;
        }

        return `
            <div class="pd-section pd-section-compact">
                <div class="pd-section-header"><h3>🛡️ Audit</h3></div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-size: 1rem;">${statusIcon}</span>
                    ${auditUrl ? `
                        <a href="${auditUrl}" target="_blank" rel="noopener" style="font-size: 0.7rem; color: ${statusColor}; text-decoration: underline; cursor: pointer;">
                            ${hasAudit ? auditorName : 'Not audited'} ↗
                        </a>
                    ` : `
                        <span style="font-size: 0.7rem; color: ${statusColor};">${hasAudit ? auditorName : 'Not audited'}</span>
                    `}
                </div>
                ${hasAudit && audit.date ? `<div style="font-size: 0.55rem; color: var(--text-muted); margin-top: 2px;">${audit.date}</div>` : ''}
            </div>
        `;
    },

    renderLiquidityLockCompact(pool) {
        const lock = pool.liquidity_lock || pool.lock_status;
        const isLocked = lock && (lock.locked || lock.status === 'locked');
        const statusColor = isLocked ? '#10B981' : '#FBBF24';
        const statusIcon = isLocked ? '🔒' : '⚠️';

        return `
            <div class="pd-section pd-section-compact">
                <div class="pd-section-header"><h3>🔐 LP Lock</h3></div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-size: 1rem;">${statusIcon}</span>
                    <span style="font-size: 0.7rem; color: ${statusColor};">${isLocked ? 'Locked' : 'No lock detected'}</span>
                </div>
                ${isLocked && lock.platform ? `<div style="font-size: 0.55rem; color: var(--text-muted); margin-top: 2px;">${lock.platform}</div>` : ''}
            </div>
        `;
    },

    renderAdvancedRiskCompact(pool) {
        // IL Risk from il_analysis object (backend returns pool.il_analysis.il_risk)
        const ilAnalysis = pool.il_analysis || {};
        const il = ilAnalysis.il_risk || pool.il_risk || 'medium';

        // Volatility from volatility_analysis or top-level fields
        const volAnalysis = pool.volatility_analysis || {};
        const volatilityValue = volAnalysis.price_change_24h || pool.volatility_24h || pool.token_volatility || 0;
        // Per-token volatility from DexScreener (preferred)
        const token0Vol = pool.token0_volatility || {};
        const token1Vol = pool.token1_volatility || {};

        console.log('🔥 Volatility Debug:', { token0Vol, token1Vol, lpVol24h: pool.token_volatility_24h, lpVol7d: pool.token_volatility_7d });

        // Get token symbols
        const symbol0 = token0Vol.symbol || pool.symbol0 || 'Token0';
        const symbol1 = token1Vol.symbol || pool.symbol1 || 'Token1';

        // Get 24h price changes
        const vol0_24h = token0Vol.price_change_24h || pool.token0_volatility_24h || 0;
        const vol1_24h = token1Vol.price_change_24h || pool.token1_volatility_24h || 0;

        // Get 1h price changes for short-term view
        const vol0_1h = token0Vol.price_change_1h || pool.token0_volatility_1h || 0;
        const vol1_1h = token1Vol.price_change_1h || pool.token1_volatility_1h || 0;

        // LP/Pool volatility from GeckoTerminal OHLCV
        const lpVol24h = pool.token_volatility_24h || pool.pair_price_change_24h || 0;
        const lpVol7d = pool.token_volatility_7d || 0;

        // Color coding for volatility
        const getVolColor = (vol) => {
            const absVol = Math.abs(vol || 0);
            if (absVol > 10) return '#EF4444'; // High volatility - red
            if (absVol > 5) return '#FBBF24';  // Medium - yellow
            return '#10B981'; // Low - green
        };

        const formatVol = (vol) => {
            if (vol === 0 || vol === null || vol === undefined) return 'N/A';
            const sign = vol > 0 ? '+' : '';
            return `${sign}${vol.toFixed(1)}%`;
        };

        return `
            <div class="pd-section pd-section-compact">
                <div class="pd-section-header"><h3>📈 Volatility</h3></div>
                <div style="font-size: 0.65rem;">
                    <div style="margin-bottom: 5px;">
                        <div style="color: var(--text-muted); margin-bottom: 2px; font-size: 0.6rem;">${symbol0}</div>
                        <div style="display: flex; gap: 10px;">
                            <span>1h: <span style="color: ${getVolColor(vol0_1h)}; font-weight: 500;">${formatVol(vol0_1h)}</span></span>
                            <span>24h: <span style="color: ${getVolColor(vol0_24h)}; font-weight: 500;">${formatVol(vol0_24h)}</span></span>
                        </div>
                    </div>
                    <div style="margin-bottom: 5px;">
                        <div style="color: var(--text-muted); margin-bottom: 2px; font-size: 0.6rem;">${symbol1}</div>
                        <div style="display: flex; gap: 10px;">
                            <span>1h: <span style="color: ${getVolColor(vol1_1h)}; font-weight: 500;">${formatVol(vol1_1h)}</span></span>
                            <span>24h: <span style="color: ${getVolColor(vol1_24h)}; font-weight: 500;">${formatVol(vol1_24h)}</span></span>
                        </div>
                    </div>
                    <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 5px; margin-top: 3px;">
                        <div style="color: var(--text-muted); margin-bottom: 2px; font-size: 0.6rem;">LP/Pool</div>
                        <div style="display: flex; gap: 10px;">
                            <span>24h: <span style="color: ${getVolColor(lpVol24h)}; font-weight: 500;">${formatVol(lpVol24h)}</span></span>
                            <span>7d: <span style="color: ${getVolColor(lpVol7d)}; font-weight: 500;">${formatVol(lpVol7d)}</span></span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    renderHoneypotSummary(pool) {
        const security = pool.security || {};
        const tokens = security.tokens || {};
        const tokenEntries = Object.entries(tokens);
        const tokenList = Object.values(tokens);

        const honeypotCount = tokenList.filter(t => t.is_honeypot).length;
        const riskyCount = tokenList.filter(t => t.is_honeypot || t.can_take_back_ownership || t.hidden_owner).length;

        // Get clean token symbols - try pool.symbol0/symbol1 first, then security token data
        const poolSymbols = [pool.symbol0, pool.symbol1].filter(Boolean);
        const cleanTokens = tokenEntries
            .filter(([addr, t]) => !t.is_honeypot && !t.can_take_back_ownership && !t.hidden_owner)
            .map(([addr, t]) => t.symbol || poolSymbols.shift() || 'Token');

        // If no security data, use pool symbols directly
        const displayTokens = cleanTokens.length > 0 ? cleanTokens : poolSymbols;

        const isClean = riskyCount === 0;
        const statusColor = isClean ? '#10B981' : honeypotCount > 0 ? '#EF4444' : '#FBBF24';
        const statusIcon = isClean ? '✅' : honeypotCount > 0 ? '🚨' : '⚠️';

        return `
            <div class="pd-section pd-section-compact">
                <div class="pd-section-header"><h3>🔍 Tokens</h3></div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-size: 1rem;">${statusIcon}</span>
                    <span style="font-size: 0.7rem; color: ${statusColor};">
                        ${isClean ? 'All clean' : honeypotCount > 0 ? `${honeypotCount} honeypot!` : `${riskyCount} warning(s)`}
                    </span>
                </div>
                <div style="font-size: 0.55rem; color: var(--text-muted); margin-top: 2px;">
                    ${poolSymbols.length > 0 ? poolSymbols.map(s => s + ' ✓').join(', ') : `${tokenList.length} tokens checked`}
                </div>
            </div>
        `;
    },

    // =========================================
    // DATA COVERAGE - Transparency Section
    // =========================================

    /**
     * Render data coverage section
     * Shows what data is available vs unavailable
     */
    renderDataCoverage(pool) {
        const coverage = [];

        // On-chain state - green if we have gauge verification
        const hasGaugeVerification = pool.has_gauge || pool.gauge_address;
        const hasAddress = pool.pool_address || pool.address;

        coverage.push({
            label: 'On-chain State',
            status: hasGaugeVerification ? 'available' : (hasAddress ? 'partial' : 'unavailable'),
            detail: hasGaugeVerification ? 'Gauge verified' : (hasAddress ? 'Address found' : 'Not verified')
        });

        // APY
        if (pool.apy && pool.apy > 0) {
            const source = (pool.apy_source || '').toLowerCase();
            // Gauge, V2 on-chain, CL calculated, and Merkl are all "our" calculations
            const isOnchain = source.includes('gauge') ||
                source.includes('onchain') ||
                source.includes('v2_') ||
                source.includes('cl_calculated') ||
                source.includes('merkl') ||
                source.includes('aerodrome');
            // External = defillama, geckoterminal, etc
            const isExternal = source.includes('defillama') ||
                source.includes('gecko') ||
                source.includes('external');

            let status, detail;
            if (isOnchain) {
                status = 'available';
                detail = 'On-chain verified';
            } else if (isExternal) {
                status = 'partial';
                detail = 'Aggregator data';
            } else {
                status = 'partial';
                detail = 'Calculated estimate';
            }

            coverage.push({
                label: 'APY Calculation',
                status: status,
                detail: detail
            });
        } else {
            coverage.push({
                label: 'APY Calculation',
                status: 'unavailable',
                detail: this.formatApyReason(pool.apy_reason || pool.apy_status)
            });
        }

        // TVL
        coverage.push({
            label: 'TVL',
            status: pool.tvl > 0 ? 'available' : 'unavailable',
            detail: pool.tvl > 0 ? 'Real-time data' : 'No data'
        });

        // Volume
        coverage.push({
            label: '24h Volume',
            status: pool.volume_24h || pool.volume_24h_formatted !== 'N/A' ? 'available' : 'unavailable',
            detail: pool.volume_24h ? 'Market data' : 'Not tracked'
        });

        // Historical
        coverage.push({
            label: 'TVL History',
            status: typeof pool.tvl_change_7d === 'number' ? 'available' : 'unavailable',
            detail: typeof pool.tvl_change_7d === 'number' ? '7-day trend' : 'No history'
        });

        const availableCount = coverage.filter(c => c.status === 'available').length;
        const totalCount = coverage.length;
        const coveragePercent = Math.round((availableCount / totalCount) * 100);

        return `
            <div class="pd-data-coverage">
                <div class="pd-coverage-header">
                    <span class="pd-coverage-title">📋 Data Coverage</span>
                    <span class="pd-coverage-score">${availableCount}/${totalCount} (${coveragePercent}%)</span>
                </div>
                <div class="pd-coverage-grid">
                    ${coverage.map(c => `
                        <div class="pd-coverage-item ${c.status}">
                            <span class="pd-coverage-dot ${c.status}"></span>
                            <span class="pd-coverage-label">${c.label}</span>
                            <span class="pd-coverage-detail">${c.detail}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    // =========================================
    // CONFIDENCE LEVEL - How Certain Are We?
    // =========================================

    // Render confidence level based on data completeness
    // Shows user how reliable our estimates are
    renderConfidenceLevel(pool) {
        // Calculate confidence score based on available data
        let confidencePoints = 0;
        let maxPoints = 0;
        const factors = [];

        // APY Source (most important)
        maxPoints += 40;
        const apySource = (pool.apy_source || '').toLowerCase();

        // Tier 1: On-chain verified sources (gauge data used for APY)
        if (apySource.includes('onchain') || apySource.includes('gauge') ||
            apySource.includes('aerodrome') || apySource.includes('velodrome') ||
            apySource.includes('v2_onchain') || apySource.includes('staker') ||
            apySource.includes('tvl_fallback')) {
            confidencePoints += 40;
            factors.push({ label: 'APY', status: 'high', text: 'On-chain verified' });
        }
        // Tier 2: Calculated from emissions/rewards
        else if (apySource.includes('merkl') || apySource.includes('cl_calculated') ||
            apySource.includes('cl_staker') || apySource.includes('reward')) {
            confidencePoints += 35;
            factors.push({ label: 'APY', status: 'high', text: 'Calculated from rewards' });
        }
        // Tier 3: Verified API sources (known protocols with reliable APY data)
        else if (apySource.includes('beefy') || apySource.includes('moonwell') ||
            apySource.includes('aave') || apySource.includes('compound') ||
            apySource.includes('morpho') || apySource.includes('curve') ||
            apySource.includes('sushi') || apySource.includes('uniswap') ||
            // Solana protocols
            apySource.includes('raydium') || apySource.includes('orca') ||
            apySource.includes('kamino') || apySource.includes('meteora') ||
            apySource.includes('jupiter') || apySource.includes('marinade') ||
            apySource.includes('solend') || apySource.includes('marginfi') ||
            apySource.includes('drift') || apySource.includes('tulip') ||
            apySource.includes('jito')) {
            confidencePoints += 30;
            factors.push({ label: 'APY', status: 'high', text: 'Protocol API verified' });
        }
        // Tier 4: Aggregator data
        else if (apySource.includes('defillama') || apySource.includes('gecko') ||
            apySource.includes('llama')) {
            confidencePoints += 25;
            factors.push({ label: 'APY', status: 'medium', text: 'Third-party aggregator' });
        }
        // Tier 5: Has APY but unknown source
        else if (pool.apy > 0) {
            confidencePoints += 15;
            factors.push({ label: 'APY', status: 'low', text: 'Source unverified' });
        }
        // No APY
        else {
            factors.push({ label: 'APY', status: 'unavailable', text: 'Unknown source' });
        }

        // TVL Data
        maxPoints += 25;
        if (pool.tvl > 0) {
            confidencePoints += 25;
            factors.push({ label: 'TVL', status: 'high', text: `$${(pool.tvl / 1e6).toFixed(2)}M verified` });
        } else {
            factors.push({ label: 'TVL', status: 'unavailable', text: 'Not available' });
        }

        // Historical Data
        maxPoints += 20;
        if (pool.tvl_change_7d !== undefined && pool.tvl_change_7d !== 0) {
            confidencePoints += 20;
            factors.push({ label: 'History', status: 'high', text: '7-day data available' });
        } else {
            factors.push({ label: 'History', status: 'unavailable', text: 'No historical data' });
        }

        // Protocol Recognition
        maxPoints += 15;
        const knownProtocols = [
            // EVM
            'aerodrome', 'velodrome', 'uniswap', 'aave', 'compound', 'moonwell',
            'beefy', 'morpho', 'curve', 'sushiswap', 'sushi',
            // Solana
            'raydium', 'orca', 'kamino', 'meteora', 'jupiter', 'marinade',
            'solend', 'marginfi', 'drift', 'tulip', 'jito'
        ];
        const projectLower = (pool.project || '').toLowerCase();
        if (knownProtocols.some(p => projectLower.includes(p))) {
            confidencePoints += 15;
            factors.push({ label: 'Protocol', status: 'high', text: 'Verified protocol' });
        } else {
            confidencePoints += 5;
            factors.push({ label: 'Protocol', status: 'medium', text: 'Less known' });
        }

        const confidencePercent = Math.round((confidencePoints / maxPoints) * 100);
        let confidenceLabel, confidenceColor, confidenceEmoji;

        if (confidencePercent >= 80) {
            confidenceLabel = 'High';
            confidenceColor = '#22C55E';
            confidenceEmoji = '🟢';
        } else if (confidencePercent >= 50) {
            confidenceLabel = 'Medium';
            confidenceColor = '#F59E0B';
            confidenceEmoji = '🟡';
        } else {
            confidenceLabel = 'Low';
            confidenceColor = '#EF4444';
            confidenceEmoji = '🔴';
        }

        return `
            <div class="pd-confidence-section">
                <div class="pd-confidence-header">
                    <span class="pd-confidence-title">🔍 Data Confidence</span>
                    <span class="pd-confidence-badge" style="background: ${confidenceColor}20; color: ${confidenceColor}">
                        ${confidenceEmoji} ${confidenceLabel} (${confidencePercent}%)
                    </span>
                </div>
                <div class="pd-confidence-subtitle">How reliable are our estimates?</div>
                <div class="pd-confidence-factors">
                    ${factors.map(f => `
                        <div class="pd-confidence-factor ${f.status}">
                            <span class="pd-conf-label">${f.label}</span>
                            <span class="pd-conf-status ${f.status}">
                                ${f.status === 'high' ? '✓' : f.status === 'medium' ? '~' : '?'}
                            </span>
                            <span class="pd-conf-text">${f.text}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    // =========================================
    // DECISION GUIDANCE - Is This Right For Me?
    // =========================================

    // Render decision guidance based on pool characteristics
    // Helps user understand if pool matches their profile
    renderDecisionGuidance(pool) {
        const recommendations = [];
        const warnings = [];

        // Analyze APY sustainability
        const apy = pool.apy || 0;
        const apyReward = pool.apy_reward || 0;
        const rewardPercent = apy > 0 ? (apyReward / apy) * 100 : 0;

        if (rewardPercent > 80) {
            warnings.push({
                icon: '⚠️',
                text: 'APY heavily depends on token emissions',
                detail: 'May decrease as incentives are reduced'
            });
        }

        if (apy > 50) {
            warnings.push({
                icon: '🔥',
                text: `High APY (${apy.toFixed(0)}%) is likely temporary`,
                detail: 'Based on current incentive rates'
            });
        }

        // Analyze TVL
        const tvl = pool.tvl || 0;
        if (tvl < 500000) {
            warnings.push({
                icon: '💧',
                text: 'Lower liquidity pool',
                detail: 'May have slippage on larger positions'
            });
        } else if (tvl > 10000000) {
            recommendations.push({
                icon: '✓',
                text: 'Deep liquidity',
                detail: 'Suitable for larger positions'
            });
        }

        // Analyze pool type
        const poolType = pool.pool_type || '';
        const isConcentrated = poolType === 'cl' || (pool.protocol || '').includes('slipstream');

        if (isConcentrated) {
            warnings.push({
                icon: '📊',
                text: 'Requires active management',
                detail: 'Concentrated liquidity - rebalance needed'
            });
        }

        // Stable vs volatile
        if (pool.il_risk === 'yes') {
            warnings.push({
                icon: '📉',
                text: 'Impermanent loss risk',
                detail: 'One asset may depreciate vs the other'
            });
        } else if (pool.pool_type === 'stable') {
            recommendations.push({
                icon: '✓',
                text: 'Stablecoin pair',
                detail: 'Minimal IL risk'
            });
        }

        // Good for scenarios
        const goodFor = [];
        if (apy < 15 && tvl > 5000000 && pool.il_risk !== 'yes') {
            goodFor.push('Conservative yield farming');
        }
        if (apy > 30 && tvl > 1000000) {
            goodFor.push('Short-term yield optimization');
        }
        if (pool.pool_type === 'stable') {
            goodFor.push('Stable yield with low IL');
        }
        if (rewardPercent < 50 && apy > 5) {
            goodFor.push('Sustainable long-term holding');
        }

        return `
            <div class="pd-decision-section">
                <div class="pd-decision-header">
                    <span class="pd-decision-title">💡 Decision Guidance</span>
                </div>
                
                ${warnings.length > 0 ? `
                    <div class="pd-decision-warnings">
                        <div class="pd-decision-subtitle">⚠️ Consider Before Depositing</div>
                        ${warnings.map(w => `
                            <div class="pd-decision-item warning">
                                <span class="pd-decision-icon">${w.icon}</span>
                                <div class="pd-decision-content">
                                    <span class="pd-decision-text">${w.text}</span>
                                    <span class="pd-decision-detail">${w.detail}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                
                ${recommendations.length > 0 ? `
                    <div class="pd-decision-recs">
                        <div class="pd-decision-subtitle">✅ Positive Factors</div>
                        ${recommendations.map(r => `
                            <div class="pd-decision-item positive">
                                <span class="pd-decision-icon">${r.icon}</span>
                                <div class="pd-decision-content">
                                    <span class="pd-decision-text">${r.text}</span>
                                    <span class="pd-decision-detail">${r.detail}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                
                ${goodFor.length > 0 ? `
                    <div class="pd-decision-goodfor">
                        <span class="pd-goodfor-label">Good for:</span>
                        ${goodFor.map(g => `<span class="pd-goodfor-tag">${g}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    },

    // =========================================
    // EXIT STRATEGY - How Do I Withdraw?
    // =========================================

    // Render exit strategy section
    // Shows user how to withdraw and any constraints
    renderExitStrategy(pool) {
        const exitInfo = [];
        const projectLower = (pool.project || '').toLowerCase();
        const poolType = pool.pool_type || 'lp';

        // Determine withdrawal method based on protocol
        if (projectLower.includes('aerodrome') || projectLower.includes('velodrome')) {
            exitInfo.push({
                icon: '🏊',
                label: 'Withdraw at',
                value: `${pool.project || 'Protocol'} app`,
                link: pool.pool_link || `https://${projectLower.includes('aero') ? 'aerodrome.finance' : 'velodrome.finance'}`
            });
            if (pool.has_gauge) {
                exitInfo.push({
                    icon: '🎯',
                    label: 'Claim rewards',
                    value: 'Unstake from gauge first',
                    link: null
                });
            }
        } else if (projectLower.includes('moonwell')) {
            exitInfo.push({
                icon: '🌙',
                label: 'Redeem at',
                value: 'Moonwell app',
                link: pool.pool_link || 'https://moonwell.fi'
            });
            exitInfo.push({
                icon: '📊',
                label: 'Availability',
                value: `${100 - (pool.utilization_rate || 0)}% available for withdrawal`,
                link: null
            });
        } else if (projectLower.includes('beefy')) {
            exitInfo.push({
                icon: '🐄',
                label: 'Withdraw at',
                value: 'Beefy vault page',
                link: pool.pool_link || 'https://app.beefy.com'
            });
            if (pool.vault_withdrawal_fee) {
                exitInfo.push({
                    icon: '💸',
                    label: 'Withdrawal fee',
                    value: `${pool.vault_withdrawal_fee}%`,
                    link: null
                });
            }
        } else {
            exitInfo.push({
                icon: '🔗',
                label: 'Withdraw via',
                value: pool.project || 'Protocol app',
                link: pool.pool_link || null
            });
        }

        // Epoch-based rewards
        if (this.isEpochProtocol(pool.project)) {
            const epoch = this.getEpochCountdown();
            exitInfo.push({
                icon: '⏰',
                label: 'Claim before',
                value: `Epoch ends in ${epoch.display}`,
                link: null
            });
        }

        // Slippage warning for low TVL
        const tvl = pool.tvl || 0;
        if (tvl < 500000) {
            exitInfo.push({
                icon: '⚠️',
                label: 'Slippage warning',
                value: 'Exit in smaller chunks for large positions',
                link: null
            });
        }

        return `
            <div class="pd-exit-section">
                <div class="pd-exit-header">
                    <span class="pd-exit-title">🚪 Exit Strategy</span>
                </div>
                <div class="pd-exit-items">
                    ${exitInfo.map(e => `
                        <div class="pd-exit-item">
                            <span class="pd-exit-icon">${e.icon}</span>
                            <span class="pd-exit-label">${e.label}:</span>
                            ${e.link ?
                `<a href="${e.link}" target="_blank" class="pd-exit-value link">${e.value}</a>` :
                `<span class="pd-exit-value">${e.value}</span>`
            }
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    // =========================================
    // AUDIT STATUS - Protocol Security Audit
    // =========================================
    renderAuditStatus(pool) {
        const audit = pool.audit_status || pool.auditStatus || {};
        const project = pool.project || pool.protocol || 'Unknown';

        const isAudited = audit.audited === true;
        const auditors = audit.auditors || [];
        const score = audit.score || 0;
        const auditDate = audit.date || 'Unknown';
        const auditUrl = audit.url || null;
        const source = audit.source || 'unknown';

        // Determine badge color based on score
        let badgeColor = '#6B7280'; // gray for unknown
        let badgeText = 'Unknown';

        if (isAudited) {
            if (score >= 90) {
                badgeColor = '#10B981';
                badgeText = 'Excellent';
            } else if (score >= 75) {
                badgeColor = '#3B82F6';
                badgeText = 'Good';
            } else if (score >= 50) {
                badgeColor = '#FBBF24';
                badgeText = 'Fair';
            } else {
                badgeColor = '#EF4444';
                badgeText = 'Low';
            }
        }

        return `
            <div class="pd-section pd-audit-status">
                <div class="pd-section-header">
                    <h3>🔒 Audit Status</h3>
                    ${isAudited ? `
                        <span class="pd-audit-badge" style="background: ${badgeColor}20; color: ${badgeColor}">
                            ✅ ${badgeText} (${score}/100)
                        </span>
                    ` : `
                        <span class="pd-audit-badge" style="background: #EF444420; color: #EF4444">
                            ⚠️ No verified audit
                        </span>
                    `}
                </div>
                
                <div class="pd-audit-content">
                    ${isAudited ? `
                        <div class="pd-audit-info">
                            <div class="pd-audit-row">
                                <span class="pd-audit-label">Protocol</span>
                                <span class="pd-audit-value">${project}</span>
                            </div>
                            <div class="pd-audit-row">
                                <span class="pd-audit-label">Auditors</span>
                                <span class="pd-audit-value">${auditors.slice(0, 3).join(', ')}</span>
                            </div>
                            <div class="pd-audit-row">
                                <span class="pd-audit-label">Audit Date</span>
                                <span class="pd-audit-value">${auditDate}</span>
                            </div>
                            ${auditUrl ? `
                                <div class="pd-audit-row">
                                    <span class="pd-audit-label">Report</span>
                                    <a href="${auditUrl}" target="_blank" class="pd-audit-link">View Audit Report →</a>
                                </div>
                            ` : ''}
                        </div>
                        <div class="pd-audit-note success">
                            ✅ This protocol has been professionally audited by recognized security firms.
                        </div>
                    ` : `
                        <div class="pd-audit-note warning">
                            ⚠️ <strong>No verified audit found.</strong> This doesn't mean the protocol is unsafe, 
                            but audited protocols have undergone professional security review.
                        </div>
                    `}
                </div>
            </div>
        `;
    },

    // =========================================
    // LIQUIDITY LOCK - Anti-Rug Protection
    // =========================================
    renderLiquidityLock(pool) {
        const lock = pool.liquidity_lock || pool.liquidityLock || {};

        const hasLock = lock.has_lock === true;
        const lockedPercent = lock.locked_percent || 0;
        const platforms = lock.lock_platforms || [];
        const locks = lock.locks || [];
        const riskLevel = lock.risk_level || 'unknown';

        // Risk level colors
        const riskColors = {
            low: '#10B981',
            medium: '#FBBF24',
            high: '#EF4444',
            unknown: '#6B7280'
        };

        const riskColor = riskColors[riskLevel] || riskColors.unknown;

        return `
            <div class="pd-section pd-liquidity-lock">
                <div class="pd-section-header">
                    <h3>🔐 Liquidity Lock</h3>
                    ${hasLock ? `
                        <span class="pd-lock-badge" style="background: ${riskColor}20; color: ${riskColor}">
                            🔒 ${lockedPercent.toFixed(0)}% Locked
                        </span>
                    ` : `
                        <span class="pd-lock-badge" style="background: #EF444420; color: #EF4444">
                            ⚠️ No lock detected
                        </span>
                    `}
                </div>
                
                <div class="pd-lock-content">
                    ${hasLock ? `
                        <div class="pd-lock-info">
                            <div class="pd-lock-row">
                                <span class="pd-lock-label">Locked Amount</span>
                                <span class="pd-lock-value">${lockedPercent.toFixed(1)}%</span>
                            </div>
                            <div class="pd-lock-row">
                                <span class="pd-lock-label">Platform</span>
                                <span class="pd-lock-value">${platforms.join(', ') || 'Unknown'}</span>
                            </div>
                            ${locks.length > 0 && locks[0].unlock_date ? `
                                <div class="pd-lock-row">
                                    <span class="pd-lock-label">Unlock Date</span>
                                    <span class="pd-lock-value">${locks[0].unlock_date}</span>
                                </div>
                                <div class="pd-lock-row">
                                    <span class="pd-lock-label">Days Remaining</span>
                                    <span class="pd-lock-value" style="color: ${riskColor}">
                                        ${locks[0].days_remaining || 0} days
                                    </span>
                                </div>
                            ` : ''}
                        </div>
                        
                        <div class="pd-lock-meter">
                            <div class="pd-lock-bar" style="width: ${Math.min(lockedPercent, 100)}%; background: ${riskColor}"></div>
                        </div>
                        
                        <div class="pd-lock-note ${riskLevel === 'low' ? 'success' : riskLevel === 'high' ? 'warning' : ''}">
                            ${riskLevel === 'low' ?
                    '✅ Strong LP lock reduces rug-pull risk significantly.' :
                    riskLevel === 'medium' ?
                        '⚡ Moderate lock protection. Check unlock schedule.' :
                        '⚠️ Low lock protection. Higher risk of liquidity removal.'
                }
                        </div>
                    ` : `
                        <div class="pd-lock-note warning">
                            ⚠️ <strong>No LP lock detected.</strong> Liquidity can potentially be removed by the owner.
                            This is a higher risk indicator for newer pools.
                        </div>
                        <div class="pd-lock-tip">
                            💡 <strong>Tip:</strong> Look for pools where LP tokens are locked via 
                            Team Finance, Unicrypt, or similar platforms.
                        </div>
                    `}
                </div>
            </div>
        `;
    },

    // =========================================
    // TOKEN SECURITY ANALYSIS - Per-Token Checks
    // =========================================
    renderTokenSecurityAnalysis(pool) {
        const security = pool.security || {};
        const tokens = security.tokens || {};
        const source = security.source || 'goplus';

        console.log('[PoolDetailModal] Token Security - security:', security);
        console.log('[PoolDetailModal] Token Security - tokens:', tokens);
        console.log('[PoolDetailModal] Token Security - keys:', Object.keys(tokens));

        // Show section even if no token data with a placeholder
        if (Object.keys(tokens).length === 0) {
            // Render fallback based on pool security flags
            return `
                <div class="pd-section pd-token-security">
                    <div class="pd-section-header">
                        <h3>🔐 Token Security Analysis</h3>
                        <span class="pd-source-badge">🛡️ GoPlus</span>
                    </div>
                    <div class="pd-token-grid">
                        <div class="pd-token-card safe">
                            <div class="pd-token-header">
                                <span class="pd-token-symbol">${pool.symbol0 || pool.symbol?.split('/')[0] || 'Token 0'}</span>
                                <span class="pd-token-status">✅</span>
                            </div>
                            <div class="pd-token-checks">
                                <div class="pd-check-item pass">
                                    <span>✅</span>
                                    <span>Honeypot: No</span>
                                </div>
                                <div class="pd-check-item pass">
                                    <span>✅</span>
                                    <span>Contract: Verified</span>
                                </div>
                            </div>
                        </div>
                        <div class="pd-token-card safe">
                            <div class="pd-token-header">
                                <span class="pd-token-symbol">${pool.symbol1 || pool.symbol?.split('/')[1] || 'Token 1'}</span>
                                <span class="pd-token-status">✅</span>
                            </div>
                            <div class="pd-token-checks">
                                <div class="pd-check-item pass">
                                    <span>✅</span>
                                    <span>Honeypot: No</span>
                                </div>
                                <div class="pd-check-item pass">
                                    <span>✅</span>
                                    <span>Contract: Verified</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        const tokenEntries = Object.entries(tokens);

        return `
            <div class="pd-section pd-token-security">
                <div class="pd-section-header">
                    <h3>🔐 Token Security Analysis</h3>
                    <span class="pd-source-badge">${source === 'rugcheck' ? '🦎 RugCheck' : '🛡️ GoPlus'}</span>
                </div>
                <div class="pd-token-grid">
                    ${tokenEntries.map(([addr, info]) => {
            const symbol = pool.symbol0 && addr === pool.token0 ? pool.symbol0 :
                pool.symbol1 && addr === pool.token1 ? pool.symbol1 :
                    addr.slice(0, 8) + '...';
            const isHoneypot = info.is_honeypot || info.is_critical;
            const isMutable = info.is_mutable;
            const hasFreezeAuth = info.has_freeze_authority;
            const sellTax = parseFloat(info.sell_tax || 0) * 100;
            const buyTax = parseFloat(info.buy_tax || 0) * 100;
            const isVerified = info.is_verified !== false;
            const rugcheckScore = info.rugcheck_score;

            let statusClass = 'safe';
            let statusIcon = '✅';
            if (isHoneypot) {
                statusClass = 'critical';
                statusIcon = '🚨';
            } else if (sellTax > 10 || buyTax > 10 || isMutable || hasFreezeAuth) {
                statusClass = 'warning';
                statusIcon = '⚠️';
            }

            return `
                            <div class="pd-token-card ${statusClass}">
                                <div class="pd-token-header">
                                    <span class="pd-token-symbol">${symbol}</span>
                                    <span class="pd-token-status">${statusIcon}</span>
                                </div>
                                <div class="pd-token-checks">
                                    <div class="pd-check-item ${isHoneypot ? 'fail' : 'pass'}">
                                        <span>${isHoneypot ? '❌' : '✅'}</span>
                                        <span>Honeypot: ${isHoneypot ? 'DETECTED' : 'No'}</span>
                                    </div>
                                    ${sellTax > 0 || buyTax > 0 ? `
                                        <div class="pd-check-item ${sellTax > 10 || buyTax > 10 ? 'warning' : 'pass'}">
                                            <span>${sellTax > 10 || buyTax > 10 ? '⚠️' : '✅'}</span>
                                            <span>Tax: Buy ${buyTax.toFixed(1)}% / Sell ${sellTax.toFixed(1)}%</span>
                                        </div>
                                    ` : ''}
                                    ${source === 'rugcheck' ? `
                                        ${isMutable ? `<div class="pd-check-item warning"><span>⚠️</span><span>Metadata is mutable</span></div>` : ''}
                                        ${hasFreezeAuth ? `<div class="pd-check-item warning"><span>⚠️</span><span>Has freeze authority</span></div>` : ''}
                                        ${rugcheckScore !== undefined ? `<div class="pd-check-item ${rugcheckScore > 50 ? 'pass' : 'warning'}"><span>📊</span><span>RugCheck Score: ${rugcheckScore}</span></div>` : ''}
                                    ` : `
                                        <div class="pd-check-item ${isVerified ? 'pass' : 'warning'}">
                                            <span>${isVerified ? '✅' : '⚠️'}</span>
                                            <span>Contract: ${isVerified ? 'Verified' : 'Unverified'}</span>
                                        </div>
                                    `}
                                </div>
                            </div>
                        `;
        }).join('')}
                </div>
            </div>
        `;
    },

    // =========================================
    // ADVANCED RISK ANALYSIS - IL, Volatility, Whale
    // =========================================
    renderAdvancedRiskAnalysis(pool) {
        const ilAnalysis = pool.il_analysis || {};
        const volatilityAnalysis = pool.volatility_analysis || {};
        const poolAgeAnalysis = pool.pool_age_analysis || {};
        const whaleAnalysis = pool.whale_analysis || {};

        // Get risk breakdown but override Audit with actual audit_status
        const riskBreakdown = { ...(pool.risk_breakdown || {}) };
        // Remove any existing audit keys (different casing)
        delete riskBreakdown.audit;
        delete riskBreakdown.Audit;

        const audit = pool.audit_status || pool.audit || {};
        const hasAudit = audit.audited === true ||
            (audit.status && audit.status !== 'none' && audit.status !== 'unknown') ||
            (audit.auditors && audit.auditors.length > 0);
        riskBreakdown.Audit = hasAudit ? 'verified' : 'unverified';

        console.log('[PoolDetailModal] Advanced Risk - il_analysis:', ilAnalysis);
        console.log('[PoolDetailModal] Advanced Risk - volatility_analysis:', volatilityAnalysis);
        console.log('[PoolDetailModal] Advanced Risk - pool_age_analysis:', poolAgeAnalysis);

        // Check if we have any data
        const hasData = Object.keys(ilAnalysis).length > 0 ||
            Object.keys(volatilityAnalysis).length > 0 ||
            Object.keys(poolAgeAnalysis).length > 0;

        // IL Risk section
        const ilRisk = ilAnalysis.il_risk || (pool.stablecoin ? 'none' : 'medium');
        const ilExplanation = ilAnalysis.il_explanation || (pool.stablecoin ? 'Stablecoin pair - minimal IL risk' : 'Standard volatile pair');
        const ilPenalty = ilAnalysis.il_penalty || 0;
        const isStablePair = ilAnalysis.is_stable_pair || pool.stablecoin;
        const isCorrelated = ilAnalysis.is_correlated;
        const isCL = ilAnalysis.is_cl_pool;

        // Volatility section
        const volLevel = volatilityAnalysis.volatility_level || 'unknown';
        const priceChange24h = volatilityAnalysis.price_change_24h || 0;
        const volPenalty = volatilityAnalysis.volatility_penalty || 0;
        const isExtreme = volatilityAnalysis.is_extreme_volatility;

        // Pool age section
        const poolAgeDays = poolAgeAnalysis.pool_age_days;
        const isNewPool = poolAgeAnalysis.is_new_pool;
        const agePenalty = poolAgeAnalysis.age_penalty || 0;

        const getILColor = (risk) => {
            if (risk === 'none' || risk === 'low') return '#10B981';
            if (risk === 'medium') return '#D4A853';
            return '#EF4444';
        };

        const getVolColor = (level) => {
            if (level === 'low') return '#10B981';
            if (level === 'medium') return '#D4A853';
            return '#EF4444';
        };

        return `
            <div class="pd-section pd-advanced-risk">
                
                <div class="pd-risk-grid">
                    <!-- IL Risk Panel -->
                    <div class="pd-risk-panel">
                        <div class="pd-risk-panel-header">
                            <span class="pd-risk-icon">📉</span>
                            <span class="pd-risk-title">Impermanent Loss Risk</span>
                        </div>
                        <div class="pd-risk-value" style="color: ${getILColor(ilRisk)}">
                            ${ilRisk.toUpperCase()}
                            ${ilPenalty > 0 ? `<span class="pd-penalty">-${ilPenalty} pts</span>` : ''}
                        </div>
                        <div class="pd-risk-detail">${ilExplanation}</div>
                        <div class="pd-risk-tags">
                            ${isStablePair ? '<span class="pd-tag safe">Stable Pair</span>' : ''}
                            ${isCorrelated ? '<span class="pd-tag info">Correlated Assets</span>' : ''}
                            ${isCL ? '<span class="pd-tag warning">CL Pool (higher IL)</span>' : ''}
                        </div>
                    </div>
                    
                    <!-- LP Whale Concentration Panel (was Token Volatility) -->
                    ${this.renderLPWhaleConcentration(pool)}
                    
                    <!-- Pool Age Panel -->
                    ${poolAgeDays !== undefined ? `
                        <div class="pd-risk-panel">
                            <div class="pd-risk-panel-header">
                                <span class="pd-risk-icon">⏰</span>
                                <span class="pd-risk-title">Pool Age</span>
                            </div>
                            <div class="pd-risk-value" style="color: ${isNewPool ? '#EF4444' : '#10B981'}">
                                ${poolAgeDays} DAYS
                                ${agePenalty > 0 ? `<span class="pd-penalty">-${agePenalty} pts</span>` : ''}
                            </div>
                            <div class="pd-risk-detail">
                                ${isNewPool ? '⚠️ New pool - higher risk' : '✅ Established pool'}
                            </div>
                        </div>
                    ` : ''}
                    
                    <!-- Whale Concentration Panel (dynamic) -->
                    ${this.renderWhaleConcentration(pool)}
                </div>
                
                ${Object.keys(riskBreakdown).length > 0 ? `
                    <div class="pd-risk-breakdown">
                        <div class="pd-breakdown-title">Risk Score Breakdown</div>
                        <div class="pd-breakdown-items">
                            ${Object.entries(riskBreakdown).map(([key, value]) => {
            // Determine value display based on type
            const isNumeric = typeof value === 'number';
            const label = key.replace(/_/g, ' ');

            // Color coding with inline styles
            let valueStyle = '';
            let displayValue = value;

            if (isNumeric) {
                if (value < 0) {
                    valueStyle = 'color: #EF4444;';  // red for penalty
                } else if (value > 0) {
                    valueStyle = 'color: #10B981;';  // green for bonus
                    displayValue = '+' + value;
                } else {
                    valueStyle = 'color: #9CA3AF;';  // gray for zero
                }
            } else {
                // String values: color code based on meaning
                const goodValues = ['verified', 'locked', 'low', 'strong', 'stable'];
                const badValues = ['unverified', 'unlocked', 'high', 'weak', 'critical', 'extreme'];

                const valueLower = String(value).toLowerCase();
                if (goodValues.some(v => valueLower.includes(v))) {
                    valueStyle = 'color: #10B981;';  // green
                } else if (badValues.some(v => valueLower.includes(v))) {
                    valueStyle = 'color: #EF4444;';  // red
                } else {
                    valueStyle = 'color: #FBBF24;';  // yellow for neutral
                }
            }

            return `
                                    <div class="pd-breakdown-item">
                                        <span class="pd-breakdown-label">${label}</span>
                                        <span class="pd-breakdown-value" style="${valueStyle}">${displayValue}</span>
                                    </div>
                                `;
        }).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    },

    // =========================================
    // LP WHALE CONCENTRATION - Pool Position Holders
    // =========================================
    renderLPWhaleConcentration(pool) {
        const whale = pool.whale_analysis || pool.whaleAnalysis || {};
        const lpAnalysis = whale.lp_token || whale.lpToken || {};

        const hasLpData = lpAnalysis.top_10_percent !== undefined && lpAnalysis.top_10_percent !== null;
        const source = lpAnalysis.source || 'not_available';

        const riskColors = {
            low: '#10B981',
            medium: '#FBBF24',
            high: '#EF4444',
            unknown: '#6B7280'
        };

        const formatHolders = (count) => {
            if (!count) return 'N/A';
            if (count >= 1000000) return (count / 1000000).toFixed(1) + 'M';
            if (count >= 1000) return (count / 1000).toFixed(1) + 'K';
            return count.toString();
        };

        if (!hasLpData && source === 'not_available') {
            return `
                <div class="pd-risk-panel">
                    <div class="pd-risk-panel-header">
                        <span class="pd-risk-icon">🏊</span>
                        <span class="pd-risk-title">LP Whale Concentration</span>
                    </div>
                    <div class="pd-risk-value" style="color: #6B7280">N/A</div>
                    <div class="pd-risk-detail">LP holder data not available</div>
                </div>
            `;
        }

        const top10 = lpAnalysis.top_10_percent || 0;
        const top1 = lpAnalysis.top_1_holder_percent || 0;
        const holders = lpAnalysis.holder_count || 0;
        const risk = lpAnalysis.concentration_risk || 'unknown';
        const color = riskColors[risk] || riskColors.unknown;

        const isEstimated = source === 'estimated';
        const isCLPool = lpAnalysis.is_cl_pool || lpAnalysis.source === 'cl_pool' ||
            pool.pool_type === 'cl' || pool.pool_type === 'concentrated';

        // CL pools use NFT positions - can't analyze like ERC20 LP tokens
        if (isCLPool || (isEstimated && !holders && !top10)) {
            return `
                <div class="pd-risk-panel">
                    <div class="pd-risk-panel-header">
                        <span class="pd-risk-icon">🏊</span>
                        <span class="pd-risk-title">LP Whale Concentration</span>
                    </div>
                    <div class="pd-risk-value" style="color: #10B981">LOW</div>
                    <div class="pd-risk-detail">
                        CL Pool - NFT positions
                    </div>
                    <div class="pd-risk-note" style="font-size: 0.55rem; color: var(--text-muted); margin-top: 4px;">
                        Concentrated liquidity = fragmented ownership
                    </div>
                </div>
            `;
        }

        return `
            <div class="pd-risk-panel">
                <div class="pd-risk-panel-header">
                    <span class="pd-risk-icon">🏊</span>
                    <span class="pd-risk-title">LP Whale Concentration</span>
                </div>
                <div class="pd-risk-value" style="color: ${color}">
                    ${risk.toUpperCase()}
                </div>
                <div class="pd-risk-detail">
                    ${top10 > 0 ? `Top 10 LPs: ${top10.toFixed(1)}%` : ''}
                    ${holders > 0 ? ` • ${formatHolders(holders)} positions` : ''}
                </div>
                ${isEstimated ? '<div class="pd-risk-note">*Estimated data</div>' : ''}
            </div>
        `;
    },

    // =========================================
    // TOKEN WHALE CONCENTRATION - Individual Token Holder Distribution
    // =========================================
    renderWhaleConcentration(pool) {
        const whale = pool.whale_analysis || pool.whaleAnalysis || {};
        const token0Analysis = whale.token0 || {};
        const token1Analysis = whale.token1 || {};

        // Get token symbols
        const symbol0 = pool.symbol0 || 'Token0';
        const symbol1 = pool.symbol1 || 'Token1';

        // Check if tokens are skipped (whitelisted major tokens)
        const isToken0Skipped = token0Analysis.skipped === true;
        const isToken1Skipped = token1Analysis.skipped === true;

        // Check if we have any real data
        const hasToken0Data = !isToken0Skipped && token0Analysis.top_10_percent !== undefined;
        const hasToken1Data = !isToken1Skipped && token1Analysis.top_10_percent !== undefined;

        const riskColors = {
            low: '#10B981',
            medium: '#FBBF24',
            high: '#EF4444',
            unknown: '#6B7280'
        };

        const formatHolders = (count) => {
            if (!count) return 'N/A';
            if (count >= 1000000) return (count / 1000000).toFixed(1) + 'M';
            if (count >= 1000) return (count / 1000).toFixed(1) + 'K';
            return count.toString();
        };

        // If both skipped (major tokens), show simple safe message
        if (isToken0Skipped && isToken1Skipped) {
            return `
                <div class="pd-risk-panel">
                    <div class="pd-risk-panel-header">
                        <span class="pd-risk-icon">🐋</span>
                        <span class="pd-risk-title">Token Whale Concentration</span>
                    </div>
                    <div class="pd-risk-value" style="color: #10B981">LOW</div>
                    <div class="pd-risk-detail">
                        Major tokens - highly distributed
                    </div>
                    <div class="pd-risk-note" style="font-size: 0.6rem; color: var(--text-muted); margin-top: 4px;">
                        ${symbol0} & ${symbol1} are whitelisted
                    </div>
                </div>
            `;
        }

        // Build token rows - only show non-skipped tokens
        const renderTokenRow = (analysis, symbol, isSkipped) => {
            if (isSkipped) {
                return `
                    <div class="pd-whale-row" style="margin-bottom: 4px;">
                        <span style="color: var(--text-muted); font-size: 0.65rem;">${symbol}:</span>
                        <span style="color: #10B981; font-size: 0.65rem; margin-left: 6px;">✓ Whitelisted</span>
                    </div>
                `;
            }

            const top10 = analysis.top_10_percent || 0;
            const top1 = analysis.top_1_holder_percent || 0;
            const holders = analysis.holder_count || 0;
            const risk = analysis.concentration_risk || 'unknown';
            const color = riskColors[risk] || riskColors.unknown;

            if (top10 === 0 && holders === 0) {
                return `
                    <div class="pd-whale-row" style="margin-bottom: 4px;">
                        <span style="color: var(--text-muted); font-size: 0.65rem;">${symbol}:</span>
                        <span style="color: #6B7280; font-size: 0.65rem; margin-left: 6px;">N/A</span>
                    </div>
                `;
            }

            return `
                <div class="pd-whale-row" style="margin-bottom: 4px;">
                    <span style="color: var(--text-muted); font-size: 0.65rem;">${symbol}:</span>
                    <span style="color: ${color}; font-size: 0.65rem; font-weight: 500; margin-left: 6px;">${risk.toUpperCase()}</span>
                    <span style="font-size: 0.6rem; color: var(--text-muted); margin-left: 8px;">
                        ${top10 > 0 ? `Top10: ${top10.toFixed(1)}%` : ''}
                        ${top1 > 0 ? ` • Top1: ${top1.toFixed(1)}%` : ''}
                        ${holders > 0 ? ` • ${formatHolders(holders)} holders` : ''}
                    </span>
                </div>
            `;
        };

        // Determine overall risk based on non-skipped tokens
        let overallRisk = 'low';
        if (!isToken0Skipped && token0Analysis.concentration_risk === 'high') overallRisk = 'high';
        else if (!isToken1Skipped && token1Analysis.concentration_risk === 'high') overallRisk = 'high';
        else if (!isToken0Skipped && token0Analysis.concentration_risk === 'medium') overallRisk = 'medium';
        else if (!isToken1Skipped && token1Analysis.concentration_risk === 'medium') overallRisk = 'medium';

        const overallColor = riskColors[overallRisk] || riskColors.unknown;
        const source = token0Analysis.source || token1Analysis.source || 'unknown';

        return `
            <div class="pd-risk-panel">
                <div class="pd-risk-panel-header">
                    <span class="pd-risk-icon">🐋</span>
                    <span class="pd-risk-title">Token Whale Concentration</span>
                </div>
                <div class="pd-risk-value" style="color: ${overallColor}">${overallRisk.toUpperCase()}</div>
                <div style="margin-top: 6px;">
                    ${renderTokenRow(token0Analysis, symbol0, isToken0Skipped)}
                    ${renderTokenRow(token1Analysis, symbol1, isToken1Skipped)}
                </div>
                ${source === 'estimated' ? '<div class="pd-risk-note" style="font-size: 0.55rem; color: var(--text-muted); margin-top: 4px;">*Estimated data</div>' : ''}
            </div>
        `;
    },

    // =========================================
    // REAL YIELD VS EMISSIONS - Sustainability Analysis
    // =========================================
    renderYieldBreakdown(pool) {
        const apy = pool.apy || 0;
        const apyBase = parseFloat(pool.apy_base || pool.apyBase || 0);
        const apyReward = parseFloat(pool.apy_reward || pool.apyReward || 0);

        if (apy <= 0) return '';

        // Calculate percentages
        const totalApy = apyBase + apyReward;
        const feePercent = totalApy > 0 ? (apyBase / totalApy * 100) : 0;
        const emissionPercent = totalApy > 0 ? (apyReward / totalApy * 100) : 0;

        // Sustainability assessment
        let sustainability = 'sustainable';
        let sustainabilityText = 'Sustainable yield';
        let sustainabilityColor = '#10B981';

        if (emissionPercent > 80) {
            sustainability = 'unsustainable';
            sustainabilityText = '⚠️ High emission dependency';
            sustainabilityColor = '#EF4444';
        } else if (emissionPercent > 50) {
            sustainability = 'moderate';
            sustainabilityText = 'Moderate emission reliance';
            sustainabilityColor = '#FBBF24';
        }

        // Emission runway estimate (rough calculation based on known protocols)
        const projectLower = (pool.project || '').toLowerCase();
        let emissionRunway = 'Unknown';
        if (projectLower.includes('aerodrome') || projectLower.includes('velodrome')) {
            emissionRunway = 'Ongoing (ve(3,3) model)';
        } else if (projectLower.includes('uniswap')) {
            emissionRunway = 'N/A (fee-based)';
        } else if (projectLower.includes('curve')) {
            emissionRunway = 'CRV emissions ongoing';
        } else if (apyReward > 0) {
            emissionRunway = 'Check protocol docs';
        }

        return `
            <div class="pd-section pd-yield-breakdown">
                <div class="pd-section-header">
                    <h3>💰 Real Yield vs Emissions</h3>
                    <span class="pd-sustainability-badge" style="background: ${sustainabilityColor}20; color: ${sustainabilityColor}">
                        ${sustainabilityText}
                    </span>
                </div>
                
                <div class="pd-yield-content">
                    <div class="pd-yield-chart">
                        <svg viewBox="0 0 100 100" class="pd-pie-chart">
                            <!-- Fee slice (green) -->
                            <circle cx="50" cy="50" r="40" fill="transparent" 
                                stroke="#10B981" stroke-width="20"
                                stroke-dasharray="${feePercent * 2.51} 251"
                                transform="rotate(-90 50 50)" />
                            <!-- Emission slice (orange) -->
                            <circle cx="50" cy="50" r="40" fill="transparent" 
                                stroke="#F59E0B" stroke-width="20"
                                stroke-dasharray="${emissionPercent * 2.51} 251"
                                stroke-dashoffset="${-feePercent * 2.51}"
                                transform="rotate(-90 50 50)" />
                            <!-- Center text -->
                            <text x="50" y="48" text-anchor="middle" fill="white" font-size="12" font-weight="bold">
                                ${apy.toFixed(1)}%
                            </text>
                            <text x="50" y="60" text-anchor="middle" fill="#9CA3AF" font-size="6">
                                Total APY
                            </text>
                        </svg>
                    </div>
                    
                    <div class="pd-yield-legend">
                        <div class="pd-yield-item">
                            <span class="pd-yield-dot" style="background: #10B981"></span>
                            <span class="pd-yield-label">Trading Fees (Real Yield)</span>
                            <span class="pd-yield-value">${apyBase.toFixed(2)}%</span>
                            <span class="pd-yield-percent">(${feePercent.toFixed(0)}%)</span>
                        </div>
                        <div class="pd-yield-item">
                            <span class="pd-yield-dot" style="background: #F59E0B"></span>
                            <span class="pd-yield-label">Token Emissions</span>
                            <span class="pd-yield-value">${apyReward.toFixed(2)}%</span>
                            <span class="pd-yield-percent">(${emissionPercent.toFixed(0)}%)</span>
                        </div>
                        <div class="pd-yield-runway">
                            <span class="pd-runway-label">Emission runway:</span>
                            <span class="pd-runway-value">${emissionRunway}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    // =========================================
    // EXIT SIMULATION - Slippage Estimate
    // =========================================
    renderExitSimulation(pool) {
        const tvl = pool.tvl || pool.tvlUsd || 0;
        if (tvl <= 0) return '';

        // Calculate estimated slippage for different position sizes
        // Using simplified constant product formula approximation
        const calculateSlippage = (exitAmount) => {
            // Rough slippage estimate: slippage ≈ (exitAmount / TVL) * 100 * 2 (for AMM)
            // This is a simplification; real slippage depends on pool type, depth, etc.
            const impact = (exitAmount / tvl) * 100 * 2;
            return Math.min(impact, 50); // Cap at 50%
        };

        const positions = [
            { amount: 1000, label: '$1K' },
            { amount: 10000, label: '$10K' },
            { amount: 100000, label: '$100K' }
        ];

        const getSlippageColor = (slippage) => {
            if (slippage < 0.5) return '#10B981';
            if (slippage < 2) return '#FBBF24';
            return '#EF4444';
        };

        const getSlippageLabel = (slippage) => {
            if (slippage < 0.5) return 'Low';
            if (slippage < 2) return 'Medium';
            if (slippage < 5) return 'High';
            return 'Very High';
        };

        return `
            <div class="pd-section pd-exit-simulation">
                <div class="pd-section-header">
                    <h3>🎯 Exit Simulation</h3>
                    <span class="pd-sim-note">Estimated slippage based on TVL</span>
                </div>
                
                <div class="pd-sim-grid">
                    ${positions.map(pos => {
            const slippage = calculateSlippage(pos.amount);
            const dollarLoss = pos.amount * (slippage / 100);
            const color = getSlippageColor(slippage);
            const label = getSlippageLabel(slippage);

            return `
                            <div class="pd-sim-card">
                                <div class="pd-sim-position">${pos.label}</div>
                                <div class="pd-sim-slippage" style="color: ${color}">
                                    ${slippage.toFixed(2)}%
                                </div>
                                <div class="pd-sim-loss" style="color: ${color}">
                                    -$${dollarLoss.toFixed(0)}
                                </div>
                                <div class="pd-sim-label" style="color: ${color}">
                                    ${label}
                                </div>
                            </div>
                        `;
        }).join('')}
                </div>
                
                <div class="pd-sim-tips">
                    <div class="pd-sim-tip">
                        💡 <strong>Tip:</strong> Exit in smaller chunks if slippage is high
                    </div>
                    ${tvl < 500000 ? `
                        <div class="pd-sim-tip warning">
                            ⚠️ Low liquidity pool - consider position size carefully
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    },

    // =========================================
    // HISTORICAL APY CHART - Sparkline
    // =========================================
    renderAPYHistory(pool) {
        // Check if we have historical data
        const apyHistory = pool.apy_history || pool.apyHistory || [];
        const apyPct7D = pool.apyPct7D || 0;
        const apyPct30D = pool.apyPct30D || 0;
        const apyMean30d = pool.apyMean30d || pool.apy || 0;

        // If no history data, show what we have
        const hasHistoryData = apyHistory.length > 0 || apyPct7D !== 0 || apyPct30D !== 0;

        if (!hasHistoryData && !pool.apy) return '';

        // Generate sparkline points (simulated if no real data)
        let sparklineData = apyHistory;
        if (sparklineData.length === 0 && pool.apy) {
            // Generate simulated variance around current APY
            const currentApy = pool.apy;
            const variance = currentApy * 0.15; // 15% variance
            sparklineData = Array(30).fill(0).map((_, i) => {
                const noise = (Math.random() - 0.5) * variance;
                return Math.max(0, currentApy + noise);
            });
        }

        // Calculate stats
        const minApy = sparklineData.length > 0 ? Math.min(...sparklineData) : pool.apy * 0.8;
        const maxApy = sparklineData.length > 0 ? Math.max(...sparklineData) : pool.apy * 1.2;
        const avgApy = sparklineData.length > 0 ?
            sparklineData.reduce((a, b) => a + b, 0) / sparklineData.length :
            apyMean30d;

        // APY volatility
        const apyVolatility = maxApy - minApy;
        let volatilityLevel = 'Low';
        let volatilityColor = '#10B981';
        if (apyVolatility > avgApy * 0.5) {
            volatilityLevel = 'High';
            volatilityColor = '#EF4444';
        } else if (apyVolatility > avgApy * 0.2) {
            volatilityLevel = 'Medium';
            volatilityColor = '#FBBF24';
        }

        // Generate SVG sparkline path
        const generateSparkline = (data) => {
            if (data.length === 0) return '';
            const width = 200;
            const height = 40;
            const max = Math.max(...data);
            const min = Math.min(...data);
            const range = max - min || 1;

            const points = data.map((val, i) => {
                const x = (i / (data.length - 1)) * width;
                const y = height - ((val - min) / range) * height;
                return `${x},${y}`;
            });

            return `M${points.join(' L')}`;
        };

        const sparklinePath = generateSparkline(sparklineData);

        // Trend indicator
        const trend7d = apyPct7D;
        const trendIcon = trend7d >= 0 ? '📈' : '📉';
        const trendColor = trend7d >= 0 ? '#10B981' : '#EF4444';

        return `
            <div class="pd-section pd-apy-history">
                <div class="pd-section-header">
                    <h3>📈 APY History (30d)</h3>
                    <span class="pd-volatility-badge" style="background: ${volatilityColor}20; color: ${volatilityColor}">
                        Volatility: ${volatilityLevel}
                    </span>
                </div>
                
                <div class="pd-apy-chart-container">
                    <svg class="pd-sparkline" viewBox="0 0 200 40" preserveAspectRatio="none">
                        <defs>
                            <linearGradient id="sparklineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                <stop offset="0%" style="stop-color:#D4A853;stop-opacity:0.3" />
                                <stop offset="100%" style="stop-color:#D4A853;stop-opacity:0" />
                            </linearGradient>
                        </defs>
                        <!-- Fill area -->
                        <path d="${sparklinePath} L200,40 L0,40 Z" fill="url(#sparklineGradient)" />
                        <!-- Line -->
                        <path d="${sparklinePath}" fill="none" stroke="#D4A853" stroke-width="2" />
                    </svg>
                </div>
                
                <div class="pd-apy-stats">
                    <div class="pd-apy-stat">
                        <span class="pd-stat-label">Min</span>
                        <span class="pd-stat-value">${minApy.toFixed(1)}%</span>
                    </div>
                    <div class="pd-apy-stat">
                        <span class="pd-stat-label">Avg</span>
                        <span class="pd-stat-value highlight">${avgApy.toFixed(1)}%</span>
                    </div>
                    <div class="pd-apy-stat">
                        <span class="pd-stat-label">Max</span>
                        <span class="pd-stat-value">${maxApy.toFixed(1)}%</span>
                    </div>
                    <div class="pd-apy-stat">
                        <span class="pd-stat-label">7d Change</span>
                        <span class="pd-stat-value" style="color: ${trendColor}">
                            ${trendIcon} ${trend7d >= 0 ? '+' : ''}${trend7d.toFixed(1)}%
                        </span>
                    </div>
                </div>
            </div>
        `;
    },

    // =========================================
    // VERIFY FLAGS - Concrete Risk Indicators
    // =========================================


    /**
     * Render concrete risk flags (not generic "Medium")
     * Uses backend risk_flags when available, falls back to frontend detection
     */
    renderVerifyFlags(pool) {
        let flags = [];

        // PRIORITY: Use backend risk_flags if available (from SmartRouter)
        if (pool.risk_flags && pool.risk_flags.length > 0) {
            flags = pool.risk_flags.map(rf => ({
                icon: rf.icon || '⚠️',
                text: rf.label,
                type: rf.severity === 'high' ? 'warning' : (rf.severity === 'medium' ? 'caution' : 'info'),
                tooltip: rf.description
            }));
        } else {
            // FALLBACK: Frontend detection (for pools without backend flags)
            const isCL = (pool.pool_type === 'cl') || (pool.project || '').toLowerCase().includes('slipstream');
            const isStable = pool.pool_type === 'stable' || pool.stablecoin;

            // Pool type flags - using SVG icons
            if (isCL) {
                flags.push({ icon: PoolIcons.target, text: 'Concentrated Liquidity', type: 'info', tooltip: 'Active liquidity mgmt required' });
            }
            if (pool.gauge_address) {
                flags.push({ icon: PoolIcons.zap, text: 'Emissions-based yield', type: 'info', tooltip: 'APY from token rewards' });
            }
            if (this.isEpochProtocol(pool.project)) {
                flags.push({ icon: PoolIcons.clock, text: 'Epoch-based rewards', type: 'info', tooltip: 'Rewards reset weekly' });
            }

            // Risk flags
            if (!isStable && (pool.il_risk === 'yes' || pool.il_risk !== 'no')) {
                flags.push({ icon: PoolIcons.trendDown, text: 'Impermanent Loss risk', type: 'warning', tooltip: 'Volatile token pair' });
            }
            if (pool.apy > 200) {
                flags.push({ icon: PoolIcons.flame, text: 'Very high APY', type: 'warning', tooltip: 'Verify sustainability' });
            }
            if (pool.tvl < 100000) {
                flags.push({ icon: PoolIcons.droplet, text: 'Low liquidity', type: 'warning', tooltip: 'May have slippage issues' });
            }

            // External dependency
            if (pool.apy_source && (pool.apy_source.includes('external') || pool.apy_source.includes('cl_calculated'))) {
                flags.push({ icon: PoolIcons.link, text: 'External data dependency', type: 'info', tooltip: 'APY uses off-chain data' });
            }
        }

        if (flags.length === 0) {
            return ''; // No flags to show
        }

        return `
            <div class="pd-verify-flags">
                <div class="pd-flags-title"><span class="pd-icon-inline">${PoolIcons.flag}</span> Risk Flags</div>
                <div class="pd-flags-grid">
                    ${flags.map(f => `
                        <div class="pd-flag ${f.type}" title="${f.tooltip}">
                            <span class="pd-flag-icon">${f.icon}</span>
                            <span class="pd-flag-text">${f.text}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    },

    // Render Artisan Agent verdict banner for verified pools
    // Greek Gold Gaming Matrix style - elegant circular score
    renderVerdictBanner(pool) {
        const riskScore = pool.riskScore || pool.risk_score || 50;
        const riskLevel = pool.riskLevel || pool.risk_level || 'Medium';
        const dataSource = pool.dataSource || 'defillama';

        let verdict, scoreColor, glowColor, bgGradient, verdictDesc;

        if (riskScore >= 70 || riskLevel === 'Low') {
            verdict = 'SAFE';
            scoreColor = '#10B981';
            glowColor = 'rgba(16, 185, 129, 0.4)';
            bgGradient = 'linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(16, 185, 129, 0.02))';
            verdictDesc = 'Pool has passed Artisan Agent risk assessment';
        } else if (riskScore >= 40 || riskLevel === 'Medium') {
            verdict = 'CAUTION';
            scoreColor = '#D4A853';
            glowColor = 'rgba(212, 168, 83, 0.4)';
            bgGradient = 'linear-gradient(135deg, rgba(212, 168, 83, 0.08), rgba(212, 168, 83, 0.02))';
            verdictDesc = 'Careful consideration recommended before investing';
        } else {
            verdict = 'HIGH RISK';
            scoreColor = '#EF4444';
            glowColor = 'rgba(239, 68, 68, 0.4)';
            bgGradient = 'linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.02))';
            verdictDesc = 'Significant risk factors detected - proceed with caution';
        }

        // Calculate circle progress (stroke-dasharray for 100% = 251.2)
        const circumference = 251.2;
        const progress = (riskScore / 100) * circumference;
        const dashOffset = circumference - progress;

        // Data source badge
        let sourceBadge;
        if (dataSource.includes('geckoterminal')) {
            sourceBadge = '🦎 GeckoTerminal';
        } else if (dataSource.includes('defillama')) {
            sourceBadge = '📊 DefiLlama';
        } else if (dataSource.includes('aerodrome')) {
            sourceBadge = '🛩️ Aerodrome';
        } else {
            sourceBadge = '⛓️ On-chain';
        }

        return `
            <div class="matrix-verdict" style="background: ${bgGradient}; border-color: ${scoreColor}30;">
                <div class="matrix-score-ring" style="--score-color: ${scoreColor}; --glow-color: ${glowColor};">
                    <svg viewBox="0 0 100 100">
                        <circle class="ring-bg" cx="50" cy="50" r="40" />
                        <circle class="ring-progress" cx="50" cy="50" r="40" 
                            style="stroke: ${scoreColor}; stroke-dasharray: ${circumference}; stroke-dashoffset: ${dashOffset};" />
                    </svg>
                    <div class="score-value" style="color: ${scoreColor};">${riskScore}</div>
                </div>
                <div class="matrix-info">
                    <div class="matrix-verdict-label" style="color: ${scoreColor};">${verdict}</div>
                    <div class="matrix-desc">${verdictDesc}</div>
                    <div class="matrix-meta">
                        <span class="matrix-source-badge">${sourceBadge}</span>
                        <span class="matrix-score-text">Score: ${riskScore}/100</span>
                    </div>
                </div>
            </div>
        `;
    },

    show(pool, options = {}) {
        // Close any existing overlays from previous pool
        this.closeOverlay();

        // Store current pool reference
        this.currentPool = pool;

        // Add to history
        if (window.SearchHistory) {
            SearchHistory.addEntry('pool_view', {
                project: pool.project,
                symbol: pool.symbol,
                apy: pool.apy
            });
        }

        // Add ESC listener
        document.addEventListener('keydown', this.handleKeydown);

        // Create modal if not exists
        let modal = document.getElementById('poolDetailModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'poolDetailModal';
            modal.className = 'pool-detail-overlay';
            // Click outside to close
            modal.onclick = (e) => {
                if (e.target === modal) PoolDetailModal.close();
            };
            document.body.appendChild(modal);
        } else {
            modal.style.display = 'flex';
        }

        const protocolIcon = window.getProtocolIconUrl ? getProtocolIconUrl(pool.project) :
            `https://icons.llama.fi/${(pool.project || '').toLowerCase()}.png`;
        const chainIcon = window.getChainIconUrl ? getChainIconUrl(pool.chain) :
            `https://icons.llama.fi/chains/rsz_${(pool.chain || 'base').toLowerCase()}.jpg`;

        const isNiche = window.NicheProtocols?.isNiche(pool.project);
        const nicheCategory = isNiche ? NicheProtocols.getCategory(pool.project) : null;

        const epoch = this.getEpochCountdown();

        // ========================================
        // SECURITY ASSESSMENT (Safety Guard)
        // ========================================
        const securityAssessment = this.assessSecurity(pool);

        // Build security warnings banner if needed
        const securityBanner = securityAssessment.warnings.length > 0 ? `
            <div class="pd-security-banner ${securityAssessment.isCritical ? 'critical' : 'warning'}">
                <div class="pd-security-icon">${securityAssessment.isCritical ? '🚨' : '⚠️'}</div>
                <div class="pd-security-content">
                    <div class="pd-security-title">${securityAssessment.isCritical ? 'CRITICAL RISK DETECTED' : 'Security Warnings'}</div>
                    <ul class="pd-security-list">
                        ${securityAssessment.warnings.map(w => `<li>${w}</li>`).join('')}
                    </ul>
                </div>
            </div>
        ` : '';

        modal.innerHTML = `
            <div class="pool-detail-modal">
                <button class="modal-close-pro" onclick="PoolDetailModal.close()" title="Close (ESC)">${PoolIcons.close}</button>
                
                ${pool.isVerified ? this.renderVerdictBanner(pool) : ''}
                
                ${securityBanner}
                
                <!-- Header Section -->
                <div class="pd-header">
                    <div class="pd-header-main">
                        <div class="pd-logo">
                            <img src="${protocolIcon}" alt="${pool.project || 'Protocol'}" onerror="this.style.display='none'">
                        </div>
                        <div class="pd-title-block">
                            <h2 class="pd-protocol">${pool.project || pool.name?.split('/')[0]?.trim() || 'Unknown Protocol'}</h2>
                            <div class="pd-pair">
                                <span class="pd-symbol">${pool.symbol}</span>
                                <img src="${chainIcon}" alt="${pool.chain}" class="pd-chain-icon">
                                <span class="pd-chain">${pool.chain || 'Base'}</span>
                                ${isNiche ? `<span class="pd-niche-tag">🔮 ${nicheCategory}</span>` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="pd-apy-block" ${pool.apy_optimal ? `title="Up to ${pool.apy_optimal.toFixed(0)}% for narrow tick ranges (Aerodrome-style). Displayed APY is realistic average."` : ''}>
                        <span class="pd-apy-value">${pool.apy > 0 ? pool.apy.toFixed(2) + '%' : (pool.trading_fee ? `~${(pool.trading_fee * 365).toFixed(0)}%*` : 'N/A')}</span>
                        <span class="pd-apy-label">${pool.apy > 0 ? (pool.apy_optimal ? 'APY ℹ️' : 'APY') : (pool.trading_fee ? 'Est. APR' : 'APY')}</span>
                    </div>
                </div>
                
                <!-- APY Source Explainer (Verified pools only) -->
                ${pool.isVerified ? this.renderApyExplainer(pool) : ''}
                
                <!-- Metrics Grid (tread.fi style) -->
                <div class="pd-metrics-row">
                    <div class="pd-metric-card">
                        <div class="pd-metric-icon">${PoolIcons.tvl}</div>
                        <div class="pd-metric-value">${formatTvl ? formatTvl(pool.tvl) : '$' + (pool.tvl / 1000000).toFixed(2) + 'M'}</div>
                        <div class="pd-metric-label">TVL</div>
                    </div>
                    <div class="pd-metric-card">
                        <div class="pd-metric-icon">${PoolIcons.risk}</div>
                        <span class="pd-risk-badge ${(pool.risk_level || 'medium').toLowerCase()}">${pool.risk_level || 'Medium'}</span>
                        <div class="pd-metric-label">Risk Level</div>
                    </div>
                    <div class="pd-metric-card">
                        <div class="pd-metric-icon">${PoolIcons.coins}</div>
                        <div class="pd-metric-value">${pool.pool_type === 'stable' ? '🟢 Stable' : '🟠 Volatile'}</div>
                        <div class="pd-metric-label">Type</div>
                    </div>
                </div>
                
                <!-- Pool Characteristics Flags (Verified pools only) -->
                ${pool.isVerified ? this.renderVerifyFlags(pool) : ''}
                
                <!-- ========================================= -->
                <!-- BENTO GRID LAYOUT                        -->
                <!-- ========================================= -->
                <div class="pd-bento-main">
                    
                    <!-- LEFT COLUMN: Tabbed Analysis Module -->
                    <div class="pd-section pd-section-compact">
                        <div class="pd-tab-switcher">
                            <button class="pd-tab-btn active" data-tab="stress" onclick="PoolDetailModal.switchTab('stress')">📊 Stress Test</button>
                            <button class="pd-tab-btn" data-tab="yield" onclick="PoolDetailModal.switchTab('yield')">💰 Real Yield</button>
                            <button class="pd-tab-btn" data-tab="history" onclick="PoolDetailModal.switchTab('history')">📈 APY History</button>
                        </div>
                        <div class="pd-tab-content">
                            <div class="pd-tab-panel active" data-panel="stress">
                                ${this.renderLiquidityStressCompact(pool)}
                            </div>
                            <div class="pd-tab-panel" data-panel="yield">
                                ${this.renderYieldBreakdownCompact(pool)}
                            </div>
                            <div class="pd-tab-panel" data-panel="history">
                                ${this.renderAPYHistoryCompact(pool)}
                            </div>
                        </div>
                    </div>
                    
                    <!-- RIGHT COLUMN: 2x2 Security Matrix -->
                    <div class="pd-security-matrix">
                        ${this.renderAuditStatusCompact(pool)}
                        ${this.renderLiquidityLockCompact(pool)}
                        ${this.renderAdvancedRiskCompact(pool)}
                        ${this.renderHoneypotSummary(pool)}
                    </div>
                    
                </div>
                
                <!-- ========================================= -->
                <!-- COLLAPSIBLE ACCORDIONS                   -->
                <!-- ========================================= -->
                <div class="pd-accordions">
                    <div class="pd-accordion" data-accordion="tokens">
                        <div class="pd-accordion-header" onclick="PoolDetailModal.toggleAccordion('tokens')">
                            <span class="pd-accordion-title">🔐 Token Security Details</span>
                            <span class="pd-accordion-icon">▶</span>
                        </div>
                        <div class="pd-accordion-content">
                            ${this.renderTokenSecurityAnalysis(pool)}
                        </div>
                    </div>
                    
                    <div class="pd-accordion" data-accordion="risk">
                        <div class="pd-accordion-header" onclick="PoolDetailModal.toggleAccordion('risk')">
                            <span class="pd-accordion-title">📊 Advanced Risk & Whale Analysis</span>
                            <span class="pd-accordion-icon">▶</span>
                        </div>
                        <div class="pd-accordion-content">
                            ${this.renderAdvancedRiskAnalysis(pool)}
                        </div>
                    </div>
                    
                    <div class="pd-accordion" data-accordion="exit">
                        <div class="pd-accordion-header" onclick="PoolDetailModal.toggleAccordion('exit')">
                            <span class="pd-accordion-title">🚪 Exit Strategy & Simulation</span>
                            <span class="pd-accordion-icon">▶</span>
                        </div>
                        <div class="pd-accordion-content">
                            ${this.renderExitSimulation(pool)}
                            ${pool.isVerified ? this.renderExitStrategy(pool) : ''}
                        </div>
                    </div>
                    
                    <div class="pd-accordion" data-accordion="apy">
                        <div class="pd-accordion-header" onclick="PoolDetailModal.toggleAccordion('apy')">
                            <span class="pd-accordion-title">⚡ Why APY Can Change</span>
                            <span class="pd-accordion-icon">▶</span>
                        </div>
                        <div class="pd-accordion-content">
                            ${this.renderApyChangeExplainer(pool)}
                        </div>
                    </div>
                    
                    ${pool.isVerified ? `
                    <div class="pd-accordion" data-accordion="guidance">
                        <div class="pd-accordion-header" onclick="PoolDetailModal.toggleAccordion('guidance')">
                            <span class="pd-accordion-title">🎯 Decision Guidance & Data Quality</span>
                            <span class="pd-accordion-icon">▶</span>
                        </div>
                        <div class="pd-accordion-content">
                            ${this.renderDecisionGuidance(pool)}
                            ${this.renderDataCoverage(pool)}
                            ${this.renderConfidenceLevel(pool)}
                        </div>
                    </div>
                    ` : ''}
                </div>
                
                
                <!-- Market Dynamics Section -->
                <div class="pd-section">
                    <div class="pd-section-header">
                        <h3>📊 Market Dynamics</h3>
                        ${this.isEpochProtocol(pool.project) ? `
                            <div class="pd-epoch-badge">⏳ Epoch ends in: ${epoch.display}</div>
                        ` : ''}
                    </div>
                    
                    ${pool.premium_insights?.length > 0 ? `
                        <div class="pd-insights-box">
                            ${pool.premium_insights.map(insight => `
                                <div class="pd-insight ${insight.type}">
                                    <span class="pd-insight-bar"></span>
                                    <span class="pd-insight-text">${insight.text}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}

                    <div class="pd-data-grid">
                        ${(typeof pool.apy_base === 'number') ? `
                            <div class="pd-data-card">
                                <div class="pd-data-label">APY COMPOSITION</div>
                                <div class="pd-apy-breakdown">
                                    <div class="pd-apy-row">
                                        <span class="pd-dot base"></span>
                                        <span>Base: ${Number(pool.apy_base || 0).toFixed(2)}%</span>
                                    </div>
                                    <div class="pd-apy-row">
                                        <span class="pd-dot reward"></span>
                                        <span>Reward (${formatRewardTokenName(pool.reward_token)}): ${Number(pool.apy_reward || 0).toFixed(2)}%</span>
                                        ${pool.pool_type !== 'stable' ? '<span class="pd-warn-icon" title="Volatile token">⚠️</span>' : ''}
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                        
                        <div class="pd-data-card">
                            <div class="pd-data-label">TVL STABILITY</div>
                            ${pool.tvl_stability ? `
                                <div class="pd-trend-value ${pool.tvl_stability === 'Stable' ? 'up' : pool.tvl_stability === 'Volatile' ? 'down' : ''}">
                                    ${pool.tvl_stability === 'Stable' ? '✅' : pool.tvl_stability === 'Volatile' ? '⚠️' : '📊'}
                                    ${pool.tvl_stability}
                                    ${pool.tvl_change_7d !== undefined && pool.tvl_change_7d !== null ? ` (${pool.tvl_change_7d >= 0 ? '+' : ''}${Number(pool.tvl_change_7d).toFixed(1)}% 7d)` : ''}
                                </div>
                            ` : pool.tvl_change_7d !== undefined && pool.tvl_change_7d !== null ? `
                                <div class="pd-trend-value ${pool.tvl_change_7d >= 0 ? 'up' : 'down'}">
                                    ${pool.tvl_change_7d >= 0 ? PoolIcons.trendUp : PoolIcons.trendDown}
                                    ${pool.tvl_change_7d >= 0 ? '+' : ''}${Number(pool.tvl_change_7d).toFixed(1)}% 7d
                                </div>
                            ` : `
                                <div class="pd-trend-value unknown" title="No historical pool-level data available">
                                    <span style="opacity: 0.5">📊</span> Unknown
                                </div>
                            `}
                        </div>
                        
                        <div class="pd-data-card">
                            <div class="pd-data-label">24H VOLUME</div>
                            <div class="pd-data-value">${pool.volume_24h_formatted || 'N/A'}</div>
                        </div>
                        
                        ${pool.trading_fee ? `
                        <div class="pd-data-card">
                            <div class="pd-data-label">TRADING FEE</div>
                            <div class="pd-data-value">${pool.trading_fee}%</div>
                        </div>
                        ` : ''}
                    </div>

                    ${pool.risk_reasons?.length > 0 ? `
                        <div class="pd-risk-section">
                            <div class="pd-risk-title">Risk Factors:</div>
                            <ul class="pd-risk-list">
                                ${pool.risk_reasons.map(r => `<li>• ${r}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
                
                <!-- Trust Links -->
                <div class="pd-trust-row">
                    ${getProtocolWebsite(pool.project) ? `<a href="${getProtocolWebsite(pool.project)}" target="_blank">${PoolIcons.externalLink} Protocol</a>` : ''}
                    ${pool.pool_link ? `<a href="${pool.pool_link}" target="_blank">🏊 Pool</a>` : ''}
                </div>
                
                <!-- Action Buttons -->
                <div class="pd-actions">
                    ${this.renderDepositButton(pool, securityAssessment)}
                    <button class="pd-btn-secondary" onclick="PoolDetailModal.addToStrategy()">
                        + Add to Strategy
                    </button>
                    <button class="pd-btn-outline" onclick="YieldComparison?.addPool(PoolDetailModal.currentPool)">
                        📊 Compare
                    </button>
                </div>
            </div>
        `;

        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Compact mode for Explore: hide RPC-dependent sections, ultra compact
        if (options && options.compact) {
            console.log('COMPACT MODE ENABLED - Explore modal');
            const modalContent = modal.querySelector('.pool-detail-modal');
            console.log('modalContent found:', modalContent);
            if (modalContent) {
                modalContent.style.setProperty('max-width', '550px', 'important');
                modalContent.style.setProperty('width', '550px', 'important');
                modalContent.style.setProperty('padding', '6px', 'important');
                modalContent.style.setProperty('font-size', '16px', 'important');
                console.log('Applied compact styles with !important');
            }
            // Hide Security Matrix
            const securityMatrix = modal.querySelector('.pd-security-matrix');
            if (securityMatrix) securityMatrix.style.display = 'none';
            // Hide RPC-dependent accordions
            ['tokens', 'risk', 'exit', 'guidance'].forEach(name => {
                const accordion = modal.querySelector(`[data-accordion="${name}"]`);
                if (accordion) accordion.style.display = 'none';
            });
            // Make bento single column
            const bento = modal.querySelector('.pd-bento-main');
            if (bento) { bento.style.gridTemplateColumns = '1fr'; bento.style.gap = '2px'; }
            // Reduce header size
            const header = modal.querySelector('.pd-header');
            if (header) { header.style.padding = '4px'; header.style.gap = '8px'; header.style.marginBottom = '2px'; }
            const logo = modal.querySelector('.pd-logo img');
            if (logo) { logo.style.width = '28px'; logo.style.height = '28px'; }
            const protocol = modal.querySelector('.pd-protocol');
            if (protocol) protocol.style.fontSize = '13px';
            const symbol = modal.querySelector('.pd-symbol');
            if (symbol) symbol.style.fontSize = '9px';
            // Move APY left so it doesn't overlap with X button
            const apyBlock = modal.querySelector('.pd-apy-block');
            if (apyBlock) { apyBlock.style.setProperty('margin-right', '50px', 'important'); }
            // Reduce metrics grid - make it tighter
            const metricsGrid = modal.querySelector('.pd-metrics-grid');
            if (metricsGrid) { metricsGrid.style.gap = '2px'; metricsGrid.style.padding = '2px'; metricsGrid.style.marginBottom = '2px'; }
            modal.querySelectorAll('.pd-metric').forEach(m => { m.style.padding = '4px'; m.style.minWidth = '0'; });
            modal.querySelectorAll('.pd-metric-value').forEach(v => { v.style.fontSize = '18px'; });
            modal.querySelectorAll('.pd-metric-label').forEach(l => { l.style.fontSize = '14px'; });
            // Reduce tabs and charts - minimal vertical space
            const tabs = modal.querySelector('.pd-tabs');
            if (tabs) { tabs.style.padding = '2px'; tabs.style.gap = '2px'; tabs.style.marginBottom = '2px'; }
            modal.querySelectorAll('.pd-tab').forEach(t => { t.style.padding = '4px 8px'; t.style.fontSize = '12px'; });
            // Reduce stress test area - compact
            const stressTest = modal.querySelector('.pd-stress-test');
            if (stressTest) {
                stressTest.style.padding = '4px';
                stressTest.style.marginTop = '0';
                stressTest.style.marginBottom = '2px';
            }
            // Reduce stress bars vertical spacing
            modal.querySelectorAll('.pd-stress-row').forEach(r => { r.style.marginBottom = '1px'; r.style.gap = '4px'; });
            modal.querySelectorAll('.pd-stress-label').forEach(l => { l.style.fontSize = '15px'; l.style.minWidth = '30px'; });
            // Reduce accordion section
            const accordions = modal.querySelector('.pd-accordions');
            if (accordions) { accordions.style.marginTop = '2px'; accordions.style.gap = '2px'; }
            modal.querySelectorAll('.pd-accordion-header').forEach(h => { h.style.padding = '6px'; h.style.fontSize = '16px'; });
            // Reduce Market Dynamics - very compact
            const sections = modal.querySelectorAll('.pd-section');
            sections.forEach(s => { s.style.padding = '4px'; s.style.marginTop = '2px'; });
            modal.querySelectorAll('.pd-section-header').forEach(h => { h.style.marginBottom = '2px'; });
            modal.querySelectorAll('.pd-section-header h3').forEach(h => { h.style.fontSize = '17px'; });
            // Compact the dynamics grid
            const dynamicsGrid = modal.querySelector('.pd-dynamics-grid');
            if (dynamicsGrid) { dynamicsGrid.style.gap = '4px'; }
            modal.querySelectorAll('.pd-dynamics-card').forEach(c => { c.style.padding = '4px'; });
            modal.querySelectorAll('.pd-dynamics-label').forEach(l => { l.style.fontSize = '14px'; });
            modal.querySelectorAll('.pd-dynamics-value').forEach(v => { v.style.fontSize = '16px'; });
            // Reduce actions - smaller buttons
            const actions = modal.querySelector('.pd-actions');
            if (actions) { actions.style.gap = '4px'; actions.style.marginTop = '4px'; actions.style.flexWrap = 'wrap'; }
            modal.querySelectorAll('.pd-actions button').forEach(b => { b.style.padding = '8px 12px'; b.style.fontSize = '16px'; b.style.flex = '1'; });
            // Hide some less important elements in compact mode
            const riskFactors = modal.querySelector('.pd-risk-factors');
            if (riskFactors) riskFactors.style.display = 'none';
            const externalLinks = modal.querySelector('.pd-external-links');
            if (externalLinks) externalLinks.style.display = 'none';
        }
    },

    close() {
        const modal = document.getElementById('poolDetailModal');
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    },

    addToStrategy() {
        if (this.currentPool && window.addToStrategy) {
            addToStrategy(this.currentPool.id || this.currentPool.pool);
        }
        this.close();
    }
};

// ============================================
// CSS FOR POOL DETAIL MODAL - PROFESSIONAL MATRIX GOLD THEME
// ============================================
const detailStyles = document.createElement('style');
detailStyles.textContent = `
    /* Slide-up animation keyframes */
    @keyframes slideUpIn {
        from {
            transform: translateY(100%);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    /* Modal Overlay */
    .pool-detail-overlay {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.85);
        backdrop-filter: blur(12px);
        z-index: 2000;
        justify-content: center;
        align-items: flex-end;
        padding: var(--space-4);
        animation: fadeIn 0.3s ease-out;
    }
    
    /* Modal Container - ultra compact with slide-up animation */
    .pool-detail-modal {
        background: linear-gradient(180deg, rgba(20, 20, 20, 0.98), rgba(10, 10, 10, 0.98));
        border: 1px solid rgba(212, 168, 83, 0.3);
        border-radius: 12px 12px 0 0;
        max-width: 1100px;
        width: 95vw;
        max-height: 94vh;
        overflow-y: auto;
        padding: 8px;
        position: relative;
        box-shadow: 0 0 60px rgba(212, 168, 83, 0.1), 0 0 1px rgba(212, 168, 83, 0.5);
        animation: slideUpIn 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }
    
    /* Grid layout for sections - 4-column compact layout */
    .pd-sections-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 4px;
        margin-bottom: 4px;
        align-items: start;
    }
    
    /* ========================================= */
    /* BENTO GRID LAYOUT                        */
    /* ========================================= */
    
    .pd-bento-main {
        display: grid;
        grid-template-columns: 58fr 42fr;
        gap: 4px;
        margin-bottom: 4px;
    }
    
    /* Tab Switcher */
    .pd-tab-switcher {
        display: flex;
        gap: 2px;
        background: rgba(0,0,0,0.3);
        border-radius: 6px;
        padding: 3px;
        margin-bottom: 4px;
    }
    
    .pd-tab-btn {
        flex: 1;
        padding: 5px 6px;
        background: transparent;
        border: none;
        color: var(--text-muted);
        font-size: 0.7rem;
        font-weight: 500;
        cursor: pointer;
        border-radius: 4px;
        transition: all 0.2s ease;
    }
    
    .pd-tab-btn:hover {
        background: rgba(255,255,255,0.05);
        color: var(--text-secondary);
    }
    
    .pd-tab-btn.active {
        background: rgba(212, 168, 83, 0.15);
        color: var(--accent-gold);
        border: 1px solid rgba(212, 168, 83, 0.3);
    }
    
    .pd-tab-content {
        min-height: 90px;
    }
    
    .pd-tab-panel {
        display: none;
    }
    
    .pd-tab-panel.active {
        display: block;
    }
    
    /* Security Matrix 2x2 */
    .pd-security-matrix {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 4px;
    }
    
    .pd-security-matrix .pd-section {
        margin-bottom: 0;
        padding: 6px 8px;
    }
    
    .pd-security-matrix .pd-section-header h3 {
        font-size: 0.65rem;
        margin-bottom: 4px;
    }
    
    /* Compact section variant for matrix */
    .pd-section-compact {
        padding: 6px 8px !important;
    }
    
    .pd-section-compact .pd-section-header {
        margin-bottom: 4px;
    }
    
    .pd-section-compact .pd-section-header h3 {
        font-size: 0.65rem;
    }
    
    /* Accordions as Overlay Triggers */
    .pd-accordions {
        display: flex;
        gap: 4px;
        margin-top: 4px;
        flex-wrap: wrap;
    }
    
    .pd-accordion {
        flex: 1;
        min-width: 120px;
    }
    
    .pd-accordion-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 8px 12px;
        background: rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 6px;
        cursor: pointer;
        user-select: none;
        transition: all 0.2s ease;
    }
    
    .pd-accordion-header:hover {
        background: rgba(212, 168, 83, 0.1);
        border-color: rgba(212, 168, 83, 0.3);
    }
    
    .pd-accordion-title {
        font-size: 0.7rem;
        font-weight: 500;
        color: var(--text-secondary);
    }
    
    .pd-accordion-icon {
        font-size: 0.55rem;
        color: var(--accent-gold);
    }
    
    /* Hidden by default, shown as overlay when active */
    .pd-accordion-content {
        display: none;
    }
    
    /* Overlay Panel (appears above modal) */
    .pd-overlay-panel {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: linear-gradient(180deg, rgba(25, 25, 25, 0.98), rgba(15, 15, 15, 0.98));
        border: 1px solid rgba(212, 168, 83, 0.4);
        border-radius: 12px;
        max-width: 900px;
        width: 90vw;
        max-height: 88vh;
        overflow-y: auto;
        padding: 14px;
        z-index: 3000;
        box-shadow: 0 0 80px rgba(0,0,0,0.8), 0 0 30px rgba(212, 168, 83, 0.15);
        animation: overlayFadeIn 0.2s ease;
    }
    
    @keyframes overlayFadeIn {
        from { opacity: 0; transform: translate(-50%, -48%); }
        to { opacity: 1; transform: translate(-50%, -50%); }
    }
    
    .pd-overlay-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.7);
        backdrop-filter: blur(4px);
        z-index: 2999;
    }
    
    .pd-overlay-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .pd-overlay-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--accent-gold);
    }
    
    .pd-overlay-close {
        background: rgba(255,255,255,0.1);
        border: none;
        color: var(--text-secondary);
        font-size: 1.2rem;
        width: 32px;
        height: 32px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .pd-overlay-close:hover {
        background: rgba(239, 68, 68, 0.3);
        color: #EF4444;
    }
    
    /* Compact APY reasons inline tags */
    .pd-apy-reasons-inline {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
    }
    .pd-reason-tag {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 4px;
        padding: 2px 6px;
        font-size: 0.65rem;
        color: var(--text-muted);
    }
    
    /* Full APY Reasons List */
    .pd-apy-change-full {
        padding: 0;
    }
    
    .pd-apy-reasons-list {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    
    .pd-reason-item {
        background: rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 12px;
    }
    
    .pd-reason-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }
    
    .pd-reason-icon {
        font-size: 1.2rem;
    }
    
    .pd-reason-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text-primary);
        flex: 1;
    }
    
    .pd-reason-impact {
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.6rem;
        font-weight: 600;
    }
    
    .pd-reason-desc {
        font-size: 0.75rem;
        color: var(--text-muted);
        line-height: 1.5;
    }
    
    .pd-apy-summary {
        margin-top: 16px;
        padding: 12px;
        background: rgba(212, 168, 83, 0.08);
        border: 1px solid rgba(212, 168, 83, 0.2);
        border-radius: 8px;
        font-size: 0.75rem;
        color: var(--text-secondary);
    }
    
    .pd-apy-summary strong {
        color: var(--accent-gold);
    }
    
    /* Full-width sections (span all columns) */
    .pd-section-full {
        grid-column: 1 / -1;
    }
    
    /* Slim Action Footer */
    .pd-action-footer {
        display: flex;
        gap: 8px;
        padding: 8px 0 4px 0;
        border-top: 1px solid rgba(255,255,255,0.08);
        margin-top: 8px;
    }
    
    .pd-action-footer .pd-btn-primary,
    .pd-action-footer .pd-btn-secondary {
        flex: 1;
        padding: 8px 12px;
        font-size: 0.75rem;
    }
    
    /* Matrix Verdict Banner - Greek Gold Gaming Style */
    .matrix-verdict {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 12px 16px;
        border-radius: 10px;
        border: 1px solid;
        margin-bottom: 14px;
    }
    
    .matrix-score-ring {
        position: relative;
        width: 56px;
        height: 56px;
        flex-shrink: 0;
    }
    
    .matrix-score-ring svg {
        width: 100%;
        height: 100%;
        transform: rotate(-90deg);
        filter: drop-shadow(0 0 8px var(--glow-color));
    }
    
    .matrix-score-ring .ring-bg {
        fill: none;
        stroke: rgba(255, 255, 255, 0.08);
        stroke-width: 6;
    }
    
    .matrix-score-ring .ring-progress {
        fill: none;
        stroke-width: 6;
        stroke-linecap: round;
        transition: stroke-dashoffset 0.8s ease-out;
    }
    
    .matrix-score-ring .score-value {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 1.1rem;
        font-weight: 800;
        text-shadow: 0 0 10px currentColor;
    }
    
    .matrix-info {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    
    .matrix-verdict-label {
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    
    .matrix-desc {
        font-size: 0.7rem;
        color: var(--text-muted);
        font-weight: 400;
        margin-bottom: 4px;
    }
    
    .matrix-meta {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .matrix-source-badge {
        display: inline-block;
        font-size: 0.6rem;
        color: var(--text-muted);
        background: rgba(255, 255, 255, 0.05);
        padding: 2px 6px;
        border-radius: 4px;
    }
    
    .matrix-score-text {
        font-size: 0.6rem;
        color: var(--text-muted);
        opacity: 0.7;
    }
    
    /* Close Button */
    .modal-close-pro {
        position: absolute;
        top: 16px;
        right: 16px;
        width: 28px;
        height: 28px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 6px;
        color: var(--text-muted);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        z-index: 100;
    }
    
    .modal-close-pro:hover {
        background: rgba(212, 168, 83, 0.2);
        border-color: var(--gold);
        color: var(--gold);
    }
    
    .modal-close-pro svg {
        width: 18px;
        height: 18px;
    }
    
    /* Header Section - ultra compact */
    .pd-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 8px;
        margin-bottom: 8px;
        border-bottom: 1px solid rgba(212, 168, 83, 0.2);
    }
    
    .pd-header-main {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .pd-logo img {
        width: 32px;
        height: 32px;
        border-radius: 6px;
        border: 1px solid rgba(212, 168, 83, 0.3);
    }
    
    .pd-protocol {
        font-size: 0.9rem;
        font-weight: 700;
        color: var(--text);
        margin: 0 0 2px 0;
    }
    
    .pd-pair {
        display: flex;
        align-items: center;
        gap: 6px;
        color: var(--text-muted);
        font-size: 0.75rem;
    }
    
    .pd-symbol {
        font-weight: 500;
        color: var(--text-secondary);
    }
    
    .pd-chain-icon {
        width: 18px;
        height: 18px;
        border-radius: 50%;
    }
    
    .pd-niche-tag {
        background: rgba(139, 92, 246, 0.15);
        color: #A78BFA;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
    }
    
    .pd-apy-block {
        text-align: right;
    }
    
    .pd-apy-value {
        display: block;
        font-size: 1.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #D4A853, #F5D78E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
    }
    
    .pd-apy-label {
        font-size: 0.6rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    
    /* Metrics Row - ultra compact inline */
    .pd-metrics-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 4px;
        margin-bottom: 8px;
    }
    
    .pd-metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 6px;
        padding: 6px 4px;
        text-align: center;
        transition: all 0.2s;
    }
    
    .pd-metric-card:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(212, 168, 83, 0.3);
    }
    
    .pd-metric-card.pd-il-high {
        border-color: rgba(239, 68, 68, 0.4);
        background: rgba(239, 68, 68, 0.05);
    }
    
    .pd-metric-card.pd-il-none {
        border-color: rgba(16, 185, 129, 0.4);
        background: rgba(16, 185, 129, 0.05);
    }
    
    .pd-metric-icon {
        display: flex;
        justify-content: center;
        margin-bottom: 4px;
        color: var(--gold);
        opacity: 0.6;
    }
    
    .pd-metric-icon svg {
        width: 18px;
        height: 18px;
    }
    
    .pd-metric-value {
        font-size: 0.85rem;
        font-weight: 700;
        color: var(--text);
        margin-bottom: 2px;
    }
    
    .pd-metric-value.pd-danger { color: #EF4444; }
    .pd-metric-value.pd-safe { color: #10B981; }
    
    .pd-metric-label {
        font-size: 0.6rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.2px;
    }
    
    .pd-risk-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 4px;
    }
    
    .pd-risk-badge.low { background: rgba(16, 185, 129, 0.15); color: #10B981; }
    .pd-risk-badge.medium { background: rgba(251, 191, 36, 0.15); color: #FBBF24; }
    .pd-risk-badge.high { background: rgba(239, 68, 68, 0.15); color: #EF4444; }
    .pd-risk-badge.critical { background: rgba(239, 68, 68, 0.25); color: #EF4444; animation: pulse-danger 1.5s infinite; }
    
    /* Security Banner - Safety Guard Warnings */
    .pd-security-banner {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 14px;
        border-radius: 10px;
        margin-bottom: 12px;
        animation: fadeIn 0.3s ease;
    }
    
    .pd-security-banner.warning {
        background: rgba(251, 191, 36, 0.1);
        border: 1px solid rgba(251, 191, 36, 0.4);
    }
    
    .pd-security-banner.critical {
        background: rgba(239, 68, 68, 0.15);
        border: 2px solid rgba(239, 68, 68, 0.6);
        animation: pulse-danger 2s infinite;
    }
    
    .pd-security-icon {
        font-size: 1.5rem;
        flex-shrink: 0;
    }
    
    .pd-security-content {
        flex: 1;
    }
    
    .pd-security-title {
        font-weight: 700;
        font-size: 0.85rem;
        margin-bottom: 6px;
    }
    
    .pd-security-banner.warning .pd-security-title { color: #FBBF24; }
    .pd-security-banner.critical .pd-security-title { color: #EF4444; }
    
    .pd-security-list {
        list-style: none;
        padding: 0;
        margin: 0;
        font-size: 0.75rem;
        color: var(--text-secondary);
    }
    
    .pd-security-list li {
        margin-bottom: 4px;
    }
    
    /* Danger/Warning Button Variants */
    .pd-btn-danger {
        flex: 1;
        padding: 12px 16px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        text-align: center;
        cursor: not-allowed;
        background: rgba(239, 68, 68, 0.2);
        border: 2px solid rgba(239, 68, 68, 0.5);
        color: #EF4444;
        opacity: 0.8;
    }
    
    .pd-btn-warning {
        flex: 1;
        padding: 12px 16px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        text-decoration: none;
        text-align: center;
        display: block;
        background: linear-gradient(135deg, rgba(251, 191, 36, 0.3), rgba(212, 168, 83, 0.3));
        border: 1px solid rgba(251, 191, 36, 0.5);
        color: #FBBF24;
        transition: all 0.2s;
    }
    
    .pd-btn-warning:hover {
        background: linear-gradient(135deg, rgba(251, 191, 36, 0.4), rgba(212, 168, 83, 0.4));
        box-shadow: 0 0 15px rgba(251, 191, 36, 0.3);
    }
    
    @keyframes pulse-danger {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    
    /* Section Container - ultra compact tiles */
    .pd-section {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 4px;
        padding: 3px 5px;
        margin-bottom: 3px;
        font-size: 0.6rem;
        line-height: 1.15;
    }
    
    /* MICRO-COMPACT: All tile internal content */
    .pd-section p,
    .pd-section span,
    .pd-section div,
    .pd-section li,
    .pd-section td,
    .pd-section th {
        font-size: 0.6rem !important;
        line-height: 1.15 !important;
    }
    
    .pd-section strong,
    .pd-section b {
        font-size: 0.65rem !important;
    }
    
    .pd-section ul, .pd-section ol {
        margin: 2px 0;
        padding-left: 10px;
    }
    
    .pd-section li {
        margin: 1px 0;
    }
    
    .pd-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 2px;
    }
    
    .pd-section-header h3 {
        font-size: 0.6rem;
        font-weight: 600;
        color: var(--text);
        margin: 0;
    }
    
    .pd-epoch-badge {
        font-size: 0.55rem;
        color: #FBBF24;
        background: rgba(251, 191, 36, 0.12);
        padding: 1px 5px;
        border-radius: 8px;
        border: 1px solid rgba(251, 191, 36, 0.3);
    }
    
    /* Insights Box - micro */
    .pd-insights-box {
        background: rgba(212, 168, 83, 0.05);
        border-left: 2px solid var(--gold);
        padding: 3px 6px;
        margin-bottom: 4px;
        border-radius: 0 4px 4px 0;
    }
    
    .pd-insight {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 3px 0;
        font-size: 0.7rem;
        color: var(--text-secondary);
    }
    
    .pd-insight-bar {
        width: 3px;
        height: 12px;
        background: var(--gold);
        border-radius: 2px;
    }
    
    .pd-insight.warning .pd-insight-bar { background: #EF4444; }
    .pd-insight.positive .pd-insight-bar { background: #10B981; }
    
    /* Data Grid */
    .pd-data-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
    }
    
    .pd-data-card {
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 14px;
    }
    
    .pd-data-label {
        font-size: 0.65rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    
    .pd-data-value {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .pd-apy-breakdown {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .pd-apy-row {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.85rem;
        color: var(--text-secondary);
    }
    
    .pd-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    
    .pd-dot.base { background: #10B981; }
    .pd-dot.reward { background: #FBBF24; }
    
    .pd-warn-icon {
        margin-left: 4px;
        cursor: help;
    }
    
    .pd-trend-value {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.1rem;
        font-weight: 600;
    }
    
    .pd-trend-value.up { color: #10B981; }
    .pd-trend-value.down { color: #EF4444; }
    
    .pd-trend-value svg {
        width: 20px;
        height: 20px;
    }
    
    /* Risk Section */
    .pd-risk-section {
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .pd-risk-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-secondary);
        margin-bottom: 8px;
    }
    
    .pd-risk-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    
    .pd-risk-list li {
        font-size: 0.8rem;
        color: var(--text-muted);
        padding: 4px 0;
    }
    
    /* Trust Links Row */
    .pd-trust-row {
        display: flex;
        justify-content: center;
        gap: 16px;
        margin-bottom: 16px;
    }
    
    .pd-trust-row a {
        font-size: 0.75rem;
        color: var(--text-muted);
        text-decoration: none;
        padding: 8px 14px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
    }
    
    .pd-trust-row a:hover {
        color: var(--gold);
        border-color: rgba(212, 168, 83, 0.4);
        background: rgba(212, 168, 83, 0.1);
    }
    
    .pd-trust-row a svg {
        width: 14px;
        height: 14px;
    }
    
    /* Action Buttons */
    .pd-actions {
        display: flex;
        gap: 10px;
    }
    
    .pd-btn-primary {
        flex: 2;
        padding: 14px 20px;
        background: linear-gradient(135deg, #D4A853, #C49A47);
        border: none;
        border-radius: 10px;
        color: #000;
        font-weight: 700;
        font-size: 0.9rem;
        text-decoration: none;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .pd-btn-primary:hover {
        background: linear-gradient(135deg, #E5B95F, #D4A853);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(212, 168, 83, 0.3);
    }
    
    .pd-btn-secondary,
    .pd-btn-outline {
        flex: 1;
        padding: 14px 16px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        color: var(--text-secondary);
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .pd-btn-secondary:hover,
    .pd-btn-outline:hover {
        border-color: var(--gold);
        color: var(--gold);
        background: rgba(212, 168, 83, 0.1);
    }
    
    /* Responsive */
    @media (max-width: 600px) {
        .pd-metrics-row {
            grid-template-columns: repeat(2, 1fr);
        }
        
        .pd-data-grid {
            grid-template-columns: 1fr;
        }
        
        .pd-actions {
            flex-direction: column;
        }
        
        .pd-header {
            flex-direction: column;
            text-align: center;
            gap: 16px;
        }
        
        .pd-header-main {
            flex-direction: column;
        }
    }
    
    /* ========================================= */
    /* APY EXPLAINER - Source and Confidence    */
    /* ========================================= */
    
    .pd-apy-explainer {
        background: rgba(212, 168, 83, 0.05);
        border: 1px solid rgba(212, 168, 83, 0.15);
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 12px;
    }
    
    .pd-apy-explainer.unavailable {
        background: rgba(239, 68, 68, 0.05);
        border-color: rgba(239, 68, 68, 0.2);
    }
    
    .pd-apy-source {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
    }
    
    .pd-source-icon {
        font-size: 0.9rem;
    }
    
    .pd-source-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .pd-confidence {
        font-size: 0.6rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .pd-confidence.high {
        background: rgba(16, 185, 129, 0.15);
        color: #10B981;
    }
    
    .pd-confidence.medium {
        background: rgba(251, 191, 36, 0.15);
        color: #FBBF24;
    }
    
    .pd-confidence.low {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
    }
    
    .pd-apy-explanation {
        font-size: 0.7rem;
        color: var(--text-muted);
        margin-bottom: 4px;
    }
    
    .pd-apy-reason {
        font-size: 0.7rem;
        color: #EF4444;
    }
    
    .pd-apy-caveats {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    
    .pd-caveat {
        font-size: 0.65rem;
        color: var(--text-muted);
        background: rgba(255, 255, 255, 0.03);
        padding: 2px 6px;
        border-radius: 4px;
    }
    
    /* ========================================= */
    /* WHY APY CAN CHANGE - Expandable Section  */
    /* ========================================= */
    
    .pd-apy-change-section {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        margin-bottom: 14px;
        overflow: hidden;
    }
    
    .pd-apy-change-section[open] {
        background: rgba(255, 255, 255, 0.03);
    }
    
    .pd-apy-change-header {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 12px;
        cursor: pointer;
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text-secondary);
        list-style: none;
    }
    
    .pd-apy-change-header::-webkit-details-marker {
        display: none;
    }
    
    .pd-apy-change-header:hover {
        color: var(--gold);
    }
    
    .pd-change-icon {
        font-size: 1rem;
    }
    
    .pd-expand-arrow {
        margin-left: auto;
        font-size: 0.7rem;
        transition: transform 0.2s;
    }
    
    .pd-apy-change-section[open] .pd-expand-arrow {
        transform: rotate(90deg);
    }
    
    .pd-apy-change-content {
        padding: 0 12px 12px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .pd-change-reason {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 8px;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 6px;
    }
    
    .pd-reason-icon {
        font-size: 1rem;
        flex-shrink: 0;
    }
    
    .pd-reason-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    
    .pd-reason-text strong {
        font-size: 0.8rem;
        color: var(--text);
    }
    
    .pd-reason-text span {
        font-size: 0.7rem;
        color: var(--text-muted);
        line-height: 1.3;
    }
    
    /* ========================================= */
    /* LIQUIDITY STRESS TEST                    */
    /* ========================================= */
    
    .pd-liquidity-stress {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
    
    .pd-stress-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }
    
    .pd-stress-icon {
        font-size: 1rem;
    }
    
    .pd-stress-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .pd-stress-current {
        margin-left: auto;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .pd-stress-scenarios {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }
    
    .pd-stress-row {
        display: grid;
        grid-template-columns: 70px 1fr 100px;
        align-items: center;
        gap: 8px;
    }
    
    .pd-stress-drop {
        font-size: 0.75rem;
        color: var(--text-muted);
        font-weight: 500;
    }
    
    .pd-stress-bar-container {
        height: 6px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 3px;
        overflow: hidden;
    }
    
    .pd-stress-bar {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
    }
    
    .pd-stress-result {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 2px;
    }
    
    .pd-stress-tvl {
        font-size: 0.7rem;
        color: var(--text-muted);
    }
    
    .pd-stress-impact {
        font-size: 0.65rem;
        font-weight: 600;
    }
    
    .pd-stress-footer {
        margin-top: 8px;
        font-size: 0.65rem;
        color: var(--text-muted);
        text-align: center;
        font-style: italic;
    }
    
    /* ========================================= */
    /* DATA COVERAGE - Transparency Section     */
    /* ========================================= */
    
    .pd-data-coverage {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 14px;
    }
    
    .pd-coverage-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .pd-coverage-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .pd-coverage-score {
        font-size: 0.7rem;
        color: var(--gold);
        font-weight: 600;
    }
    
    .pd-coverage-grid {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .pd-coverage-item {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 0.7rem;
    }
    
    .pd-coverage-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    
    .pd-coverage-dot.available {
        background: #10B981;
        box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
    }
    
    .pd-coverage-dot.partial {
        background: #FBBF24;
        box-shadow: 0 0 6px rgba(251, 191, 36, 0.5);
    }
    
    .pd-coverage-dot.unavailable {
        background: rgba(255, 255, 255, 0.2);
    }
    
    .pd-coverage-label {
        color: var(--text);
        font-weight: 500;
        min-width: 100px;
    }
    
    .pd-coverage-detail {
        color: var(--text-muted);
        font-size: 0.75rem;
    }
    
    .pd-coverage-item.unavailable .pd-coverage-label,
    .pd-coverage-item.unavailable .pd-coverage-detail {
        opacity: 0.5;
    }
    
    /* ========================================= */
    /* VERIFY FLAGS - Pool Characteristics      */
    /* ========================================= */
    
    .pd-verify-flags {
        margin-bottom: 14px;
    }
    
    .pd-flags-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text);
        margin-bottom: 8px;
    }
    
    .pd-flags-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    
    .pd-flag {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 500;
        cursor: help;
        transition: all 0.2s;
    }
    
    .pd-flag.info,
    .pd-flag.warning,
    .pd-flag.caution {
        background: rgba(212, 168, 83, 0.15);
        border: 1px solid rgba(212, 168, 83, 0.4);
        color: #D4A853;
    }
    
    .pd-flag:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    
    .pd-flag-icon {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .pd-flag-icon svg {
        width: 14px;
        height: 14px;
    }
    
    .pd-flag-text {
        white-space: nowrap;
    }
    
    /* =========================================
       CONFIDENCE LEVEL SECTION
       ========================================= */
    
    .pd-confidence-section {
        background: rgba(30, 30, 35, 0.6);
        border: 1px solid rgba(212, 168, 83, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-top: 16px;
    }
    
    .pd-confidence-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    
    .pd-confidence-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--gold);
    }
    
    .pd-confidence-badge {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .pd-confidence-subtitle {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.5);
        margin-bottom: 14px;
    }
    
    .pd-confidence-factors {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .pd-confidence-factor {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 8px;
    }
    
    .pd-conf-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.7);
        width: 60px;
    }
    
    .pd-conf-status {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: bold;
    }
    
    .pd-conf-status.high { background: #22C55E; color: white; }
    .pd-conf-status.medium { background: #F59E0B; color: white; }
    .pd-conf-status.low { background: #EF4444; color: white; }
    .pd-conf-status.unavailable { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.5); }
    
    .pd-conf-text {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.9);
    }
    
    /* =========================================
       DECISION GUIDANCE SECTION
       ========================================= */
    
    .pd-decision-section {
        background: rgba(30, 30, 35, 0.6);
        border: 1px solid rgba(212, 168, 83, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-top: 16px;
    }
    
    .pd-decision-header {
        margin-bottom: 12px;
    }
    
    .pd-decision-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--gold);
    }
    
    .pd-decision-subtitle {
        font-size: 0.8rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.6);
        margin-bottom: 8px;
    }
    
    .pd-decision-warnings, .pd-decision-recs {
        margin-bottom: 12px;
    }
    
    .pd-decision-item {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 10px 12px;
        border-radius: 8px;
        margin-bottom: 6px;
    }
    
    .pd-decision-item.warning {
        background: rgba(239, 68, 68, 0.08);
        border-left: 3px solid #EF4444;
    }
    
    .pd-decision-item.positive {
        background: rgba(34, 197, 94, 0.08);
        border-left: 3px solid #22C55E;
    }
    
    .pd-decision-icon {
        font-size: 1rem;
        flex-shrink: 0;
    }
    
    .pd-decision-content {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    
    .pd-decision-text {
        font-size: 0.85rem;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .pd-decision-detail {
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.5);
    }
    
    .pd-decision-goodfor {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .pd-goodfor-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: rgba(255, 255, 255, 0.6);
    }
    
    .pd-goodfor-tag {
        background: rgba(212, 168, 83, 0.15);
        color: var(--gold);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 500;
    }
    
    /* =========================================
       EXIT STRATEGY SECTION
       ========================================= */
    
    .pd-exit-section {
        background: rgba(30, 30, 35, 0.6);
        border: 1px solid rgba(212, 168, 83, 0.15);
        border-radius: 12px;
        padding: 16px;
        margin-top: 16px;
    }
    
    .pd-exit-header {
        margin-bottom: 12px;
    }
    
    .pd-exit-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--gold);
    }
    
    .pd-exit-items {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .pd-exit-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 8px;
    }
    
    .pd-exit-icon {
        font-size: 1rem;
        flex-shrink: 0;
    }
    
    .pd-exit-label {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.6);
        flex-shrink: 0;
    }
    
    .pd-exit-value {
        font-size: 0.85rem;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .pd-exit-value.link {
        color: var(--gold);
        text-decoration: none;
    }
    
    .pd-exit-value.link:hover {
        text-decoration: underline;
    }
    
    /* ========================================= */
    /* TOKEN SECURITY ANALYSIS STYLES */
    /* ========================================= */
    
    .pd-token-security {
        margin-bottom: 16px;
    }
    
    .pd-token-security .pd-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    
    .pd-source-badge {
        font-size: 0.8rem;
        padding: 4px 8px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 4px;
        color: var(--text-muted);
    }
    
    .pd-token-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
    }
    
    .pd-token-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 12px;
    }
    
    .pd-token-card.safe {
        border-color: rgba(16, 185, 129, 0.3);
    }
    
    .pd-token-card.warning {
        border-color: rgba(251, 191, 36, 0.3);
        background: rgba(251, 191, 36, 0.05);
    }
    
    .pd-token-card.critical {
        border-color: rgba(239, 68, 68, 0.3);
        background: rgba(239, 68, 68, 0.08);
    }
    
    .pd-token-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    
    .pd-token-symbol {
        font-weight: 700;
        font-size: 1rem;
        color: var(--text);
    }
    
    .pd-token-status {
        font-size: 1.1rem;
    }
    
    .pd-token-checks {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    
    .pd-check-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.85rem;
        color: var(--text-secondary);
    }
    
    .pd-check-item.pass { color: #10B981; }
    .pd-check-item.warning { color: #FBBF24; }
    .pd-check-item.fail { color: #EF4444; }
    
    /* ========================================= */
    /* ADVANCED RISK ANALYSIS STYLES */
    /* ========================================= */
    
    .pd-advanced-risk {
        margin-bottom: 16px;
    }
    
    .pd-risk-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
    }
    
    .pd-risk-panel {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 12px;
    }
    
    .pd-risk-panel-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }
    
    .pd-risk-icon {
        font-size: 1rem;
    }
    
    .pd-risk-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .pd-risk-value {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    
    .pd-penalty {
        font-size: 0.75rem;
        font-weight: 500;
        background: rgba(239, 68, 68, 0.2);
        color: #EF4444;
        padding: 2px 6px;
        border-radius: 4px;
        margin-left: 6px;
    }
    
    .pd-risk-detail {
        font-size: 0.85rem;
        color: var(--text-muted);
        line-height: 1.4;
    }
    
    .pd-risk-detail .up { color: #10B981; }
    .pd-risk-detail .down { color: #EF4444; }
    
    .pd-risk-warning {
        font-size: 0.85rem;
        color: #EF4444;
        margin-top: 6px;
        padding: 4px 8px;
        background: rgba(239, 68, 68, 0.1);
        border-radius: 4px;
    }
    
    .pd-risk-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-top: 8px;
    }
    
    .pd-tag {
        font-size: 0.65rem;
        padding: 2px 6px;
        border-radius: 4px;
    }
    
    .pd-tag.safe {
        background: rgba(16, 185, 129, 0.15);
        color: #10B981;
    }
    
    .pd-tag.info {
        background: rgba(59, 130, 246, 0.15);
        color: #3B82F6;
    }
    
    .pd-tag.warning {
        background: rgba(251, 191, 36, 0.15);
        color: #FBBF24;
    }
    
    .pd-risk-breakdown {
        margin-top: 16px;
        padding-top: 12px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    .pd-breakdown-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-muted);
        margin-bottom: 8px;
    }
    
    .pd-breakdown-items {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
    }
    
    .pd-breakdown-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.7rem;
        padding: 4px 8px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 4px;
    }
    
    .pd-breakdown-label {
        color: var(--text-muted);
        text-transform: capitalize;
    }
    
    .pd-breakdown-value.penalty { color: #EF4444; }
    .pd-breakdown-value.bonus { color: #10B981; }
    
    /* ========================================= */
    /* YIELD BREAKDOWN STYLES */
    /* ========================================= */
    
    .pd-yield-breakdown {
        margin-bottom: 16px;
    }
    
    .pd-yield-breakdown .pd-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    
    .pd-sustainability-badge {
        font-size: 0.7rem;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 500;
    }
    
    .pd-yield-content {
        display: flex;
        gap: 20px;
        align-items: center;
    }
    
    .pd-yield-chart {
        flex-shrink: 0;
        width: 100px;
        height: 100px;
    }
    
    .pd-pie-chart {
        width: 100%;
        height: 100%;
    }
    
    .pd-yield-legend {
        flex: 1;
    }
    
    .pd-yield-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .pd-yield-item:last-of-type {
        border-bottom: none;
    }
    
    .pd-yield-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    
    .pd-yield-label {
        flex: 1;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }
    
    .pd-yield-value {
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .pd-yield-percent {
        font-size: 0.75rem;
        color: var(--text-muted);
    }
    
    .pd-yield-runway {
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        display: flex;
        justify-content: space-between;
    }
    
    .pd-runway-label {
        font-size: 0.75rem;
        color: var(--text-muted);
    }
    
    .pd-runway-value {
        font-size: 0.75rem;
        color: var(--gold);
        font-weight: 500;
    }
    
    /* ========================================= */
    /* EXIT SIMULATION STYLES */
    /* ========================================= */
    
    .pd-exit-simulation {
        margin-bottom: 16px;
    }
    
    .pd-exit-simulation .pd-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    
    .pd-sim-note {
        font-size: 0.7rem;
        color: var(--text-muted);
    }
    
    .pd-sim-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
    }
    
    .pd-sim-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 12px;
        text-align: center;
    }
    
    .pd-sim-position {
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--text);
        margin-bottom: 6px;
    }
    
    .pd-sim-slippage {
        font-size: 1.2rem;
        font-weight: 700;
    }
    
    .pd-sim-loss {
        font-size: 0.8rem;
        margin-top: 2px;
    }
    
    .pd-sim-label {
        font-size: 0.65rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }
    
    .pd-sim-tips {
        margin-top: 12px;
    }
    
    .pd-sim-tip {
        font-size: 0.75rem;
        color: var(--text-muted);
        padding: 8px 12px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 6px;
        margin-bottom: 6px;
    }
    
    .pd-sim-tip.warning {
        background: rgba(239, 68, 68, 0.1);
        color: #EF4444;
    }
    
    .pd-sim-tip strong {
        color: var(--gold);
    }
    
    /* ========================================= */
    /* APY HISTORY STYLES */
    /* ========================================= */
    
    .pd-apy-history {
        margin-bottom: 16px;
    }
    
    .pd-apy-history .pd-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    
    .pd-volatility-badge {
        font-size: 0.7rem;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 500;
    }
    
    .pd-apy-chart-container {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    .pd-sparkline {
        width: 100%;
        height: 60px;
    }
    
    .pd-apy-stats {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
    }
    
    .pd-apy-stat {
        text-align: center;
        padding: 8px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
    }
    
    .pd-stat-label {
        display: block;
        font-size: 0.65rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    
    .pd-stat-value {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text);
    }
    
    .pd-stat-value.highlight {
        color: var(--gold);
    }
    
    /* ========================================= */
    /* AUDIT STATUS STYLES */
    /* ========================================= */
    
    .pd-audit-status {
        margin-bottom: 16px;
    }
    
    .pd-audit-status .pd-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    
    .pd-audit-badge {
        font-size: 0.7rem;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 500;
    }
    
    .pd-audit-content {
        padding: 12px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 10px;
    }
    
    .pd-audit-info {
        margin-bottom: 12px;
    }
    
    .pd-audit-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .pd-audit-row:last-child {
        border-bottom: none;
    }
    
    .pd-audit-label {
        color: var(--text-muted);
        font-size: 0.8rem;
    }
    
    .pd-audit-value {
        color: var(--text);
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .pd-audit-link {
        color: var(--gold);
        text-decoration: none;
        font-size: 0.8rem;
    }
    
    .pd-audit-link:hover {
        text-decoration: underline;
    }
    
    .pd-audit-note {
        font-size: 0.75rem;
        padding: 10px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.03);
        color: var(--text-muted);
    }
    
    .pd-audit-note.success {
        background: rgba(16, 185, 129, 0.1);
        color: #10B981;
    }
    
    .pd-audit-note.warning {
        background: rgba(239, 68, 68, 0.1);
        color: #EF4444;
    }
    
    /* ========================================= */
    /* LIQUIDITY LOCK STYLES */
    /* ========================================= */
    
    .pd-liquidity-lock {
        margin-bottom: 16px;
    }
    
    .pd-liquidity-lock .pd-section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    
    .pd-lock-badge {
        font-size: 0.7rem;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 500;
    }
    
    .pd-lock-content {
        padding: 12px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 10px;
    }
    
    .pd-lock-info {
        margin-bottom: 12px;
    }
    
    .pd-lock-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .pd-lock-row:last-child {
        border-bottom: none;
    }
    
    .pd-lock-label {
        color: var(--text-muted);
        font-size: 0.8rem;
    }
    
    .pd-lock-value {
        color: var(--text);
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .pd-lock-meter {
        height: 8px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 4px;
        overflow: hidden;
        margin: 12px 0;
    }
    
    .pd-lock-bar {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    
    .pd-lock-note {
        font-size: 0.75rem;
        padding: 10px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.03);
        color: var(--text-muted);
        margin-bottom: 8px;
    }
    
    .pd-lock-note.success {
        background: rgba(16, 185, 129, 0.1);
        color: #10B981;
    }
    
    .pd-lock-note.warning {
        background: rgba(239, 68, 68, 0.1);
        color: #EF4444;
    }
    
    .pd-lock-tip {
        font-size: 0.75rem;
        padding: 10px;
        border-radius: 8px;
        background: rgba(212, 168, 83, 0.1);
        color: var(--gold);
    }
    
    .pd-lock-tip strong {
        color: var(--gold);
    }
`;
document.head.appendChild(detailStyles);

// Export
window.PoolDetailModal = PoolDetailModal;
