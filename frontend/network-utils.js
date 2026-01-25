/**
 * Network Utilities - Chain Switching for Techne Finance
 * Ensures user is on Base chain before transactions
 */

const BASE_CHAIN_ID = 8453;
const BASE_CHAIN_ID_HEX = '0x2105';

const BASE_CHAIN_CONFIG = {
    chainId: BASE_CHAIN_ID_HEX,
    chainName: 'Base',
    nativeCurrency: {
        name: 'Ether',
        symbol: 'ETH',
        decimals: 18
    },
    rpcUrls: ['https://mainnet.base.org'],
    blockExplorerUrls: ['https://basescan.org']
};

// USDC on Base
const BASE_USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

// Techne Agent Vault V4.3.3 on Base 
const TECHNE_VAULT_ADDRESS = '0x1ff18a7b56d7fd3b07ce789e47ac587de2f14e0d';

// Smart Account Factory (ERC-4337) - deployed 2026-01-25
const TECHNE_FACTORY_ADDRESS = '0xc1ee3090330ad3f946eee995f975e9fe541aa676';
const TECHNE_IMPLEMENTATION_ADDRESS = '0xe185c5ffadf51425509ce4186f7328d8bcdbc6cd';

/**
 * Check if user is on Base network
 */
async function isOnBase() {
    if (!window.ethereum) return false;

    try {
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        const chainIdNum = parseInt(chainId, 16);
        return chainIdNum === BASE_CHAIN_ID;
    } catch (error) {
        console.error('[NetworkUtils] Failed to get chainId:', error);
        return false;
    }
}

/**
 * Get current chain ID
 */
async function getCurrentChainId() {
    if (!window.ethereum) return null;

    try {
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        return parseInt(chainId, 16);
    } catch (error) {
        return null;
    }
}

/**
 * Switch to Base network
 * @returns {boolean} true if switch successful
 */
async function switchToBase() {
    if (!window.ethereum) {
        alert('Please install MetaMask or another Web3 wallet');
        return false;
    }

    try {
        // Try to switch to Base
        await window.ethereum.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: BASE_CHAIN_ID_HEX }]
        });
        console.log('[NetworkUtils] Switched to Base');
        return true;
    } catch (switchError) {
        // If Base not added, add it
        if (switchError.code === 4902) {
            try {
                await window.ethereum.request({
                    method: 'wallet_addEthereumChain',
                    params: [BASE_CHAIN_CONFIG]
                });
                console.log('[NetworkUtils] Added and switched to Base');
                return true;
            } catch (addError) {
                console.error('[NetworkUtils] Failed to add Base:', addError);
                alert('Failed to add Base network. Please add it manually.');
                return false;
            }
        }
        console.error('[NetworkUtils] Failed to switch to Base:', switchError);
        return false;
    }
}

/**
 * Ensure user is on Base before proceeding
 * Shows UI prompt if not on Base
 * @returns {boolean} true if on Base (or switched successfully)
 */
async function ensureBaseNetwork() {
    const onBase = await isOnBase();

    if (onBase) {
        console.log('[NetworkUtils] ✓ Already on Base');
        return true;
    }

    const currentChain = await getCurrentChainId();
    console.log(`[NetworkUtils] Wrong network (${currentChain}). Switching to Base...`);

    // Show user-friendly prompt
    const shouldSwitch = confirm(
        `Techne Finance operates on Base network.\n\n` +
        `You are currently on chain ID ${currentChain}.\n\n` +
        `Click OK to switch to Base.`
    );

    if (!shouldSwitch) {
        return false;
    }

    return await switchToBase();
}

/**
 * Get USDC contract on Base
 */
function getUSDCContract(signer) {
    const USDC_ABI = [
        'function approve(address spender, uint256 amount) external returns (bool)',
        'function allowance(address owner, address spender) external view returns (uint256)',
        'function balanceOf(address account) external view returns (uint256)',
        'function transfer(address to, uint256 amount) external returns (bool)'
    ];

    return new ethers.Contract(BASE_USDC_ADDRESS, USDC_ABI, signer);
}

/**
 * Get Techne Vault contract on Base
 */
function getTechneVaultContract(signer) {
    const VAULT_ABI = [
        'function deposit(uint256 amount) external',
        'function depositWithPermit(uint256 amount, uint256 deadline, uint8 v, bytes32 r, bytes32 s) external',
        'function balances(address user) external view returns (uint256)',
        'function withdraw(uint256 amount) external'
    ];

    return new ethers.Contract(TECHNE_VAULT_ADDRESS, VAULT_ABI, signer);
}

/**
 * Get user's deployed agent address from backend
 * @param {string} userAddress - User's wallet address
 * @returns {string|null} Agent wallet address or null
 */
async function getAgentAddress(userAddress) {
    try {
        const response = await fetch(`/api/agent/status/${userAddress}`);
        const data = await response.json();

        if (data.success && data.agents && data.agents.length > 0) {
            // Get first active agent's address
            const activeAgent = data.agents.find(a => a.is_active);
            if (activeAgent && activeAgent.agent_address) {
                console.log(`[NetworkUtils] Found agent wallet: ${activeAgent.agent_address}`);
                return activeAgent.agent_address;
            }
        }
        console.log('[NetworkUtils] No active agent found for user');
        return null;
    } catch (error) {
        console.error('[NetworkUtils] Failed to get agent address:', error);
        return null;
    }
}

/**
 * Fund agent's wallet with USDC and trigger allocation (NO smart contract!)
 * @param {number} amountUSDC - Amount in USDC (human readable, e.g. 100 for $100)
 * @param {string} userAddress - User's wallet address (to look up agent)
 */
