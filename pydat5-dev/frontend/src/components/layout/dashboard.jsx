import React, { useContext, useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';

import { makeStyles} from '@material-ui/core/styles';
import CssBaseline from '@material-ui/core/CssBaseline';
import AppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar';
import List from '@material-ui/core/List';
import IconButton from '@material-ui/core/IconButton';
import MenuIcon from '@material-ui/icons/Menu';
import MenuItem from '@material-ui/core/MenuItem';
import Menu from '@material-ui/core/Menu';
import MoreIcon from '@material-ui/icons/MoreVert';
import ListItem from '@material-ui/core/ListItem'
import {Link as RouterLink} from 'react-router-dom'
import ListItemText from '@material-ui/core/ListItemText';

import {PluginManagers} from '../plugins'
import {whoisRoute, whoisNavigation} from '../whois'
import {OptionsContext} from '../layout'


// https://material-ui.com/components/app-bar/#app-bar-with-a-primary-search-field
// https://ansonlowzf.com/how-to-build-a-material-ui-navbar/

const useStyles = makeStyles((theme) => ({
  grow: {
    flexGrow: 1,
  },
  menuButton: {
    marginRight: theme.spacing(2),
  },
  layoutDesktop: {
    display: 'none',
    [theme.breakpoints.up('md')]: {
      display: 'flex',
    },
  },
  layoutMobile: {
    display: 'flex',
    [theme.breakpoints.up('md')]: {
      display: 'none',
    },
  },

  linkText: {
    textDecoration: 'none',
    textTransform: 'uppercase',
    color: `${theme.palette.primary.contrastText}`
  },
  menuLinkText: {
    textDecoration: 'none',
    textTransform: 'uppercase',
  },
  desktopNav: {
    justifyContent: 'space-between',
    display: 'flex',
  },
  content: {
    flexGrow: 1,
    padding: theme.spacing(3),
    transition: theme.transitions.create('margin', {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
  },
}));


const Navigation = () => {
  const classes = useStyles()
  const [anchorEl, setAnchorEl] = useState(null);
  const isMenuOpen = Boolean(anchorEl)

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }


  const all_paths = useMemo(() => (
    [
      whoisNavigation,
      ...Object.values(PluginManagers.nav.plugins)
    ]
  ), [])

  const menuId = 'mobile-navigation-menu'
  const mobileMenu = (
    <Menu
      anchorEl={anchorEl}
      anchorOrigin={{vertical: 'top', horizontal: 'left'}}
      id={menuId}
      keepMounted
      transformOrigin={{vertical: 'top', horizontal: 'left'}}
      open={isMenuOpen}
      onClose={handleMenuClose}
    >
      {all_paths.map(({path, title}, index) => (
        <MenuItem key={index}>
        <RouterLink
          to={path}
          className={classes.menuLinkText}
          onClick={handleMenuClose}
        >
          {title}
        </RouterLink>
      </MenuItem>
      ))}
    </Menu>
  )

  return (
    <React.Fragment>
      <div className={classes.layoutMobile}>
        <IconButton
          edge="start"
          className={clsx(classes.menuButton)}
          color="inherit"
          aria-label="open drawer"
          onClick={handleMenuOpen}
        >
          <MenuIcon />
        </IconButton>
        {mobileMenu}
      </div>

      <div className={classes.layoutDesktop}>
        <List
          component="nav"
          className={clsx(classes.desktopNav)}
        >
          {all_paths.map(({path, title}, index) => (
            <RouterLink
              to={path}
              key={index}
              className={classes.linkText}
            >
              <ListItem button>
                <ListItemText primary={title} />
              </ListItem>
            </RouterLink>
          ))}
        </List>
      </div>
    </React.Fragment>
  )
}

const Options = () => {
  const classes = useStyles()

  const [anchorEl, setAnchorEl] = useState(null);
  const isMenuOpen = Boolean(anchorEl)
  const optionsContext = useContext(OptionsContext)

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget)
  }

  const handleMenuClose = () => {
    setAnchorEl(null)
  }

  const routes = useMemo(() => (
    {
      ...PluginManagers.routes.plugins,
      whois: whoisRoute
    }
  ), [])

  let match = []
  for (const name in routes) {
    if (routes[name].matchRoute()) {
      match = routes[name].options
      break
    }
  }

  const menuId = 'mobile-options-menu'
  const mobileMenu = (
    <Menu
      anchorEl={anchorEl}
      anchorOrigin={{vertical: 'top', horizontal: 'right'}}
      id={menuId}
      keepMounted
      transformOrigin={{vertical: 'top', horizontal: 'right'}}
      open={isMenuOpen}
      onClose={handleMenuClose}
    >
      {match.map((option_element, index) => (
        option_element.getMobileElement({
          optionsContext: optionsContext,
          index: index
        })
      ))}

    </Menu>
  )

  return (
    <React.Fragment>
      <div className={classes.layoutDesktop}>
        {match.map((option_element, index) => (
          option_element.getDesktopElement({
            optionsContext: optionsContext,
            index: index
          })
        ))}
      </div>
      <div className={classes.layoutMobile}>
        {match.length > 0 &&
        <IconButton
          aria-label="show more"
          aria-controls={menuId}
          aria-haspopup="true"
          onClick={handleMenuOpen}
          color="inherit"
        >
          <MoreIcon />
        </IconButton>}
        {mobileMenu}
      </div>
    </React.Fragment>
  )
}

const Dashboard = (props) => {
  const classes = useStyles();
  const [optionsState, setOptionsState] = useState({})

  return (
    <div>
      <CssBaseline />
      <OptionsContext.Provider value={{
          optionsState: optionsState,
          setOptionsState: setOptionsState
        }}
      >
        <div className={classes.grow}>
          <AppBar position="static">
            <Toolbar variant="dense">
              <Navigation />
              <div className={classes.grow} />
              <Options />
            </Toolbar>
          </AppBar>

          <main className={classes.content}>
              {props.children}
          </main>
        </div>
      </OptionsContext.Provider>
    </div>

  );
}

export default Dashboard