import React, {Suspense} from 'react'
import {
    BrowserRouter as Router,
    Switch,
    Route,
    Redirect
} from 'react-router-dom'

import Dashboard from './components/layout/dashboard'
import {BackdropLoader} from './components/helpers/loaders'
// import WhoisHandler from './components/whois'
// import PassiveHandler from './components/passive'


const WhoisHandler = React.lazy(() => import('./components/whois'))
const PassiveHandler = React.lazy(() => import ('./components/passive'))

const Pydat = (props) => {
    return (
        <React.Fragment>
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
                            <Route path="help">

                            </Route>
                            <Route path="stats">

                            </Route>
                        </Switch>
                    </Suspense>
                </Dashboard>
            </Router>
        </React.Fragment>
    )
}

export default Pydat