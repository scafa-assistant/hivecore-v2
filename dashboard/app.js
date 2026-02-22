/**
 * EGON Dashboard — app.js
 *
 * 1. Web3Auth Init + Login
 * 2. Session Management (Backend Token)
 * 3. Dashboard Data Loading (Profile, Wallet, Chat)
 */

// ================================================================
// Config
// ================================================================

const API_BASE = window.location.origin;
const REFRESH_INTERVAL = 30_000; // 30s Auto-Refresh

// ================================================================
// State
// ================================================================

const state = {
    web3auth: null,
    provider: null,
    token: localStorage.getItem('egon_token') || null,
    egonId: localStorage.getItem('egon_id') || 'adam_001',
    walletAddress: localStorage.getItem('wallet_address') || null,
    refreshTimer: null,
};


// ================================================================
// API Helper
// ================================================================

async function api(path, options = {}) {
    const url = `${API_BASE}${path}`;
    const headers = { 'Content-Type': 'application/json', ...options.headers };

    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }

    const res = await fetch(url, { ...options, headers });

    if (res.status === 401) {
        // Token ungueltig — Logout
        doLogout();
        throw new Error('Session expired');
    }

    return res.json();
}


// ================================================================
// Web3Auth
// ================================================================

async function initWeb3Auth() {
    try {
        // Web3Auth Config vom Backend holen
        const config = await api('/api/config/web3auth');
        if (!config.client_id) {
            console.warn('No Web3Auth Client ID configured');
            return false;
        }

        // Web3Auth Modal SDK (CDN → window.Modal)
        const Web3AuthModal = window.Modal;
        if (!Web3AuthModal || !Web3AuthModal.Web3Auth) {
            console.warn('Web3Auth SDK not loaded from CDN');
            return false;
        }

        // Chain Config — Ethereum Mainnet (MetaMask default)
        const chainConfig = {
            chainNamespace: 'eip155',
            chainId: '0x1',
            rpcTarget: 'https://rpc.ankr.com/eth',
            displayName: 'Ethereum Mainnet',
            blockExplorerUrl: 'https://etherscan.io',
            ticker: 'ETH',
            tickerName: 'Ethereum',
        };

        state.web3auth = new Web3AuthModal.Web3Auth({
            clientId: config.client_id,
            web3AuthNetwork: 'sapphire_mainnet',
            chainConfig: chainConfig,
            uiConfig: {
                appName: 'EGON Dashboard',
                theme: { primary: '#00d4aa' },
                mode: 'dark',
                defaultLanguage: 'de',
            },
        });

        await state.web3auth.initModal();
        console.log('Web3Auth initialized');

        // Check if already connected (session restore)
        if (state.web3auth.connected) {
            state.provider = state.web3auth.provider;
            const address = await getWalletAddress();
            if (address) {
                await loginToBackend(address, 'restored');
                return true;
            }
        }

        return true;
    } catch (err) {
        console.error('Web3Auth init failed:', err);
        return false;
    }
}


async function getWalletAddress() {
    try {
        if (!state.provider) return null;

        const accounts = await state.provider.request({
            method: 'eth_requestAccounts',
        });

        return accounts && accounts.length > 0 ? accounts[0] : null;
    } catch (err) {
        console.error('getWalletAddress error:', err);

        // Fallback: getUserInfo (fuer Social Logins)
        try {
            const userInfo = await state.web3auth.getUserInfo();
            return userInfo.email || userInfo.name || 'web3auth-user';
        } catch {
            return null;
        }
    }
}


// ================================================================
// Backend Auth
// ================================================================

async function loginToBackend(walletAddress, provider) {
    const data = await api('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({
            wallet_address: walletAddress,
            provider: provider || 'web3auth',
        }),
    });

    if (data.token) {
        state.token = data.token;
        state.egonId = data.egon_id;
        state.walletAddress = walletAddress;
        localStorage.setItem('egon_token', data.token);
        localStorage.setItem('egon_id', data.egon_id);
        localStorage.setItem('wallet_address', walletAddress);
        return true;
    }
    return false;
}


