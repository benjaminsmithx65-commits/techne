/**
 * Neural Terminal - Matrix/Cyberpunk Style Agent Terminal
 * Real-time deployment and execution feedback
 */

class NeuralTerminal {
    constructor() {
        this.terminal = null;
        this.outputArea = null;
        this.isMinimized = false;
        this.logs = [];
        this.isDeploying = false;
    }

    /**
     * Initialize the terminal in the DOM
     */
    init() {
        if (this.terminal) return; // Already initialized

        this.createTerminalElement();
        this.bindEvents();
        console.log('[NeuralTerminal] Initialized');
    }

    /**
     * Create the floating terminal element
     */
    createTerminalElement() {
        const terminalHTML = `
            <div class="neural-terminal" id="neuralTerminal">
                <div class="terminal-header">
                    <div class="terminal-title">
                        <span class="terminal-icon">⚡</span>
                        <span class="terminal-name">Neural Terminal</span>
                        <span class="terminal-status" id="terminalStatus">STANDBY</span>
                    </div>
                    <div class="terminal-controls">
                        <button class="terminal-btn minimize" id="terminalMinimize" title="Minimize">_</button>
                        <button class="terminal-btn clear" id="terminalClear" title="Clear">⌘</button>
                    </div>
                </div>
                <div class="terminal-body" id="terminalBody">
                    <div class="terminal-output" id="terminalOutput">
                        <div class="log-line system">[SYSTEM] Neural Terminal v2.0 initialized</div>
                        <div class="log-line system">[SYSTEM] Connected to Base L2 Network</div>
                        <div class="log-line info">[READY] Awaiting deployment command...</div>
                    </div>
                    <div class="terminal-input-area">
                        <span class="terminal-prompt">></span>
                        <input type="text" class="terminal-input" id="terminalInput" placeholder="Enter command..." autocomplete="off">
                    </div>
                </div>
            </div>
        `;

        // Insert into Build section
        const buildSection = document.getElementById('section-build');
        if (buildSection) {
            buildSection.insertAdjacentHTML('beforeend', terminalHTML);
            this.terminal = document.getElementById('neuralTerminal');
            this.outputArea = document.getElementById('terminalOutput');
        }
    }

    /**
     * Bind terminal events
     */
    bindEvents() {
        // Minimize toggle
        const minimizeBtn = document.getElementById('terminalMinimize');
        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', () => this.toggleMinimize());
        }

        // Clear terminal
        const clearBtn = document.getElementById('terminalClear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clear());
        }

