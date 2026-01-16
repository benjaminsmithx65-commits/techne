/**
 * Protocol Icons & Metadata
 * Official logos from DefiLlama, protocol websites
 */

const PROTOCOL_ICONS = {
    // Major Protocols
    aave: {
        name: 'Aave',
        icon: '/icons/protocols/aave.png',
        color: '#B6509E',
        chains: ['ethereum', 'arbitrum', 'optimism', 'polygon', 'base']
    },
    compound: {
        name: 'Compound',
        icon: '/icons/protocols/compound.png',
        color: '#00D395',
        chains: ['ethereum', 'arbitrum', 'base']
    },
    uniswap: {
        name: 'Uniswap',
        icon: '/icons/protocols/uniswap.png',
        color: '#FF007A',
        chains: ['ethereum', 'arbitrum', 'optimism', 'polygon', 'base']
    },
    curve: {
        name: 'Curve',
        icon: '/icons/protocols/curve.png',
        color: '#FF0000',
        chains: ['ethereum', 'arbitrum', 'optimism', 'polygon']
    },
    lido: {
        name: 'Lido',
        icon: '/icons/protocols/lido.png',
        color: '#00A3FF',
        chains: ['ethereum']
    },
    convex: {
        name: 'Convex',
        icon: '/icons/protocols/convex.png',
        color: '#3A3A3A',
        chains: ['ethereum']
    },
    yearn: {
        name: 'Yearn',
        icon: '/icons/protocols/yearn.png',
        color: '#006AE3',
        chains: ['ethereum', 'arbitrum', 'optimism']
    },

    // Base/L2 Specific
    aerodrome: {
        name: 'Aerodrome',
        icon: '/icons/protocols/aerodrome.png',
        color: '#0052FF',
        chains: ['base']
    },
    velodrome: {
        name: 'Velodrome',
        icon: 'https://icons.llama.fi/velodrome.png',
        color: '#FF0420',
        chains: ['optimism']
    },

    // GMX & Perps
    gmx: {
        name: 'GMX',
        icon: '/icons/protocols/gmx.png',
        color: '#1E90FF',
        chains: ['arbitrum', 'avalanche']
    },

    // New Protocols (Airdrop Potential)
    morpho: {
        name: 'Morpho',
        icon: '/icons/protocols/morpho.png',
        color: '#2470FF',
        chains: ['ethereum', 'base']
    },
    pendle: {
        name: 'Pendle',
        icon: '/icons/protocols/pendle.png',
        color: '#15BDB6',
        chains: ['ethereum', 'arbitrum']
    },
    eigenlayer: {
        name: 'EigenLayer',
        icon: '/icons/protocols/eigenlayer.png',
        color: '#6366F1',
        chains: ['ethereum']
    },

    // RWA & Stablecoin
    peapods: {
        name: 'Peapods Finance',
        icon: '/icons/protocols/peapods.png',
        color: '#00D26A',
        chains: ['ethereum', 'base', 'arbitrum']
    },
    midas: {
        name: 'Midas',
        icon: 'https://icons.llama.fi/midas.png',
        color: '#FFD700',
        chains: ['ethereum', 'base']
    },
    maker: {
        name: 'MakerDAO',
        icon: 'https://icons.llama.fi/makerdao.png',
        color: '#1AAB9B',
        chains: ['ethereum']
    },

    // Lending
    radiant: {
        name: 'Radiant',
        icon: '/icons/protocols/radiant.png',
        color: '#00D9FF',
        chains: ['arbitrum']
    },
    spark: {
        name: 'Spark',
        icon: '/icons/protocols/spark.png',
        color: '#EB8C00',
        chains: ['ethereum']
    },

    // More Base protocols
    beefy: {
        name: 'Beefy',
        icon: '/icons/protocols/beefy.png',
        color: '#6DCB56',
        chains: ['base', 'arbitrum', 'optimism', 'polygon']
    },
    moonwell: {
        name: 'Moonwell',
        icon: '/icons/protocols/moonwell.png',
        color: '#5A67D8',
        chains: ['base', 'optimism']
    },
    seamless: {
        name: 'Seamless',
        icon: '/icons/protocols/seamless.png',
        color: '#00D395',
        chains: ['base']
    },
    balancer: {
        name: 'Balancer',
        icon: '/icons/protocols/balancer.png',
        color: '#1E1E1E',
        chains: ['ethereum', 'arbitrum', 'base', 'polygon']
    },

    // Solana
    meteora: {
        name: 'Meteora',
        icon: '/icons/protocols/meteora.png',
        color: '#00C2FF',
        chains: ['solana']
    },
    orca: {
        name: 'Orca',
        icon: '/icons/protocols/orca.png',
        color: '#FFDD00',
        chains: ['solana']
    },
    jupiter: {
        name: 'Jupiter',
        icon: '/icons/protocols/jupiter.png',
        color: '#00FF94',
        chains: ['solana']
    },
    kamino: {
        name: 'Kamino',
        icon: '/icons/protocols/kamino.png',
        color: '#6366F1',
        chains: ['solana']
    },
    marginfi: {
        name: 'marginfi',
        icon: '/icons/protocols/marginfi.png',
        color: '#00D26A',
        chains: ['solana']
    },
    drift: {
        name: 'Drift',
        icon: '/icons/protocols/drift.png',
        color: '#B14FFF',
        chains: ['solana']
    },
    solend: {
        name: 'Solend',
        icon: '/icons/protocols/solend.png',
        color: '#00B4D8',
        chains: ['solana']
    },
    raydium: {
        name: 'Raydium',
        icon: '/icons/protocols/raydium.png',
        color: '#7CEBFE',
        chains: ['solana']
    },
    jito: {
        name: 'Jito',
        icon: '/icons/protocols/jito.png',
        color: '#00D26A',
        chains: ['solana']
    },
    marinade: {
        name: 'Marinade',
        icon: '/icons/protocols/marinade.png',
        color: '#2DD4BF',
        chains: ['solana']
    },
    sanctum: {
        name: 'Sanctum',
        icon: '/icons/protocols/sanctum.png',
        color: '#9333EA',
        chains: ['solana']
    },

    // More
    sonne: {
        name: 'Sonne',
        icon: '/icons/protocols/sonne.png',
        color: '#FF6B35',
        chains: ['base', 'optimism']
    },
    exactly: {
        name: 'Exactly',
        icon: '/icons/protocols/exactly.png',
        color: '#00C2FF',
        chains: ['base', 'optimism']
    },
    extra: {
        name: 'Extra',
        icon: '/icons/protocols/extra.png',
        color: '#00FFB2',
        chains: ['base']
    },
    origin: {
        name: 'Origin',
        icon: '/icons/protocols/origin.png',
        color: '#0074F0',
        chains: ['ethereum', 'base']
    },
    merkl: {
        name: 'Merkl',
        icon: '/icons/protocols/merkl.png',
        color: '#FFB800',
        chains: ['base', 'arbitrum', 'optimism', 'ethereum']
    }
};

