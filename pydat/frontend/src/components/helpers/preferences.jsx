import React, {useState} from 'react'

import Typography from '@material-ui/core/Typography'
import Container from '@material-ui/core/Container'
import Divider from '@material-ui/core/Divider'
import TableContainer from '@material-ui/core/TableContainer'
import Table from '@material-ui/core/Table'
import TableBody from '@material-ui/core/TableBody'
import TableRow from '@material-ui/core/TableRow'
import TableCell from '@material-ui/core/TableCell'
import Grid from '@material-ui/core/Grid'
import Switch from '@material-ui/core/Switch'
import AccountCircleIcon from '@material-ui/icons/AccountCircle';
import Paper from '@material-ui/core/Paper'

import { OptionElement } from "../layout"
import { FullScreenDialog } from "../layout/dialogs"


const PREFERENCES_NAME = 'pydat5-prefs'

export class UserPreferenceNamespace {
    constructor({name, title="", description=""}) {
        this.name = name
        this.title = title
        this.description = description
    }
}
export class UserPreference {
    constructor ({
        name,
        type,
        title="",
        description="",
        default_value=null,
        internal=false
    }) {
        this.name = name
        this.type = type
        this.title = title
        this.description = description
        this.default_value = default_value
        this.internal = internal
    }
}
class UserPreferencesManager {
    constructor () {
        this._namespaces = {}
        this._prefs = {}
        this.registerPref.bind(this)
        this.registerPrefs.bind(this)
        this.registerNamespace.bind(this)
    }

    get default_values () {
        // TODO memoize this
        let default_values = {}

        Object.keys(this._prefs).forEach((name) => {
            default_values[name] = {}
            Object.keys(this._prefs[name]).forEach((pref) => {
                default_values[name][pref] = this._prefs[name][pref].default_value
            })
        })

        return default_values
    }

    registerPref (namespace, pref) {
        if (!(namespace instanceof UserPreferenceNamespace)) {
            throw TypeError("namespace must be UserPreferenceNamespace Instance")
        }

        if (!(pref instanceof UserPreference)) {
            throw TypeError("Pref must be UserPreference Instance")
        }

        if (!(namespace.name in this._namespaces)) {
            throw ReferenceError("Namespace must be registered befored adding preference to it")
        }

        this._prefs[namespace.name][pref.name] = pref
    }

    registerPrefs (namespace, prefs) {
        prefs.forEach((pref) => {
            this.registerPref(namespace, pref)
        })
    }

    registerNamespace (namespace) {
        if (!(namespace instanceof UserPreferenceNamespace)) {
            throw TypeError("namespace must be UserPreferenceNamespace Instance")
        }

        if (!(namespace.name in this._namespaces)) {
            this._namespaces[namespace.name] = namespace
            this._prefs[namespace.name] = {}
        }
    }
}

export const userPreferencesManager = new UserPreferencesManager()

class UserPreferencesContainer {
    constructor() {
        this.__preferences = {}

        this.getPref = this.getPref.bind(this)
        this.getPrefs = this.getPrefs.bind(this)
        this.setPref = this.setPref.bind(this)
        this.clearPrefs = this.clearPrefs.bind(this)
        this._initializePreferences = this._initializePreferences.bind(this)
    }

    _initializePreferences () {
        let storage = localStorage.getItem(PREFERENCES_NAME)
        const default_prefs = userPreferencesManager.default_values

        if (storage !== null) {
            this.__preferences = JSON.parse(storage)
            for (let namespace in default_prefs){
                if (!(namespace in this.__preferences)) {
                    this.__preferences[namespace] = default_prefs[namespace]
                } else {
                    for (let name in default_prefs[namespace]){
                        if (!(name in this.__preferences[namespace])) {
                            this.__preferences[namespace][name] = default_prefs[namespace][name]
                        }
                    }
                }
            }
            localStorage.setItem(PREFERENCES_NAME, JSON.stringify(this.__preferences))
        } else {
            this.__preferences = default_prefs
            localStorage.setItem(PREFERENCES_NAME, JSON.stringify(default_prefs))
        }
    }

    getPref(namespace, name) {
        if (!(namespace in this.__preferences)) {
            throw ReferenceError(`Preference namespace ${namespace} was never registered`)
        } else if (name in this.__preferences[namespace]) {
            return this.__preferences[namespace][name]
        } else {
            throw ReferenceError(`Preference ${namespace}:${name} was never registered`)
        }
    }

