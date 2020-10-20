import React from 'react';
import {useHistory} from 'react-router-dom'
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemText from '@material-ui/core/ListItemText';
import ListSubheader from '@material-ui/core/ListSubheader';
import Divider from '@material-ui/core/Divider'

import SearchIcon from '@material-ui/icons/Search'
import LanguageIcon from '@material-ui/icons/Language'
import HelpIcon from '@material-ui/icons/Help'
import EqualizerIcon from '@material-ui/icons/Equalizer'

import {PyDatPluginContext} from '../plugins'
import { useContext } from 'react';

export const MainListItems = (props) => {
  const drawer_plugins = useContext(PyDatPluginContext).drawer

  let history = useHistory()

  const handleRedirect = (url) => {
    props.handleDrawerClose()
    history.push(url)
  }

  return (
    <React.Fragment>
      <ListItem button onClick={() => {handleRedirect('/whois')}}>
        <ListItemIcon> <SearchIcon /> </ListItemIcon>
        <ListItemText primary="WHOIS Search" />
      </ListItem>
      <ListItem button onClick={() => {handleRedirect('/passive')}}>
        <ListItemIcon> <LanguageIcon /> </ListItemIcon>
        <ListItemText primary="Passive DNS" />
      </ListItem>
      <ListItem button>
        <ListItemIcon> <EqualizerIcon /> </ListItemIcon>
        <ListItemText primary="Stats" />
      </ListItem>
      <ListItem button>
        <ListItemIcon> <HelpIcon /> </ListItemIcon>
        <ListItemText primary="Help" />
      </ListItem>
      {Object.keys(drawer_plugins.plugins).length > 0 && <Divider />}
      {Object.keys(drawer_plugins.plugins).map((name, index) => (
        React.cloneElement(
          drawer_plugins.plugins[name],
          {key: index,
           handleRedirect: handleRedirect
          }
        )
      ))}
    </React.Fragment>
  )
}