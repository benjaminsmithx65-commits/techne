/**
 * Reasoning Terminal v2.0
 * Displays Agent decision logs in cyberpunk style
 * 
 * Usage:
 *   const terminal = new ReasoningTerminal('reasoning-terminal-container');
 *   terminal.start();  // Starts auto-refresh
 *   terminal.stop();   // Stops auto-refresh
 */

class ReasoningTerminal {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            refreshInterval: options.refreshInterval || 5000,
            maxLogs: options.maxLogs || 10,
            apiUrl: options.apiUrl || `${window.API_BASE || 'http://localhost:8000'}/api/audit/reasoning-logs`,
            userAddress: options.userAddress || null
        };
        this.intervalId = null;
        this.logs = [];

        if (this.container) {
            this.render();
        }
    }

    render() {
        // SVG Icons (no emoji per ui-ux-pro-max guidelines)
        const brainIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><path d="M12 2a9 9 0 0 1 9 9c0 3.6-1.5 5.5-3 7-1.5 1.5-2 3.5-2 5H8c0-1.5-.5-3.5-2-5-1.5-1.5-3-3.4-3-7a9 9 0 0 1 9-9z"/><path d="M12 2v8"/><path d="M8 10h8"/></svg>`;

        this.container.innerHTML = `
            <div class="reasoning-terminal">
                <div class="terminal-header">
                    <span class="terminal-icon">${brainIcon}</span>
                    <span class="terminal-title">Neural Terminal v2.0</span>
                    <span class="terminal-status" id="terminal-status">● LIVE</span>
                </div>
                <div class="terminal-body" id="terminal-logs">
                    <div class="terminal-loading">
                        <span class="loading-cursor">▋</span> Initializing neural network...
                    </div>
                </div>
                <div class="terminal-footer">
                    <span class="terminal-hint">Agent reasoning logs • Auto-refresh 5s</span>
                </div>
            </div>
        `;

        this.logsContainer = document.getElementById('terminal-logs');
        this.statusIndicator = document.getElementById('terminal-status');
    }

    async fetchLogs() {
        try {
            let url = `${this.options.apiUrl}?limit=${this.options.maxLogs}`;
            if (this.options.userAddress) {
                url += `&user_address=${this.options.userAddress}`;
            }

            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch');

            const data = await response.json();
            const newLogs = data.logs || [];

            // Check if logs changed to avoid unnecessary re-render/animation
            const newHash = JSON.stringify(newLogs.map(l => l.id || l.timestamp));
            if (this.lastLogsHash === newHash) {
                // Logs unchanged, skip re-render
                return;
            }
            this.lastLogsHash = newHash;

            this.logs = newLogs;
            this.updateStatus('online');
            this.renderLogs();

        } catch (error) {
            console.error('Reasoning Terminal error:', error);
            this.updateStatus('offline');
            this.renderError();
        }
    }

    renderLogs() {
        if (!this.logsContainer) return;

        if (this.logs.length === 0) {
            this.logsContainer.innerHTML = `
                <div class="terminal-empty">
                    <span class="empty-icon">${this.getSvgIcon('inbox')}</span>
                    <span class="empty-text">No reasoning logs yet. Agent is waiting...</span>
                </div>
            `;
            return;
        }

        const logsHtml = this.logs.map(log => this.renderLogEntry(log)).join('');
        this.logsContainer.innerHTML = logsHtml;

        // Auto-scroll to bottom
        this.logsContainer.scrollTop = this.logsContainer.scrollHeight;
    }

    renderLogEntry(log) {
        const time = this.formatTime(log.timestamp);
        const colorClass = `log-${log.color || 'green'}`;

        // Map category to SVG icon type
        const categoryToIcon = {
            '[GUARD]': 'guard',
            '[SECURITY]': 'security',
            '[PARK]': 'park',
            '[ORACLE]': 'oracle',
            'GUARD': 'guard',
            'SECURITY': 'security',
            'PARK': 'park',
            'ORACLE': 'oracle'
        };
        const iconType = categoryToIcon[log.category] || 'warning';
        const svgIcon = this.getSvgIcon(iconType);

        return `
            <div class="terminal-log ${colorClass}" data-severity="${log.severity}">
                <span class="log-time">${time}</span>
                <span class="log-category">${log.category}</span>
                <span class="log-icon">${svgIcon}</span>
                <span class="log-message">${log.message}</span>
            </div>
        `;
    }


    renderError() {
        if (!this.logsContainer) return;
        this.logsContainer.innerHTML = `
            <div class="terminal-error">
                <span class="error-icon">${this.getSvgIcon('warning')}</span>
                <span class="error-text">Connection lost. Retrying...</span>
            </div>
        `;
    }

    updateStatus(status) {
        if (!this.statusIndicator) return;

        if (status === 'online') {
            this.statusIndicator.textContent = '● LIVE';
            this.statusIndicator.className = 'terminal-status status-online';
        } else {
            this.statusIndicator.textContent = '○ OFFLINE';
            this.statusIndicator.className = 'terminal-status status-offline';
        }
    }

    formatTime(timestamp) {
        if (!timestamp) return '--:--';
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    }

    start() {
        this.fetchLogs();
        this.intervalId = setInterval(() => this.fetchLogs(), this.options.refreshInterval);
        console.log('🧠 Reasoning Terminal started');
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        this.updateStatus('offline');
        console.log('[ReasoningTerminal] Stopped');
    }

    // SVG icon helper (no emoji per ui-ux-pro-max guidelines)
    getSvgIcon(type) {
        const icons = {
            guard: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4" y1="4" x2="20" y2="20"/></svg>',
            security: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L3 7v6c0 5.5 3.8 10.7 9 12 5.2-1.3 9-6.5 9-12V7l-9-5z"/><path d="M12 8v4"/><circle cx="12" cy="16" r="1"/></svg>',
            park: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 17V7h4a3 3 0 0 1 0 6H9"/></svg>',
            oracle: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M18 9l-5 5-4-4-3 3"/></svg>',
            warning: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 22h20L12 2z"/><path d="M12 9v4"/><circle cx="12" cy="17" r="1"/></svg>',
            inbox: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-6l-2 3H10l-2-3H2"/><path d="M5.5 5.1L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.7 4H7.3a2 2 0 0 0-1.8 1.1z"/></svg>'
        };
        return icons[type] || icons.warning;
    }

    // Add demo logs for testing
    addDemoLogs() {
        this.logs = [
            {
                timestamp: new Date().toISOString(),
                category: '[GUARD]',
                icon: this.getSvgIcon('guard'),
                message: 'Rotation aborted. Costs ($11.50) > Profit ($8.20)',
                color: 'yellow',
                severity: 'warning'
            },
            {
                timestamp: new Date(Date.now() - 60000).toISOString(),
                category: '[SECURITY]',
                icon: this.getSvgIcon('security'),
                message: 'Security Alert: Contract flagged as scam (score: 85)',
                color: 'red',
                severity: 'critical'
            },
            {
                timestamp: new Date(Date.now() - 120000).toISOString(),
                category: '[PARK]',
                icon: this.getSvgIcon('park'),
                message: 'Capital parked in Aave V3. Earning 3.5% APY while waiting.',
                color: 'cyan',
                severity: 'info'
            },
            {
                timestamp: new Date(Date.now() - 180000).toISOString(),
                category: '[ORACLE]',
                icon: this.getSvgIcon('oracle'),
                message: 'Price deviation 2.3% detected. Monitoring.',
                color: 'green',
                severity: 'info'
            }
        ];
        this.renderLogs();
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ReasoningTerminal;
}
