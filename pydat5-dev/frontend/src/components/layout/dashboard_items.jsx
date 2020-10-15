import React from 'react';
import {useHistory} from 'react-router-dom'
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemText from '@material-ui/core/ListItemText';
import ListSubheader from '@material-ui/core/ListSubheader';

import SearchIcon from '@material-ui/icons/Search'
import LanguageIcon from '@material-ui/icons/Language'
import HelpIcon from '@material-ui/icons/Help'
import EqualizerIcon from '@material-ui/icons/Equalizer'

export const MainListItems = (props) => {
  let history = useHistory()

  const handleRedirect = (url) => {
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
    </React.Fragment>
  )
}