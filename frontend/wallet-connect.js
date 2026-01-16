/**
 * Wallet Connect Module for Techne.finance
 * Supports multiple wallets: MetaMask, WalletConnect, Coinbase, Rainbow, etc.
 */

// Supported wallet types
const WALLET_TYPES = {
    METAMASK: 'metamask',
    COINBASE: 'coinbase',
    WALLETCONNECT: 'walletconnect',
    RAINBOW: 'rainbow',
    INJECTED: 'injected'
};

// Wallet icons and metadata
const WALLET_METADATA = {
    metamask: {
        name: 'MetaMask',
        icon: '🦊',
        description: 'Popular browser extension',
        rdns: 'io.metamask'
    },
    coinbase: {
        name: 'Coinbase Wallet',
        icon: '🔵',
        description: 'Easy to use mobile wallet',
        rdns: 'com.coinbase.wallet'
    },
    walletconnect: {
        name: 'WalletConnect',
        icon: '🔗',
        description: 'Connect with QR code',
        rdns: null
    },
    rainbow: {
        name: 'Rainbow',
        icon: '🌈',
        description: 'Beautiful mobile wallet',
        rdns: 'me.rainbow'
    },
    trust: {
        name: 'Trust Wallet',
        icon: '🛡️',
        description: 'Mobile DeFi wallet',
        rdns: 'com.trustwallet.app'
    },
    phantom: {
        name: 'Phantom',
        icon: '👻',
        description: 'Multi-chain wallet',
        rdns: 'app.phantom'
    },
    rabby: {
        name: 'Rabby',
        icon: '🐰',
        description: 'Security-focused wallet',
        rdns: 'io.rabby'
    }
};

// Detect available wallets
function detectAvailableWallets() {
    const wallets = [];

    if (typeof window.ethereum !== 'undefined') {
        // Check for EIP-6963 providers (new standard)
        if (window.ethereum.providers && Array.isArray(window.ethereum.providers)) {
            window.ethereum.providers.forEach(provider => {
                wallets.push({
                    type: 'injected',
                    provider: provider,
                    name: provider.isMetaMask ? 'MetaMask' :
                        provider.isCoinbaseWallet ? 'Coinbase Wallet' :
                            provider.isRabby ? 'Rabby' : 'Browser Wallet',
                    icon: provider.isMetaMask ? '🦊' :
                        provider.isCoinbaseWallet ? '🔵' :
                            provider.isRabby ? '🐰' : '💼'
                });
            });
        } else {
            // Single provider
            if (window.ethereum.isMetaMask) {
                wallets.push({
                    type: WALLET_TYPES.METAMASK,
                    provider: window.ethereum,
                    name: 'MetaMask',
                    icon: '🦊'
                });
            } else if (window.ethereum.isCoinbaseWallet) {
                wallets.push({
                    type: WALLET_TYPES.COINBASE,
                    provider: window.ethereum,
                    name: 'Coinbase Wallet',
                    icon: '🔵'
                });
            } else if (window.ethereum.isRabby) {
                wallets.push({
                    type: 'rabby',
                    provider: window.ethereum,
                    name: 'Rabby',
                    icon: '🐰'
                });
            } else if (window.ethereum.isPhantom) {
                wallets.push({
                    type: 'phantom',
                    provider: window.ethereum,
                    name: 'Phantom',
                    icon: '👻'
                });
            } else {
                wallets.push({
                    type: WALLET_TYPES.INJECTED,
                    provider: window.ethereum,
                    name: 'Browser Wallet',
                    icon: '💼'
                });
            }
        }
    }

    // WalletConnect is always available (via QR)
    wallets.push({
        type: WALLET_TYPES.WALLETCONNECT,
        provider: null,
        name: 'WalletConnect',
        icon: '🔗',
        description: 'Scan QR with mobile wallet'
    });

    return wallets;
}

