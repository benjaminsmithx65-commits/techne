/**
 * Techne AI Vault Agent - Extended Version
 * 
 * Autonomous AI agent that manages vault allocations.
 * Supports comprehensive configuration from Agent Builder UI.
 */

// Mock Beefy service for standalone usage
const beefyServiceMock = {
    baseVaults: [],
    async fetchBaseVaults() {
        // In production, this would fetch from Beefy API
        this.baseVaults = [];
    }
};

class VaultAgent {
    constructor() {
        this.agentWallet = null;
        this.agentAddress = null;
        this.userAddress = null;
        this.provider = null;
        this.isActive = false;

        // Extended configuration
        this.config = {
            // Strategy preset
            preset: 'balanced-growth',

            // Risk & Returns
            riskLevel: 'medium',
            minApy: 10,
            maxApy: 50,
            maxDrawdown: 20,

            // Protocols whitelist
            protocols: ['aerodrome', 'aave', 'compound'],

            // Assets whitelist
            preferredAssets: ['USDC', 'WETH'],

            // Duration & Allocation
            duration: 30,
            maxAllocationPerVault: 25,
            vaultCount: 5,

            // Advanced settings
            autoRebalance: true,
            rebalanceThreshold: 5,
            maxGasPrice: 50,
            slippage: 0.5,
            compoundFrequency: 7,
            onlyAudited: true,
            avoidIL: false,
            emergencyExit: true
        };

        this.currentAllocations = [];
        this.executionHistory = [];

        // Protocol metadata
        this.protocolInfo = {
            aerodrome: { name: 'Aerodrome', type: 'dex', audited: true, chain: 'base' },
            aave: { name: 'Aave V3', type: 'lending', audited: true, chain: 'multi' },
            compound: { name: 'Compound', type: 'lending', audited: true, chain: 'multi' },
            uniswap: { name: 'Uniswap', type: 'dex', audited: true, chain: 'multi' },
            curve: { name: 'Curve', type: 'dex', audited: true, chain: 'multi' },
            moonwell: { name: 'Moonwell', type: 'lending', audited: true, chain: 'base' },
            morpho: { name: 'Morpho', type: 'lending', audited: true, chain: 'multi' },
            extra: { name: 'Extra Finance', type: 'leverage', audited: false, chain: 'base' },
            beefy: { name: 'Beefy', type: 'yield', audited: true, chain: 'multi' },
            yearn: { name: 'Yearn', type: 'yield', audited: true, chain: 'multi' },
            convex: { name: 'Convex', type: 'yield', audited: true, chain: 'ethereum' },
            stargate: { name: 'Stargate', type: 'bridge', audited: true, chain: 'multi' }
        };

        // Asset metadata
        this.assetInfo = {
            // Stablecoins
            USDC: { type: 'stable', risk: 'low' },
            USDT: { type: 'stable', risk: 'low' },
            DAI: { type: 'stable', risk: 'low' },
            FRAX: { type: 'stable', risk: 'medium' },
            crvUSD: { type: 'stable', risk: 'medium' },
            GHO: { type: 'stable', risk: 'medium' },
            LUSD: { type: 'stable', risk: 'low' },
            'USD+': { type: 'stable', risk: 'medium' },
            // ETH & LSTs
            WETH: { type: 'eth', risk: 'medium' },
            cbETH: { type: 'lst', risk: 'low' },
            wstETH: { type: 'lst', risk: 'low' },
            rETH: { type: 'lst', risk: 'low' },
            stETH: { type: 'lst', risk: 'low' },
            swETH: { type: 'lst', risk: 'medium' },
            // BTC
            WBTC: { type: 'btc', risk: 'medium' },
            cbBTC: { type: 'btc', risk: 'low' },
            tBTC: { type: 'btc', risk: 'medium' },
            // DeFi
            AERO: { type: 'defi', risk: 'high' },
            CRV: { type: 'defi', risk: 'high' },
            AAVE: { type: 'defi', risk: 'medium' },
            COMP: { type: 'defi', risk: 'medium' },
            UNI: { type: 'defi', risk: 'medium' }
        };
    }

    /**
     * Set full configuration from UI
     */
    setConfig(configUpdate) {
        this.config = { ...this.config, ...configUpdate };
        console.log('[Agent] Configuration updated:', this.config);
    }

    /**
     * Initialize agent with Smart Account address (from backend)
     */
    async initAgentWallet(provider, smartAccountAddress) {
        try {
            this.provider = provider;
            // ERC-8004: Use Smart Account address from backend deployment
            this.agentAddress = smartAccountAddress;

            console.log(`[Agent] ERC-8004 Smart Account initialized: ${this.agentAddress}`);
            this.isActive = true;
            return this.agentAddress;
        } catch (error) {
            console.error('[Agent] Failed to init Smart Account:', error);
            throw error;
        }
    }

    /**
     * Create new agent wallet (ERC-8004 Smart Account)
     * NOTE: Actual Smart Account is created by backend via SmartAccountService
     * This method returns a placeholder indicating the backend will deploy the account
     */
    static createAgentWallet() {
        return {
            address: null,  // Will be set by backend Smart Account creation
            accountType: 'erc8004',
            fundingRequired: true,
            message: 'Smart Account will be deployed on-chain by backend'
        };
    }

