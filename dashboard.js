// Dashboard JavaScript - Real-time updates and interactions

const API_BASE_URL = 'http://localhost:5000/api';
const WS_URL = 'ws://localhost:5000/ws';
let ws = null;
let userId = null;
let walletData = {};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeUserId();
    initializeWebSocket();
    loadDashboardData();
    initializeCharts();
    startAutoRefresh();
});

// Generate unique user ID
function initializeUserId() {
    userId = localStorage.getItem('userId');
    if (!userId) {
        userId = 'USER_' + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('userId', userId);
    }
    document.getElementById('userId').textContent = userId;
}

// Copy user ID to clipboard
function copyUserId() {
    const userIdElement = document.getElementById('userId');
    navigator.clipboard.writeText(userIdElement.textContent).then(() => {
        showNotification('User ID copied to clipboard!', 'success');
    });
}

// WebSocket connection for real-time updates
function initializeWebSocket() {
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        console.log('WebSocket connected');
        document.getElementById('connectionStatus').innerHTML =
            '<i class="fas fa-circle text-green-400 mr-2 pulse-animation"></i> Live';
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleRealtimeUpdate(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        document.getElementById('connectionStatus').innerHTML =
            '<i class="fas fa-circle text-red-400 mr-2"></i> Disconnected';
    };

    ws.onclose = () => {
        document.getElementById('connectionStatus').innerHTML =
            '<i class="fas fa-circle text-yellow-400 mr-2"></i> Reconnecting...';
        setTimeout(initializeWebSocket, 5000);
    };
}

// Handle real-time updates
function handleRealtimeUpdate(data) {
    switch (data.type) {
        case 'trade':
            addTradeToTable(data.trade);
            updateTotalTrades();
            break;
        case 'volume':
            updateVolume(data.volume);
            break;
        case 'wallet':
            updateWalletCard(data.wallet);
            break;
        case 'stats':
            updateStats(data.stats);
            break;
    }
}

