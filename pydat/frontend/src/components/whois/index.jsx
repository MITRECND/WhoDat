import React, {useState, useEffect, useContext, useMemo} from 'react'
import {useHistory, useLocation} from 'react-router-dom'
import update from 'immutability-helper'
import qs from 'qs'

import Grid from '@material-ui/core/Grid'
import TextField from '@material-ui/core/TextField'
import Button from '@material-ui/core/Button'
import CheckBox from '@material-ui/core/Checkbox'
import FormControlLabel from '@material-ui/core/FormControlLabel';
import FormControl from '@material-ui/core/FormControl';
import Container from '@material-ui/core/Container'
import Paper from '@material-ui/core/Paper'
import HelpIcon from '@material-ui/icons/Help';
// import EqualizerIcon from '@material-ui/icons/Equalizer';

import WhoisTable from './whois_table'
import {
    useUserPreferences,
    userPreferencesManager,
    UserPreferenceNamespace,
    UserPreference,
} from '../helpers/preferences'
import {SearchSettings} from '../layout/dialogs'
import {
    OptionElement,
    RouteElement,
    NavigationElement
} from '../layout'
import {OptionsContext} from '../layout'
import HelpPage from './help'
// import StatsPage from './stats'
import ClusterStatus from './status'
import { useSnackbar } from 'notistack'

const whoisPreferencesNamespace = new UserPreferenceNamespace({
    name: "whois",
    title: "Whois Search Preferences",
    description: "Preferences for Whois Search"
})
userPreferencesManager.registerNamespace(whoisPreferencesNamespace)
userPreferencesManager.registerPrefs(
    whoisPreferencesNamespace, [
        new UserPreference({
            name: 'fang',
            type: "boolean",
            title: "De-fang Queries",
            description: "Automatically replace [.] with . in search queries",
            default_value: true
        }),
        new UserPreference({
            name: 'page_size',
            type: "number",
            title: "Results Page Size",
            description: "Default Page Size to use for result pagination",
            default_value: 50,
        }),
        new UserPreference({
            name: "remember_page_size",
            type: "boolean",
            title: "Remember Results Page Size",
            description: "Remember last used page size when displaying results",
            default_value: true,
        }),
        new UserPreference({
            name: 'details_colon',
            type: "boolean",
            title: "Full Details Colon Suffix",
            description: "Append a colon (:) to the names in the Full Details dialog",
            default_value: false
        })
    ]
)

export const whoisRoute = new RouteElement({
    path: "/whois",
    title: "Whois",
    component: null,
    options: [
    //   new OptionElement({
    //     icon: <EqualizerIcon />,
    //     text: "Stats",
    //     childComponent: <StatsPage />
    //   }),
      new OptionElement({
        icon: <HelpIcon />,
        text: "Help",
        childComponent: <HelpPage />
      }),
    ]
  })

export const whoisNavigation = new NavigationElement({
    title: 'WhoIs',
    path: '/whois',
    text: "Whois Search"
  })

const GeneralOptions = ({}) => {
    const preferences = useUserPreferences('whois')
    const [fangStatus, setFangStatus] = useState(preferences.getPref('fang'))

    const toggleFangOption = () => {
        preferences.setPref('fang', !fangStatus)
        setFangStatus(!fangStatus)
    }

    return (
        <Grid item xs={1}>
            <FormControl component="fieldset">
                <FormControlLabel
                    value="fang"
                    control={
                        <CheckBox
                            color="primary"
                            checked={fangStatus}
                            onClick={toggleFangOption}
                        />}
                    label="ReFang"
                    labelPlacement="end"
                />
            </FormControl>
        </Grid>
    )
}

const WhoisHandler = ({}) => {
    const preferences = useUserPreferences('whois')

    const [formData, setFormData] = useState({
        query: "",
    })

    const [queryData, setQueryData] = useState({
        ...formData
    })

    const {enqueueSnackbar} = useSnackbar()
    const location = useLocation()
    let history = useHistory()

    useEffect(() => {
        console.log(location)
        let query_string
        try {
            query_string = qs.parse(location.search, {
                ignoreQueryPrefix: true
            }).query
        } catch (err) {
            enqueueSnackbar("Unable to parse query from params", {variant: "error"})
        }

        let updated
        if (!!query_string) {
            updated = update(formData, {
                query: {$set: query_string}
            })
        } else {
            updated = update(formData, {
                query: {$set: ""}
            })
        }

        setFormData(updated)
        setQueryData(updated)
    }, [location])

    const handleOnSubmit = (e) => {
        e.preventDefault()

        let updated = {...formData}

        console.log(formData)

        if (preferences.getPref('fang')) {
            let refanged = formData.query.replace('[.]', '.')
            if (refanged !== formData.query) {
                updated = update(formData, {
                    query: {$set: refanged}
                })
                setFormData(updated)
            }
        }

        history.push({
            pathname: '/whois',
            search: `?query=${encodeURIComponent(updated.query)}`
        })

    }

    const handleOnChangeQuery = (e) => {
        setFormData(update(formData, {
            query: {$set: e.target.value}
        }))
    }

    const wtable = useMemo(() => {
        if (!!queryData.query && queryData != "") {
            return (
                <Paper>
                    <Grid item xs={12}>
                        <WhoisTable
                            queryData={queryData}
                        />
                    </Grid>
                </Paper>
            )
        }
    }, [queryData])

    return (
        <React.Fragment>
            <Container style={{paddingBottom: '1rem'}}>
                <ClusterStatus />
                <form onSubmit={handleOnSubmit}>
                    <Grid container spacing={1} justifyContent="center" alignItems="flex-end">
                        <Grid container item xs={11} justifyContent="center" alignItems="flex-end">
                            <TextField
                                label="Query"
                                variant="outlined"
                                name="query"
                                value={formData.query}
                                onChange={handleOnChangeQuery}
                                fullWidth
                                InputProps={{
                                    endAdornment: (
                                        <SearchSettings title={"Search Settings"}>
                                            <GeneralOptions
                                                formData={formData}
                                                setFormData={setFormData}
                                            />
                                        </SearchSettings>
                                    )
                                }}
                            />
                        </Grid>
                        <Grid item xs={1}>
                            <Button variant="outlined" type="submit">
                                Search
                            </Button>
                        </Grid>
                    </Grid>
                </form>
            </Container>
            {wtable}
        </React.Fragment>
    )
}

export default WhoisHandler