// Chain Icons
const CHAIN_ICONS = {
    ethereum: {
        name: 'Ethereum',
        icon: 'https://icons.llama.fi/ethereum.png',
        color: '#627EEA',
        chainId: 1
    },
    arbitrum: {
        name: 'Arbitrum',
        icon: 'https://icons.llama.fi/arbitrum.png',
        color: '#28A0F0',
        chainId: 42161
    },
    optimism: {
        name: 'Optimism',
        icon: 'https://icons.llama.fi/optimism.png',
        color: '#FF0420',
        chainId: 10
    },
    base: {
        name: 'Base',
        icon: 'https://icons.llama.fi/base.png',
        color: '#0052FF',
        chainId: 8453
    },
    polygon: {
        name: 'Polygon',
        icon: 'https://icons.llama.fi/polygon.png',
        color: '#8247E5',
        chainId: 137
    },
    scroll: {
        name: 'Scroll',
        icon: 'https://icons.llama.fi/scroll.png',
        color: '#FFEEDA',
        chainId: 534352
    },
    linea: {
        name: 'Linea',
        icon: 'https://icons.llama.fi/linea.png',
        color: '#121212',
        chainId: 59144
    },
    zksync: {
        name: 'zkSync Era',
        icon: 'https://icons.llama.fi/zksync-era.png',
        color: '#8C8DFC',
        chainId: 324
    }
};

