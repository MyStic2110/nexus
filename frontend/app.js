// IPL Nexus 2026 - Frontend Logic
const API_BASE = window.location.origin;
const WS_BASE = window.location.origin.replace(/^http/, 'ws');

let currentUser = null;
let authToken = null;
let activeWS = null;
let liveScoreInterval = null; // 10-second live refresh handle
let activeArenaTab = 'all'; // Default tab
let cachedMatches = []; // Store matches for frontend filtering

let multiplierInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Nexus IPL Initialized');
    
    // Referral Tracking: Extract ref from URL and persist in localStorage
    const urlParams = new URLSearchParams(window.location.search);
    const refCode = urlParams.get('ref');
    if (refCode) {
        localStorage.setItem('nexus_ref', refCode);
        console.log(`[Nexus] Referral Code detected and persisted: ${refCode}`);
        // Clean URL for aesthetics
        window.history.replaceState({}, document.title, window.location.pathname);
    }
});

// Google Sign-In Callback
window.handleCredentialResponse = (response) => {
    console.log('Google Auth Response received');
    authToken = response.credential;
    loginWithBackend(authToken);
};

async function loginWithBackend(token) {
    const loginBtn = document.querySelector('.g_id_signin');
    if (loginBtn) loginBtn.style.opacity = '0.5';

    // Anti-Fraud: Generate unique device fingerprint
    const fingerprint = getDeviceFingerprint();
    const storedRef = localStorage.getItem('nexus_ref');

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify({
                ref: storedRef,
                fingerprint: fingerprint
            })
        });
        
        if (!res.ok) throw new Error('Nexus Auth Failed');
        
        const data = await res.json();
        currentUser = data.user;
        showDashboard();
    } catch (err) {
        console.error('Auth Error:', err);
        alert('Nexus access denied. Please verify your Google account.');
        if (loginBtn) loginBtn.style.opacity = '1';
    }
}

function showDashboard() {
    document.getElementById('login-section').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('user-profile').classList.remove('hidden');
    
    const display = (currentUser.username || currentUser.email || 'USER').toUpperCase();
    document.getElementById('username').textContent = display;
    document.getElementById('user-points').textContent = currentUser.score || 0;
    
    document.getElementById('nexus-links').classList.remove('hidden');
    document.getElementById('referral-section').classList.remove('hidden');
    document.getElementById('multiplier-status-card').classList.remove('hidden');

    // Initialize Referral UI
    const refCode = currentUser.referral_code || 'NEXUS';
    const refLink = `${window.location.origin}?ref=${refCode}`;
    document.getElementById('referral-link-display').textContent = refLink;

    // Play Welcome Sound for first-time login
    if (currentUser.is_new_user) {
        console.log('[Nexus] First-time login detected. Playing welcome sound...');
        const welcomeAudio = new Audio('/static/ipl_horn_2010.mp3');
        welcomeAudio.play().catch(err => {
            console.warn('[Nexus] Audio autoplay blocked or failed:', err.message);
        });
    }
    
    fetchMatches();
    fetchGlobalLeaderboard();
    updateMultiplierStats();
    
    // Start live polling
    if (liveScoreInterval) clearInterval(liveScoreInterval);
    liveScoreInterval = setInterval(refreshLiveScores, 10000);
    
    if (multiplierInterval) clearInterval(multiplierInterval);
    multiplierInterval = setInterval(updateMultiplierStats, 30000); // 30s for multiplier
    
    console.log('[Nexus] Live polling initialized (10s Scores / 30s Multiplier)');
}

