/**
 * Wallet Manager
 * MetaMask integration, transaction signing, balance tracking
 */

class WalletManager {
    constructor() {
        this.provider = null;
        this.signer = null;
        this.address = null;
        this.chainId = null;
        this.balances = {};
        this.isConnected = false;

        this.supportedChains = {
            8453: { name: 'Base', rpc: 'https://mainnet.base.org', explorer: 'https://basescan.org' },
            1: { name: 'Ethereum', rpc: 'https://eth.llamarpc.com', explorer: 'https://etherscan.io' },
            42161: { name: 'Arbitrum', rpc: 'https://arb1.arbitrum.io/rpc', explorer: 'https://arbiscan.io' },
            10: { name: 'Optimism', rpc: 'https://mainnet.optimism.io', explorer: 'https://optimistic.etherscan.io' }
        };

        this.tokens = {
            USDC: { address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', decimals: 6 },
            WETH: { address: '0x4200000000000000000000000000000000000006', decimals: 18 },
            cbETH: { address: '0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22', decimals: 18 },
            AERO: { address: '0x940181a94A35A4569E4529A3CDfB74e38FD98631', decimals: 18 }
        };
    }

    async init() {
        if (typeof window.ethereum === 'undefined') {
            console.warn('[Wallet] No wallet provider found');
            return false;
        }

        // Listen for account/chain changes
        window.ethereum.on('accountsChanged', (accounts) => this.handleAccountChange(accounts));
        window.ethereum.on('chainChanged', (chainId) => this.handleChainChange(chainId));

        // Check if already connected
        const accounts = await window.ethereum.request({ method: 'eth_accounts' });
        if (accounts.length > 0) {
            await this.connect();
        }

        console.log('[Wallet] Manager initialized');
        return true;
    }

    async connect() {
        try {
            if (typeof window.ethereum === 'undefined') {
                window.Notifications?.error('Please install MetaMask to connect');
                return null;
            }

            // Request accounts
            const accounts = await window.ethereum.request({
                method: 'eth_requestAccounts'
            });

            if (accounts.length === 0) {
                throw new Error('No accounts found');
            }

            this.address = accounts[0];
            this.chainId = parseInt(await window.ethereum.request({ method: 'eth_chainId' }), 16);

            // Create ethers provider
            if (window.ethers) {
                this.provider = new ethers.BrowserProvider(window.ethereum);
                this.signer = await this.provider.getSigner();
            }

            this.isConnected = true;

            // *** SYNC with app.js wallet state ***
            window.connectedWallet = this.address;

            // Update UI
            this.updateUI();
            await this.fetchBalances();

            // *** Refresh wallet-gated sections ***
            if (typeof updateWalletGatedSections === 'function') {
                updateWalletGatedSections();
            }

            window.Notifications?.success(`Connected: ${this.formatAddress(this.address)}`);

            return this.address;
        } catch (error) {
            console.error('[Wallet] Connection failed:', error);
            window.Notifications?.error('Failed to connect wallet');
            return null;
        }
    }

    async disconnect() {
        this.address = null;
        this.signer = null;
        this.isConnected = false;
        this.balances = {};

        // *** SYNC with app.js wallet state ***
        window.connectedWallet = null;

        this.updateUI();

        // *** Refresh wallet-gated sections ***
        if (typeof updateWalletGatedSections === 'function') {
            updateWalletGatedSections();
        }

        window.Notifications?.info('Wallet disconnected');
    }

    async switchChain(chainId) {
        try {
            await window.ethereum.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: `0x${chainId.toString(16)}` }]
            });
            return true;
        } catch (error) {
            if (error.code === 4902) {
                // Chain not added, try to add it
                return await this.addChain(chainId);
            }
            console.error('[Wallet] Failed to switch chain:', error);
            return false;
        }
    }

    async addChain(chainId) {
        const chainInfo = this.supportedChains[chainId];
        if (!chainInfo) return false;

        try {
            await window.ethereum.request({
                method: 'wallet_addEthereumChain',
                params: [{
                    chainId: `0x${chainId.toString(16)}`,
                    chainName: chainInfo.name,
                    rpcUrls: [chainInfo.rpc],
                    blockExplorerUrls: [chainInfo.explorer]
                }]
            });
            return true;
        } catch (error) {
            console.error('[Wallet] Failed to add chain:', error);
            return false;
        }
    }

    async fetchBalances() {
        if (!this.address || !this.provider) return;

        try {
            // Native balance
            const ethBalance = await this.provider.getBalance(this.address);
            this.balances.ETH = parseFloat(ethers.formatEther(ethBalance));

            // Token balances
            const erc20Abi = ['function balanceOf(address) view returns (uint256)'];

            for (const [symbol, token] of Object.entries(this.tokens)) {
                try {
                    const contract = new ethers.Contract(token.address, erc20Abi, this.provider);
                    const balance = await contract.balanceOf(this.address);
                    this.balances[symbol] = parseFloat(ethers.formatUnits(balance, token.decimals));
                } catch (e) {
                    this.balances[symbol] = 0;
                }
            }

            this.updateBalanceUI();
        } catch (error) {
            console.error('[Wallet] Failed to fetch balances:', error);
        }
    }

    async sendTransaction(to, value, data = '0x') {
        if (!this.signer) {
            window.Notifications?.error('Wallet not connected');
            return null;
        }

        try {
            window.Notifications?.info('Please confirm transaction in your wallet...');

            const tx = await this.signer.sendTransaction({
                to,
                value: ethers.parseEther(value.toString()),
                data
            });

            window.Notifications?.info(`Transaction sent: ${tx.hash.slice(0, 10)}...`);

            const receipt = await tx.wait();

            window.Notifications?.success('Transaction confirmed!', {
                onClick: () => window.open(`${this.getExplorer()}/tx/${tx.hash}`, '_blank')
            });

            return receipt;
        } catch (error) {
            if (error.code === 'ACTION_REJECTED') {
                window.Notifications?.warning('Transaction cancelled');
            } else {
                window.Notifications?.error(`Transaction failed: ${error.message}`);
            }
            return null;
        }
    }

    async approveToken(tokenAddress, spenderAddress, amount) {
        if (!this.signer) return null;

        const erc20Abi = ['function approve(address spender, uint256 amount) returns (bool)'];
        const contract = new ethers.Contract(tokenAddress, erc20Abi, this.signer);

        try {
            window.Notifications?.info('Please approve token spending...');
            const tx = await contract.approve(spenderAddress, amount);
            await tx.wait();
            window.Notifications?.success('Token approved!');
            return true;
        } catch (error) {
            window.Notifications?.error('Approval failed');
            return false;
        }
    }

    async fundAgent(agentAddress, amount, token = 'ETH') {
        if (!agentAddress) {
            window.Notifications?.error('No agent deployed');
            return false;
        }

        if (token === 'ETH') {
            return await this.sendTransaction(agentAddress, amount);
        } else {
            // ERC20 transfer
            const tokenInfo = this.tokens[token];
            if (!tokenInfo) return false;

            const erc20Abi = ['function transfer(address to, uint256 amount) returns (bool)'];
            const contract = new ethers.Contract(tokenInfo.address, erc20Abi, this.signer);

            try {
                const tx = await contract.transfer(
                    agentAddress,
                    ethers.parseUnits(amount.toString(), tokenInfo.decimals)
                );
                await tx.wait();
                window.Notifications?.success(`Funded agent with ${amount} ${token}`);
                return true;
            } catch (error) {
                window.Notifications?.error('Transfer failed');
                return false;
            }
        }
    }

    handleAccountChange(accounts) {
        if (accounts.length === 0) {
            this.disconnect();
        } else {
            this.address = accounts[0];
            this.updateUI();
            this.fetchBalances();
        }
    }

    handleChainChange(chainId) {
        this.chainId = parseInt(chainId, 16);
        this.updateUI();
        this.fetchBalances();

        const chainName = this.supportedChains[this.chainId]?.name || 'Unknown';
        window.Notifications?.info(`Switched to ${chainName}`);
    }

    updateUI() {
        // Use correct ID 'connectWallet' from HTML
        const connectBtn = document.getElementById('connectWallet');
        const addressEl = document.getElementById('walletAddress');

        if (this.isConnected) {
            if (connectBtn) {
                connectBtn.innerHTML = `
                    <span class="wallet-icon">✓</span>
                    <span>Wallet Connected</span>
                `;
                connectBtn.classList.add('connected');
            }
            if (addressEl) {
                addressEl.textContent = this.formatAddress(this.address);
            }
            // Also call app.js updateWalletUI if available
            if (typeof updateWalletUI === 'function') {
                updateWalletUI();
            }
        } else {
            if (connectBtn) {
                connectBtn.innerHTML = 'Connect Wallet';
                connectBtn.classList.remove('connected');
            }
        }
    }

    updateBalanceUI() {
        const balanceEl = document.getElementById('walletBalance');
        if (balanceEl) {
            balanceEl.textContent = `${this.balances.ETH?.toFixed(4) || 0} ETH`;
        }

        // Update portfolio if on that page
        if (window.PortfolioDash) {
            window.PortfolioDash.loadPortfolioData();
        }
    }

    formatAddress(address) {
        if (!address) return '';
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    }

    getExplorer() {
        return this.supportedChains[this.chainId]?.explorer || 'https://basescan.org';
    }

    getChainName() {
        return this.supportedChains[this.chainId]?.name || 'Unknown';
    }

    isOnCorrectChain() {
        return this.chainId === 8453; // Base mainnet
    }
}

// Initialize
const WalletMgr = new WalletManager();
document.addEventListener('DOMContentLoaded', () => {
    WalletMgr.init();

    // Connect button is handled by app.js (with showWalletMenu when connected)
    // Don't add another listener here to avoid conflicts

    // Fund agent button - opens the deposit modal
    document.getElementById('btnFundAgent')?.addEventListener('click', async () => {
        // Check if agent exists
        const agentAddr = window.AgentWallet?.agentAddress
            || window.VaultAgent?.agentAddress;

        if (!agentAddr) {
            window.Notifications?.warning('No agent deployed. Deploy from Build section first.');
            return;
        }

        // Open the Fund Agent Vault modal (handles ETH/USDC selection)
        if (window.AgentWalletUI?.showDepositModal) {
            window.AgentWalletUI.showDepositModal();
        } else {
            window.Notifications?.error('Deposit modal not available');
        }
    });
});

// Export
window.WalletMgr = WalletMgr;