function doLogout() {
    state.token = null;
    state.walletAddress = null;
    localStorage.removeItem('egon_token');
    localStorage.removeItem('egon_id');
    localStorage.removeItem('wallet_address');
    if (state.refreshTimer) clearInterval(state.refreshTimer);
    showLogin();
}


// ================================================================
// UI: Screens
// ================================================================

function showLogin() {
    document.getElementById('login-screen').classList.remove('hidden');
    document.getElementById('dashboard-screen').classList.add('hidden');
    document.getElementById('login-loading').classList.add('hidden');
    document.getElementById('login-error').classList.add('hidden');
    document.getElementById('btn-connect').classList.remove('hidden');
}


function showDashboard() {
    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('dashboard-screen').classList.remove('hidden');

    // Wallet-Adresse in Topbar
    const addr = state.walletAddress || '';
    const short = addr.length > 12
        ? addr.slice(0, 6) + '...' + addr.slice(-4)
        : addr;
    document.getElementById('wallet-addr').textContent = short;

    // Daten laden
    loadDashboardData();

    // Auto-Refresh
    if (state.refreshTimer) clearInterval(state.refreshTimer);
    state.refreshTimer = setInterval(loadDashboardData, REFRESH_INTERVAL);
}


function showError(msg) {
    const el = document.getElementById('login-error');
    el.textContent = msg;
    el.classList.remove('hidden');
    document.getElementById('login-loading').classList.add('hidden');
    document.getElementById('btn-connect').classList.remove('hidden');
}


// ================================================================
// Dashboard Data
// ================================================================

async function loadDashboardData() {
    try {
        await Promise.all([
            loadProfile(),
            loadWallet(),
        ]);
    } catch (err) {
        console.error('Dashboard data error:', err);
    }
}


async function loadProfile() {
    try {
        const data = await api(`/api/egon/${state.egonId}/profile`);

        // Mood
        document.getElementById('v-mood').textContent = data.mood || 'neutral';

        // Progress Bars
        const vitals = data.vitals || {};
        setProgress('v-energy', vitals.energy || 0.5);
        setProgress('v-safety', vitals.safety || 0.5);
        setProgress('v-belonging', vitals.belonging || 0.5);
        setProgress('v-trust', vitals.trust_owner || 0.5);

        // Bond Score
        document.getElementById('v-bond').textContent =
            typeof data.bond_score === 'number' ? data.bond_score.toFixed(1) : '--';

        // Drives
        const drivesEl = document.getElementById('v-drives');
        const drives = data.drives || {};
        const driveKeys = Object.keys(drives);
        if (driveKeys.length > 0) {
            drivesEl.innerHTML = driveKeys.map(k =>
                `<span class="tag">${k}</span>`
            ).join('');
        } else {
            drivesEl.innerHTML = '<span class="muted">ruhig</span>';
        }

        // Status Card
        document.getElementById('s-name').textContent = data.name || 'Adam';
        document.getElementById('s-owner').textContent = data.owner_name || '--';
        document.getElementById('s-episodes').textContent = data.total_episodes || 0;
        document.getElementById('s-contacts').textContent = data.total_contacts || 0;

        const skills = data.skills || [];
        document.getElementById('s-skills').textContent =
            skills.length > 0
                ? skills.map(s => s.name).join(', ')
                : 'keine';

        document.getElementById('s-assessment').textContent =
            data.self_assessment || '--';

    } catch (err) {
        console.error('loadProfile error:', err);
    }
}


async function loadWallet() {
    try {
        const data = await api('/api/auth/me');

        document.getElementById('w-balance').textContent =
            typeof data.balance === 'number' ? data.balance.toFixed(2) : '0';

        document.getElementById('w-daily').textContent =
            typeof data.daily_cost === 'number' ? data.daily_cost.toFixed(1) : '--';

        document.getElementById('w-runway').textContent =
            typeof data.days_left === 'number' ? data.days_left.toFixed(1) + ' Tage' : '-- Tage';

        // Transactions von wallet.yaml laden
        await loadTransactions();

    } catch (err) {
        console.error('loadWallet error:', err);
    }
}