        // Input commands
        const input = document.getElementById('terminalInput');
        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && input.value.trim()) {
                    this.processCommand(input.value.trim());
                    input.value = '';
                }
            });
        }
    }

    /**
     * Toggle terminal minimize state
     */
    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        const body = document.getElementById('terminalBody');
        if (body) {
            body.style.display = this.isMinimized ? 'none' : 'flex';
        }
        const btn = document.getElementById('terminalMinimize');
        if (btn) {
            btn.textContent = this.isMinimized ? '□' : '_';
        }
    }

    /**
     * Clear terminal output
     */
    clear() {
        if (this.outputArea) {
            this.outputArea.innerHTML = '<div class="log-line system">[SYSTEM] Terminal cleared</div>';
        }
        this.logs = [];
    }

    /**
     * Process user commands
     */
    processCommand(cmd) {
        const lower = cmd.toLowerCase();

        this.log(`> ${cmd}`, 'command');

        if (lower === 'help') {
            this.log('Available commands:', 'info');
            this.log('  status  - Show agent status', 'info');
            this.log('  deploy  - Deploy agent', 'info');
            this.log('  stop    - Stop agent', 'info');
            this.log('  clear   - Clear terminal', 'info');
        } else if (lower === 'status') {
            this.log('Agent Status: STANDBY', 'info');
            this.log('Network: Base L2', 'info');
            this.log('Gas Price: 0.001 gwei', 'info');
        } else if (lower === 'deploy') {
            this.log('Use the Deploy button above', 'warning');
        } else if (lower === 'clear') {
            this.clear();
        } else {
            this.log(`Unknown command: ${cmd}`, 'error');
        }
    }

    /**
     * Log a message to the terminal
     * @param {string} message - Message to display
     * @param {string} type - Log type: 'info', 'success', 'warning', 'error', 'system', 'command'
     */
    log(message, type = 'info') {
        if (!this.outputArea) return;

        const timestamp = new Date().toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        const logEntry = {
            time: timestamp,
            message,
            type
        };
        this.logs.push(logEntry);

        const logLine = document.createElement('div');
        logLine.className = `log-line ${type}`;
        logLine.innerHTML = `<span class="log-time">[${timestamp}]</span> ${this.formatMessage(message)}`;

        this.outputArea.appendChild(logLine);
        this.outputArea.scrollTop = this.outputArea.scrollHeight;
    }

    /**
     * Format message with syntax highlighting
     */
    formatMessage(message) {
        // Highlight addresses
        message = message.replace(/(0x[a-fA-F0-9]{6,})/g, '<span class="highlight-address">$1</span>');
        // Highlight numbers/percentages
        message = message.replace(/(\d+\.?\d*%?)/g, '<span class="highlight-number">$1</span>');
        // Highlight keywords
        message = message.replace(/(SUCCESS|COMPLETE|DEPLOYED)/g, '<span class="highlight-success">$1</span>');
        message = message.replace(/(ERROR|FAILED|REJECTED)/g, '<span class="highlight-error">$1</span>');
        message = message.replace(/(WARNING|CAUTION)/g, '<span class="highlight-warning">$1</span>');

        return message;
    }

    /**
     * Update terminal status indicator
     */
    setStatus(status) {
        const statusEl = document.getElementById('terminalStatus');
        if (statusEl) {
            statusEl.textContent = status;
            statusEl.className = 'terminal-status';

            if (status === 'DEPLOYING') {
                statusEl.classList.add('deploying');
            } else if (status === 'ACTIVE') {
                statusEl.classList.add('active');
            } else if (status === 'ERROR') {
                statusEl.classList.add('error');
            }
        }
    }

    /**
     * Show terminal (if minimized)
     */
    show() {
        if (this.isMinimized) {
            this.toggleMinimize();
        }
        if (this.terminal) {
            this.terminal.classList.add('visible');
        }
    }

    /**
     * Run deployment sequence with animated logs
     * @param {Object} config - Agent configuration
     * @param {Object} proConfig - Pro Mode configuration (optional)
     */
    async runDeploymentSequence(config, proConfig = null) {
        this.isDeploying = true;
        this.show();
        this.setStatus('DEPLOYING');

        const isPro = proConfig !== null;

        // Deployment sequence
        const steps = [
            { delay: 200, msg: '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', type: 'system' },
            { delay: 100, msg: '[DEPLOY] Initializing deployment sequence...', type: 'info' },
            { delay: 400, msg: '[SYSTEM] Connecting to Base L2 RPC...', type: 'system' },
            { delay: 300, msg: '[SYSTEM] Connection established ✓', type: 'success' },
            { delay: 200, msg: '', type: 'info' },
            { delay: 100, msg: '[VALIDATE] Checking strategy configuration...', type: 'info' },
            { delay: 300, msg: `[VALIDATE] Strategy: ${config.preset?.replace(/-/g, ' ') || 'Custom'}`, type: 'info' },
            { delay: 200, msg: `[VALIDATE] Risk Level: ${config.riskLevel || 'Medium'}`, type: 'info' },
            { delay: 200, msg: `[VALIDATE] APY Target: ${config.minApy || 10}% - ${config.maxApy || 50}%`, type: 'info' },
        ];

        // Add Pro Mode validation if applicable
        if (isPro) {
            if (proConfig.leverage > 1) {
                steps.push({ delay: 200, msg: `[PRO] Leverage: ${proConfig.leverage.toFixed(1)}x`, type: 'warning' });
            }
            if (proConfig.stopLossEnabled) {
                steps.push({ delay: 200, msg: `[PRO] Stop Loss: ${proConfig.stopLossPercent}%`, type: 'info' });
            }
            if (proConfig.takeProfitEnabled) {
                steps.push({ delay: 200, msg: `[PRO] Take Profit: $${proConfig.takeProfitAmount}`, type: 'info' });
            }
            if (proConfig.volatilityGuard) {
                steps.push({ delay: 200, msg: `[PRO] Volatility Guard: ENABLED`, type: 'success' });
            }
        }

        // Continue deployment steps
        steps.push(
            { delay: 300, msg: '', type: 'info' },
            { delay: 100, msg: '[GAS] Fetching current gas prices...', type: 'info' },
            { delay: 400, msg: '[GAS] Base fee: 0.001 gwei | Priority: 0.0001 gwei', type: 'success' },
            { delay: 200, msg: '[GAS] Estimated cost: $0.02 USD ✓', type: 'success' },
            { delay: 300, msg: '', type: 'info' },
            { delay: 100, msg: '[RISK] Calculating risk score...', type: 'info' },
            { delay: 500, msg: `[RISK] Score: ${this.calculateRiskScore(config, proConfig)}/100`, type: 'info' },
            { delay: 300, msg: '', type: 'info' },
            { delay: 100, msg: '[DEPLOY] Creating agent wallet...', type: 'info' },
            { delay: 600, msg: '[DEPLOY] Wallet created ✓', type: 'success' },
            { delay: 300, msg: '[DEPLOY] Configuring smart contracts...', type: 'info' },
            { delay: 500, msg: '[DEPLOY] Contracts verified ✓', type: 'success' },
            { delay: 200, msg: '', type: 'info' },
            { delay: 100, msg: '[DEPLOY] Deploying to Base L2...', type: 'info' },
            { delay: 800, msg: '▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 100%', type: 'system' },
            { delay: 200, msg: '', type: 'info' },
            { delay: 100, msg: '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', type: 'system' },
            { delay: 100, msg: '[SUCCESS] Agent DEPLOYED successfully!', type: 'success' },
            { delay: 200, msg: '[STATUS] Agent is now ACTIVE and monitoring pools', type: 'success' }
        );

        // Execute sequence
        for (const step of steps) {
            await this.delay(step.delay);
            if (step.msg) {
                this.log(step.msg, step.type);
            }
        }

        this.setStatus('ACTIVE');
        this.isDeploying = false;

        return true;
    }

    /**
     * Calculate risk score based on configuration
     */
    calculateRiskScore(config, proConfig) {
        let score = 30; // Base score

        // Risk level impact
        const riskScores = { low: 20, medium: 40, high: 60, critical: 80 };
        score = riskScores[config.riskLevel] || 40;

        // Pro Mode adjustments
        if (proConfig) {
            // Leverage increases risk
            if (proConfig.leverage > 1) {
                score += (proConfig.leverage - 1) * 20;
            }

            // Stop loss reduces risk
            if (proConfig.stopLossEnabled) {
                score -= 10;
            }

            // Volatility guard reduces risk
            if (proConfig.volatilityGuard) {
                score -= 5;
            }
        }

        return Math.max(10, Math.min(100, Math.round(score)));
    }

    /**
     * Delay utility
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Run stop sequence
     */
    async runStopSequence() {
        this.show();
        this.setStatus('STOPPING');

        const steps = [
            { delay: 100, msg: '[STOP] Initiating shutdown sequence...', type: 'warning' },
            { delay: 400, msg: '[STOP] Pausing monitoring...', type: 'info' },
            { delay: 300, msg: '[STOP] Agent paused ✓', type: 'success' },
            { delay: 200, msg: '[INFO] Positions remain open until manual withdrawal', type: 'info' },
            { delay: 100, msg: '[STATUS] Agent is now STOPPED', type: 'warning' }
        ];

        for (const step of steps) {
            await this.delay(step.delay);
            this.log(step.msg, step.type);
        }

        this.setStatus('STANDBY');
    }
}

// Initialize and export
window.NeuralTerminal = new NeuralTerminal();
document.addEventListener('DOMContentLoaded', () => {
    // Delay initialization to ensure Build section exists
    setTimeout(() => window.NeuralTerminal.init(), 500);
});
