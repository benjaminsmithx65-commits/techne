/**
 * Agent Builder UI Logic - Extended Version
 * Handles configuration panel and chat interface interactions
 */

class AgentBuilderUI {
    constructor() {
        this.config = {
            // Strategy preset
            preset: 'balanced-growth',

            // Chain - LOCKED to Base
            chain: 'base',

            // Pool type - Single-sided only
            poolType: 'single',

            // Risk & Returns
            riskLevel: 'medium',
            minApy: 10,
            maxApy: 50,
            maxDrawdown: 20,

            // Protocols - Base only
            protocols: ['morpho', 'aave', 'moonwell', 'aerodrome', 'beefy'],

            // Assets
            preferredAssets: ['USDC', 'WETH'],

            // Duration & Allocation
            duration: 30,
            maxAllocation: 25,
            vaultCount: 5,

            // Advanced
            autoRebalance: true,
            rebalanceThreshold: 5,
            maxGasPrice: 50,
            slippage: 0.5,
            compoundFrequency: 7,
            onlyAudited: true,
            avoidIL: true,  // True for single-sided
            emergencyExit: true
        };

        // Preset configurations - All use Base-only protocols
        this.presets = {
            'stable-farmer': {
                riskLevel: 'low',
                minApy: 5, maxApy: 20, maxDrawdown: 10,
                protocols: ['aave', 'morpho', 'moonwell', 'compound'],
                preferredAssets: ['USDC', 'USDT', 'DAI'],
                vaultCount: 3, avoidIL: true, onlyAudited: true
            },
            'balanced-growth': {
                riskLevel: 'medium',
                minApy: 10, maxApy: 50, maxDrawdown: 20,
                protocols: ['morpho', 'aave', 'moonwell', 'aerodrome'],
                preferredAssets: ['USDC', 'WETH'],
                vaultCount: 5, avoidIL: true, onlyAudited: true
            },
            'yield-maximizer': {
                riskLevel: 'high',
                minApy: 25, maxApy: 100, maxDrawdown: 40,
                protocols: ['aerodrome', 'beefy', 'morpho', 'moonwell'],
                preferredAssets: ['WETH', 'AERO', 'cbETH'],
                vaultCount: 8, avoidIL: true, onlyAudited: false
            },
            'airdrop-hunter': {
                riskLevel: 'medium',
                minApy: 5, maxApy: 50, maxDrawdown: 30,
                protocols: ['morpho', 'moonwell', 'aerodrome'],
                preferredAssets: ['WETH', 'USDC', 'cbETH'],
                vaultCount: 5, avoidIL: true, onlyAudited: false
            },
            'eth-maxi': {
                riskLevel: 'low',
                minApy: 3, maxApy: 15, maxDrawdown: 15,
                protocols: ['aave', 'morpho', 'moonwell'],
                preferredAssets: ['WETH', 'cbETH', 'wstETH'],
                vaultCount: 3, avoidIL: true, onlyAudited: true
            },
            'custom': {}
        };
    }

    init() {
        this.bindChainPoolEvents();
        this.bindPresetEvents();
        this.bindConfigEvents();
        this.bindAdvancedEvents();
        this.bindChatEvents();
        this.bindCollapsibleEvents();
        console.log('[AgentBuilder] Extended UI initialized');
    }

