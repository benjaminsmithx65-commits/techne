/**
 * Engineer Client - Frontend integration for execution layer
 * Handles deposits, withdrawals, and task tracking
 */

const EngineerClient = {
    baseUrl: window.API_BASE || 'http://localhost:8000',

    /**
     * Create a USDT deposit task
     */
    async createDeposit(userAddress, vaultAddress, amountUSDT, maxGasUSD = 2.0) {
        try {
            const response = await fetch(`${this.baseUrl}/api/engineer/deposit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userAddress,
                    vault_address: vaultAddress,
                    amount_usdt: amountUSDT,
                    max_gas_usd: maxGasUSD
                })
            });

            if (!response.ok) {
                throw new Error(`Deposit failed: ${response.statusText}`);
            }

            const data = await response.json();

            Toast?.show(`✅ Deposit task created: ${data.task_id}`, 'success');

            return data;
        } catch (error) {
            console.error('Deposit error:', error);
            Toast?.show(`❌ Deposit failed: ${error.message}`, 'error');
            throw error;
        }
    },

    /**
     * Create a withdrawal task
     */
    async createWithdrawal(userAddress, vaultAddress, sharesAmount, maxGasUSD = 2.0) {
        try {
            const response = await fetch(`${this.baseUrl}/api/engineer/withdraw`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userAddress,
                    vault_address: vaultAddress,
                    shares_amount: sharesAmount,
                    max_gas_usd: maxGasUSD
                })
            });

            if (!response.ok) {
                throw new Error(`Withdrawal failed: ${response.statusText}`);
            }

            const data = await response.json();

            Toast?.show(`✅ Withdrawal task created`, 'success');

            return data;
        } catch (error) {
            console.error('Withdrawal error:', error);
            Toast?.show(`❌ Withdrawal failed: ${error.message}`, 'error');
            throw error;
        }
    },

    /**
     * Get task status
     */
    async getTaskStatus(taskId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/engineer/tasks/${taskId}`);

            if (!response.ok) {
                throw new Error('Task not found');
            }

            return await response.json();
        } catch (error) {
            console.error('Task status error:', error);
            return null;
        }
    },

    /**
     * Get all tasks for a user
     */
    async getUserTasks(userAddress, statusFilter = null) {
        try {
            let url = `${this.baseUrl}/api/engineer/tasks/user/${userAddress}`;
            if (statusFilter) {
                url += `?status_filter=${statusFilter}`;
            }

            const response = await fetch(url);

            if (!response.ok) {
                return [];
            }

            return await response.json();
        } catch (error) {
            console.error('Get tasks error:', error);
            return [];
        }
    },

    /**
     * Get current gas price
     */
    async getGasPrice() {
        try {
            const response = await fetch(`${this.baseUrl}/api/engineer/gas-price`);

            if (!response.ok) {
                return { current_gwei: 1, chain: 'Base' };
            }

            return await response.json();
        } catch (error) {
            console.error('Gas price error:', error);
            return { current_gwei: 1, chain: 'Base' };
        }
    },

    /**
     * Get recommended USDT vaults
     */
    async getRecommendedVaults() {
        try {
            const response = await fetch(`${this.baseUrl}/api/engineer/vaults/recommended`);

            if (!response.ok) {
                throw new Error('Failed to fetch vaults');
            }

            return await response.json();
        } catch (error) {
            console.error('Get vaults error:', error);
            return { vaults: [] };
        }
    },

    /**
     * Simulate a deposit (dry run)
     */
    async simulateDeposit(userAddress, vaultAddress, amountUSDT, maxGasUSD = 2.0) {
        try {
            const response = await fetch(`${this.baseUrl}/api/engineer/simulate-deposit`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userAddress,
                    vault_address: vaultAddress,
                    amount_usdt: amountUSDT,
                    max_gas_usd: maxGasUSD
                })
            });

            if (!response.ok) {
                throw new Error('Simulation failed');
            }

            return await response.json();
        } catch (error) {
            console.error('Simulate error:', error);
            return null;
        }
    },

    /**
     * Poll task status until completion
     */
    async waitForTaskCompletion(taskId, maxWaitMs = 120000, pollIntervalMs = 3000) {
        const startTime = Date.now();

        while (Date.now() - startTime < maxWaitMs) {
            const status = await this.getTaskStatus(taskId);

            if (!status) {
                throw new Error('Task not found');
            }

            if (status.status === 'completed') {
                Toast?.show('✅ Transaction completed!', 'success');
                return status;
            } else if (status.status.startsWith('failed')) {
                Toast?.show(`❌ Transaction failed: ${status.error_message}`, 'error');
                throw new Error(status.error_message || 'Task failed');
            }

            // Still pending/executing
            await new Promise(resolve => setTimeout(resolve, pollIntervalMs));
        }

        throw new Error('Task timeout - taking too long');
    },

    /**
     * Show task status in UI
     */
    showTaskStatus(task) {
        const statusEmoji = {
            'queued': '⏳',
            'waiting_gas': '⛽',
            'executing': '🔄',
            'completed': '✅',
            'failed_reverted': '❌',
            'failed_slippage': '⚠️',
            'failed_timeout': '⏰'
        };

        const emoji = statusEmoji[task.status] || '📋';
        const message = `${emoji} ${task.type}: ${task.status}`;

        const type = task.status === 'completed' ? 'success' :
            task.status.startsWith('failed') ? 'error' : 'info';

        Toast?.show(message, type);
    }
};

// Export to window for global access
window.EngineerClient = EngineerClient;

// Example usage in UI:
/*
// Deposit USDT
const depositBtn = document.getElementById('btn-deposit-usdt');
depositBtn.addEventListener('click', async () => {
    const amount = parseFloat(document.getElementById('deposit-amount').value);
    const vaultAddress = document.getElementById('vault-select').value;
    
    // Create task
    const task = await EngineerClient.createDeposit(
        window.connectedWallet,
        vaultAddress,
        amount
    );
    
    // Wait for completion
    await EngineerClient.waitForTaskCompletion(task.task_id);
    
    // Refresh balance
    loadBalance();
});

// Show gas price
async function updateGasPrice() {
    const gas = await EngineerClient.getGasPrice();
    document.getElementById('current-gas').textContent = `${gas.current_gwei} gwei`;
}
*/
