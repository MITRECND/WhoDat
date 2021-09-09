import React from 'react'
import {
    BrowserRouter as Router,
    Switch,
    Route,
    Redirect
} from 'react-router-dom'

import ThemeProvider from '@material-ui/styles/ThemeProvider'
import useMediaQuery from '@material-ui/core/useMediaQuery'
import Slide from '@material-ui/core/Slide'

import {SnackbarProvider} from 'notistack'

import {PluginManagers} from './components/plugins'
import {userPreferencesContainer} from './components/helpers/preferences'
import Dashboard from './components/layout/dashboard'
import NotFound from './components/layout/notfound'
import { appSettings } from './settings'
import {defaultTheme, darkTheme } from './components/layout/themes'

import './plugins'
import './active_resolution'
import { Typography } from '@material-ui/core'

const WhoisHandler = React.lazy(() => import('./components/whois'))

userPreferencesContainer._initializePreferences()

const Pydat = () => {
    const routes = PluginManagers.routes
    const enableDarkMode = useMediaQuery('@media (prefers-color-scheme: dark')

    const theme = enableDarkMode ? darkTheme : defaultTheme

    if (!appSettings['loaded']) {
        return (
            <React.Fragment>
                <span>
                    <Typography variant="h3" align="center">
                        Unable to talk to backend API!!
                    </Typography>
                </span>
            </React.Fragment>
        )
    }

    return (
        <React.Fragment>
            <ThemeProvider theme={theme}>
                <Router>
                    <SnackbarProvider
                        anchorOrigin={{
                            vertical: "top",
                            horizontal: "right"
                        }}
                        TransitionComponent={Slide}
                        maxSnack={3}
                    >
                        <Dashboard>
                            <Switch>
                                <Route exact path="/">
                                    <Redirect to="/whois" />
                                </Route>
                                <Route exact path="/whois">
                                    <WhoisHandler/>
                                </Route>
                                {Object.keys(routes.plugins).map((name, index) => {
                                    return (
                                        <Route
                                            key={index}
                                            exact
                                            path={routes.plugins[name].path}
                                            {...routes.plugins[name].extra}
                                        >
                                            {React.cloneElement(routes.plugins[name].component)}
                                        </Route>
                                    )
                                })}
                                <Route component={NotFound} />
                            </Switch>
                        </Dashboard>
                    </SnackbarProvider>
                </Router>
            </ThemeProvider>
        </React.Fragment>
    )
}

export default Pydat