async function loadTransactions() {
    try {
        // Wallet-Daten direkt via Profile (wallet_balance ist dort schon)
        // Fuer Transactions brauchen wir einen direkten Read —
        // Erstmal Placeholder, bis ein dedizierter Endpoint existiert
        const txEl = document.getElementById('w-transactions');
        txEl.innerHTML = '<p class="muted">Transaktionen werden im Wallet gespeichert.</p>';
    } catch {
        // Ignorieren
    }
}


function setProgress(id, value) {
    const el = document.getElementById(id);
    if (el) {
        const pct = Math.max(0, Math.min(100, value * 100));
        el.style.width = pct + '%';

        // Farbe je nach Wert
        if (pct < 25) {
            el.style.background = '#ff4466';
        } else if (pct < 50) {
            el.style.background = '#ffaa33';
        } else {
            el.style.background = '#00d4aa';
        }
    }
}


// ================================================================
// Chat
// ================================================================

async function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    addChatMessage('user', msg);

    try {
        const data = await api('/api/chat', {
            method: 'POST',
            body: JSON.stringify({
                egon_id: state.egonId,
                message: msg,
                conversation_type: 'owner_chat',
            }),
        });

        addChatMessage('assistant', data.response || 'Keine Antwort.');

        // Tier-Info anzeigen
        if (data.tier_used) {
            addChatMessage('system', `Tier ${data.tier_used} | ${data.model || ''}`);
        }

    } catch (err) {
        addChatMessage('system', 'Fehler: ' + err.message);
    }
}


function addChatMessage(role, text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}


// ================================================================
// Public API (called from HTML)
// ================================================================

const app = {

    /** Connect Wallet via Web3Auth */
    async connect() {
        const btn = document.getElementById('btn-connect');
        const loading = document.getElementById('login-loading');
        const error = document.getElementById('login-error');

        btn.classList.add('hidden');
        error.classList.add('hidden');
        loading.classList.remove('hidden');

        try {
            if (state.web3auth && state.web3auth.status === 'ready') {
                // Web3Auth Modal oeffnen
                state.provider = await state.web3auth.connect();
                const address = await getWalletAddress();

                if (!address) {
                    showError('Konnte Wallet-Adresse nicht lesen.');
                    return;
                }

                const success = await loginToBackend(address, 'web3auth');
                if (success) {
                    showDashboard();
                } else {
                    showError('Backend-Login fehlgeschlagen.');
                }
            } else {
                // Web3Auth nicht verfuegbar — Demo-Login
                showError(
                    'Web3Auth nicht geladen. Pruefe die Console fuer Details. '
                    + 'Starte den Server neu oder lade die Seite.'
                );
            }
        } catch (err) {
            console.error('Connect error:', err);
            if (err.message && err.message.includes('User closed')) {
                // User hat das Modal geschlossen — kein Fehler
                showLogin();
            } else {
                showError('Verbindung fehlgeschlagen: ' + (err.message || err));
            }
        }
    },

    /** Send Chat Message */
    sendChat,

    /** Logout */
    async logout() {
        try {
            // Backend Session loeschen
            await api('/api/auth/logout', { method: 'POST' });
        } catch {
            // Ignorieren
        }

        try {
            // Web3Auth Logout
            if (state.web3auth && state.web3auth.connected) {
                await state.web3auth.logout();
            }
        } catch {
            // Ignorieren
        }

        doLogout();
    },
};

// Global machen
window.app = app;


// ================================================================
// Init
// ================================================================

(async function init() {
    console.log('EGON Dashboard starting...');

    // 1. Web3Auth initialisieren
    const web3authReady = await initWeb3Auth();
    console.log('Web3Auth ready:', web3authReady);

    // 2. Bestehende Session pruefen
    if (state.token) {
        try {
            // Token validieren
            await api('/api/auth/me');
            showDashboard();
            return;
        } catch {
            // Token ungueltig — Login zeigen
            doLogout();
        }
    }

    // 3. Login-Screen zeigen
    showLogin();
})();
