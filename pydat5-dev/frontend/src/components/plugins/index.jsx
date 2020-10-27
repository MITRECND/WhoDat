import React, { createContext, forwardRef } from 'react'

class RoutePlugin {
    constructor(path, title, component, extra) {
        this.path = path
        this.title = title
        this.component = component
        this.extra = extra

        if (this.extra === null) {
            this.extra = {}
        }
    }
}

class ToolPlugin {
    constructor(text, component) {
        this.text = text
        this.component = component
    }
}

class PluginContainer {
    constructor() {
        this._plugins = {}
    }

    get plugins() {
        return this._plugins
    }
}

class DrawerPluginContainer extends PluginContainer {
    addPlugin(name, component) {
        this._plugins[name] = component
    }
}


class MenuPlugin {
    constructor(text, action, extra) {
        this.text = text
        this.action = action
        this.extra = extra

        if (this.extra === null) {
            this.extra = {}
        }
    }
}

class MenuPluginContainer extends PluginContainer {
    constructor() {
        super()
        this._plugins = {
            tld: {},
            domain: {},
            ip: {},
            email: {}
        }
    }

    addPlugin(name, type, component) {
        const validKeys = [
            'tld',
            'domain',
            'ip',
            'email'
        ]
        if (!validKeys.includes(type)) {
            throw('type must be "tld", "domain", "ip", or "email"')
        }

        if (!Object.keys(this._plugins).includes(type)) {
            this._plugins[type] = {}
        }

        this._plugins[type][name] = component
    }
}

class RoutePluginContainer extends PluginContainer {
    addPlugin(name, path, component, extra = null) {
        this._plugins[name] = new RoutePlugin(path, component, extra)
    }
}

class ToolPluginContainer extends PluginContainer {
    addPlugin(name, text, component) {
        this._plugins[name] = new ToolPlugin(text, component)
    }
}

export const PluginManagers = {
    drawer: new DrawerPluginContainer(),
    routes: new RoutePluginContainer(),
    menu: new MenuPluginContainer(),
    tool: new ToolPluginContainer(),
}
