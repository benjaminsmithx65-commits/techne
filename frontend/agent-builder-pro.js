/**
 * Agent Builder Pro Mode - Helper Class
 * Reads values from Pro Mode DOM controls (leverage, ALM, exit targets)
 */

class AgentBuilderPro {
    constructor() {
        this.warnings = [];
    }

    /**
     * Check if Pro Mode is currently active
     */
    isProModeActive() {
        return document.body.classList.contains('builder-pro');
    }

    /**
     * Get the current pool type (single/dual/all)
     */
    getPoolType() {
        const activeBtn = document.querySelector('.pool-type-btn-build.active');
        return activeBtn?.dataset.poolType || 'single';
    }

    /**
     * Read all Pro Mode configuration values from DOM
     */
    getProConfig() {
        if (!this.isProModeActive()) {
            return null; // Not in Pro Mode
        }

        const config = {
            // Leverage (Smart Loop Engine)
            leverage: this.getLeverageLevel(),

            // Liquidity Strategy (for dual-sided)
            liquidityStrategy: this.getLiquidityStrategy(),
            rebalanceThreshold: this.getRebalanceThreshold(),

            // Precision Duration
            duration: this.getDuration(),

            // Exit Targets
            takeProfitEnabled: this.isTakeProfitEnabled(),
            takeProfitAmount: this.getTakeProfitAmount(),
            stopLossEnabled: this.isStopLossEnabled(),
            stopLossPercent: this.getStopLossPercent(),
            apyTargetEnabled: this.isApyTargetEnabled(),
            apyTargetValue: this.getApyTargetValue(),

            // Safety & Gas
            volatilityGuard: this.isVolatilityGuardEnabled(),
            gasStrategy: this.getGasStrategy(),

            // Custom Instructions
            customInstructions: this.getCustomInstructions()
        };

        return config;
    }

    // ==========================================
    // LEVERAGE (Smart Loop Engine)
    // ==========================================

    getLeverageLevel() {
        const slider = document.getElementById('leverageSlider');
        return slider ? slider.value / 100 : 1.0;
    }

    // ==========================================
    // LIQUIDITY STRATEGY (Dual-Sided)
    // ==========================================

    getLiquidityStrategy() {
        const activeBtn = document.querySelector('.liq-btn.active');
        return activeBtn?.dataset.strategy || 'passive';
    }

    getRebalanceThreshold() {
        const input = document.getElementById('rebalancePercent');
        return input ? parseInt(input.value) || 5 : 5;
    }

    // ==========================================
    // PRECISION DURATION
    // ==========================================

    getDuration() {
        const valueInput = document.getElementById('durationValue');
        const unitSelect = document.getElementById('durationUnit');

        const value = valueInput ? parseInt(valueInput.value) || 24 : 24;
        const unit = unitSelect ? unitSelect.value : 'hours';

        // Convert to hours for backend
        const multipliers = {
            hours: 1,
            days: 24,
            weeks: 168,
            months: 720
        };

        return {
            value: value,
            unit: unit,
            totalHours: value * (multipliers[unit] || 1)
        };
    }

    // ==========================================
    // EXIT TARGETS
    // ==========================================

    isTakeProfitEnabled() {
        const check = document.getElementById('takeProfitEnabled');
        return check?.checked || false;
    }

    getTakeProfitAmount() {
        const input = document.getElementById('takeProfitAmount');
        return input ? parseFloat(input.value) || 500 : 500;
    }

    isStopLossEnabled() {
        const check = document.getElementById('stopLossEnabled');
        return check?.checked || true;
    }

    getStopLossPercent() {
        const input = document.getElementById('stopLossPercent');
        return input ? parseInt(input.value) || 15 : 15;
    }

    isApyTargetEnabled() {
        const check = document.getElementById('apyTargetEnabled');
        return check?.checked || false;
    }

    getApyTargetValue() {
        const input = document.getElementById('apyTargetValue');
        return input ? parseInt(input.value) || 5 : 5;
    }

    // ==========================================
    // SAFETY & GAS
    // ==========================================

