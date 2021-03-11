import React, {useState} from 'react'

import Button from '@material-ui/core/Button'
import Checkbox from '@material-ui/core/Checkbox'
import FormControlLabel from '@material-ui/core/FormControlLabel';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogContentText from '@material-ui/core/DialogContentText';
import List from '@material-ui/core/List'
import ListSubheader from '@material-ui/core/ListSubheader'
import ListItem from '@material-ui/core/ListItem'
import ListItemText from '@material-ui/core/ListItemText'
// import EqualizerIcon from '@material-ui/icons/Equalizer';

import { useSnackbar } from 'notistack'

import {
    useUserPreferences,
    userPreferencesManager,
    UserPreferenceNamespace,
    UserPreference,
} from './components/helpers/preferences'
import {RegularDialog} from './components/layout/dialogs'
import {MenuElement} from './components/layout'
import {PluginManagers} from './components/plugins'
import {activeResolutionFetcher} from './components/helpers/fetchers'


const generalPreferencesNamespace = new UserPreferenceNamespace({
    name: "general",
    title: "General PyDat Preferences",
    description: "General Preferences across the PyDat Search"
})
userPreferencesManager.registerNamespace(generalPreferencesNamespace)
userPreferencesManager.registerPrefs(
    generalPreferencesNamespace, [
        new UserPreference({
            name: "ar_confirm",
            type: "boolean",
            title: "Prompt/Confirm before making Active queries",
            description: "To prevent accidental dns queries, pydat will confirm before making requests. Toggle this to disable that confirmation",
            default_value: true
        })

])

const ActiveResolutionConfirmation = ({
    data,
    setConfirm,
    onClose,
}) => {
    const preferences = useUserPreferences('general')
    const [repromptOption, setRepromptOption] = useState(false)

    const handleConfirm = () => {
        if (repromptOption) {
            preferences.setPref('ar_confirm', true)
        }
        setConfirm(true)
    }

    const handleDeny = () => {
        onClose()
    }

    const handleRepromptChange = () => {
        setRepromptOption(true)
    }

    return (
        <React.Fragment>
            <DialogContent>
                <DialogContentText>
                    <strong>Warning</strong>: Making Active DNS Resolutions has the potential to leak information to outside parties without your knowledge. Are you sure would you like to actively resolve "{data}"?
                </DialogContentText>
                <FormControlLabel
                    control={<Checkbox checked={repromptOption} onChange={handleRepromptChange} name="reprompt" />}
                    label="Never Prompt Again"
                />
            </DialogContent>
            <DialogActions>
                <Button onClick={handleConfirm} color="primary">
                    Yes, I'm Sure
                </Button>
                <Button onClick={handleDeny} color="primary" autoFocus>
                    No, Cancel
                </Button>
            </DialogActions>
        </React.Fragment>
    )
}

const ActiveResolutionDialog = ({open, onClose, data}) => {
    const preferences = useUserPreferences('general')
    const [confirm, setConfirm] = useState(preferences.getPref('ar_confirm')? false : true)
    const [fetching, setFetching] = useState(false)
    const [domainData, setDomainData] = useState(null)
    const {enqueueSnackbar} = useSnackbar()

    const fetchData = () => {
        const asyncfetch = async () => {
            try {
                let results = await activeResolutionFetcher({domainName: data})
                setDomainData(results)
            } catch (err) {
                enqueueSnackbar("Unable to contact API to resolve domain name", {variant: "error"})
            }
        }
        asyncfetch()
    }

    let body
    if (!confirm) {
        body = <ActiveResolutionConfirmation
                    data={data}
                    confirm={confirm}
                    setConfirm={setConfirm}
                    onClose={onClose}
                />
    } else {
        if (!fetching){
            setFetching(true)
            fetchData()
        }

        if (domainData === null) {
            body = <React.Fragment>Querying ...</React.Fragment>
        } else {
            body = (
                <React.Fragment>
                    <List subheader={<ListSubheader>Hostnames</ListSubheader>}>
                        {domainData.hostnames.map((domainName, index) => (
                            <ListItem key={index}>
                                <ListItemText>
                                    {domainName}
                                </ListItemText>
                            </ListItem>
                        ))}
                    </List>
                    <List  subheader={<ListSubheader>IPs</ListSubheader>}>
                        {domainData.ips.map((ip, index) => (
                            <ListItem key={index}>
                                <ListItemText>
                                    {ip}
                                </ListItemText>
                            </ListItem>
                        ))}
                    </List>

                </React.Fragment>
            )
        }
    }

    return (
        <RegularDialog
            open={open}
            onClose={onClose}
            title="Active Resolution"
        >
            {open &&
                <React.Fragment>
                    {body}
                </React.Fragment>
            }
        </RegularDialog>
    )
}

const ActiveResolutionMenu = new MenuElement({
    text: "Actively Resolve",
    RenderComponent: <ActiveResolutionDialog/>
})

PluginManagers.menu.addPlugin("active_resolution", "domain", ActiveResolutionMenu)
PluginManagers.menu.addPlugin("active_resolution", "tld", ActiveResolutionMenu)