    /**
     * Analyze vaults and filter by configuration
     */
    async analyzeAndAllocate() {
        if (!this.isActive) throw new Error('Agent not active');

        await beefyServiceMock.fetchBaseVaults();
        const vaults = beefyServiceMock.baseVaults;

        // Apply all filters
        const eligible = vaults.filter(v => this.meetsAllCriteria(v));

        // Score and sort
        const scored = eligible.map(v => ({
            vault: v,
            score: this.scoreVault(v)
        })).sort((a, b) => b.score - a.score);

        // Take top N vaults based on config
        const count = this.config.vaultCount === 0 ?
            Math.min(scored.length, 10) : this.config.vaultCount;

        const topVaults = scored.slice(0, count);
        const allocations = [];

        for (const { vault } of topVaults) {
            allocations.push({
                vaultId: vault.id,
                vaultName: vault.name,
                apy: vault.apy,
                platform: vault.platform,
                assets: vault.assets,
                allocationPercent: (100 / count).toFixed(1),
                timestamp: new Date().toISOString()
            });
        }

        this.currentAllocations = allocations;
        this.executionHistory.push({
            action: 'allocation',
            vaults: allocations.length,
            config: { ...this.config },
            timestamp: new Date().toISOString()
        });

        return allocations;
    }

    /**
     * Check if vault meets ALL configured criteria
     */
    meetsAllCriteria(vault) {
        const apy = parseFloat(vault.apy);

        // APY range check
        if (apy < this.config.minApy || apy > this.config.maxApy) return false;

        // Protocol check
        if (this.config.protocols.length > 0) {
            if (!this.config.protocols.includes(vault.platform)) return false;
        }

        // Assets check
        if (this.config.preferredAssets.length > 0) {
            const hasPreferred = vault.assets.some(a =>
                this.config.preferredAssets.includes(a));
            if (!hasPreferred) return false;
        }

        // Audited check
        if (this.config.onlyAudited) {
            const protocolInfo = this.protocolInfo[vault.platform];
            if (protocolInfo && !protocolInfo.audited) return false;
        }

        // IL avoidance check
        if (this.config.avoidIL) {
            const protocolInfo = this.protocolInfo[vault.platform];
            if (protocolInfo && protocolInfo.type === 'dex') return false;
            if (vault.assets.length > 1) return false; // Multi-asset = IL risk
        }

        // Risk level check
        if (!this.meetsRiskCriteria(vault)) return false;

        return true;
    }

    /**
     * Risk criteria based on risk level setting
     */
    meetsRiskCriteria(vault) {
        const apy = parseFloat(vault.apy);
        const { riskLevel } = this.config;

        // Higher APY generally = higher risk
        switch (riskLevel) {
            case 'low':
                if (apy > 20) return false;
                // Prefer stables and LSTs
                const lowRiskAssets = ['USDC', 'USDT', 'DAI', 'cbETH', 'wstETH', 'rETH'];
                if (!vault.assets.some(a => lowRiskAssets.includes(a))) return false;
                break;
            case 'medium':
                if (apy > 60) return false;
                break;
            case 'high':
                // Allow everything
                break;
        }
        return true;
    }

    /**
     * Score vault for ranking
     */
    scoreVault(vault) {
        let score = 0;
        const apy = parseFloat(vault.apy);

        // APY score (0-40)
        score += Math.min(apy, 40);

        // TVL score (0-30)
        if (vault.tvl > 10000000) score += 30;
        else if (vault.tvl > 1000000) score += 25;
        else if (vault.tvl > 100000) score += 15;
        else if (vault.tvl > 10000) score += 5;

        // Audited bonus (0-15)
        const protocolInfo = this.protocolInfo[vault.platform];
        if (protocolInfo?.audited) score += 15;

        // Preferred asset bonus (0-10)
        const hasPreferred = vault.assets.some(a =>
            this.config.preferredAssets.includes(a));
        if (hasPreferred) score += 10;

        // Stable asset bonus for low risk (0-10)
        if (this.config.riskLevel === 'low') {
            const hasStable = vault.assets.some(a =>
                ['USDC', 'USDT', 'DAI'].includes(a));
            if (hasStable) score += 10;
        }

        return score;
    }

    /**
     * Check if rebalance needed
     */
    needsRebalance() {
        if (!this.config.autoRebalance) return false;
        // In production: compare current allocations vs target
        return false;
    }

    /**
     * Emergency exit if drawdown exceeds threshold
     */
    async checkEmergencyExit() {
        if (!this.config.emergencyExit) return false;
        // In production: check portfolio value vs initial
        return false;
    }

    /**
     * Get agent status
     */
    getStatus() {
        return {
            isActive: this.isActive,
            agentAddress: this.agentAddress,
            config: this.config,
            allocations: this.currentAllocations,
            historyCount: this.executionHistory.length,
            lastAction: this.executionHistory[this.executionHistory.length - 1]
        };
    }
}

// Export singleton
const vaultAgent = new VaultAgent();
window.VaultAgent = vaultAgent;

export default vaultAgent;
