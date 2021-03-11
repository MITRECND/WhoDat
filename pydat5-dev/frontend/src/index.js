import React from 'react';
import ReactDOM from 'react-dom';
import {appSettings} from './settings'
import {BackdropLoader} from './components/helpers/loaders'
import 'fontsource-roboto';
import * as serviceWorker from './serviceWorker';
import { Suspense } from 'react';

const Pydat = React.lazy(() => import('./pydat'))

const fetchSettings = async () => {
  let response = await fetch (
      '/api/v2/settings', {
          method: 'GET',
          headers: {
              'Content-Type': 'application/json'

          },
  })

  if (response.status === 200) {
      let jresp = await response.json()
      for (let key in jresp) {
          appSettings[key] = jresp[key]
      }
      return jresp
  } else {
      throw response
  }
}

const runAppAsync = async () => {

  await fetchSettings()

  ReactDOM.render(
    <React.Fragment>
      <Suspense fallback={<BackdropLoader/>}>
        <Pydat />
      </Suspense>
    </React.Fragment>
    ,
    // <React.StrictMode>
    //   <Pydat/>
    // </React.StrictMode>,
    document.getElementById('root')
  );

  // If you want your app to work offline and load faster, you can change
  // unregister() to register() below. Note this comes with some pitfalls.
  // Learn more about service workers: https://bit.ly/CRA-PWA
  serviceWorker.unregister();
}

const runApp = () => {
  runAppAsync()
}

runApp()