    // Chain and Pool Type selectors
    bindChainPoolEvents() {
        // Chain selector (only Base active for now)
        document.querySelectorAll('.chain-btn-build:not(.disabled)').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.chain-btn-build').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.config.chain = btn.dataset.chain;
                this.markCustom();
                console.log('[AgentBuilder] Chain set to:', this.config.chain);
            });
        });

        // Pool type selector
        document.querySelectorAll('.pool-type-btn-build').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.pool-type-btn-build').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.config.poolType = btn.dataset.poolType;

                // Update avoidIL based on pool type
                if (this.config.poolType === 'single') {
                    this.config.avoidIL = true;
                } else if (this.config.poolType === 'dual') {
                    this.config.avoidIL = false;
                }

                this.markCustom();
                console.log('[AgentBuilder] Pool type set to:', this.config.poolType);
            });
        });
    }

    bindPresetEvents() {
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const preset = btn.dataset.preset;
                this.applyPreset(preset);
            });
        });
    }

    applyPreset(presetName) {
        const preset = this.presets[presetName];
        if (!preset || presetName === 'custom') {
            this.config.preset = 'custom';
            return;
        }

        this.config = { ...this.config, ...preset, preset: presetName };

        // Update UI to match preset
        this.updateAllUI();

        // Send chat message
        this.addAgentMessage(`Applied "${presetName.replace(/-/g, ' ')}" preset! Configuration updated.`);
    }

    updateAllUI() {
        // Risk buttons
        document.querySelectorAll('.risk-option').forEach(b => {
            b.classList.toggle('active', b.dataset.risk === this.config.riskLevel);
        });

        // APY sliders
        const minApySlider = document.getElementById('minApyConfig');
        const maxApySlider = document.getElementById('maxApyConfig');
        if (minApySlider) minApySlider.value = this.config.minApy;
        if (maxApySlider) maxApySlider.value = this.config.maxApy;
        this.updateApyDisplay();

        // Drawdown
        const drawdown = document.getElementById('maxDrawdown');
        if (drawdown) {
            drawdown.value = this.config.maxDrawdown;
            document.getElementById('maxDrawdownValue').textContent = `-${this.config.maxDrawdown}%`;
        }

        // Protocols
        document.querySelectorAll('.protocol-chip').forEach(chip => {
            chip.classList.toggle('active', this.config.protocols.includes(chip.dataset.protocol));
        });

        // Assets
        document.querySelectorAll('.asset-chip').forEach(chip => {
            chip.classList.toggle('active', this.config.preferredAssets.includes(chip.dataset.asset));
        });

        // Vault count
        document.querySelectorAll('.count-btn').forEach(b => {
            b.classList.toggle('active', parseInt(b.dataset.count) === this.config.vaultCount);
        });

        // Advanced toggles
        const autoRebalance = document.getElementById('autoRebalance');
        const onlyAudited = document.getElementById('onlyAudited');
        const avoidIL = document.getElementById('avoidIL');
        const emergencyExit = document.getElementById('emergencyExit');
        if (autoRebalance) autoRebalance.checked = this.config.autoRebalance;
        if (onlyAudited) onlyAudited.checked = this.config.onlyAudited;
        if (avoidIL) avoidIL.checked = this.config.avoidIL;
        if (emergencyExit) emergencyExit.checked = this.config.emergencyExit;
    }

    updateApyDisplay() {
        const minDisp = document.getElementById('minApyDisplay');
        const maxDisp = document.getElementById('maxApyDisplay');
        if (minDisp) minDisp.textContent = this.config.minApy + '%';
        if (maxDisp) maxDisp.textContent = this.config.maxApy + '%';
    }

    bindConfigEvents() {
        // Risk selector
        document.querySelectorAll('.risk-option').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.risk-option').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.config.riskLevel = btn.dataset.risk;
                this.markCustom();
            });
        });

        // Duration buttons
        document.querySelectorAll('.duration-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.duration-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.config.duration = parseInt(btn.dataset.days);
            });
        });

        // Asset chips
        document.querySelectorAll('.asset-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.classList.toggle('active');
                const asset = btn.dataset.asset;
                if (btn.classList.contains('active')) {
                    if (!this.config.preferredAssets.includes(asset)) {
                        this.config.preferredAssets.push(asset);
                    }
                } else {
                    this.config.preferredAssets = this.config.preferredAssets.filter(a => a !== asset);
                }
                this.markCustom();
            });
        });

        // Protocol chips
        document.querySelectorAll('.protocol-chip').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.classList.toggle('active');
                const protocol = btn.dataset.protocol;
                if (btn.classList.contains('active')) {
                    if (!this.config.protocols.includes(protocol)) {
                        this.config.protocols.push(protocol);
                    }
                } else {
                    this.config.protocols = this.config.protocols.filter(p => p !== protocol);
                }
                this.markCustom();
            });
        });

        // Vault count
        document.querySelectorAll('.count-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.count-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.config.vaultCount = parseInt(btn.dataset.count);
            });
        });

        // Min/Max APY sliders
        const minApySlider = document.getElementById('minApyConfig');
        const maxApySlider = document.getElementById('maxApyConfig');
        if (minApySlider) {
            minApySlider.addEventListener('input', () => {
                this.config.minApy = parseInt(minApySlider.value);
                if (this.config.minApy > this.config.maxApy) {
                    this.config.maxApy = this.config.minApy;
                    if (maxApySlider) maxApySlider.value = this.config.maxApy;
                }
                this.updateApyDisplay();
                this.markCustom();
            });
        }
        if (maxApySlider) {
            maxApySlider.addEventListener('input', () => {
                this.config.maxApy = parseInt(maxApySlider.value);
                if (this.config.maxApy < this.config.minApy) {
                    this.config.minApy = this.config.maxApy;
                    if (minApySlider) minApySlider.value = this.config.minApy;
                }
                this.updateApyDisplay();
                this.markCustom();
            });
        }

        // Max Drawdown
        const drawdown = document.getElementById('maxDrawdown');
        if (drawdown) {
            drawdown.addEventListener('input', () => {
                this.config.maxDrawdown = parseInt(drawdown.value);
                document.getElementById('maxDrawdownValue').textContent = `-${drawdown.value}%`;
                this.markCustom();
            });
        }

        // Max allocation
        const allocSlider = document.getElementById('maxAllocation');
        const allocValue = document.getElementById('maxAllocationValue');
        if (allocSlider) {
            allocSlider.addEventListener('input', () => {
                this.config.maxAllocation = parseInt(allocSlider.value);
                allocValue.textContent = allocSlider.value + '%';
            });
        }

        // Deploy button
        const deployBtn = document.getElementById('deployAgentBtn');
        if (deployBtn) {
            deployBtn.addEventListener('click', () => this.deployAgent());
        }

        // Stop button
        const stopBtn = document.getElementById('stopAgentBtn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopAgent());
        }
    }

    bindAdvancedEvents() {
        // Slippage buttons
        document.querySelectorAll('.slippage-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.slippage-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.config.slippage = parseFloat(btn.dataset.slippage);
            });
        });

        // Compound buttons
        document.querySelectorAll('.compound-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.compound-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.config.compoundFrequency = parseInt(btn.dataset.freq);
            });
        });

        // Rebalance threshold
        const rebalanceSlider = document.getElementById('rebalanceThreshold');
        if (rebalanceSlider) {
            rebalanceSlider.addEventListener('input', () => {
                this.config.rebalanceThreshold = parseInt(rebalanceSlider.value);
                document.getElementById('rebalanceThresholdValue').textContent = rebalanceSlider.value + '%';
            });
        }

        // Max gas price
        const gasSlider = document.getElementById('maxGasPrice');
        if (gasSlider) {
            gasSlider.addEventListener('input', () => {
                this.config.maxGasPrice = parseInt(gasSlider.value);
                document.getElementById('maxGasPriceValue').textContent = gasSlider.value;
            });
        }

        // Toggles
        ['autoRebalance', 'onlyAudited', 'avoidIL', 'emergencyExit'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', () => {
                    this.config[id] = el.checked;
                    this.markCustom();
                });
            }
        });
    }

    bindCollapsibleEvents() {
        document.querySelectorAll('.collapsible-header').forEach(header => {
            header.addEventListener('click', () => {
                header.closest('.config-card').classList.toggle('collapsed');
            });
        });
    }

    markCustom() {
        // When user manually changes settings, mark as custom preset
        if (this.config.preset !== 'custom') {
            this.config.preset = 'custom';
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('.preset-btn[data-preset="custom"]')?.classList.add('active');
        }
    }

    bindChatEvents() {
        const input = document.getElementById('agentChatInput');
        const sendBtn = document.getElementById('sendAgentMessage');

        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendMessage();
            });
        }

        // Quick commands
        document.querySelectorAll('.quick-cmd').forEach(btn => {
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.cmd;
                if (input) input.value = cmd;
                this.sendMessage();
            });
        });
    }

    async sendMessage() {
        const input = document.getElementById('agentChatInput');
        const messagesContainer = document.getElementById('agentChatMessages');
        if (!input || !input.value.trim()) return;

        const userMessage = input.value.trim();
        input.value = '';

        // Add user message
        messagesContainer.innerHTML += `
            <div class="chat-message user">
                <div class="message-content">
                    <p>${userMessage}</p>
                </div>
            </div>
        `;

        // Process with AI
        const response = await this.processAgentCommand(userMessage);
        this.addAgentMessage(response);
    }

    async processAgentCommand(message) {
        const lower = message.toLowerCase();

        // Preset commands
        if (lower.includes('stable') && (lower.includes('farm') || lower.includes('yield'))) {
            this.applyPresetByName('stable-farmer');
            return "Stable Farmer preset applied! Focusing on safe stablecoin yields from Aave, Compound, and Curve.";
        }
        if (lower.includes('maximize') || lower.includes('max return') || lower.includes('aggressive')) {
            this.applyPresetByName('yield-maximizer');
            return "Yield Maximizer preset applied! Targeting 25-100%+ APY with higher risk tolerance.";
        }
        if (lower.includes('airdrop') || lower.includes('points')) {
            this.applyPresetByName('airdrop-hunter');
            return "Airdrop Hunter preset applied! Targeting emerging protocols for potential token distributions.";
        }
        if (lower.includes('eth') && (lower.includes('only') || lower.includes('maxi'))) {
            this.applyPresetByName('eth-maxi');
            return "ETH Maxi preset applied! Focusing on ETH and liquid staking tokens for conservative yields.";
        }
        if (lower.includes('balanced') || lower.includes('mix')) {
            this.applyPresetByName('balanced-growth');
            return "Balanced Growth preset applied! Mix of stable and volatile assets with moderate risk.";
        }

        // Specific asset focus
        if (lower.includes('usdc') || lower.includes('usdt') || lower.includes('stablecoin')) {
            this.setAssetsAndUpdate(['USDC', 'USDT', 'DAI', 'FRAX']);
            return "Configured for stablecoin focus: USDC, USDT, DAI, and FRAX. Risk set to low.";
        }

        // APY targets
        const apyMatch = lower.match(/(\d+)%?\s*(apy|yield|return)/);
        if (apyMatch) {
            const apy = parseInt(apyMatch[1]);
            this.config.minApy = Math.max(0, apy - 5);
            this.config.maxApy = apy + 15;
            this.updateAllUI();
            return `Target APY configured to ${this.config.minApy}%-${this.config.maxApy}%. I'll find vaults in this range.`;
        }

        // Protocol specific
        const protocols = ['aave', 'compound', 'curve', 'uniswap', 'beefy', 'yearn', 'morpho'];
        const mentionedProtocols = protocols.filter(p => lower.includes(p));
        if (mentionedProtocols.length > 0) {
            this.config.protocols = mentionedProtocols;
            this.updateAllUI();
            return `Protocol filter set to: ${mentionedProtocols.join(', ')}. Only vaults from these protocols will be considered.`;
        }

        // Duration
        const durationMatch = lower.match(/(\d+)\s*(month|week|year)/);
        if (durationMatch) {
            let days = parseInt(durationMatch[1]);
            const unit = durationMatch[2];
            if (unit.includes('month')) days *= 30;
            if (unit.includes('year')) days *= 365;
            if (unit.includes('week')) days *= 7;
            this.config.duration = days;
            document.querySelectorAll('.duration-btn').forEach(b => {
                b.classList.toggle('active', parseInt(b.dataset.days) === days);
            });
            return `Investment duration set to ${durationMatch[1]} ${unit}(s). The agent will optimize for this timeframe.`;
        }

        // No IL
        if (lower.includes('no il') || lower.includes('avoid impermanent') || lower.includes('single-sided')) {
            this.config.avoidIL = true;
            document.getElementById('avoidIL').checked = true;
            return "Impermanent Loss protection enabled. I'll focus on single-sided staking and lending protocols.";
        }

        return `I understand you want to "${message}". I can help configure:
• **Presets**: stable farmer, balanced, aggressive, airdrop hunter, ETH maxi
• **Target APY**: "I want 20% APY"
• **Assets**: "focus on stablecoins" or "only ETH"
• **Protocols**: "use only Aave and Compound"
• **Duration**: "invest for 3 months"

What would you like to configure?`;
    }

    applyPresetByName(name) {
        document.querySelectorAll('.preset-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.preset === name);
        });
        this.applyPreset(name);
    }

    setAssetsAndUpdate(assets) {
        this.config.preferredAssets = assets;
        this.config.riskLevel = 'low';
        this.updateAllUI();
        this.markCustom();
    }

    async deployAgent() {
        const btn = document.getElementById('deployAgentBtn');
        const statusBar = document.getElementById('agentStatusBar');

        // Check if wallet is connected (required for deployment)
        if (!window.connectedWallet) {
            this.addAgentMessage('⚠️ Please connect your wallet first to deploy an agent.');
            return;
        }

        btn.innerHTML = '<span>⏳</span> Deploying...';
        btn.disabled = true;

        try {
            // Get Pro Mode configuration if available
            const proHelper = window.AgentBuilderPro;
            const isProMode = proHelper?.isProModeActive() || false;
            let proConfig = null;

            if (isProMode && proHelper) {
                proConfig = proHelper.getProConfig();

                // Validate Pro Mode settings
                const validation = proHelper.validate();
                if (!validation.valid) {
                    this.addAgentMessage(`❌ Validation failed:\n${validation.errors.join('\n')}`);
                    btn.innerHTML = '<span>🚀</span> Deploy Agent';
                    btn.disabled = false;
                    return;
                }

                // Show warnings if any
                if (validation.warnings.length > 0) {
                    console.log('[AgentBuilder] Pro Mode warnings:', validation.warnings);
                }
            }

            // Run Neural Terminal deployment sequence
            const terminal = window.NeuralTerminal;
            if (terminal) {
                await terminal.runDeploymentSequence(this.config, proConfig);
            }

            // Simulate wallet creation
            const address = '0x' + Array.from({ length: 40 }, () =>
                '0123456789abcdef'[Math.floor(Math.random() * 16)]).join('');

            document.getElementById('agentAddress').textContent =
                address.slice(0, 6) + '...' + address.slice(-4);
            document.getElementById('agentBalance').textContent = '0 ETH';

            statusBar.style.display = 'flex';
            btn.innerHTML = '<span>✅</span> Agent Deployed';

            // Build configuration summary
            let configSummary = `🚀 Agent deployed successfully on **Base**!

**Agent Wallet:** \`${address.slice(0, 10)}...${address.slice(-6)}\`

**Configuration Summary:**
• Chain: Base (single-sided pools only)
• Strategy: ${this.config.preset.replace(/-/g, ' ')}
• Risk: ${this.config.riskLevel}
• APY Target: ${this.config.minApy}%-${this.config.maxApy}%
• Protocols: ${this.config.protocols.slice(0, 3).join(', ')}${this.config.protocols.length > 3 ? '...' : ''}
• Assets: ${this.config.preferredAssets.slice(0, 4).join(', ')}${this.config.preferredAssets.length > 4 ? '...' : ''}
• Max per vault: ${this.config.maxAllocation}%`;

            // Add Pro Mode details if active
            if (isProMode && proConfig) {
                configSummary += `

**🔥 Pro Mode Settings:**`;
                if (proConfig.leverage > 1) {
                    configSummary += `\n• Leverage: ${proConfig.leverage.toFixed(1)}x`;
                }
                if (proConfig.stopLossEnabled) {
                    configSummary += `\n• Stop Loss: ${proConfig.stopLossPercent}%`;
                }
                if (proConfig.takeProfitEnabled) {
                    configSummary += `\n• Take Profit: $${proConfig.takeProfitAmount}`;
                }
                if (proConfig.volatilityGuard) {
                    configSummary += `\n• Volatility Guard: Enabled`;
                }
                configSummary += `\n• Duration: ${proConfig.duration.value} ${proConfig.duration.unit}`;
                if (proConfig.customInstructions) {
                    configSummary += `\n• Custom: "${proConfig.customInstructions.slice(0, 50)}${proConfig.customInstructions.length > 50 ? '...' : ''}"`;
                }
            }

            configSummary += `

⚠️ Send USDC or ETH to the agent address on Base to start. The agent will automatically allocate to single-sided pools based on your settings.`;

            this.addAgentMessage(configSummary);

            // Log to backend (optional - for analytics)
            this.logDeploymentToBackend(address, isProMode, proConfig);

        } catch (error) {
            btn.innerHTML = '<span>❌</span> Deploy Failed';
            this.addAgentMessage(`Deployment failed: ${error.message}. Please try again.`);

            if (window.NeuralTerminal) {
                window.NeuralTerminal.log(`[ERROR] Deployment failed: ${error.message}`, 'error');
                window.NeuralTerminal.setStatus('ERROR');
            }
        }
    }

    async logDeploymentToBackend(address, isProMode, proConfig) {
        try {
            // Optional: Send deployment data to backend for analytics
            const payload = {
                agentAddress: address,
                chain: this.config.chain,
                preset: this.config.preset,
                riskLevel: this.config.riskLevel,
                protocols: this.config.protocols,
                assets: this.config.preferredAssets,
                isProMode: isProMode,
                proConfig: proConfig
            };
            console.log('[AgentBuilder] Deployment logged:', payload);
            // Could send to backend: await fetch('/api/agents/deploy', { ... })
        } catch (e) {
            console.error('[AgentBuilder] Failed to log deployment:', e);
        }
    }

    stopAgent() {
        const statusBar = document.getElementById('agentStatusBar');
        const btn = document.getElementById('deployAgentBtn');

        statusBar.style.display = 'none';
        btn.innerHTML = '<span>🚀</span> Deploy Agent';
        btn.disabled = false;

        this.addAgentMessage("Agent stopped. All positions will remain until you manually withdraw. You can redeploy anytime with new settings.");
    }

    addAgentMessage(text) {
        const messagesContainer = document.getElementById('agentChatMessages');
        if (!messagesContainer) return;

        messagesContainer.innerHTML += `
            <div class="chat-message agent">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <p>${text.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</p>
                </div>
            </div>
        `;
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Initialize when DOM ready
const agentBuilderUI = new AgentBuilderUI();
document.addEventListener('DOMContentLoaded', () => agentBuilderUI.init());

// Also export
window.AgentBuilderUI = agentBuilderUI;
