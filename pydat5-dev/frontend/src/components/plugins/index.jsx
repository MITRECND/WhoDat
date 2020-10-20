import { createContext } from 'react'

class RoutePlugin {
    constructor(path, component, extra) {
        this.path = path
        this.component = component
        this.extra = extra

        if (this.extra === null) {
            this.extra = {}
        }
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

class MenuPluginContainer extends PluginContainer {
    addPlugin(name, type, component) {
        const validKeys = [
            'domain',
            'ip',
        ]
        if (!validKeys.includes(type)) {
            // some error
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

export const PluginManagers = {
    drawer: new DrawerPluginContainer(),
    routes: new RoutePluginContainer(),
    menu: new MenuPluginContainer()
}


export const PyDatPluginContext = createContext(PluginManagers)
