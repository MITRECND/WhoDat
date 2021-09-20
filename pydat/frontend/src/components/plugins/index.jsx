import {
    RouteElement,
    NavigationElement,
    MenuElement
} from '../layout'
class PluginContainer {
    constructor() {
        this._plugins = {}
    }

    get plugins() {
        return this._plugins
    }
}
class MenuPluginContainer extends PluginContainer {
    constructor() {
        super()
        this._plugins = {
            tld: {},
            domain: {},
            ip: {},
            email: {},
            telephone: {},
            registrant: {}
        }
    }

    addPlugin(name, type, plugin) {
        if (!(plugin instanceof MenuElement)){
            throw new TypeError("Must provide object of type 'MenuElement'")
        }

        const validKeys = [
            'tld',
            'domain',
            'ip',
            'email',
            'telephone',
            'registrant'
        ]

        if (!validKeys.includes(type)) {
            throw new TypeError(`type must be one of ${validKeys.join()}`)
        }

        if (!Object.keys(this._plugins).includes(type)) {
            this._plugins[type] = {}
        }

        this._plugins[type][name] = plugin
    }
}

class RoutePluginContainer extends PluginContainer {
    addPlugin(name, plugin) {
        if (!(plugin instanceof RouteElement)){
            throw new TypeError("Must provide object of type 'RouteElement'")
        }

        this._plugins[name] = plugin
    }
}

class NavigationPluginContainer extends PluginContainer {
    addPlugin(name, plugin) {
        if (!(plugin instanceof NavigationElement)){
            throw new TypeError("Must provide object of type 'NavigationElement'")
        }
        this._plugins[name] = plugin
    }
}

export const PluginManagers = {
    routes: new RoutePluginContainer(),
    menu: new MenuPluginContainer(),
    nav: new NavigationPluginContainer(),
}