window.switchNexusView = (view) => {
    const dashboard = document.getElementById('dashboard');
    const changelog = document.getElementById('changelog-section');
    const history = document.getElementById('history-section');
    const squad = document.getElementById('squad-section');
    const navLinks = document.querySelectorAll('#nexus-links a');
    
    // Reset state
    navLinks.forEach(l => {
        l.style.opacity = '0.6';
        l.style.color = 'white';
        l.style.borderBottom = 'none';
        l.style.fontWeight = '400';
    });

    dashboard.classList.add('hidden');
    changelog.classList.add('hidden');
    if (history) history.classList.add('hidden');
    if (squad) squad.classList.add('hidden');

    const activeLink = document.getElementById(`nav-${view}`);
    if (activeLink) {
        activeLink.style.opacity = '1';
        activeLink.style.color = 'var(--nexus-primary)';
        activeLink.style.fontWeight = '800';
    }

    if (view === 'dashboard') {
        dashboard.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
        if (!liveScoreInterval) {
            liveScoreInterval = setInterval(refreshLiveScores, 10000);
        }
        if (navLinks[1]) {
            navLinks[1].style.opacity = '1';
            navLinks[1].style.color = 'var(--nexus-primary)';
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
        fetchUserHistory();
        if (liveScoreInterval) {
            clearInterval(liveScoreInterval);
            liveScoreInterval = null;
        }
    } else if (view === 'changelog') {
        changelog.classList.remove('hidden');
        if (navLinks[2]) {
            navLinks[2].style.opacity = '1';
            navLinks[2].style.color = 'var(--nexus-primary)';
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
        // Pause polling when not on Arena
        if (liveScoreInterval) {
            clearInterval(liveScoreInterval);
            liveScoreInterval = null;
        }
    }
};

async function fetchMatches() {
    const container = document.getElementById('matches-container');
    if (!cachedMatches.length) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 4rem; color: var(--nexus-text-muted);">INITIALizing ARENA...</div>';
    }
    
    try {
        const res = await fetch(`${API_BASE}/matches`);
        const matches = await res.json();
        if (!Array.isArray(matches)) {
            console.error('Invalid matches type', matches);
            return;
        }
        cachedMatches = matches;
        filterAndRenderMatches();
        document.getElementById('live-count').textContent = `${matches.filter(m => m.status === 'LIVE').length} LIVE`;
    } catch (err) {
        console.error('Nexus Sync Error:', err);
        container.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 4rem; background: rgba(239, 68, 68, 0.05); border-radius: 20px; border: 1px solid rgba(239, 68, 68, 0.2);">
                <p style="color: #ef4444; font-weight: 700;">CONNECTION INTERRUPTED</p>
                <p style="font-size: 0.8rem; color: var(--nexus-text-muted); margin-top: 0.5rem;">Failed to synchronize with Nexus backend.</p>
                <p style="font-size: 0.6rem; color: var(--nexus-accent); font-family: monospace; opacity: 0.7; margin-top: 1rem;">ERR_SIG: ${err.message}</p>
            </div>`;
    }
}

function filterAndRenderMatches() {
    let filtered = cachedMatches;
    if (activeArenaTab !== 'all') {
        filtered = cachedMatches.filter(m => m.status === activeArenaTab);
    }
    renderMatches(filtered);
}

window.switchArenaTab = (tab) => {
    activeArenaTab = tab;
    // Update UI active state
    document.querySelectorAll('.arena-tab').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.includes(tab === 'all' ? 'ALL' : (tab === 'LIVE' ? 'LIVE' : tab))) {
            btn.classList.add('active');
        }
    });
    filterAndRenderMatches();
};

// Lightweight 10s refresh — only updates LIVE score/over spans without re-rendering cards
async function refreshLiveScores() {
    try {
        const res = await fetch(`${API_BASE}/matches`);
        const matches = await res.json();
        
        let liveCount = 0;
        matches.forEach(m => {
            const scoreEl = document.querySelector(`[data-score-id="${m.match_id}"]`);
            const overEl = document.querySelector(`[data-over-id="${m.match_id}"]`);
            const statusEl = document.querySelector(`[data-status-id="${m.match_id}"]`);
            const badgeEl = document.querySelector(`[data-badge-id="${m.match_id}"]`);
            const lastUpdatedEl = document.querySelector(`[data-last-updated="${m.match_id}"]`);
            
            if (m.status === 'LIVE') {
                liveCount++;
                if (scoreEl) scoreEl.textContent = m.current_score || '0/0';
                if (overEl) overEl.textContent = `OV ${m.current_over || '0.0'}`;
                if (statusEl) statusEl.textContent = 'MATCH STARTED';
                if (badgeEl) { badgeEl.textContent = 'LIVE'; badgeEl.style.background = '#22c55e'; }
                if (lastUpdatedEl) lastUpdatedEl.textContent = `Last update: ${new Date().toLocaleTimeString()}`;
                
                // Update Live Stats & Insights
                const statsEl = document.querySelector(`[data-stats-container="${m.match_id}"]`);
                if (statsEl && m.live_stats) {
                    statsEl.innerHTML = renderLiveStatsMarkup(m.live_stats, m.nexus_insights);
                    statsEl.classList.remove('hidden');
                }
            } else if (m.status === 'COMPLETED') {
                if (scoreEl) scoreEl.textContent = m.current_score || '0/0';
                if (overEl) overEl.textContent = 'MATCH OVER';
                if (statusEl) statusEl.textContent = 'FINAL SCORE';
                if (badgeEl) { badgeEl.textContent = 'COMPLETED'; badgeEl.style.background = '#a855f7'; }
                if (lastUpdatedEl) lastUpdatedEl.textContent = `Finalized: ${new Date().toLocaleTimeString()}`;
            }
        });
        
        const liveCountEl = document.getElementById('live-count');
        if (liveCountEl) liveCountEl.textContent = `${liveCount} LIVE`;
        
        // Refresh User Points and Global Leaderboard
        if (authToken) {
            fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}` 
                }
            }).then(r => r.json()).then(data => {
                if (data && data.user) {
                    currentUser = data.user;
                    document.getElementById('user-points').textContent = currentUser.score || 0;
                }
            }).catch(() => {});
            
            fetchGlobalLeaderboard();
        }

        console.log(`[Nexus] Live score & points refreshed at ${new Date().toLocaleTimeString()}`);
    } catch (e) {
        console.warn('[Nexus] Live score refresh failed silently:', e.message);
    }
}

