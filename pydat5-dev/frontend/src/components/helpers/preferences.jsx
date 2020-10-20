import React, {createContext} from 'react'

class UserPreferencesContainer {
    constructor() {
        this._name = 'pydat5-prefs'
        let storage = localStorage.getItem(this._name)
        this._prefs = {};

        if (storage !== null) {
            this._prefs = JSON.parse(storage)
        }

        if (this._prefs === null) {
            this._prefs = {}
        }

        this.getPref = this.getPref.bind(this)
        this.getPrefs = this.getPrefs.bind(this)
        this.setPref = this.setPref.bind(this)
        this.clearPrefs = this.clearPrefs.bind(this)
    }

    getPref(namespace, name, def=null) {
        if (namespace in this._prefs && name in this._prefs[namespace]) {
            return this._prefs[namespace][name]
        } else {
            return def
        }
    }

    getPrefs(namespace, inprefs) {
        let outprefs = {}
        if (namespace in this._prefs) {
            let config = this._prefs[namespace]
            Object.keys(inprefs).forEach((name) => {
                let value = inprefs[name]
                if (name in config) {
                    outprefs[name] = config[name]
                } else {
                    outprefs[name] = value
                }
            })
        } else {
            return inprefs
        }

        console.log(outprefs)
        return outprefs
    }

    setPref(namespace, name, value) {
        if (!(namespace in this._prefs)) {
            this._prefs[namespace] = {}
        }

        this._prefs[namespace][name] = value
        localStorage.setItem(this._name, JSON.stringify(this._prefs))
    }

    clearPrefs() {
        this._prefs = {}
        localStorage.setItem(this._name, JSON.stringify(this._prefs))
    }
}


export const UserPreferences = new UserPreferencesContainer()
export const UserPreferencesContext = createContext()