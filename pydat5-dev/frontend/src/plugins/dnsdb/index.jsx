import React from 'react'
import qs from 'qs'

import { PluginManagers } from '../../components/plugins'

import {
    MenuElement,
    RouteElement,
    NavigationElement
} from '../../components/layout'

import {
    userPreferencesManager,
    UserPreferenceNamespace,
    UserPreference,
} from '../../components/helpers/preferences'

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

const dnsdbPreferencesNamespace = new UserPreferenceNamespace({
    name: "dnsdb",
    title: "DNSDB Search Preferences",
    desription: "Preferences for DNSDB Search and Presentation"
})
userPreferencesManager.registerNamespace(dnsdbPreferencesNamespace)
userPreferencesManager.registerPrefs(
    dnsdbPreferencesNamespace, [
        new UserPreference({
            name: "page_size",
            type: "number",
            title: "Results Page Size",
            description: "Default Page Size to use for result pagination",
            default_value: 100
        }),
        new UserPreference({
            name: "remember_page_size",
            type: "boolean",
            title: "Remember Results Page Size",
            description: "Remember last used page size when displaying results",
            default_value: true,
        }),
        new UserPreference({
            name: "domain_search_type",
            type: "string",
            title: "Domain Search Method",
            description: "Search method to use when searching forward domains, (absolute, prefix-wildcard, suffix-wildcard)",
            default_value: "prefix-wildcard"
        }),
        new UserPreference({
            name: "remember_domain_search_type",
            type: "boolean",
            title: "Remember Domain Search Method",
            description: "Remember last used Forward Domain Search Type (e.g., Prefix Wildcard)",
            default_value: false
        })

    ]
)

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
