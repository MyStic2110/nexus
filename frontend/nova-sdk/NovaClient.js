import { EventBus } from './core/EventBus.js';
import { ContextStore } from './core/ContextStore.js';
import { TimelineSync } from './core/TimelineSync.js';

class NovaClient {
    constructor() {
        this.eventBus = new EventBus();
        this.store = new ContextStore();
        this.timeline = new TimelineSync(this.eventBus);
        this.publishData = null;
    }
    setPublisher(publishFn) { this.publishData = publishFn; }
    registerCapability({ name, description, execute }) {
        this.store.register(name, description, execute);
        this.eventBus.publish('schema_updated', this.store.getSchema());
    }
    executeCapability(name, payload) {
        const cap = this.store.getCapability(name);
        const onAck = (status, message) => {
            if (this.publishData) {
                const ackPayload = JSON.stringify({ type: "ack", key: name, status, message });
                this.publishData(new TextEncoder().encode(ackPayload), { topic: "ui_control" });
            }
        };
        if (cap) { this.timeline.enqueue(() => cap.execute(payload), onAck); }
        else { onAck("error", "Capability not registered."); }
    }
}
export const novaClient = new NovaClient();
