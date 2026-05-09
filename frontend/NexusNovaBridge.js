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

    // 2. The Listener: Receiving commands from the Swarm Parent
    window.addEventListener('message', (event) => {
        const data = event.data;
        if (data && data.type === 'nova_command') {
            if (data.key === 'navigate') {
                executeNavigation(data.parameters);
            }
        }
    });
});