// Get protocol icon HTML
function getProtocolIcon(protocolId, size = 24) {
    const protocol = PROTOCOL_ICONS[protocolId.toLowerCase()];
    if (protocol) {
        return `<img src="${protocol.icon}" alt="${protocol.name}" width="${size}" height="${size}" class="protocol-icon" onerror="this.src='/icons/default.svg'">`;
    }
    return `<div class="protocol-icon-placeholder" style="width:${size}px;height:${size}px;"></div>`;
}

// Get chain icon HTML
function getChainIcon(chainId, size = 20) {
    const chain = CHAIN_ICONS[chainId.toLowerCase()];
    if (chain) {
        return `<img src="${chain.icon}" alt="${chain.name}" width="${size}" height="${size}" class="chain-icon" onerror="this.style.display='none'">`;
    }
    return '';
}

// Get protocol icon URL (used by pool-detail.js)
function getProtocolIconUrl(protocolName) {
    if (!protocolName) return '/icons/default.svg';

    // Known mappings for common variations
    const EXPLICIT_MAPPINGS = {
        'aerodrome slipstream': 'aerodrome',
        'aerodrome-slipstream': 'aerodrome',
        'aerodrome-slipstream-2': 'aerodrome',
        'aave v3': 'aave',
        'aave-v3': 'aave',
        'compound v3': 'compound',
        'compound-v3': 'compound',
        'uniswap v2': 'uniswap',
        'uniswap v3': 'uniswap',
        'uniswap v4': 'uniswap',
        'uniswap-v2': 'uniswap',
        'uniswap-v3': 'uniswap',
        'uniswap-v4': 'uniswap',
        'uniswap-v2-base': 'uniswap',
        'uniswap-v3-base': 'uniswap',
        'uniswap-v4-base': 'uniswap',
        'beefy-base': 'beefy',
        'beefy-arbitrum': 'beefy',
        'beefy-optimism': 'beefy',
        'morpho blue': 'morpho',
        'morpho-blue': 'morpho',
    };

    const lowerName = protocolName.toLowerCase().trim();

    // Check explicit mappings first
    if (EXPLICIT_MAPPINGS[lowerName]) {
        const key = EXPLICIT_MAPPINGS[lowerName];
        const protocol = PROTOCOL_ICONS[key];
        if (protocol && protocol.icon) return protocol.icon;
        return `/icons/protocols/${key}.png`;
    }

    // Normalize: remove chain suffixes and common protocol suffixes
    let key = lowerName
        .replace(/-(?:base|arbitrum|optimism|polygon|ethereum|mainnet)$/gi, '')  // Remove chain suffix FIRST
        .replace(/\s+slipstream/gi, '')
        .replace(/\s+finance/gi, '')
        .replace(/\s+protocol/gi, '')
        .replace(/\s+v[234]/gi, '')
        .replace(/-v[234]/gi, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '')
        .trim();

    // Check known protocols
    const protocol = PROTOCOL_ICONS[key];
    if (protocol && protocol.icon) return protocol.icon;

    // Check for local icon file
    return `/icons/protocols/${key}.png`;
}

// Get chain icon URL
function getChainIconUrl(chainName) {
    if (!chainName) return '';
    const chain = CHAIN_ICONS[chainName.toLowerCase()];
    if (chain) return chain.icon;
    return `https://icons.llama.fi/chains/rsz_${chainName.toLowerCase()}.jpg`;
}

// Export for use
window.ProtocolIcons = {
    protocols: PROTOCOL_ICONS,
    chains: CHAIN_ICONS,
    getProtocolIcon,
    getChainIcon
};

// Global helper functions for pool-detail.js
window.getProtocolIconUrl = getProtocolIconUrl;
window.getChainIconUrl = getChainIconUrl;