async function fundAgentWallet(amountUSDC, userAddress) {
    // Step 1: Ensure on Base
    const onBase = await ensureBaseNetwork();
    if (!onBase) {
        console.log('[NetworkUtils] User declined network switch');
        return { success: false, error: 'Wrong network - please switch to Base' };
    }

    // Step 2: Get agent's wallet address from backend
    const agentWallet = await getAgentAddress(userAddress);
    if (!agentWallet) {
        return {
            success: false,
            error: 'No deployed agent found. Please deploy an agent first.'
        };
    }

    // Step 3: Get signer
    const provider = new ethers.BrowserProvider(window.ethereum);
    const signer = await provider.getSigner();
    const signerAddress = await signer.getAddress();

    // Step 4: Check USDC balance
    const usdc = getUSDCContract(signer);
    const balance = await usdc.balanceOf(signerAddress);
    const amountWei = ethers.parseUnits(amountUSDC.toString(), 6); // USDC has 6 decimals

    if (balance < amountWei) {
        return {
            success: false,
            error: `Insufficient USDC. You have ${ethers.formatUnits(balance, 6)} USDC`
        };
    }

    // Step 5: Transfer USDC directly to agent's wallet
    console.log(`[NetworkUtils] Funding agent ${agentWallet} with ${amountUSDC} USDC...`);
    try {
        const transferTx = await usdc.transfer(agentWallet, amountWei);
        const receipt = await transferTx.wait();
        console.log('[NetworkUtils] ✓ Agent funded:', receipt.hash);

        // Step 6: Trigger allocation on backend (NO smart contract needed!)
        console.log('[NetworkUtils] Triggering allocation...');
        try {
            const allocResponse = await fetch(`/api/agent/trigger-allocation?user_address=${userAddress}`, {
                method: 'POST'
            });
            const allocData = await allocResponse.json();

            if (allocData.success) {
                console.log('[NetworkUtils] ✓ Allocation triggered:', allocData);
                return {
                    success: true,
                    txHash: receipt.hash,
                    amount: amountUSDC,
                    agentWallet: agentWallet,
                    allocation: allocData
                };
            } else {
                console.warn('[NetworkUtils] Allocation trigger failed:', allocData.error);
                // Transfer succeeded but allocation failed - user still has funds in agent wallet
                return {
                    success: true,
                    txHash: receipt.hash,
                    amount: amountUSDC,
                    agentWallet: agentWallet,
                    allocationPending: true,
                    allocationError: allocData.error
                };
            }
        } catch (allocError) {
            console.error('[NetworkUtils] Allocation trigger error:', allocError);
            return {
                success: true,
                txHash: receipt.hash,
                amount: amountUSDC,
                agentWallet: agentWallet,
                allocationPending: true,
                allocationError: allocError.message
            };
        }
    } catch (error) {
        return { success: false, error: 'Transfer failed: ' + error.message };
    }
}


/**
 * Get user's Smart Account address (ERC-4337)
 * @param {string} userAddress - User's EOA wallet address
 * @returns {object} Smart account info
 */
async function getSmartAccount(userAddress) {
    try {
        const response = await fetch(`/api/smart-account/${userAddress}`);
        const data = await response.json();

        if (data.success) {
            console.log(`[NetworkUtils] Smart Account: ${data.smart_account} (deployed: ${data.is_deployed})`);
            return {
                success: true,
                smartAccount: data.smart_account,
                isDeployed: data.is_deployed
            };
        }
        return { success: false, error: data.error };
    } catch (error) {
        console.error('[NetworkUtils] Failed to get smart account:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Create/Deploy Smart Account for user (ERC-4337)
 * @param {string} userAddress - User's EOA wallet address
 * @returns {object} Deployment result
 */
async function createSmartAccount(userAddress) {
    try {
        const response = await fetch(`/api/smart-account/create?user_address=${userAddress}`, {
            method: 'POST'
        });
        const data = await response.json();

        if (data.success) {
            console.log(`[NetworkUtils] ✅ Smart Account created: ${data.smart_account}`);
            return {
                success: true,
                smartAccount: data.smart_account,
                txHash: data.tx_hash,
                message: data.message
            };
        }
        return { success: false, error: data.message };
    } catch (error) {
        console.error('[NetworkUtils] Failed to create smart account:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Ensure user has a Smart Account (create if doesn't exist)
 * @param {string} userAddress - User's EOA wallet address
 * @returns {object} Smart account info
 */
async function ensureSmartAccount(userAddress) {
    // First check if exists
    const existing = await getSmartAccount(userAddress);

    if (existing.success && existing.isDeployed) {
        return existing;
    }

    // Create if not deployed
    console.log('[NetworkUtils] Smart Account not deployed, creating...');
    return await createSmartAccount(userAddress);
}

// Export to window
window.NetworkUtils = {
    BASE_CHAIN_ID,
    BASE_USDC_ADDRESS,
    TECHNE_VAULT_ADDRESS,
    TECHNE_FACTORY_ADDRESS,
    TECHNE_IMPLEMENTATION_ADDRESS,
    isOnBase,
    getCurrentChainId,
    switchToBase,
    ensureBaseNetwork,
    getUSDCContract,
    getTechneVaultContract,
    getAgentAddress,
    fundAgentWallet,
    getSmartAccount,
    createSmartAccount,
    ensureSmartAccount
};

console.log('[NetworkUtils] Loaded - Base chain enforcement + Smart Accounts enabled');