    getPrefs(namespace) {
        if (!(namespace in this.__preferences)) {
            throw ReferenceError(`Preference namespace ${namespace} was never registered`)
        } else {
            return this.__preferences[namespace]
        }
    }

    setPref(namespace, name, value) {
        const default_prefs = userPreferencesManager._prefs
        if (!(namespace in this.__preferences)) {
            throw ReferenceError(`Preference namespace ${namespace} was never registered`)
        }

        if (!(name in this.__preferences[namespace])) {
            throw ReferenceError(`Preference ${namespace}:${name} was never registered`)
        }

        const expected_type = default_prefs[namespace][name].type
        if (expected_type !== null && !(expected_type == typeof value )) {
            throw TypeError(`Preference ${namespace}:${name} is expected to be of type ${expected_type}`)
        }

        this.__preferences[namespace][name] = value
        localStorage.setItem(PREFERENCES_NAME, JSON.stringify(this.__preferences))
    }

    clearPrefs() {
        this._initializePreferences()
    }
}

export const userPreferencesContainer = new UserPreferencesContainer()

export const useUserPreferences = (namespace) => {
    const userPreferences = userPreferencesContainer

    const getPref = (name, def=null) => {
        return userPreferences.getPref(namespace, name, def)
    }

    const getPrefs = (defaults) => {
        return userPreferences.getPrefs(namespace, defaults)
    }

    const setPref = (name, value) => {
        return userPreferences.setPref(namespace, name, value)
    }

    return {getPref, getPrefs, setPref}
}

const PreferenceToggle = ({namespace, prefName}) => {
    const preferences = useUserPreferences(namespace)
    const [toggleState, setToggleState] = useState(preferences.getPref(prefName))

    const handleChange = (e) => {
        setToggleState(e.target.checked)
        preferences.setPref(prefName, e.target.checked)
    }

    return (
        <Switch
            checked={toggleState}
            onChange={handleChange}
        />
    )
}

const SubPreferences = ({title, namespace, preferences}) => {
    let toggleableFound = false
    for (const pref in preferences) {
        if (preferences[pref].type == 'boolean' && !preferences[pref].internal){
            toggleableFound = true
            break
        }
    }

    if (!toggleableFound) {
        return null
    }

    return (
        <React.Fragment>
            <Typography variant="h5">{title}</Typography>
            <Paper>
                <TableContainer>
                    <Table>
                        <TableBody>
                            {Object.keys(preferences).map((pref, index) => {
                                const localPref = preferences[pref]
                                if (localPref.type !== 'boolean' || localPref.internal){
                                    return null
                                }
                                return (
                                    <TableRow key={index}>
                                        <TableCell>
                                            <Grid container>
                                                <Grid item xs={12}>
                                                    {localPref.title}
                                                </Grid>
                                                <Grid item xs={12}>
                                                    {localPref.description}
                                                </Grid>
                                            </Grid>
                                        </TableCell>
                                        <TableCell width={"10%"}>
                                            <PreferenceToggle
                                                namespace={namespace}
                                                prefName={localPref.name}
                                            />
                                        </TableCell>
                                    </TableRow>
                                )
                            })}
                        </TableBody>
                    </Table>
                </TableContainer>
            </Paper>

        </React.Fragment>
    )
}

export const PreferencesDialog = ({open, onClose}) => {
    return (
        <FullScreenDialog
            open={open}
            onClose={onClose}
            title="PyDat Preferences"
        >
            {open &&
                <React.Fragment>
                    <Grid container spacing={2}>
                        {Object.keys(userPreferencesManager._namespaces).map((namespace, index) => (
                            <Grid container item key={index}>
                                <Container>
                                    {Object.keys(userPreferencesManager._prefs[namespace]).length > 0 &&
                                        <SubPreferences
                                            title={userPreferencesManager._namespaces[namespace].title}
                                            namespace={namespace}
                                            preferences={userPreferencesManager._prefs[namespace]}/>}
                                    <Divider />
                                </Container>
                            </Grid>
                        ))}
                    </Grid>
                </React.Fragment>
            }
        </FullScreenDialog>
    )
}


export const userPreferencesOption = new OptionElement({
    icon: <AccountCircleIcon />,
    text: "User Preferences",
    childComponent: <PreferencesDialog />
  })