// Manual refresh for a specific match
async function manualRefreshMatch(matchId, btn) {
    if (btn) btn.classList.add('spinning');
    try {
        const res = await fetch(`${API_BASE}/matches`);
        const matches = await res.json();
        const m = matches.find(match => match.match_id === matchId);
        
        if (m) {
            const scoreEl = document.querySelector(`[data-score-id="${m.match_id}"]`);
            const overEl = document.querySelector(`[data-over-id="${m.match_id}"]`);
            const statusEl = document.querySelector(`[data-status-id="${m.match_id}"]`);
            const badgeEl = document.querySelector(`[data-badge-id="${m.match_id}"]`);
            const lastUpdatedEl = document.querySelector(`[data-last-updated="${m.match_id}"]`);
            
            if (m.status === 'LIVE') {
                if (scoreEl) scoreEl.textContent = m.current_score || '0/0';
                if (overEl) overEl.textContent = `OV ${m.current_over || '0.0'}`;
                if (statusEl) statusEl.textContent = 'MATCH STARTED';
                if (badgeEl) { badgeEl.textContent = 'LIVE'; badgeEl.style.background = '#22c55e'; }
                if (lastUpdatedEl) lastUpdatedEl.textContent = `Refreshed: ${new Date().toLocaleTimeString()}`;
                const statsEl = document.querySelector(`[data-stats-container="${m.match_id}"]`);
                if (statsEl && m.live_stats) {
                    statsEl.innerHTML = renderLiveStatsMarkup(m.live_stats, m.nexus_insights);
                    statsEl.classList.remove('hidden');
                }
            } else if (m.status === 'COMPLETED') {
                if (scoreEl) scoreEl.textContent = m.current_score || '0/0';
                if (overEl) overEl.textContent = 'MATCH OVER';
                if (statusEl) statusEl.textContent = 'FINAL SCORE';
                if (badgeEl) { badgeEl.textContent = 'COMPLETED'; badgeEl.style.background = '#a855f7'; }
                if (lastUpdatedEl) lastUpdatedEl.textContent = `Refreshed: ${new Date().toLocaleTimeString()}`;
            } else {
                if (scoreEl) scoreEl.textContent = m.time || '--:--';
                if (overEl) overEl.textContent = 'IST';
                if (statusEl) statusEl.textContent = 'UPCOMING FIXTURE';
                if (badgeEl) { badgeEl.textContent = 'UPCOMING'; badgeEl.style.background = 'var(--nexus-secondary)'; }
                if (lastUpdatedEl) lastUpdatedEl.textContent = 'Waiting for match to start';
            }
        }
    } catch (e) {
        console.error('Manual refresh failed:', e);
    } finally {
        if (btn) setTimeout(() => btn.classList.remove('spinning'), 600);
    }
}

async function fetchGlobalLeaderboard() {
    const tbody = document.getElementById('global-leaderboard-body');
    
    // Only show "Synchronizing" if empty
    if (tbody.children.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 2rem; color: var(--nexus-text-muted);">Synchronizing Rankings...</td></tr>';
    }
    
    try {
        const res = await fetch(`${API_BASE}/matches/leaderboard/global`);
        const data = await res.json();
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 2rem; color: var(--nexus-text-muted);">Season standings will appear after match analysis.</td></tr>';
            return;
        }

        // Build new rows to avoid layout flicker
        let newContent = '';
        data.forEach((row, idx) => {
            const isTop3 = idx < 3;
            newContent += `
                <tr style="background: rgba(255, 255, 255, 0.02); border-radius: 12px;">
                    <td style="padding: 1.25rem; font-weight: 800; color: ${isTop3 ? 'var(--nexus-primary)' : 'white'};">#${idx + 1}</td>
                    <td style="padding: 1.25rem; font-family: monospace; color: var(--nexus-text-muted);">${row.user}</td>
                    <td style="padding: 1.25rem; text-align: right; font-weight: 800; color: var(--nexus-accent);">${row.score}</td>
                </tr>
            `;
        });
        tbody.innerHTML = newContent;
    } catch (err) {
        console.error('Leaderboard Sync Error:', err);
    }
}

