import React from 'react'
import qs from 'qs'

import { PluginManagers } from '../../components/plugins'

import {
    MenuElement,
    RouteElement,
    NavigationElement
} from '../../components/layout'

const DNSDB = React.lazy(() => import ('./dnsdb'))

export const DNSDBPATH = "/passive/dnsdb"

const DNSDBDomainMenu = new MenuElement({
    type: "tld",
    path: (domainName) => {
            const search_string = '?' + qs.stringify({
                type: 'domain',
                value: domainName
            })

            return `${DNSDBPATH}${search_string}`
    },
    text: "Search DNSDB"
})

const DNSDBIPMenu = new MenuElement({
    type: "ip",
    path: (ip) => {
            const search_string = '?' + qs.stringify({
                type: 'ip',
                value: ip
            })

            return `${DNSDBPATH}${search_string}`
    },
    text: "Search DNSDB"
})

PluginManagers.menu.addPlugin('dnsdb_tld', 'tld', DNSDBDomainMenu)
PluginManagers.menu.addPlugin('dnsdb_domain', 'domain', DNSDBDomainMenu)
PluginManagers.menu.addPlugin('dnsdb_ip', 'ip', DNSDBIPMenu)
PluginManagers.routes.addPlugin(
    'dnsdb',
    new RouteElement({
        path: DNSDBPATH,
        title: 'DNSDB Passive DNS',
        component: <DNSDB />
    })
)

PluginManagers.nav.addPlugin(
    'dnsdb',
    new NavigationElement({
        title: 'DNSDB',
        path: DNSDBPATH,
        text: "Passive DNS"
    })
)
