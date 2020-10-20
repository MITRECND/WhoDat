import React, {Suspense, useContext} from 'react'
import {
    BrowserRouter as Router,
    Switch,
    Route,
    Redirect
} from 'react-router-dom'

import { ThemeProvider } from '@material-ui/styles'

import {PluginManagers, PyDatPluginContext} from './components/plugins'
import {UserPreferences, UserPreferencesContext} from './components/helpers/preferences'
import Dashboard from './components/layout/dashboard'
import NotFound from './components/layout/notfound'
import {BackdropLoader} from './components/helpers/loaders'
import { defaultTheme } from './components/layout/themes'

import './plugins'


const WhoisHandler = React.lazy(() => import('./components/whois'))
const PassiveHandler = React.lazy(() => import ('./components/passive'))

const Pydat = ({}) => {
    const routes = useContext(PyDatPluginContext).routes

    return (
        <React.Fragment>
            <UserPreferencesContext.Provider value={UserPreferences}>
                <ThemeProvider theme={defaultTheme}>
                    <PyDatPluginContext.Provider value={PluginManagers}>
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
                                        <Route path="/passive">
                                            <PassiveHandler />
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
                    </PyDatPluginContext.Provider>
                </ThemeProvider>
            </UserPreferencesContext.Provider>
        </React.Fragment>
    )
}

export default Pydat