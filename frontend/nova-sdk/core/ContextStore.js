export class ContextStore {
    constructor() {
        this.capabilities = {};
        this.context = {};
    }
    register(name, description, execute) {
        this.capabilities[name] = { name, description, execute };
    }
    updateContext(key, value) {
        this.context[key] = value;
    }
    getCapability(name) {
        return this.capabilities[name];
    }
    getSchema() {
        return Object.values(this.capabilities).map(c => ({
            name: c.name,
            description: c.description
        }));
    }
}