async function fetchUserHistory() {
    const tbody = document.getElementById('user-history-body');
    const emptyState = document.getElementById('history-empty');
    
    if (!tbody || !emptyState) return;
    
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: var(--nexus-text-muted);">Retrieving Nexus Archives...</td></tr>';
    emptyState.classList.add('hidden');
    
    try {
        const res = await fetch(`${API_BASE}/matches/users/me/history`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (!res.ok) throw new Error("API returned " + res.status);
        
        const data = await res.json();
        
        if (data.length === 0) {
            tbody.innerHTML = '';
            emptyState.classList.remove('hidden');
            return;
        }

        let newContent = '';
        data.forEach((row) => {
            const dateStr = row.date ? new Date(row.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Unknown Date';
            newContent += `
                <tr style="background: rgba(255, 255, 255, 0.02); border-radius: 12px; transition: all 0.2s;">
                    <td style="padding: 1.25rem; font-weight: 800; color: white;">${row.match_name}</td>
                    <td style="padding: 1.25rem; color: var(--nexus-text-muted);">${dateStr}</td>
                    <td style="padding: 1.25rem; font-weight: 800; color: var(--nexus-secondary);">S-${row.session_id}</td>
                    <td style="padding: 1.25rem; text-align: right; font-weight: 900; color: ${row.points > 0 ? 'var(--nexus-primary)' : 'var(--nexus-text-muted)'};">${row.points}</td>
                    <td style="padding: 1.25rem; text-align: right;">
                        <button class="btn-nexus" style="padding: 0.4rem 1rem; font-size: 0.7rem; background: rgba(56, 189, 248, 0.1); border: 1px solid var(--nexus-primary); color: var(--nexus-primary);" onclick="showNexusBreakdown('${row.match_id}', ${row.session_id})">
                            ANALYSIS
                        </button>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = newContent;
    } catch (err) {
        console.error('History Sync Error:', err);
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: #ef4444;">Failed to sync with Nexus Archives</td></tr>';
    }
}

function renderMatches(matches) {
    const container = document.getElementById('matches-container');
    container.innerHTML = '';

    if (matches.length === 0) {
        container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 4rem; color: var(--nexus-text-muted);">NO MATCHES ACTIVE IN THE NEXUS</div>';
        return;
    }

    // Priority Sort: LIVE > UPCOMING > COMPLETED
    const statusPriority = { 'LIVE': 1, 'UPCOMING': 2, 'COMPLETED': 3 };
    matches.sort((a, b) => {
        if (statusPriority[a.status] !== statusPriority[b.status]) {
            return statusPriority[a.status] - statusPriority[b.status];
        }
        return new Date(a.date + ' ' + a.time) - new Date(b.date + ' ' + b.time);
    });

    const todayIST = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' });

    matches.forEach(match => {
        const card = document.createElement('div');
        const isToday = match.date === todayIST;
        card.className = `match-card ${isToday ? 'ipl-today-highlight' : ''}`;
        
        const t1 = match.team1 || 'T1';
        const t2 = match.team2 || 'T2';
        const isLive = match.status === 'LIVE';
        const isCompleted = match.status === 'COMPLETED';
        const isLocked = (match.current_over || 0) >= 15.0 || isCompleted;
        
        const dateStr = match.date ? new Date(match.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }) : 'TODAY';
        const displayTime = match.time || 'TBD';

        card.innerHTML = `
            ${isToday ? '<div class="today-label">MATCH TODAY</div>' : ''}
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.75rem;">
                <div data-badge-id="${match.match_id}" class="status-badge" style="background: ${isCompleted ? '#a855f7' : (isLocked ? 'var(--nexus-accent)' : (isLive ? '#22c55e' : 'var(--nexus-secondary)'))}; margin: 0;">
                    ${isCompleted ? 'COMPLETED' : (isLocked ? 'LOCKED' : match.status)}
                </div>
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <button class="refresh-pill" onclick="manualRefreshMatch('${match.match_id}', this)" title="Refresh Score">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6"></path><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                    </button>
                    <div style="font-size: 0.7rem; font-weight: 800; color: var(--nexus-primary); opacity: 0.8; letter-spacing: 1px;">
                        ${dateStr.toUpperCase()} • ${displayTime}
                    </div>
                </div>
            </div>
            <div class="teams-container" style="margin: 1rem 0;">
                <div class="team-info">
                    <div class="team-logo-placeholder">${t1[0]}</div>
                    <div style="font-weight: 700; font-size: 0.8rem;">${t1}</div>
                </div>
                <div class="vs-divider">VS</div>
                <div class="team-info">
                    <div class="team-logo-placeholder" style="color: var(--nexus-secondary);">${t2[0]}</div>
                    <div style="font-weight: 700; font-size: 0.8rem;">${t2}</div>
                </div>
            </div>
            <div class="match-details" style="flex-direction: column; gap: 0.25rem; align-items: center; border-top: 1px solid var(--nexus-border); padding-top: 1rem; position: relative;">
                ${isCompleted && match.team1_final_score ? `
                    <div style="width: 100%; display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.5rem;">
                        <div class="score-row ${match.winner_team === match.team1 ? 'winner' : ''}">
                            <span class="team-name">${t1}</span>
                            <span class="final-score-val">${match.team1_final_score}</span>
                        </div>
                        <div class="score-row ${match.winner_team === match.team2 ? 'winner' : ''}">
                            <span class="team-name">${t2}</span>
                            <span class="final-score-val">${match.team2_final_score}</span>
                        </div>
                        <div class="result-banner-nexus">${match.api_status || 'MATCH FINALIZED'}</div>
                    </div>
                ` : `
                    <div data-status-id="${match.match_id}" style="font-size: 1.1rem; font-weight: 800; color: white;">
                        ${isCompleted ? 'FINAL SCORE' : (isLive ? 'MATCH STARTED' : 'UPCOMING FIXTURE')}
                    </div>
                    <div style="font-size: 1.25rem; font-weight: 900; color: var(--nexus-primary);">
                        <span data-score-id="${match.match_id}">${isLive || isCompleted ? (match.current_score || '0/0') : (match.time || '--:--')}</span>
                        <span style="font-size: 0.8rem; color: white; opacity: 0.7;">
                            <span data-over-id="${match.match_id}">${isCompleted ? 'MATCH OVER' : (isLive ? 'OV ' + (match.current_over || '0.0') : 'IST')}</span>
                        </span>
                    </div>
                `}
                <div data-last-updated="${match.match_id}" style="font-size: 0.75rem; font-weight: 700; color: var(--nexus-accent); margin-top: 0.5rem; text-align: center; opacity: 0.8;">
                    ${isLive ? 'Live Update: ' + new Date().toLocaleTimeString() : (isCompleted ? '' : 'Waiting for match to start')}
                </div>
            </div>

            <div data-stats-container="${match.match_id}" class="live-analytics ${isLive && (match.live_stats || match.nexus_insights) ? '' : 'hidden'}">
                ${isLive && match.live_stats ? renderLiveStatsMarkup(match.live_stats, match.nexus_insights) : ''}
            </div>

            <div style="display: flex; gap: 0.5rem; width: 100%; margin-top: 1rem;">
                <button class="btn-nexus" style="flex: 1; padding: 0.5rem; font-size: 0.8rem;"
                    ${isCompleted || match.innings > 1 || (match.innings === 1 && match.current_over >= 15.0) ? 'disabled' : ''} 
                    onclick="openNexusModal('${match.match_id}', '${t1}', '${t2}', ${match.current_over || 0}, 1)">
                    PREDICT S-1
                </button>
                <button class="btn-nexus" style="flex: 1; padding: 0.5rem; font-size: 0.8rem;"
                    ${isCompleted || (match.innings === 2 && match.current_over >= 15.0) ? 'disabled' : ''} 
                    onclick="openNexusModal('${match.match_id}', '${t1}', '${t2}', ${match.current_over || 0}, 2)">
                    PREDICT S-2
                </button>
            </div>
            
            <div style="margin-top: 0.75rem; display: flex; gap: 0.5rem;">
                ${(match.innings >= 1 || isCompleted) ? `
                    <button class="btn-nexus" style="flex: 1; background: rgba(56, 189, 248, 0.05); border: 1px solid var(--nexus-primary); color: var(--nexus-primary); padding: 0.4rem; font-size: 0.65rem;" 
                        onclick="showNexusBreakdown('${match.match_id}', 1)">
                        S-1 INSIGHT
                    </button>
                ` : ''}
                ${(match.innings >= 2 || isCompleted) ? `
                    <button class="btn-nexus" style="flex: 1; background: rgba(129, 140, 248, 0.05); border: 1px solid var(--nexus-secondary); color: var(--nexus-secondary); padding: 0.4rem; font-size: 0.65rem;" 
                        onclick="showNexusBreakdown('${match.match_id}', 2)">
                        S-2 INSIGHT
                    </button>
                ` : ''}
            </div>
        `;
        container.appendChild(card);
    });
}

window.openNexusModal = async (matchId, t1, t2, over, sessionId) => {
    const modal = document.getElementById('prediction-modal');
    document.getElementById('modal-match-title').textContent = `${t1} vs ${t2} - Session ${sessionId}`;
    document.getElementById('modal-match-subtitle').textContent = `Target: Predict the outcome of the deliveries for Session ${sessionId}.`;
    
    // Lock logic explicitly for this session
    const isLocked = over >= 15.0;
    const form = document.getElementById('prediction-form');
    form.innerHTML = '';
    
    for (let i = 1; i <= 12; i++) {
        const div = document.createElement('div');
        div.className = 'ball-input';
        div.setAttribute('data-ball', i);
        div.setAttribute('data-value', '0'); // Default
        div.innerHTML = `
            <div style="display: flex; flex-direction: column; width: 100%;">
                <label style="margin-bottom: 0.5rem; display: block; font-size: 0.65rem; letter-spacing: 1px; font-weight: 800;">BALL ${i}</label>
                <div class="run-selector">
                    ${['0', '1', '2', '4', '6', 'W'].map(val => `
                        <button type="button" class="run-btn ${val === '0' ? 'active' : ''}" data-value="${val}" ${isLocked ? 'disabled' : ''} onclick="selectRun(this, ${i})">
                            ${val}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
        form.appendChild(div);
    }
    
    const submitBtn = document.getElementById('submit-prediction');
    if (isLocked) {
        submitBtn.style.display = 'none';
        console.warn(`Nexus Arena: Modal open in READ-ONLY mode for locked Session ${sessionId} match ${matchId}`);
    } else {
        submitBtn.style.display = 'block';
        submitBtn.onclick = () => submitNexusPredictions(matchId, sessionId);
    }
    
    // Pre-populate data securely from Nexus
    if (authToken) {
        try {
            const res = await fetch(`${API_BASE}/matches/${matchId}/sessions/${sessionId}/predict`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (res.ok) {
                const data = await res.json();
                if (data.status === 'success' && data.predictions) {
                    data.predictions.forEach(p => {
                        const ballInput = form.querySelector(`.ball-input[data-ball="${p.ball}"]`);
                        if (ballInput) {
                            const btn = ballInput.querySelector(`.run-btn[data-value="${p.runs}"]`);
                            if (btn) selectRun(btn, p.ball);
                        }
                    });
                }
            }
        } catch(e) { console.error('Silent preload error'); }
    }
    
    modal.classList.remove('hidden');
    if (activeWS) activeWS.close();
    connectNexusWS(matchId);
};

window.selectRun = (btn, ballNum) => {
    const parent = btn.parentElement;
    parent.querySelectorAll('.run-btn').forEach(b => {
        b.classList.remove('active');
        b.classList.remove('active-wicket');
    });
    
    if (btn.dataset.value === 'W') {
        btn.classList.add('active-wicket');
    } else {
        btn.classList.add('active');
    }
    
    // Store value on the parent ball-input
    const ballInput = btn.closest('.ball-input');
    ballInput.dataset.value = btn.dataset.value;
};

async function submitNexusPredictions(matchId, sessionId) {
    const form = document.getElementById('prediction-form');
    const ballInputs = form.querySelectorAll('.ball-input');
    
    let totalRuns = 0;
    let totalWickets = 0;

    const predictions = Array.from(ballInputs).map((bi, idx) => {
        const val = bi.dataset.value;
        if (val === 'W') {
            totalWickets += 1;
        } else {
            totalRuns += parseInt(val, 10);
        }
        return {
            ball: parseInt(bi.dataset.ball, 10),
            runs: val.toString(),
            innings: sessionId
        };
    });

    const confirmed = confirm(`You are predicting ${totalRuns} Runs and ${totalWickets} Wickets across these 12 deliveries.\n\nLock these metrics into the Nexus?`);
    if (!confirmed) return;

    const btn = document.getElementById('submit-prediction');
    const originalText = btn.textContent;
    btn.textContent = 'LOCKING...';
    btn.style.opacity = '0.7';

    try {
        const res = await fetch(`${API_BASE}/matches/${matchId}/sessions/${sessionId}/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ predictions })
        });
        
        if (res.ok) {
            btn.textContent = 'LOCKED';
            btn.style.background = '#22c55e';
            setTimeout(() => {
                document.getElementById('prediction-modal').classList.add('hidden');
                btn.textContent = originalText;
                btn.style.background = '';
                btn.style.opacity = '1';
            }, 1000);
        } else {
            throw new Error('Failed');
        }
    } catch (err) {
        btn.textContent = 'ERROR';
        btn.style.background = '#ef4444';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.background = '';
            btn.style.opacity = '1';
        }, 2000);
    }
}

