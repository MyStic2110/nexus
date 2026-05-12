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

        // 2. Wait for modal to render (briefly)
        setTimeout(async () => {
            const form = document.getElementById('prediction-form');
            if (!form) return;

            // 3. Inject Values
            predictions.forEach(p => {
                const ballInput = form.querySelector(`.ball-input[data-ball="${p.ball}"]`);
                if (ballInput) {
                    ballInput.dataset.value = p.runs.toString();
                    // Visual feedback: find the button and make it active
                    const btn = ballInput.querySelector(`.run-btn[data-value="${p.runs}"]`);
                    if (btn && typeof window.selectRun === 'function') {
                        window.selectRun(btn, p.ball);
                    }
                }
            });

            // 4. Submit
            console.log('[NexusNova] Triggering Lock...');
            if (typeof window.submitNexusPredictions === 'function') {
                await window.submitNexusPredictions(match_id, session_id);
            }
        }, 500);
    };

    // 2. The Listener: Receiving commands from the Swarm Parent
    window.addEventListener('message', (event) => {
        const data = event.data;
        if (data && data.type === 'nova_command') {
            if (data.key === 'navigate') {
                executeNavigation(data.parameters);
            } else if (data.key === 'predict') {
                executePrediction(data.parameters);
            }
        }
    });
});
