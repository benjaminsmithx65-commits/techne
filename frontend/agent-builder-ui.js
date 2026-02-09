/**
 * Agent Builder UI Logic - Extended Version
 * Handles configuration panel and chat interface interactions
 */

class AgentBuilderUI {
    constructor() {
        // Default config matches Steady preset (the default selected strategy)
        this.config = {
            // Strategy preset - Steady is default
            // Core identifiers
            chain: 'base',
            preset: 'balanced-growth',
            poolType: 'single',

            // Risk & Returns - Steady values
            riskLevel: 'medium',
            tradingStyle: 'moderate',
            minApy: 10,
            maxApy: 30,
            maxApyUnlimited: false,
            maxDrawdown: 20,

            // Protocols - Base only
            protocols: ['morpho', 'aave', 'moonwell', 'aerodrome'],

            // Assets - Steady includes USDT
            preferredAssets: ['USDC', 'WETH', 'USDT'],

            // Duration & Allocation
            duration: 30,
            maxAllocation: 20,
            vaultCount: 5,

            // Advanced
            autoRebalance: true,
            rebalanceThreshold: 5,
            maxGasPrice: 50,
            slippage: 0.5,
            compoundFrequency: 7,
            onlyAudited: true,
            avoidIL: false,  // Steady allows dual pools
            emergencyExit: true,
            apyCheckHours: 24,

            // Pro Features
            minPoolTvl: 10000000,  // $10M for Steady
            maxPoolTvl: null,      // null = unlimited
            harvestStrategy: 'compound',
            volatilityThreshold: 10,
            mevProtection: false
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
                minApy: 5, maxApy: 50, maxDrawdown: 20,
                protocols: ['morpho', 'aave', 'moonwell', 'aerodrome'],
                preferredAssets: ['USDC', 'WETH'],
                vaultCount: 5, avoidIL: true, onlyAudited: true
            },
            'yield-maximizer': {
                riskLevel: 'high',
                minApy: 25, maxApy: 500, maxDrawdown: 40,
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
        this.bindModeToggle(); // NEW: 3-tier mode switching
        this.bindAIInstantEvents(); // NEW: Strategy card selection
        this.bindChainPoolEvents();
        this.bindPresetEvents();
        this.bindConfigEvents();
        this.bindAdvancedEvents();
        this.bindChatEvents();
        this.bindCollapsibleEvents();

        // Fetch protocol implemented status and disable coming soon protocols
        this.applyProtocolImplementedStatus();

        // Set initial mode
        document.body.dataset.builderMode = 'instant';
        console.log('[AgentBuilder] Extended UI initialized with AI-Instant mode');
    }

    /**
     * Fetch protocol list from API and disable unimplemented protocols
     * @returns {Promise<void>}
     */
    async applyProtocolImplementedStatus() {
        try {
            const response = await fetch('/api/protocols?pool_type=all');
            const data = await response.json();

            if (data.success && data.protocols) {
                // Build map of protocol ID -> implemented status
                const implementedMap = {};
                data.protocols.forEach(p => {
                    implementedMap[p.id] = p.implemented !== false;  // Default to true
                });

                // Apply disabled class to unimplemented protocol chips
                document.querySelectorAll('.protocol-chip').forEach(chip => {
                    const protocolId = chip.dataset.protocol;
                    const isImplemented = implementedMap[protocolId];

                    if (isImplemented === false) {
                        chip.classList.add('disabled');
                        chip.classList.remove('active');  // Remove active if disabled
                        console.log(`[AgentBuilder] Protocol ${protocolId} disabled (Coming Soon)`);
                    }
                });

                // Also remove disabled protocols from default config
                this.config.protocols = this.config.protocols.filter(p => implementedMap[p] !== false);

                console.log('[AgentBuilder] Protocol implemented status applied');
            }
        } catch (error) {
            console.error('[AgentBuilder] Failed to fetch protocol status:', error);
        }
    }

    // NEW: 3-Tier Mode Toggle (AI-Instant / Flexible / Advanced)
    bindModeToggle() {
        document.querySelectorAll('#builderModeToggle .mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Update active button
                document.querySelectorAll('#builderModeToggle .mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const mode = btn.dataset.mode;
                document.body.dataset.builderMode = mode;

                console.log('[AgentBuilder] Mode switched to:', mode);
                // Panel visibility is controlled by CSS via [data-builder-mode] attribute
            });
        });
    }

    // NEW: AI-Instant Strategy Card Selection
    bindAIInstantEvents() {
        const strategies = {
            'safe': {
                // Risk & Returns
                riskLevel: 'low',
                minApy: 5, maxApy: 12, maxDrawdown: 10,
                // Protocols & Assets
                protocols: ['aave', 'morpho', 'moonwell', 'compound'],
                preferredAssets: ['USDC', 'USDT'],
                poolType: 'single',
                // Pool Selection
                minPoolTvl: 10000000,  // $10M
                avoidIL: true,
                onlyAudited: true,
                // Allocation & Vaults
                vaultCount: 4,
                maxAllocation: 25,
                // Execution
                rebalanceThreshold: 3,
                maxGasPrice: 30,
                slippage: 0.3,
                compoundFrequency: 7,
                apyCheckHours: 24,
                // Duration
                duration: 0,  // 0 = infinite, runs until APY drops below minApy (5%)
                exitOnLowApy: true,  // Exit when APY < 5%
                // Safety
                emergencyExit: true,
                harvestStrategy: 'compound',
                volatilityThreshold: 5,
                mevProtection: false,
                narrative: '[AI] Strategy: <strong>Safe</strong> selected. Maximum security mode. Targeting 5-12% APY on audited protocols only. TVL $10M+ required. No IL exposure. Runs until APY < 5%.'
            },
            'steady': {
                // Risk & Returns
                riskLevel: 'medium',
                minApy: 10, maxApy: 30, maxDrawdown: 20,
                // Protocols & Assets
                protocols: ['morpho', 'aave', 'moonwell', 'aerodrome'],
                preferredAssets: ['USDC', 'WETH', 'USDT'],
                poolType: 'both',  // single + dual allowed
                maxDualPools: 3,   // max 3 dual-sided pools
                // Pool Selection
                minPoolTvl: 10000000,  // $10M
                avoidIL: false,  // Dual pools have IL
                onlyAudited: true,
                // Allocation & Vaults
                vaultCount: 5,
                maxAllocation: 20,
                // Execution
                rebalanceThreshold: 5,
                maxGasPrice: 50,
                slippage: 0.5,
                compoundFrequency: 7,
                apyCheckHours: 24,
                // Safety
                emergencyExit: true,
                harvestStrategy: 'compound',
                volatilityThreshold: 10,
                mevProtection: false,
                narrative: '[AI] Strategy: <strong>Steady</strong> selected. Balanced approach. Targeting 10-30% APY. TVL $10M+, single + dual pools (max 3 dual). Ready to deploy.'
            },
            'degen': {
                // Risk & Returns
                riskLevel: 'high',
                minApy: 30, maxApy: 100, maxDrawdown: 40,
                // Protocols & Assets
                protocols: ['aerodrome', 'beefy', 'morpho', 'moonwell', 'uniswap', 'extra'],
                preferredAssets: ['WETH', 'AERO', 'USDC', 'USDT'],
                poolType: 'dual',
                // Pool Selection
                minPoolTvl: 1000000,  // $1M
                avoidIL: false,
                onlyAudited: false,
                // Allocation & Vaults
                vaultCount: 7,
                maxAllocation: 15,
                // Execution
                rebalanceThreshold: 10,
                maxGasPrice: 100,
                slippage: 1.0,
                compoundFrequency: 1,
                apyCheckHours: 12,
                // Safety
                emergencyExit: true,
                harvestStrategy: 'compound',
                volatilityThreshold: 20,
                mevProtection: true,
                narrative: '[AI] Strategy: <strong>Degen</strong> selected. Aggressive growth. Targeting 30-100%+ APY. Active rotation, dual-sided LPs, IL exposure. LFG! 🚀'
            }
        };

        // Strategy card click
        document.querySelectorAll('.strategy-card').forEach(card => {
            card.addEventListener('click', () => {
                // Update active card
                document.querySelectorAll('.strategy-card').forEach(c => c.classList.remove('active'));
                card.classList.add('active');

                const strategy = card.dataset.strategy;
                const config = strategies[strategy];

                if (config) {
                    // Apply strategy config - FULLY REPLACE relevant fields
                    Object.assign(this.config, config);

                    // Set preset name for Neural Terminal display
                    this.config.preset = strategy;

                    // Log for debugging
                    console.log('[AgentBuilder] AI-Instant strategy applied:', strategy);
                    console.log('[AgentBuilder] Config now:', this.config.minApy, '-', this.config.maxApy, '% APY');

                    // Update narrative terminal
                    const narrative = document.getElementById('aiNarrativeContent');
                    if (narrative) {
                        narrative.innerHTML = config.narrative;
                    }
                }
            });
        });

        // Deploy button
        const deployBtn = document.getElementById('deployInstantBtn');
        if (deployBtn) {
            deployBtn.addEventListener('click', () => {
                const amount = document.getElementById('instantAmount')?.value || 1000;
                console.log('[AgentBuilder] Deploying AI-Instant with amount:', amount);

                // Store amount in config for deploy
                this.config.amount = parseFloat(amount);

                // Use the same ERC-8004 cold deploy flow as Advanced mode
                this.deployAgent();
            });
        }
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

        // APY sliders and custom inputs
        const minApySlider = document.getElementById('minApyConfig');
        const maxApySlider = document.getElementById('maxApyConfig');
        const minApyInput = document.getElementById('minApyInput');
        const maxApyInput = document.getElementById('maxApyInput');
        const maxApyPlus = document.getElementById('maxApyPlus');
        if (minApySlider) minApySlider.value = this.config.minApy;
        if (maxApySlider) maxApySlider.value = this.config.maxApy;
        if (minApyInput) minApyInput.value = this.config.minApy;
        if (maxApyInput) maxApyInput.value = this.config.maxApy >= 500 ? 500 : this.config.maxApy;
        if (maxApyPlus) maxApyPlus.textContent = this.config.maxApy >= 500 ? '%+' : '%';
        this.config.maxApyUnlimited = this.config.maxApy >= 500;
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

        // Show "500%+" when at max slider value (means unlimited)
        if (minDisp) {
            minDisp.textContent = this.config.minApy >= 500 ? '500%+' : this.config.minApy + '%';
        }
        if (maxDisp) {
            // When max APY is 500, it means unlimited (500%+)
            if (this.config.maxApy >= 500) {
                maxDisp.textContent = '500%+';
                // Set internal config to very high value for unlimited search
                this.config.maxApyUnlimited = true;
            } else {
                maxDisp.textContent = this.config.maxApy + '%';
                this.config.maxApyUnlimited = false;
            }
        }
    }

    updateTradingStyleHint(style) {
        const hint = document.getElementById('tradingStyleHint');
        if (!hint) return;

        const hints = {
            conservative: '<strong>Conservative:</strong> TVL >$1M, APY <100%, Pool age >14 days, Audited only',
            moderate: '<strong>Moderate:</strong> TVL >$500k, APY <300%, Pool age >7 days',
            aggressive: '<strong>Aggressive:</strong> TVL >$100k, APY unlimited, No age limit, All tokens allowed'
        };

        hint.innerHTML = hints[style] || hints.moderate;
    }

    bindConfigEvents() {
        // Risk selector (legacy) and Trading Style selector
        document.querySelectorAll('.risk-option').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.risk-option').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Handle both legacy data-risk and new data-style attributes
                if (btn.dataset.style) {
                    this.config.tradingStyle = btn.dataset.style;
                    this.updateTradingStyleHint(btn.dataset.style);
                    console.log('[AgentBuilder] Trading style:', this.config.tradingStyle);
                } else if (btn.dataset.risk) {
                    this.config.riskLevel = btn.dataset.risk;
                }
                this.markCustom();
            });
        });

        // Duration buttons
        document.querySelectorAll('.duration-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.duration-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                // Handle both data-days and data-hours attributes
                if (btn.dataset.days !== undefined) {
                    this.config.duration = parseInt(btn.dataset.days) || 0;
                } else if (btn.dataset.hours !== undefined) {
                    // Convert hours to fractional days
                    this.config.duration = parseInt(btn.dataset.hours) / 24;
                } else {
                    this.config.duration = 30; // Default fallback
                }
                // Clear custom inputs when preset selected
                const customValue = document.getElementById('customDurationValue');
                const customUnit = document.getElementById('customDurationUnit');
                if (customValue) customValue.value = '';
                console.log('[AgentBuilder] Duration preset:', this.config.duration, 'days');
            });
        });

        // Custom Duration Value + Unit combo
        const customDurationValue = document.getElementById('customDurationValue');
        const customDurationUnit = document.getElementById('customDurationUnit');

        const updateCustomDuration = () => {
            if (!customDurationValue || !customDurationUnit) return;
            const val = parseInt(customDurationValue.value) || 0;
            const unit = customDurationUnit.value || 'days';

            if (val > 0) {
                // Convert to days for config
                let days = val;
                switch (unit) {
                    case 'hours': days = val / 24; break;
                    case 'days': days = val; break;
                    case 'weeks': days = val * 7; break;
                    case 'months': days = val * 30; break;
                }
                this.config.duration = days;
                // Deselect preset buttons
                document.querySelectorAll('.duration-btn').forEach(b => b.classList.remove('active'));
                console.log('[AgentBuilder] Custom duration:', val, unit, '→', days, 'days');
            }
        };

        if (customDurationValue) {
            customDurationValue.addEventListener('change', updateCustomDuration);
            customDurationValue.addEventListener('input', updateCustomDuration);
        }
        if (customDurationUnit) {
            customDurationUnit.addEventListener('change', updateCustomDuration);
        }

        // Vault Count buttons
        document.querySelectorAll('.vault-count-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.vault-count-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const count = btn.dataset.count;
                this.config.vaultCount = count === 'auto' ? 'auto' : parseInt(count);
                console.log('[AgentBuilder] Vault count:', this.config.vaultCount);
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
                // Block clicks on disabled (Coming Soon) protocols
                if (btn.classList.contains('disabled')) {
                    console.log('[AgentBuilder] Protocol not yet implemented:', btn.dataset.protocol);
                    return;
                }

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
        const minApyInput = document.getElementById('minApyInput');
        const maxApyInput = document.getElementById('maxApyInput');
        const maxApyPlus = document.getElementById('maxApyPlus');

        // Sync function for all APY controls
        const syncApyControls = () => {
            // Show "+" when at 500 (unlimited)
            if (maxApyPlus) {
                maxApyPlus.textContent = this.config.maxApy >= 500 ? '%+' : '%';
            }
            // Sync input fields with config
            if (minApyInput) minApyInput.value = this.config.minApy;
            if (maxApyInput) maxApyInput.value = this.config.maxApy >= 500 ? 500 : this.config.maxApy;
            // Update unlimited flag
            this.config.maxApyUnlimited = this.config.maxApy >= 500;
        };

        if (minApySlider) {
            minApySlider.addEventListener('input', () => {
                this.config.minApy = parseInt(minApySlider.value);
                if (this.config.minApy > this.config.maxApy) {
                    this.config.maxApy = this.config.minApy;
                    if (maxApySlider) maxApySlider.value = this.config.maxApy;
                }
                syncApyControls();
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
                syncApyControls();
                this.updateApyDisplay();
                this.markCustom();
            });
        }

        // Custom input fields - sync with sliders
        if (minApyInput) {
            minApyInput.addEventListener('change', () => {
                let val = parseInt(minApyInput.value) || 0;
                val = Math.max(0, Math.min(500, val));
                this.config.minApy = val;
                if (minApySlider) minApySlider.value = val;
                if (this.config.minApy > this.config.maxApy) {
                    this.config.maxApy = this.config.minApy;
                    if (maxApySlider) maxApySlider.value = this.config.maxApy;
                }
                syncApyControls();
                this.updateApyDisplay();
                this.markCustom();
            });
        }
        if (maxApyInput) {
            maxApyInput.addEventListener('change', () => {
                let val = parseInt(maxApyInput.value) || 0;
                val = Math.max(0, Math.min(500, val));
                this.config.maxApy = val;
                if (maxApySlider) maxApySlider.value = val;
                if (this.config.maxApy < this.config.minApy) {
                    this.config.minApy = this.config.maxApy;
                    if (minApySlider) minApySlider.value = this.config.minApy;
                }
                syncApyControls();
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

        // APY Check Window buttons (12h, 24h, 3d, 7d)
        document.querySelectorAll('.apy-check-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.apy-check-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.config.apyCheckHours = parseInt(btn.dataset.hours);
                // Clear custom input when preset selected
                const customInput = document.getElementById('apyCheckCustom');
                if (customInput) customInput.value = '';
                console.log('[AgentBuilder] APY check window:', this.config.apyCheckHours, 'hours');
            });
        });

        // APY Check Custom input
        const apyCheckCustom = document.getElementById('apyCheckCustom');
        if (apyCheckCustom) {
            apyCheckCustom.addEventListener('change', () => {
                const hours = parseInt(apyCheckCustom.value);
                if (hours && hours > 0) {
                    document.querySelectorAll('.apy-check-btn').forEach(b => b.classList.remove('active'));
                    this.config.apyCheckHours = hours;
                    console.log('[AgentBuilder] APY check window (custom):', hours, 'hours');
                }
            });
        }

        // TVL Min/Max Sliders and Inputs
        const tvlMinSlider = document.getElementById('tvlMinSlider');
        const tvlMaxSlider = document.getElementById('tvlMaxSlider');
        const tvlMinInput = document.getElementById('tvlMinInput');
        const tvlMaxInput = document.getElementById('tvlMaxInput');

        const formatTvl = (val) => {
            if (val >= 1000000) return `$${(val / 1000000).toFixed(1)}M`;
            if (val >= 1000) return `$${(val / 1000).toFixed(0)}K`;
            return `$${val}`;
        };

        if (tvlMinSlider) {
            tvlMinSlider.addEventListener('input', () => {
                const val = parseInt(tvlMinSlider.value) || 0;
                this.config.minPoolTvl = val;
                if (tvlMinInput) tvlMinInput.value = val;
                const display = document.getElementById('tvlMinValue');
                if (display) display.textContent = formatTvl(val);
                console.log('[AgentBuilder] TVL min:', formatTvl(val));
            });
        }
        if (tvlMaxSlider) {
            tvlMaxSlider.addEventListener('input', () => {
                const val = parseInt(tvlMaxSlider.value) || 100000000;
                this.config.maxPoolTvl = val;
                if (tvlMaxInput) tvlMaxInput.value = val;
                const display = document.getElementById('tvlMaxValue');
                if (display) display.textContent = formatTvl(val);
            });
        }
        if (tvlMinInput) {
            tvlMinInput.addEventListener('change', () => {
                const val = parseInt(tvlMinInput.value) || 0;
                this.config.minPoolTvl = val;
                if (tvlMinSlider) tvlMinSlider.value = val;
            });
        }
        if (tvlMaxInput) {
            tvlMaxInput.addEventListener('change', () => {
                const val = parseInt(tvlMaxInput.value) || 100000000;
                this.config.maxPoolTvl = val;
                if (tvlMaxSlider) tvlMaxSlider.value = val;
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
        // New Command Bar (replaces old chat)
        const commandInput = document.getElementById('agentCommandInput');
        const sendBtn = document.getElementById('sendCommand');

        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        if (commandInput) {
            commandInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendMessage();
            });
        }

        // Harvest Strategy buttons
        document.querySelectorAll('.harvest-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.harvest-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.config.harvestStrategy = btn.dataset.harvest;
                console.log('[AgentBuilder] Harvest strategy:', this.config.harvestStrategy);
            });
        });
    }

    async sendMessage() {
        const input = document.getElementById('agentCommandInput');
        if (!input || !input.value.trim()) return;

        const userMessage = input.value.trim();
        input.value = '';

        console.log('[AgentBuilder] Command:', userMessage);

        // Process with AI
        const response = await this.processAgentCommand(userMessage);

        // Show response in console (could add toast notification later)
        console.log('[AgentBuilder] Response:', response);

        // Optional: Show alert or toast for now
        if (response) {
            alert(`Agent: ${response}`);
        }
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
            this.addAgentMessage('<span class="techne-icon">' + TechneIcons.warning + '</span> Please connect your wallet first to deploy an agent.');
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
                    this.addAgentMessage('<span class="techne-icon">' + TechneIcons.error + '</span> Validation failed:\\n' + validation.errors.join('\\n'));
                    btn.innerHTML = '<span class="techne-icon">' + TechneIcons.rocket + '</span> Deploy Agent';
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

            // REQUEST SIGNATURE for ownership verification
            // This proves the user owns this wallet and authorizes agent creation
            const timestamp = Date.now();
            const signMessage = `Deploy Techne Agent\nWallet: ${window.connectedWallet}\nTimestamp: ${timestamp}`;

            let signature = null;
            try {
                signature = await window.ethereum.request({
                    method: 'personal_sign',
                    params: [signMessage, window.connectedWallet]
                });
                console.log('[AgentBuilder] User signed deploy message');
            } catch (signError) {
                console.error('[AgentBuilder] Signature declined - deploy cancelled:', signError);
                btn.innerHTML = '<span class="techne-icon">' + TechneIcons.settings + '</span> Deploy Agent';
                btn.disabled = false;
                alert('Signature required to deploy agent. Please sign the message to continue.');
                return;
            }

            // Send deployment config to backend API
            // Backend returns transaction data for user to sign (cold deploy)
            const API_BASE = window.API_BASE || '';
            let deployedAddress = null;
            let agentId = null;

            try {
                const response = await fetch(`${API_BASE}/api/agent/deploy`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_address: window.connectedWallet,
                        signature: signature,
                        sign_message: signMessage,
                        chain: this.config.chain,
                        preset: this.config.preset,
                        pool_type: this.config.poolType,
                        risk_level: this.config.riskLevel,
                        min_apy: this.config.minApy,
                        max_apy: this.config.maxApyUnlimited ? 10000 : this.config.maxApy,
                        max_drawdown: this.config.maxDrawdown,
                        protocols: this.config.protocols,
                        preferred_assets: this.config.preferredAssets,
                        max_allocation: this.config.maxAllocation,
                        vault_count: this.config.vaultCount,
                        auto_rebalance: this.config.autoRebalance,
                        only_audited: this.config.onlyAudited,
                        rebalance_threshold: this.config.rebalanceThreshold,
                        max_gas_price: this.config.maxGasPrice,
                        slippage: this.config.slippage,
                        compound_frequency: this.config.compoundFrequency,
                        avoid_il: this.config.avoidIL,
                        emergency_exit: this.config.emergencyExit,
                        min_pool_tvl: this.config.minPoolTvl,
                        max_pool_tvl: this.config.maxPoolTvl,
                        duration: this.config.duration,
                        apy_check_hours: this.config.apyCheckHours,
                        trading_style: this.config.tradingStyle,
                        is_pro_mode: isProMode,
                        pro_config: proConfig
                    })

                });

                const result = await response.json();
                console.log('[AgentBuilder] Backend deployment result:', result, 'status:', response.status);

                // Check HTTP status first (for 401, 400, 422, 500 errors)
                if (!response.ok) {
                    // Handle Pydantic validation errors (422) - detail is an array
                    let errorMsg;
                    if (Array.isArray(result.detail)) {
                        // Extract field names and messages from Pydantic errors
                        errorMsg = result.detail.map(e => {
                            const field = e.loc ? e.loc.join('.') : 'unknown';
                            return `${field}: ${e.msg}`;
                        }).join('; ');
                    } else {
                        errorMsg = result.detail || result.message || `HTTP ${response.status}`;
                    }
                    throw new Error(errorMsg);
                }

                if (!result.success) {
                    throw new Error(result.detail || result.message || 'Backend deployment failed');
                }

                agentId = result.agent_id;
                deployedAddress = result.agent_address;

                // COLD DEPLOY: If backend wants us to send tx to MetaMask
                if (result.requires_transaction && result.transaction) {
                    console.log('[AgentBuilder] Cold deploy - sending tx to MetaMask for user to sign...');
                    this.addAgentMessage('<span class="techne-icon">' + TechneIcons.code + '</span> Deploying Smart Account on-chain...\n**Please confirm the transaction in MetaMask to pay gas fee.**');

                    try {
                        // Send transaction via MetaMask - USER PAYS GAS
                        const txHash = await window.ethereum.request({
                            method: 'eth_sendTransaction',
                            params: [{
                                from: window.connectedWallet,
                                to: result.transaction.to,
                                data: result.transaction.data,
                                gas: result.transaction.gas,
                                value: result.transaction.value || '0x0'
                            }]
                        });

                        console.log('[AgentBuilder] User signed deploy tx:', txHash);
                        this.addAgentMessage('<span class="techne-icon">' + TechneIcons.code + '</span> Transaction submitted! Waiting for confirmation...');

                        // Wait a moment for tx to be mined (on Base it's fast)
                        await new Promise(resolve => setTimeout(resolve, 3000));

                        // Confirm deployment with backend (saves agent to storage)
                        const confirmResponse = await fetch(`${API_BASE}/api/agent/confirm-deploy`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                user_address: window.connectedWallet,
                                agent_id: agentId,
                                tx_hash: txHash
                            })
                        });

                        const confirmResult = await confirmResponse.json();
                        console.log('[AgentBuilder] Confirm deploy result:', confirmResult);

                        if (!confirmResult.success) {
                            throw new Error(confirmResult.detail || 'Failed to confirm deployment');
                        }

                        deployedAddress = confirmResult.agent_address;
                        console.log('[AgentBuilder] Agent deployed and confirmed:', deployedAddress);

                        // STEP 2: Setup auto-trading (session key + protocol whitelist)
                        this.addAgentMessage('<span class="techne-icon">' + TechneIcons.chartLine + '</span> Setting up auto-trading permissions...\n**Please confirm one more transaction to enable automated trading.**');

                        try {
                            const setupResponse = await fetch(`${API_BASE}/api/agent/setup-auto-trading`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    user_address: window.connectedWallet,
                                    agent_id: agentId,
                                    agent_address: deployedAddress
                                })
                            });

                            const setupResult = await setupResponse.json();
                            console.log('[AgentBuilder] Setup auto-trading result:', setupResult);

                            if (setupResult.success && setupResult.transaction) {
                                // Send setup transaction via MetaMask
                                const setupTxHash = await window.ethereum.request({
                                    method: 'eth_sendTransaction',
                                    params: [{
                                        from: window.connectedWallet,
                                        to: setupResult.transaction.to,
                                        data: setupResult.transaction.data,
                                        gas: setupResult.transaction.gas,
                                        value: setupResult.transaction.value || '0x0'
                                    }]
                                });

                                console.log('[AgentBuilder] Auto-trading setup tx:', setupTxHash);
                                this.addAgentMessage('<span class="techne-icon">' + TechneIcons.check + '</span> **Auto-trading enabled!**\nSession key: `' + setupResult.session_key.slice(0, 10) + '...`\nWhitelisted: ' + setupResult.protocols_to_whitelist.join(', '));

                                // Wait for tx confirmation
                                await new Promise(resolve => setTimeout(resolve, 2000));
                            } else {
                                console.log('[AgentBuilder] Auto-trading setup skipped:', setupResult.error || 'No transaction needed');
                            }
                        } catch (setupError) {
                            // Non-blocking - agent is deployed, just warn about manual setup
                            console.warn('[AgentBuilder] Auto-trading setup failed:', setupError);
                            if (setupError.code === 4001) {
                                this.addAgentMessage('<span class="techne-icon">' + TechneIcons.alert + '</span> **Auto-trading not enabled** - you declined the transaction.\nYou can enable it later in Portfolio → Agent Settings.');
                            }
                        }

                    } catch (txError) {
                        if (txError.code === 4001) {
                            // User rejected transaction
                            console.log('[AgentBuilder] User rejected transaction');
                            throw new Error('Transaction cancelled - you must pay gas to deploy the agent');
                        }
                        throw txError;
                    }
                } else if (result.already_deployed) {
                    console.log('[AgentBuilder] Agent already deployed:', deployedAddress);
                } else {
                    console.log('[AgentBuilder] Agent deployed (no tx required):', deployedAddress);
                }

                if (!deployedAddress) {
                    throw new Error('Backend did not return agent address');
                }
                console.log('[AgentBuilder] Final Smart Account address:', deployedAddress);

            } catch (apiError) {
                console.error('[AgentBuilder] Backend API call failed:', apiError);
                btn.innerHTML = '<span class="techne-icon">' + TechneIcons.settings + '</span> Deploy Agent';
                btn.disabled = false;
                // Extract error message properly from any error type
                const errorMessage = apiError?.message || apiError?.detail ||
                    (typeof apiError === 'string' ? apiError : JSON.stringify(apiError));
                alert('Deployment failed: ' + errorMessage);
                return;
            }


            // Use address from backend - NO FALLBACK (signature verified, backend required)
            let address = deployedAddress;
            console.log('[AgentBuilder] Final agent address:', address);

            document.getElementById('agentAddress').textContent =
                address.slice(0, 6) + '...' + address.slice(-4);
            document.getElementById('agentBalance').textContent = '0 ETH';

            statusBar.style.display = 'flex';
            btn.innerHTML = '<span class="techne-icon">' + TechneIcons.success + '</span> Agent Deployed';

            // Build configuration summary
            let configSummary = `<span class="techne-icon" style="vertical-align: middle;">${TechneIcons.rocket}</span> Agent deployed successfully on **Base**!

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

**<span class="techne-icon">${TechneIcons.fire}</span> Pro Mode Settings:**`;
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
                if (proConfig.mevProtection) {
                    configSummary += `\n• MEV Protection: Enabled (Flashbots)`;
                }
                configSummary += `\n• Duration: ${proConfig.duration.value} ${proConfig.duration.unit}`;
                if (proConfig.customInstructions) {
                    configSummary += `\n• Custom: "${proConfig.customInstructions.slice(0, 50)}${proConfig.customInstructions.length > 50 ? '...' : ''}"`;
                }
            }

            configSummary += `

<span class="techne-icon">${TechneIcons.warning}</span> Send USDC or ETH to the agent address on Base to start. The agent will automatically allocate to single-sided pools based on your settings.`;

            this.addAgentMessage(configSummary);

            // Save deployed agent to localStorage for Portfolio integration
            this.saveDeployedAgent(address, isProMode, proConfig);

            // Log to backend (optional - for analytics)
            this.logDeploymentToBackend(address, isProMode, proConfig);

            // Redirect to Portfolio after 3 seconds
            setTimeout(() => {
                this.addAgentMessage('🚀 Redirecting to Portfolio Dashboard...');
                setTimeout(() => {
                    // Navigate to Portfolio section
                    const portfolioNav = document.querySelector('[data-section="portfolio"]');
                    if (portfolioNav) {
                        portfolioNav.click();
                        // Force complete refresh after navigation - longer delay for backend sync
                        setTimeout(async () => {
                            if (window.PortfolioDash) {
                                console.log('[AgentBuilder] Force refreshing Portfolio after deploy...');
                                // First reload agents from backend/localStorage
                                await window.PortfolioDash.loadAgents();
                                // Wait extra for data propagation
                                await new Promise(r => setTimeout(r, 500));
                                // Then refresh portfolio data (balances etc)
                                await window.PortfolioDash.loadPortfolioData();
                                // Also sync agent status display
                                window.PortfolioDash.syncAgentStatus();
                                // Update Fund button state (no longer grayed out)
                                window.PortfolioDash.updateFundButtonState();
                                window.PortfolioDash.updateUI();
                                console.log('[AgentBuilder] Portfolio refresh complete - Fund button should be active');
                            }
                        }, 1500);  // Increased from 800ms to 1500ms for backend sync
                    }
                }, 1500);
            }, 2000);

        } catch (error) {
            btn.innerHTML = '<span class="techne-icon">' + TechneIcons.error + '</span> Deploy Failed';
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

    saveDeployedAgent(address, isProMode, proConfig, backendResult = null) {
        // Save agent configuration to localStorage for Portfolio integration
        // Supports multiple agents (max 5) per wallet

        const agentId = backendResult?.agent_id || `agent_${Date.now()}`;

        const newAgent = {
            id: agentId,
            name: `Agent #${this.getDeployedAgents().length + 1}`,
            address: address,
            chain: this.config.chain,
            preset: this.config.preset,
            riskLevel: this.config.riskLevel,
            minApy: this.config.minApy,
            maxApy: this.config.maxApy,
            protocols: this.config.protocols,
            preferredAssets: this.config.preferredAssets,
            maxAllocation: this.config.maxAllocation,
            vaultCount: this.config.vaultCount,
            isProMode: isProMode,
            proConfig: proConfig,
            deployedAt: new Date().toISOString(),
            isActive: true
        };

        // Get existing agents
        let agents = this.getDeployedAgents();

        // Check max limit
        const MAX_AGENTS = 5;
        if (agents.length >= MAX_AGENTS) {
            console.warn('[AgentBuilder] Max agents reached, replacing oldest inactive');
            // Find oldest inactive agent to replace
            const inactiveIndex = agents.findIndex(a => !a.isActive);
            if (inactiveIndex >= 0) {
                agents.splice(inactiveIndex, 1);
            } else {
                console.error('[AgentBuilder] Cannot deploy: max 5 active agents');
                return;
            }
        }

        // Add new agent
        agents.push(newAgent);

        // Save to localStorage
        localStorage.setItem('techne_deployed_agents', JSON.stringify(agents));

        // Also keep single agent reference for backward compatibility
        localStorage.setItem('techne_deployed_agent', JSON.stringify(newAgent));

        // Also update global state
        window.deployedAgent = newAgent;
        window.deployedAgents = agents;

        console.log('[AgentBuilder] Agent saved. Total agents:', agents.length);
    }

    getDeployedAgents() {
        // Get all agents from localStorage
        try {
            const saved = localStorage.getItem('techne_deployed_agents');
            return saved ? JSON.parse(saved) : [];
        } catch (e) {
            return [];
        }
    }

    static getDeployedAgent() {
        // Static method to retrieve most recent active agent from localStorage
        try {
            const saved = localStorage.getItem('techne_deployed_agents');
            if (saved) {
                const agents = JSON.parse(saved);
                // Return first active agent
                return agents.find(a => a.isActive) || agents[agents.length - 1] || null;
            }
            // Fallback to old single agent format
            const oldSaved = localStorage.getItem('techne_deployed_agent');
            return oldSaved ? JSON.parse(oldSaved) : null;
        } catch (e) {
            console.error('[AgentBuilder] Failed to load deployed agent:', e);
            return null;
        }
    }

    static getDeployedAgents() {
        // Static method to retrieve all agents
        try {
            const saved = localStorage.getItem('techne_deployed_agents');
            return saved ? JSON.parse(saved) : [];
        } catch (e) {
            return [];
        }
    }

    static deleteAgent(agentId) {
        // Delete an agent from localStorage
        try {
            let agents = AgentBuilderUI.getDeployedAgents();
            const index = agents.findIndex(a => a.id === agentId);
            if (index >= 0) {
                agents.splice(index, 1);
                localStorage.setItem('techne_deployed_agents', JSON.stringify(agents));
                console.log('[AgentBuilder] Agent deleted:', agentId);
                return true;
            }
            return false;
        } catch (e) {
            console.error('[AgentBuilder] Failed to delete agent:', e);
            return false;
        }
    }

    stopAgent() {
        const statusBar = document.getElementById('agentStatusBar');
        const btn = document.getElementById('deployAgentBtn');

        statusBar.style.display = 'none';
        btn.innerHTML = '<span class="techne-icon">' + TechneIcons.rocket + '</span> Deploy Agent';
        btn.disabled = false;

        // Mark agent as inactive in localStorage
        try {
            const saved = localStorage.getItem('techne_deployed_agent');
            if (saved) {
                const agent = JSON.parse(saved);
                agent.isActive = false;
                agent.stoppedAt = new Date().toISOString();
                localStorage.setItem('techne_deployed_agent', JSON.stringify(agent));
                window.deployedAgent = agent;
                console.log('[AgentBuilder] Agent marked as inactive');
            }
        } catch (e) {
            console.error('[AgentBuilder] Failed to update agent status:', e);
        }

        this.addAgentMessage("Agent stopped. All positions will remain until you manually withdraw. You can redeploy anytime with new settings.");
    }

    addAgentMessage(text) {
        const messagesContainer = document.getElementById('agentChatMessages');
        if (!messagesContainer) return;

        messagesContainer.innerHTML += `
            <div class="chat-message agent">
                <div class="message-avatar"><span class="techne-icon">${TechneIcons.get('robot', 20)}</span></div>
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
