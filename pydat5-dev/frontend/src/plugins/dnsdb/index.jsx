import React from 'react'
import {useHistory} from 'react-router-dom'
import qs from 'qs'

import MenuItem from '@material-ui/core/MenuItem'
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemText from '@material-ui/core/ListItemText';
import LanguageIcon from '@material-ui/icons/Language'

import {PluginManagers} from '../../components/plugins'

const DNSDB = React.lazy(() => import ('./dnsdb'))

export const DNSDBPATH = "/passive/dnsdb"

export const DNSDBTLDDomainMenu = React.forwardRef(({domainName}, ref) => {
    let history = useHistory()

    return (
        <MenuItem onClick={() => {
            let domain = `*.${domainName}`
            history.push({
                pathname: DNSDBPATH,
                search: '?' + qs.stringify({
                    type: 'domain',
                    value: domain
                })
            })}}
        >
            Search DNSDB
        </MenuItem>
    )
})

export const DNSDBDomainMenu = React.forwardRef(({domainName}, ref) => {
    let history = useHistory()

    return (
        <MenuItem onClick={() => {
            let domain = `*.${domainName}`
            history.push({
                pathname: DNSDBPATH,
                search: '?' + qs.stringify({
                    type: 'domain',
                    value: domain
                })
            })}}
        >
            Search DNSDB
        </MenuItem>
    )
})

export const DNSDBIPMenu = React.forwardRef(({ip}, ref) => {
    let history = useHistory()

    return (
        <MenuItem onClick={() => {
            history.push({
                pathname: DNSDBPATH,
                search: '?' + qs.stringify({
                    type: 'ip',
                    value: ip
                })
            })}}
        >
            Search DNSDB
        </MenuItem>
    )
})

const DNSDBDrawer = ({handleRedirect}) => {
    return (
        <ListItem button onClick={() => {handleRedirect(DNSDBPATH)}}>
            <ListItemIcon> <LanguageIcon /> </ListItemIcon>
            <ListItemText primary="DNSDB - Passive" />
        </ListItem>
    )
}

PluginManagers.menu.addPlugin('dnsdb_tld', 'tld', DNSDBTLDDomainMenu)
PluginManagers.menu.addPlugin('dnsdb_domain', 'domain', DNSDBDomainMenu)
PluginManagers.menu.addPlugin('dnsdb_ip', 'ip', DNSDBIPMenu)
PluginManagers.routes.addPlugin('dnsdb', DNSDBPATH, 'DNSDB Passive DNS', <DNSDB />)
PluginManagers.drawer.addPlugin('dnsdb', <DNSDBDrawer />)
