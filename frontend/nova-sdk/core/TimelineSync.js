export class TimelineSync {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.queue = [];
        this.agentState = "idle";
        this.isProcessing = false;
    }
    setAgentState(newState) {
        const oldState = this.agentState;
        this.agentState = newState;
        if ((oldState === "speaking" || oldState === "thinking") && (newState === "idle" || newState === "listening")) {
            this.processQueue();
        }
    }
    enqueue(executeFn, onAck) {
        this.queue.push({ executeFn, onAck });
        this.processQueue();
    }
    async processQueue() {
        if (this.isProcessing) return;
        if (this.agentState === "speaking" || this.agentState === "thinking") return;
        this.isProcessing = true;
        while(this.queue.length > 0) {
            const { executeFn, onAck } = this.queue.shift();
            try {
                const result = await executeFn();
                if (onAck) onAck("success", result ? String(result) : "OK");
            } catch(e) {
                if (onAck) onAck("error", e.message || "Execution failed");
            }
        }
        this.isProcessing = false;
    }
}