    isVolatilityGuardEnabled() {
        const check = document.getElementById('volatilityGuard');
        return check?.checked ?? true;
    }

    getGasStrategy() {
        const select = document.getElementById('gasStrategy');
        return select?.value || 'smart';
    }

    // ==========================================
    // CUSTOM INSTRUCTIONS
    // ==========================================

    getCustomInstructions() {
        const textarea = document.getElementById('customInstructions');
        return textarea?.value?.trim() || '';
    }

    // ==========================================
    // VALIDATION
    // ==========================================

    /**
     * Validate Pro Mode configuration
     * @returns {Object} { valid: boolean, warnings: string[], errors: string[] }
     */
    validate() {
        const result = {
            valid: true,
            warnings: [],
            errors: []
        };

        const config = this.getProConfig();
        if (!config) return result; // Not in Pro Mode, no validation needed

        const poolType = this.getPoolType();

        // Leverage validation for single-sided
        if (poolType === 'single') {
            if (config.leverage > 2.5) {
                result.warnings.push('⚠️ High leverage (>2.5x) significantly increases liquidation risk');
            }
            if (config.leverage > 3.0) {
                result.errors.push('❌ Maximum leverage is 3.0x');
                result.valid = false;
            }
        }

        // Dual-sided validation
        if (poolType === 'dual') {
            if (config.liquidityStrategy === 'jit') {
                result.warnings.push('⚡ JIT Liquidity requires constant monitoring and fast execution');
            }
            if (config.rebalanceThreshold < 2) {
                result.warnings.push('⚠️ Low rebalance threshold may result in high gas costs');
            }
        }

        // Duration validation
        if (config.duration.totalHours < 1) {
            result.errors.push('❌ Minimum duration is 1 hour');
            result.valid = false;
        }

        // Stop Loss validation
        if (config.stopLossEnabled && config.stopLossPercent > 50) {
            result.warnings.push('⚠️ Stop loss above 50% may not provide effective protection');
        }

        // Take Profit validation
        if (config.takeProfitEnabled && config.takeProfitAmount < 10) {
            result.warnings.push('⚠️ Take profit below $10 may trigger frequently');
        }

        return result;
    }

    /**
     * Calculate estimated APY based on leverage
     * @param {number} baseApy - Base APY percentage
     * @returns {number} Leveraged APY
     */
    calculateLeveragedApy(baseApy) {
        const leverage = this.getLeverageLevel();
        // Simple model: APY scales with leverage (minus borrow costs ~2%)
        const borrowCost = (leverage - 1) * 2; // Approximate borrow cost
        return baseApy * leverage - borrowCost;
    }

    /**
     * Calculate liquidation threshold
     * @returns {string} Human-readable liquidation info
     */
    calculateLiquidationInfo() {
        const leverage = this.getLeverageLevel();
        if (leverage <= 1) return 'No liquidation risk';

        // LTV threshold typically around 80%
        const ltv = 0.8;
        const liquidationDrop = ((1 - (1 / (leverage * ltv))) * 100).toFixed(1);

        return `Liquidation at -${liquidationDrop}% price drop`;
    }

    /**
     * Get a summary of Pro Mode configuration for display
     */
    getSummary() {
        const config = this.getProConfig();
        if (!config) return 'Basic Mode';

        const poolType = this.getPoolType();
        const lines = [];

        if (poolType === 'single') {
            lines.push(`Leverage: ${config.leverage.toFixed(1)}x`);
        } else if (poolType === 'dual') {
            lines.push(`Strategy: ${config.liquidityStrategy}`);
            if (config.liquidityStrategy === 'active') {
                lines.push(`Rebalance at ${config.rebalanceThreshold}%`);
            }
        }

        lines.push(`Duration: ${config.duration.value} ${config.duration.unit}`);

        if (config.stopLossEnabled) {
            lines.push(`Stop Loss: ${config.stopLossPercent}%`);
        }
        if (config.takeProfitEnabled) {
            lines.push(`Take Profit: $${config.takeProfitAmount}`);
        }

        return lines.join('\n');
    }
}

// Export
window.AgentBuilderPro = new AgentBuilderPro();