// Load dashboard data from API
async function loadDashboardData() {
    try {
        // Load summary stats
        const statsResponse = await fetch(`${API_BASE_URL}/stats`);
        const stats = await statsResponse.json();
        updateStats(stats);

        // Load wallets
        const walletsResponse = await fetch(`${API_BASE_URL}/wallets`);
        const wallets = await walletsResponse.json();
        renderWallets(wallets);

        // Load recent trades
        const tradesResponse = await fetch(`${API_BASE_URL}/trades/recent`);
        const trades = await tradesResponse.json();
        renderTrades(trades);

    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Update statistics
function updateStats(stats) {
    // Total Volume
    document.getElementById('totalVolume').textContent = formatCurrency(stats.totalVolume || 0);
    document.getElementById('volumeChange').textContent =
        `${stats.volumeChange > 0 ? '+' : ''}${stats.volumeChange || 0}%`;

    // Active Wallets
    document.getElementById('activeWallets').textContent =
        `${stats.activeWallets || 0}/${stats.totalWallets || 12}`;

    // Total Trades
    document.getElementById('totalTrades').textContent = stats.totalTrades || 0;
    document.getElementById('tradesPerHour').textContent =
        `${stats.tradesPerHour || 0}/hr`;

    // Win Rate
    document.getElementById('winRate').textContent = `${stats.winRate || 0}%`;
    document.getElementById('profitLoss').textContent =
        formatCurrency(stats.profitLoss || 0);

    // Update chart if needed
    if (volumeChart && stats.volumeHistory) {
        updateVolumeChart(stats.volumeHistory);
    }
}

// Render wallet cards
function renderWallets(wallets) {
    const grid = document.getElementById('walletsGrid');
    grid.innerHTML = '';

    wallets.forEach((wallet, index) => {
        const card = createWalletCard(wallet, index);
        grid.appendChild(card);
        walletData[wallet.id] = wallet;
    });
}

// Create wallet card element
function createWalletCard(wallet, index) {
    const card = document.createElement('div');
    card.className = 'glass-effect rounded-lg p-4 card-hover cursor-pointer';
    card.style.animationDelay = `${index * 0.1}s`;

    const isActive = wallet.status === 'active';
    const statusColor = isActive ? 'green' : 'gray';
    const statusText = isActive ? 'Active' : 'Inactive';

    card.innerHTML = `
        <div class="flex justify-between items-start mb-3">
            <div>
                <h4 class="text-white font-bold">Wallet ${wallet.number}</h4>
                <p class="text-gray-400 text-xs truncate" title="${wallet.address}">
                    ${wallet.address.substring(0, 10)}...
                </p>
            </div>
            <span class="bg-${statusColor}-500 bg-opacity-20 text-${statusColor}-400 px-2 py-1 rounded text-xs">
                ${statusText}
            </span>
        </div>

        <div class="space-y-2">
            <div class="flex justify-between text-sm">
                <span class="text-gray-400">Volume (24h)</span>
                <span class="text-white font-semibold">${formatCurrency(wallet.volume24h || 0)}</span>
            </div>
            <div class="flex justify-between text-sm">
                <span class="text-gray-400">Trades</span>
                <span class="text-white">${wallet.tradesCount || 0}</span>
            </div>
            <div class="flex justify-between text-sm">
                <span class="text-gray-400">P&L</span>
                <span class="${wallet.pnl >= 0 ? 'text-green-400' : 'text-red-400'} font-semibold">
                    ${wallet.pnl >= 0 ? '+' : ''}${formatCurrency(wallet.pnl || 0)}
                </span>
            </div>
            <div class="flex justify-between text-sm">
                <span class="text-gray-400">Position</span>
                <span class="text-white">
                    ${wallet.position === 'up' ?
                        '<i class="fas fa-arrow-up text-green-400"></i> UP' :
                        wallet.position === 'down' ?
                        '<i class="fas fa-arrow-down text-red-400"></i> DOWN' :
                        '<i class="fas fa-balance-scale text-blue-400"></i> Auto'}
                </span>
            </div>
        </div>

        <button onclick="openWalletSettings('${wallet.id}')"
                class="mt-3 w-full bg-blue-600 bg-opacity-20 hover:bg-opacity-30 text-blue-400 py-2 rounded text-sm transition">
            <i class="fas fa-cog mr-1"></i> Settings
        </button>
    `;

    return card;
}

// Render recent trades
function renderTrades(trades) {
    const tbody = document.getElementById('tradesTable');
    tbody.innerHTML = '';

    trades.forEach(trade => {
        const row = createTradeRow(trade);
        tbody.appendChild(row);
    });
}

// Create trade row element
function createTradeRow(trade) {
    const row = document.createElement('tr');
    row.className = 'border-b border-gray-700 hover:bg-white hover:bg-opacity-5';

    const sideColor = trade.side === 'UP' ? 'text-green-400' : 'text-red-400';
    const statusColor = trade.status === 'filled' ? 'text-green-400' :
                        trade.status === 'pending' ? 'text-yellow-400' : 'text-gray-400';

    row.innerHTML = `
        <td class="p-2 text-sm">${formatTime(trade.timestamp)}</td>
        <td class="p-2 text-sm">Wallet ${trade.walletNumber}</td>
        <td class="p-2 text-sm truncate" title="${trade.market}">${trade.market}</td>
        <td class="p-2 text-sm ${sideColor} font-semibold">${trade.side}</td>
        <td class="p-2 text-sm text-right">${formatCurrency(trade.amount)}</td>
        <td class="p-2 text-sm text-right">${trade.price.toFixed(4)}</td>
        <td class="p-2 text-sm text-center">
            <span class="${statusColor}">
                <i class="fas fa-circle text-xs mr-1"></i>${trade.status}
            </span>
        </td>
    `;

    return row;
}

// Add new trade to table (real-time)
function addTradeToTable(trade) {
    const tbody = document.getElementById('tradesTable');
    const row = createTradeRow(trade);
    tbody.insertBefore(row, tbody.firstChild);

    // Keep only last 20 trades
    while (tbody.children.length > 20) {
        tbody.removeChild(tbody.lastChild);
    }

    // Animate new row
    row.classList.add('animate__animated', 'animate__fadeIn');
}

// Initialize charts
let volumeChart, positionChart;

function initializeCharts() {
    // Volume Chart
    const volumeCtx = document.getElementById('volumeChart').getContext('2d');
    volumeChart = new Chart(volumeCtx, {
        type: 'line',
        data: {
            labels: generateTimeLabels(24),
            datasets: [{
                label: 'Volume (USDC)',
                data: Array(24).fill(0),
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#fff' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                x: {
                    ticks: { color: '#fff' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            }
        }
    });

    // Position Distribution Chart
    const positionCtx = document.getElementById('positionChart').getContext('2d');
    positionChart = new Chart(positionCtx, {
        type: 'doughnut',
        data: {
            labels: ['UP Positions', 'DOWN Positions', 'Pending'],
            datasets: [{
                data: [45, 45, 10],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(239, 68, 68, 0.8)',
                    'rgba(251, 191, 36, 0.8)'
                ],
                borderColor: [
                    '#10b981',
                    '#ef4444',
                    '#fbbf24'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#fff' }
                }
            }
        }
    });
}

// Update volume chart
function updateVolumeChart(data) {
    if (volumeChart) {
        volumeChart.data.datasets[0].data = data;
        volumeChart.update();
    }
}

// Update position chart
function updatePositionChart(upCount, downCount, pendingCount) {
    if (positionChart) {
        positionChart.data.datasets[0].data = [upCount, downCount, pendingCount];
        positionChart.update();
    }
}

// Generate time labels
function generateTimeLabels(hours) {
    const labels = [];
    const now = new Date();
    for (let i = hours - 1; i >= 0; i--) {
        const time = new Date(now - i * 60 * 60 * 1000);
        labels.push(time.getHours() + ':00');
    }
    return labels;
}

// Modal functions
function showRegisterModal() {
    document.getElementById('registerModal').classList.remove('hidden');
}

function closeRegisterModal() {
    document.getElementById('registerModal').classList.add('hidden');
}

function openWalletSettings(walletId) {
    const wallet = walletData[walletId];
    if (!wallet) return;

    document.getElementById('walletId').value = walletId;
    document.getElementById('walletAddress').value = wallet.address;
    document.getElementById('tradingPair').value = wallet.position || 'auto';
    document.getElementById('orderAmount').value = wallet.orderAmount || 5;
    document.getElementById('maxDailyVolume').value = wallet.maxDailyVolume || 500;
    document.getElementById('autoClaimEnabled').checked = wallet.autoClaimEnabled || false;

    document.getElementById('walletModal').classList.remove('hidden');
}

function closeWalletModal() {
    document.getElementById('walletModal').classList.add('hidden');
}

// Save wallet settings
async function saveWalletSettings() {
    const walletId = document.getElementById('walletId').value;
    const settings = {
        tradingPair: document.getElementById('tradingPair').value,
        orderAmount: parseFloat(document.getElementById('orderAmount').value),
        maxDailyVolume: parseFloat(document.getElementById('maxDailyVolume').value),
        autoClaimEnabled: document.getElementById('autoClaimEnabled').checked
    };

    try {
        const response = await fetch(`${API_BASE_URL}/wallets/${walletId}/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (response.ok) {
            showNotification('Settings saved successfully!', 'success');
            closeWalletModal();
            loadDashboardData();
        } else {
            showNotification('Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showNotification('Error saving settings', 'error');
    }
}

// Check registration status
async function checkRegistration() {
    try {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/status`);
        const data = await response.json();

        if (data.registered) {
            showNotification('Registration successful!', 'success');
            closeRegisterModal();
            loadDashboardData();
        } else {
            showNotification('Registration pending. Please complete the process on Telegram.', 'info');
        }
    } catch (error) {
        console.error('Error checking registration:', error);
        showNotification('Error checking registration status', 'error');
    }
}

// Notification system
function showNotification(message, type = 'info') {
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-yellow-500'
    };

    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 ${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate__animated animate__fadeInRight`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check' :
                            type === 'error' ? 'exclamation-triangle' :
                            'info-circle'} mr-2"></i>${message}
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('animate__fadeOutRight');
        setTimeout(() => notification.remove(), 500);
    }, 3000);
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Auto refresh data
function startAutoRefresh() {
    setInterval(() => {
        loadDashboardData();
    }, 30000); // Refresh every 30 seconds
}

// Export functions for global access
window.showRegisterModal = showRegisterModal;
window.closeRegisterModal = closeRegisterModal;
window.openWalletSettings = openWalletSettings;
window.closeWalletModal = closeWalletModal;
window.saveWalletSettings = saveWalletSettings;
window.checkRegistration = checkRegistration;
window.copyUserId = copyUserId;