import React, {Suspense} from 'react'
import {
    BrowserRouter as Router,
    Switch,
    Route,
    Redirect
} from 'react-router-dom'

import { ThemeProvider } from '@material-ui/styles'
import useMediaQuery from '@material-ui/core/useMediaQuery'

import './plugins'

import {PluginManagers} from './components/plugins'
import {UserPreferences, UserPreferencesContext} from './components/helpers/preferences'
import Dashboard from './components/layout/dashboard'
import NotFound from './components/layout/notfound'
import {BackdropLoader} from './components/helpers/loaders'
import { defaultTheme, darkTheme } from './components/layout/themes'



const WhoisHandler = React.lazy(() => import('./components/whois'))

const Pydat = () => {
    const routes = PluginManagers.routes
    const enableDarkMode = useMediaQuery('@media (prefers-color-scheme: dark')

    const theme = enableDarkMode ? darkTheme : defaultTheme

    return (
        <React.Fragment>
            <UserPreferencesContext.Provider value={UserPreferences}>
                <ThemeProvider theme={theme}>
                    <Router>
                        <Dashboard>
                            <Suspense fallback={<BackdropLoader/>}>
                                <Switch>
                                    <Route exact path="/">
                                        <Redirect to="/whois" />
                                    </Route>
                                    <Route path="/whois">
                                        <WhoisHandler/>
                                    </Route>
                                    <Route path="/help">

                                    </Route>
                                    <Route path="/stats">

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
                            </Suspense>
                        </Dashboard>
                    </Router>
                </ThemeProvider>
            </UserPreferencesContext.Provider>
        </React.Fragment>
    )
}

export default Pydat