function connectNexusWS(matchId) {
    if (!authToken) return;
    try {
        activeWS = new WebSocket(`${WS_BASE}/ws/${matchId}?token=${authToken}`);
        activeWS.onmessage = (e) => {
            const data = JSON.parse(e.data);
            console.log('Nexus Live Update:', data);
        };
        activeWS.onerror = () => console.error('Nexus WS Link Error');
    } catch (err) {
        console.error('WS Connection failed');
    }
}

// Modal Interaction
document.querySelector('.close-btn').onclick = () => {
    document.getElementById('prediction-modal').classList.add('hidden');
    if (activeWS) activeWS.close();
};

window.onclick = (e) => {
    const modal = document.getElementById('prediction-modal');
    if (e.target == modal) {
        modal.classList.add('hidden');
        if (activeWS) activeWS.close();
    }
};

// Analytics Breakdown
window.showNexusBreakdown = async (matchId, sessionId) => {
    const modal = document.getElementById('breakdown-modal');
    const content = document.getElementById('breakdown-content');
    const title = modal.querySelector('h3');
    const subtitle = modal.querySelector('p');
    
    title.textContent = `Nexus Analytical Insight : Session ${sessionId}`;
    subtitle.textContent = `Scientific breakdown of your performance in match ${matchId}.`;
    
    content.innerHTML = '<div style="text-align: center; padding: 2rem; color: var(--nexus-text-muted);">DECODING NEXUS SIGNALS...</div>';
    modal.classList.remove('hidden');

    try {
        const res = await fetch(`${API_BASE}/matches/${matchId}/sessions/${sessionId}/score-breakdown`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await res.json();

        if (data.status === 'not_found' || data.breakdown.length === 0) {
            content.innerHTML = `
                <div style="text-align: center; padding: 3rem; background: rgba(255,255,255,0.02); border-radius: 20px;">
                    <p style="color: var(--nexus-text-muted);">No analysis data found for this session.</p>
                    <p style="font-size: 0.7rem; margin-top: 0.5rem;">Points are distributed after Overs 19 & 20 are complete.</p>
                </div>`;
            return;
        }

        let html = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                <div style="font-size: 2.5rem; font-weight: 900; color: white;">${data.points} <span style="font-size: 0.9rem; color: var(--nexus-text-muted); font-weight: 400;">TOTAL PTS</span></div>
                <div style="text-align: right; color: var(--nexus-primary); font-size: 0.7rem; font-weight: 800;">VERIFIED BY NEXUS ENGINE</div>
            </div>
            <table class="analytics-table">
                <thead>
                    <tr>
                        <th>Ball</th>
                        <th>Predicted</th>
                        <th>Actual</th>
                        <th>Points</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.breakdown.forEach(b => {
            const isHit = b.points > 0;
            const indicatorClass = isHit ? 'indicator-hit' : 'indicator-miss';
            const indicatorText = isHit ? 'H' : 'M';

            html += `
                <tr>
                    <td><div class="ball-indicator ${indicatorClass}">${indicatorText}</div> <span style="font-size: 0.8rem; margin-left: 0.5rem; color: var(--nexus-text-muted);">#${b.ball_num}</span></td>
                    <td style="font-weight: 800; font-variant-numeric: tabular-nums;">${b.predicted === 'W' ? 'WICKET' : b.predicted + ' RUNS'}</td>
                    <td style="font-weight: 800; color: white;">${b.actual === 'W' ? 'WICKET' : b.actual + ' RUNS'}</td>
                    <td><span class="points-pill" style="color: ${b.points > 0 ? 'var(--nexus-primary)' : 'var(--nexus-text-muted)'}">+${b.points}</span></td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
        content.innerHTML = html;
    } catch (err) {
        content.innerHTML = '<div style="color: var(--nexus-accent);">Nexus Telemetry Error: Could not synchronize breakdown.</div>';
    }
};

window.closePredictionModal = () => {
    document.getElementById('prediction-modal').classList.add('hidden');
    if (activeWS) activeWS.close();
};

function renderLiveStatsMarkup(stats, insights) {
    if (!stats) return '';
    const { bat_striker, bat_non_striker, bowler, last_over_summary } = stats;
    
    let insightsHtml = '';
    if (insights && insights.length > 0) {
        insightsHtml = `
            <div class="nexus-insights-container">
                <div class="insight-ticker">Nexus Insights</div>
                ${insights.map(str => {
                    const isStreak = str.includes('🔥') || str.includes('🚀') || str.includes('📈');
                    return `<div class="insight-pill ${isStreak ? 'streak-fire' : ''}">
                        <span>${str}</span>
                    </div>`;
                }).join('')}
            </div>
        `;
    }

    // Highlighting Logic for Striker
    const strikerSR = parseFloat(bat_striker.strikeRate || 0);
    const isStrikerHot = strikerSR > 150 && parseInt(bat_striker.runs || 0) > 15;

    return `
        <div class="stat-row">
            <div class="player-stat striker ${isStrikerHot ? 'streak-fire' : ''}">
                <span class="name ${isStrikerHot ? 'highlight-text' : ''}">${bat_striker.name || 'Batsman'}</span>
                <span class="stat-val ${isStrikerHot ? 'highlight-text' : ''}">${bat_striker.runs}(${bat_striker.balls})</span>
            </div>
            <div class="bowler-stat">
                <span style="opacity: 0.6; font-size: 0.6rem; margin-right: 4px;">BWL</span>
                ${bowler.name || 'Bowler'} ${bowler.overs}-${bowler.maidens}-${bowler.runs}-${bowler.wickets}
            </div>
        </div>
        <div class="stat-row">
            <div class="player-stat">
                <span class="name">${bat_non_striker.name || 'Batsman'}</span>
                <span class="stat-val">${bat_non_striker.runs}(${bat_non_striker.balls})</span>
            </div>
            <div class="over-summary-chips">
                ${renderOverSummary(last_over_summary)}
            </div>
        </div>
        ${insightsHtml}
    `;
}

function renderOverSummary(summary) {
    if (!summary) return '';
    const balls = summary.trim().split(' ');
    return balls.map(b => {
        let cls = 'summary-ball';
        if (b === 'W') cls += ' wicket';
        else if (b === '4' || b === '6') cls += ' boundary';
        else if (b !== '0' && b !== '.') cls += ' run';
        return `<div class="${cls}">${b}</div>`;
    }).join('');
}

// Logout
document.getElementById('logout-btn').onclick = () => {
    location.reload();
};
function getDeviceFingerprint() {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const txt = 'Nexus-IPL-Fingerprint-2026';
    ctx.textBaseline = "top";
    ctx.font = "14px 'Arial'";
    ctx.textBaseline = "alphabetic";
    ctx.fillStyle = "#f60";
    ctx.fillRect(125,1,62,20);
    ctx.fillStyle = "#069";
    ctx.fillText(txt, 2, 15);
    ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
    ctx.fillText(txt, 4, 17);
    
    const b64 = canvas.toDataURL().replace("data:image/png;base64,","");
    const bin = atob(b64);
    let crc = 0;
    for (let i = 0; i < bin.length; i++) {
        crc = (crc << 5) - crc + bin.charCodeAt(i);
        crc |= 0;
    }
    return Math.abs(crc).toString(16);
}

async function updateMultiplierStats() {
    if (!authToken) return;
    try {
        const res = await fetch(`${API_BASE}/auth/multiplier`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await res.json();
        
        const mVal = data.multiplier || 1;
        const friendsActive = data.active_today || 0;
        const referrals = data.referral_count || 0;
        
        // Update Header Multiplier
        document.getElementById('multiplier-val').textContent = `${mVal}x`;
        document.getElementById('multiplier-badge').style.display = mVal > 1 ? 'flex' : 'none';
        
        // Update Homepage CTA
        const cta = document.getElementById('referral-cta');
        if (cta) {
            cta.classList.remove('hidden');
            document.getElementById('cta-multiplier-val').textContent = `${mVal}x`;
            const friendLabel = referrals === 1 ? '1 friend' : `${referrals} friends`;
            document.getElementById('cta-squad-count').textContent = friendLabel;
        }

        // Update Dedicated Squad Hub
        const squadList = document.getElementById('squad-list');
        const countBadge = document.getElementById('squad-count-badge');
        const noSquadMsg = document.getElementById('no-squad-msg');
        
        if (referrals > 0) {
            if (noSquadMsg) noSquadMsg.classList.add('hidden');
            if (countBadge) countBadge.textContent = referrals;
            
            if (squadList) {
                squadList.innerHTML = data.squad_members.map(member => `
                    <div class="squad-member ${member.active_today ? 'active' : ''}" style="justify-content: space-between; padding: 0.75rem 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <div class="status-dot ${member.is_fraud ? 'flagged' : (member.active_today ? 'live' : '')}"></div>
                            ${member.username}
                        </div>
                        ${member.is_fraud ? '<span style="font-size: 0.55rem; color: #ef4444; font-weight: 800;">FRAUD</span>' : ''}
                    </div>
                `).join('');
            }
        } else {
            if (noSquadMsg) noSquadMsg.classList.remove('hidden');
            if (countBadge) countBadge.textContent = "0";
            if (squadList) squadList.innerHTML = '';
        }
    } catch (e) {
        console.warn('[Nexus] Multiplier sync failed');
    }
}

window.copyReferralLink = () => {
    const link = document.getElementById('referral-link-display').textContent;
    navigator.clipboard.writeText(link).then(() => {
        const btn = document.querySelector('.referral-banner button');
        const originalText = btn.textContent;
        btn.textContent = 'COPIED!';
        btn.style.background = '#22c55e';
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.background = '';
        }, 2000);
    });
};
