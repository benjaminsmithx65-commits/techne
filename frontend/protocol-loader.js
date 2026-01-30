/**
 * Protocol Loader - Dynamic Protocol Loading from API
 * Fetches protocols from /api/protocols and renders them in Build UI
 */

class ProtocolLoader {
    constructor() {
        this.protocols = {
            single: [],
            dual: []
        };
        this.selectedProtocols = new Set();
        this.currentPoolType = 'single';
    }

    /**
     * Fetch protocols from backend API
     */
    async loadProtocols(poolType = 'all') {
        try {
            const response = await fetch(`/api/protocols?pool_type=${poolType}`);
            const data = await response.json();

            if (data.success) {
                if (poolType === 'all') {
                    this.protocols.single = data.protocols.filter(p => p.pool_type === 'single');
                    this.protocols.dual = data.protocols.filter(p => p.pool_type === 'dual');
                } else {
                    this.protocols[poolType] = data.protocols;
                }
                console.log(`[ProtocolLoader] Loaded ${data.count} protocols`);
                return data.protocols;
            }
            return [];
        } catch (error) {
            console.error('[ProtocolLoader] Failed to load protocols:', error);
            return [];
        }
    }

    /**
     * Render protocols grid for given pool type
     */
    renderProtocolsGrid(containerId, poolType) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`[ProtocolLoader] Container ${containerId} not found`);
            return;
        }

        this.currentPoolType = poolType;
        const protocols = this.protocols[poolType] || [];

        if (protocols.length === 0) {
            container.innerHTML = `
                <div class="protocols-loading">
                    <div class="loading-spinner"></div>
                    <p>Loading protocols...</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="protocols-grid-header">
                <span class="protocols-title">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                        <path d="M8 1L2 5V11L8 15L14 11V5L8 1Z" stroke="currentColor" stroke-width="1.3"/>
                        <path d="M8 15V8M8 8L2 5M8 8L14 5" stroke="currentColor" stroke-width="1.3"/>
                    </svg>
                    PROTOCOLS (${poolType.toUpperCase()})
                </span>
                <span class="protocols-count">${protocols.length} available</span>
            </div>
            <div class="protocols-cards">
                ${protocols.map(p => this.renderProtocolCard(p)).join('')}
            </div>
        `;

        // Add click handlers
        container.querySelectorAll('.protocol-card').forEach(card => {
            card.addEventListener('click', () => this.toggleProtocol(card));
        });
    }

    /**
     * Render single protocol card
     */
    renderProtocolCard(protocol) {
        const isSelected = this.selectedProtocols.has(protocol.id);
        const riskColor = this.getRiskColor(protocol.risk_level);
        const icon = this.getProtocolIcon(protocol.id);
        const isImplemented = protocol.implemented !== false;  // Default to true

        // Format TVL
        const tvlFormatted = protocol.tvl >= 1000000
            ? `$${(protocol.tvl / 1000000).toFixed(0)}M`
            : `$${(protocol.tvl / 1000).toFixed(0)}K`;

        // Special badges
        let badge = '';
        if (!isImplemented) badge = '<span class="proto-badge coming-soon">Coming Soon</span>';
        else if (protocol.is_stableswap) badge = '<span class="proto-badge stable">Stableswap</span>';
        else if (protocol.is_leveraged_farm) badge = '<span class="proto-badge leverage">Leveraged</span>';
        else if (protocol.is_reward_aggregator) badge = '<span class="proto-badge rewards">Rewards</span>';

        return `
            <div class="protocol-card ${isSelected ? 'selected' : ''} ${!isImplemented ? 'disabled' : ''}" 
                 data-protocol="${protocol.id}"
                 data-pool-type="${protocol.pool_type}"
                 data-implemented="${isImplemented}">
                <div class="proto-icon">${icon}</div>
                <div class="proto-info">
                    <span class="proto-name">${protocol.name}</span>
                    ${badge}
                </div>
                <div class="proto-stats">
                    <span class="proto-apy">${protocol.apy.toFixed(1)}% APY</span>
                    <span class="proto-tvl">${tvlFormatted}</span>
                </div>
                <div class="proto-risk" style="color: ${riskColor}">
                    ${protocol.risk_level.toUpperCase()}
                </div>
                <div class="proto-check">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M3 8L7 12L13 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
            </div>
        `;
    }

    /**
     * Toggle protocol selection
     */
    toggleProtocol(card) {
        const protocolId = card.dataset.protocol;
        const isImplemented = card.dataset.implemented !== 'false';

        // Don't allow selecting unimplemented protocols
        if (!isImplemented) {
            console.log('[ProtocolLoader] Protocol not yet implemented:', protocolId);
            return;
        }

        if (this.selectedProtocols.has(protocolId)) {
            this.selectedProtocols.delete(protocolId);
            card.classList.remove('selected');
        } else {
            this.selectedProtocols.add(protocolId);
            card.classList.add('selected');
        }

        console.log('[ProtocolLoader] Selected protocols:', [...this.selectedProtocols]);

        // Dispatch event for other components
        document.dispatchEvent(new CustomEvent('protocolsChanged', {
            detail: { selected: [...this.selectedProtocols] }
        }));
    }

    /**
     * Get selected protocol IDs
     */
    getSelectedProtocols() {
        return [...this.selectedProtocols];
    }

    /**
     * Get risk level color
     */
    getRiskColor(riskLevel) {
        const colors = {
            'low': '#22C55E',
            'medium': '#F59E0B',
            'high': '#EF4444',
            'critical': '#DC2626'
        };
        return colors[riskLevel] || colors.medium;
    }

    /**
     * Get protocol icon (SVG or emoji)
     */
    getProtocolIcon(protocolId) {
        const icons = {
            'aave': '🔷',
            'morpho': '🟣',
            'moonwell': '🌙',
            'compound': '🟢',
            'seamless': '🌊',
            'sonne': '☀️',
            'exactly': 'ℹ️',
            'avantis': '🛡️',
            'origin': '🔘',
            'convex': '📝',
            'beefy': '🐮',
            'aerodrome': '✈️',
            'uniswap': '🦄',
            'extra': '🔥',
            'merkl': '🎯',
            'curve': '🌈',
            'baseswap': '🔵',
            'sushiswap': '🍣',
            'balancer': '⚖️',
            'velodrome_v2': '🚴'
        };
        return icons[protocolId] || '🔹';
    }

    /**
     * Initialize and load all protocols
     */
    async init(containerId = 'protocolsGrid') {
        // Load all protocols
        await this.loadProtocols('all');

        // Render based on current pool type selection
        this.renderProtocolsGrid(containerId, this.currentPoolType);

        // Listen for pool type changes
        document.querySelectorAll('.pool-type-btn-build').forEach(btn => {
            btn.addEventListener('click', () => {
                const poolType = btn.dataset.poolType;
                this.currentPoolType = poolType === 'all' ? 'single' : poolType;
                this.renderProtocolsGrid(containerId, this.currentPoolType);
            });
        });

        console.log('[ProtocolLoader] Initialized');
    }
}

// Create global instance
window.protocolLoader = new ProtocolLoader();

// Auto-init when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Only init if we're on Build page with protocols container
    if (document.getElementById('protocolsGrid')) {
        window.protocolLoader.init();
    }
});
