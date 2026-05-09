import { novaClient } from '../NovaClient.js';

export class NovaUI {
    constructor(options = {}) {
        this.options = { serverUrl: options.serverUrl || 'ws://localhost:7880', token: options.token || null, ...options };
        this.room = null;
        this.init();
    }
    init() { 
        this.injectStyles(); 
        // this.renderTrigger(); // Hidden for the SaaS Demo
    }
    injectStyles() {
        const styles = `
            .nova-trigger { position: fixed; bottom: 2rem; right: 2rem; width: 64px; height: 64px; background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%); border-radius: 50%; box-shadow: 0 10px 25px -5px rgba(56, 189, 248, 0.4); cursor: pointer; display: flex; align-items: center; justify-content: center; z-index: 9999; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); border: 2px solid rgba(255, 255, 255, 0.2); }
            .nova-trigger:hover { transform: scale(1.1) translateY(-5px); }
            .nova-trigger.active { background: #ef4444; }
            .nova-trigger svg { width: 32px; height: 32px; fill: white; }
            .nova-pulse { position: absolute; width: 100%; height: 100%; border-radius: 50%; background: inherit; opacity: 0.5; animation: nova-pulse 2s infinite; z-index: -1; }
            @keyframes nova-pulse { 0% { transform: scale(1); opacity: 0.5; } 100% { transform: scale(1.5); opacity: 0; } }
            .nova-status-toast { position: fixed; bottom: 7rem; right: 2rem; background: rgba(15, 23, 42, 0.9); backdrop-filter: blur(10px); border: 1px solid rgba(56, 189, 248, 0.2); color: white; padding: 0.75rem 1.5rem; border-radius: 12px; font-family: sans-serif; font-size: 0.8rem; font-weight: 600; display: none; z-index: 9999; }
        `;
        const styleSheet = document.createElement("style"); styleSheet.innerText = styles; document.head.appendChild(styleSheet);
    }
    renderTrigger() {
        const container = document.createElement('div');
        container.innerHTML = `<div id="nova-toast" class="nova-status-toast">Nexus AI Connecting...</div><div id="nova-btn" class="nova-trigger"><div class="nova-pulse"></div><svg viewBox="0 0 24 24"><path d="M12,2A10,10,0,1,0,22,12,10,10,0,0,0,12,2Zm0,18a8,8,0,1,1,8-8A8,8,0,0,1,12,20ZM12,6a6,6,0,1,0,6,6A6,6,0,0,0,12,6Zm0,10a4,4,0,1,1,4-4A4,4,0,0,1,12,16Z"/></svg></div>`;
        document.body.appendChild(container);
        const btn = document.getElementById('nova-btn');
        btn.onclick = () => this.toggleConnection();
    }
    showStatus(text) {
        const toast = document.getElementById('nova-toast');
        toast.textContent = text; toast.style.display = 'block';
        setTimeout(() => toast.style.display = 'none', 3000);
    }
    async toggleConnection() {
        const btn = document.getElementById('nova-btn');
        if (this.room) { await this.room.disconnect(); this.room = null; btn.classList.remove('active'); this.showStatus("Nexus AI Offline"); return; }
        try {
            this.showStatus("Connecting to Nexus Intelligence...");
            if (!this.options.token) {
                const urlParams = new URLSearchParams(window.location.search);
                const roomName = urlParams.get('room') || 'nova_session_default';
                const res = await fetch(`/get-nova-token?room=${roomName}`);
                const data = await res.json();
                this.options.token = data.token;
            }
            const { Room, RoomEvent } = LivekitClient;
            this.room = new Room();
            novaClient.setPublisher((payload, options) => { this.room.localParticipant.publishData(payload, options); });
            this.room.on(RoomEvent.DataReceived, (payload, participant, kind, topic) => {
                if (topic === "ui_control") {
                    const data = JSON.parse(new TextDecoder().decode(payload));
                    if (data.type === "action" || data.type === "navigate") {
                        novaClient.executeCapability(data.key, data.parameters);
                    }
                }
            });
            await this.room.connect(this.options.serverUrl, this.options.token);
            btn.classList.add('active'); this.showStatus("Link Established");
        } catch (e) { this.showStatus("Link Failed: " + e.message); }
    }
}
