/**
 * Protocol Icons & Metadata
 * Official logos from DefiLlama, protocol websites
 */

const PROTOCOL_ICONS = {
    // Major Protocols
    aave: {
        name: 'Aave',
        icon: 'https://icons.llama.fi/aave.png',
        color: '#B6509E',
        chains: ['ethereum', 'arbitrum', 'optimism', 'polygon', 'base']
    },
    compound: {
        name: 'Compound',
        icon: 'https://icons.llama.fi/compound-finance.png',
        color: '#00D395',
        chains: ['ethereum', 'arbitrum', 'base']
    },
    uniswap: {
        name: 'Uniswap',
        icon: 'https://icons.llama.fi/uniswap.png',
        color: '#FF007A',
        chains: ['ethereum', 'arbitrum', 'optimism', 'polygon', 'base']
    },
    curve: {
        name: 'Curve',
        icon: 'https://icons.llama.fi/curve.png',
        color: '#FF0000',
        chains: ['ethereum', 'arbitrum', 'optimism', 'polygon']
    },
    lido: {
        name: 'Lido',
        icon: 'https://icons.llama.fi/lido.png',
        color: '#00A3FF',
        chains: ['ethereum']
    },
    convex: {
        name: 'Convex',
        icon: 'https://icons.llama.fi/convex-finance.png',
        color: '#3A3A3A',
        chains: ['ethereum']
    },
    yearn: {
        name: 'Yearn',
        icon: 'https://icons.llama.fi/yearn-finance.png',
        color: '#006AE3',
        chains: ['ethereum', 'arbitrum', 'optimism']
    },

    // Base/L2 Specific
    aerodrome: {
        name: 'Aerodrome',
        icon: 'https://icons.llama.fi/aerodrome.png',
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
        icon: 'https://icons.llama.fi/gmx.png',
        color: '#1E90FF',
        chains: ['arbitrum', 'avalanche']
    },

    // New Protocols (Airdrop Potential)
    morpho: {
        name: 'Morpho',
        icon: 'https://icons.llama.fi/morpho.png',
        color: '#2470FF',
        chains: ['ethereum', 'base']
    },
    pendle: {
        name: 'Pendle',
        icon: 'https://icons.llama.fi/pendle.png',
        color: '#15BDB6',
        chains: ['ethereum', 'arbitrum']
    },
    eigenlayer: {
        name: 'EigenLayer',
        icon: 'https://icons.llama.fi/eigenlayer.png',
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
        icon: 'https://icons.llama.fi/radiant.png',
        color: '#00D9FF',
        chains: ['arbitrum']
    },
    spark: {
        name: 'Spark',
        icon: 'https://icons.llama.fi/spark.png',
        color: '#EB8C00',
        chains: ['ethereum']
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

// Export for use
window.ProtocolIcons = {
    protocols: PROTOCOL_ICONS,
    chains: CHAIN_ICONS,
    getProtocolIcon,
    getChainIcon
};
