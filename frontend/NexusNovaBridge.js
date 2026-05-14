// Nexus-Nova PostMessage Bridge
// This version is "Connection-Less" - it just listens to the Swarm Dashboard.

document.addEventListener('DOMContentLoaded', () => {
    console.log('[NexusNova] Bridge Active (Listening for Swarm Commands)');

    // 1. Navigation Executor
    const executeNavigation = async (payload) => {
        const view = payload.key;
        console.log(`[NexusNova] Received command: ${view}`);

        // Handle Logout
        if (view === 'logout') {
            const logoutBtn = document.getElementById('logout-btn');
            if (logoutBtn) {
                logoutBtn.click();
                return;
            }
        }

        // Handle Login
        if (view === 'login') {
            const loginSection = document.getElementById('login-section');
            if (loginSection) {
                loginSection.scrollIntoView({ behavior: 'smooth' });
                return;
            }
        }

        // Standard Route Navigation
        if (typeof window.switchNexusView === 'function') {
            window.switchNexusView(view);
        } else {
            console.warn('[NexusNova] switchNexusView not ready.');
        }
    };

    // 2. Prediction Executor (Automation)
    const executePrediction = async (payload) => {
        const { match_id, session_id, predictions } = payload;
        console.log(`[NexusNova] Automating Prediction for Match: ${match_id}, Session: ${session_id}`);

        if (typeof window.openNexusModal !== 'function') return;

        // 1. Open Modal
        // We find the match data from cachedMatches if possible to get team names
        const match = (window.cachedMatches || []).find(m => m.match_id === match_id) || { team1: 'T1', team2: 'T2', current_over: 0 };
        await window.openNexusModal(match_id, match.team1, match.team2, match.current_over, session_id);

        // 2. Wait for modal to render (with slightly more generous padding)
        setTimeout(async () => {
            const form = document.getElementById('prediction-form');
            if (!form) {
                console.error('[NexusNova] Prediction form NOT FOUND after delay.');
                return;
            }

            console.log(`[NexusNova] Injecting ${predictions.length} balls...`);

            // 3. Inject Values
            predictions.forEach(p => {
                const ballInput = form.querySelector(`.ball-input[data-ball="${p.ball}"]`);
                if (ballInput) {
                    // Visual feedback: find the button and click it to trigger UI logic
                    const btn = ballInput.querySelector(`.run-btn[data-value="${p.runs}"]`);
                    if (btn && typeof window.selectRun === 'function') {
                        window.selectRun(btn, p.ball);
                    } else {
                        // Fallback if selectRun isn't found
                        ballInput.dataset.value = p.runs.toString();
                    }
                }
            });

            // 4. Submit
            console.log('[NexusNova] Finalizing strategic lock...');
            if (typeof window.submitNexusPredictions === 'function') {
                await window.submitNexusPredictions(match_id, session_id);
                console.log('[NexusNova] ✅ Predictions locked successfully.');
            } else {
                console.warn('[NexusNova] submitNexusPredictions function missing.');
            }
        }, 1000);
    };

    // 3. Action Executor (Generic Operations)
    const executeAction = async (payload) => {
        const action = payload.key;
        console.log(`[NexusNova] Executing action: ${action}`);

        if (action === 'refresh_scores') {
            if (typeof window.refreshLiveScores === 'function') {
                await window.refreshLiveScores();
            }
        } else if (action === 'analyze_match') {
            // For analyze_match, we'll try to find a live match to analyze
            if (typeof window.showNexusBreakdown === 'function') {
                const match = (window.cachedMatches || []).find(m => m.status === 'LIVE' || m.status === 'COMPLETED');
                if (match) {
                    window.showNexusBreakdown(match.match_id, 1);
                }
            }
        } else if (action === 'switch_tab') {
            const tab = payload.parameters?.tab || 'all';
            if (typeof window.switchArenaTab === 'function') {
                window.switchArenaTab(tab);
            }
        } else if (typeof window[action] === 'function') {
            window[action]();
        }
    };

    // 4. The Listener: Receiving commands from the Swarm Parent
    window.addEventListener('message', (event) => {
        const data = event.data;
        if (data && data.type === 'nova_command') {
            if (data.key === 'navigate') {
                executeNavigation(data.parameters);
            } else if (data.key === 'predict') {
                executePrediction(data.parameters);
            } else {
                // Fallback for generic actions
                executeAction(data);
            }
        }
    });
});