// Create wallet selection modal
function createWalletModal() {
    const existingModal = document.getElementById('walletModal');
    if (existingModal) existingModal.remove();

    const modal = document.createElement('div');
    modal.id = 'walletModal';
    modal.className = 'wallet-modal';

    const wallets = detectAvailableWallets();

    modal.innerHTML = `
        <div class="wallet-modal-backdrop"></div>
        <div class="wallet-modal-content">
            <div class="wallet-modal-header">
                <h3>🔌 Connect Wallet</h3>
                <button class="wallet-modal-close">&times;</button>
            </div>
            <div class="wallet-modal-body">
                <p class="wallet-modal-subtitle">Choose your preferred wallet</p>
                <div class="wallet-options">
                    ${wallets.map(wallet => `
                        <button class="wallet-option" data-wallet-type="${wallet.type}">
                            <span class="wallet-icon">${wallet.icon}</span>
                            <div class="wallet-info">
                                <span class="wallet-name">${wallet.name}</span>
                                <span class="wallet-desc">${wallet.description || 'Connect now'}</span>
                            </div>
                            ${wallet.type === 'metamask' ? '<span class="recommended-badge">Recommended</span>' : ''}
                        </button>
                    `).join('')}
                </div>
            </div>
            <div class="wallet-modal-footer">
                <p>By connecting, you agree to our Terms of Service</p>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Event listeners
    modal.querySelector('.wallet-modal-backdrop').addEventListener('click', closeWalletModal);
    modal.querySelector('.wallet-modal-close').addEventListener('click', closeWalletModal);

    modal.querySelectorAll('.wallet-option').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const walletType = e.currentTarget.dataset.walletType;
            const wallet = wallets.find(w => w.type === walletType);
            await connectWithWallet(wallet);
        });
    });

    // Animate in
    requestAnimationFrame(() => {
        modal.classList.add('active');
    });

    return modal;
}

function closeWalletModal() {
    const modal = document.getElementById('walletModal');
    if (modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
    }
}

// Connect with specific wallet
async function connectWithWallet(wallet) {
    try {
        const statusEl = document.querySelector('.wallet-modal-subtitle');
        if (statusEl) statusEl.textContent = `Connecting to ${wallet.name}...`;

        if (wallet.type === WALLET_TYPES.WALLETCONNECT) {
            // WalletConnect flow
            await connectWithWalletConnect();
        } else if (wallet.provider) {
            // Injected provider flow
            const accounts = await wallet.provider.request({
                method: 'eth_requestAccounts'
            });

            if (accounts && accounts.length > 0) {
                // Update global state
                connectedWallet = accounts[0];
                ethersProvider = new ethers.BrowserProvider(wallet.provider);
                ethersSigner = await ethersProvider.getSigner();

                // Update UI
                updateWalletConnectUI(accounts[0], wallet);
                closeWalletModal();

                console.log(`✅ Connected with ${wallet.name}: ${accounts[0]}`);
            }
        }
    } catch (error) {
        console.error('Wallet connection error:', error);
        const statusEl = document.querySelector('.wallet-modal-subtitle');
        if (statusEl) statusEl.textContent = `Error: ${error.message || 'Connection failed'}`;
    }
}

// WalletConnect specific flow
async function connectWithWalletConnect() {
    // For now, show manual QR code instructions
    // In production, use WalletConnect SDK
    const statusEl = document.querySelector('.wallet-modal-subtitle');
    if (statusEl) {
        statusEl.innerHTML = `
            <div class="walletconnect-qr">
                <p>📱 Open your mobile wallet app</p>
                <p>Scan QR code or paste link</p>
                <p style="color: var(--text-muted); font-size: 0.75rem; margin-top: 1rem;">
                    WalletConnect V2 coming soon!<br>
                    For now, use MetaMask mobile or Coinbase Wallet.
                </p>
            </div>
        `;
    }
}

// Update UI after connection (renamed to avoid conflict with app.js updateWalletUI)
function updateWalletConnectUI(address, wallet) {
    // Update header if there's a connect button
    const connectBtn = document.querySelector('[data-wallet-connect]');
    if (connectBtn) {
        connectBtn.innerHTML = `
            <span class="wallet-connected-icon">${wallet?.icon || '✓'}</span>
            <span>Wallet Connected</span>
        `;
        connectBtn.classList.add('connected');
    }

    // Also update any connectWalletBtn if it exists
    const connectWalletBtn = document.getElementById('connectWalletBtn');
    if (connectWalletBtn) {
        connectWalletBtn.innerHTML = `
            <span class="wallet-dot"></span>
            Wallet Connected
        `;
        connectWalletBtn.classList.add('connected');
    }

    // Show session status
    const sessionStatus = document.getElementById('sessionStatus');
    if (sessionStatus) {
        sessionStatus.textContent = `Connected: ${shortAddress}`;
        sessionStatus.className = 'session-status connected';
    }
}

// Show wallet modal (called from main app)
function showWalletSelector() {
    createWalletModal();
}

// Export for use in app.js
window.WalletConnect = {
    show: showWalletSelector,
    detect: detectAvailableWallets,
    close: closeWalletModal
};
