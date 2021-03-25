import React from 'react'
import qs from 'qs'

import DropDownCell from '../helpers/dropdown_cell'
import {PluginManagers} from '../plugins'

import {MenuElement} from '../layout'

const createSearchString = (query) => {
    return(
        '?' + qs.stringify({
            query: query
        })
    )
}

const whoisDomainMenuElement = new MenuElement({
    type: "tld",
    path: (domainName) => {
        const search_string = createSearchString(`dn:"${domainName}"`)
        return `/whois${search_string}`
    },
    text: "Pivot Search",
})

const whoisRegistrantMenuElement = new MenuElement({
    type: "registrant",
    path: (registrant) => {
        const search_string = createSearchString(`registrant_name:"${registrant}"`)
        return `/whois${search_string}`
    },
    text: "Pivot Search"
})

const whoisEmailMenuElement = new MenuElement({
    type: "email",
    path: (email) => {
        const search_string = createSearchString(`contactEmail:"${email}"`)
        return `/whois${search_string}`
    },
    text: "Pivot Search"
})

const whoisTelephoneMenuElement = new MenuElement({
    type: "telephone",
    path: (telephone) => {
        const search_string = createSearchString(`registrant_telephone:"${telephone}"`)
        return `/whois${search_string}`
    },
    text: "Pivot Search"
})

export const DomainNameCell = ({value: domainName, copyFriendly}) => {
    const plugins = PluginManagers.menu.plugins.tld

    return (
        <DropDownCell
             friendly={"domain"}
             value={domainName}
             copyFriendly={copyFriendly}
        >
            {whoisDomainMenuElement.getComponent(domainName)}
            {Object.keys(plugins).map((name, index) => (
                plugins[name].getComponent(domainName, index)
            ))}
        </DropDownCell>
    )
}

export const RegistrantCell = ({value: registrant_name, copyFriendly}) => {
    const plugins = PluginManagers.menu.plugins.registrant

    if (registrant_name === null || registrant_name === "") {
        return (
            <React.Fragment></React.Fragment>
        )
    }


    return (
        <DropDownCell
            friendly={"registrantname"}
            value={registrant_name}
            copyFriendly={copyFriendly}
        >
            {whoisRegistrantMenuElement.getComponent(registrant_name)}
            {Object.keys(plugins).map((name, index) => (
                plugins[name].getComponent(registrant_name, index)
            ))}
        </DropDownCell>
    )
}

export const EmailCell = ({value: contactEmail, copyFriendly}) => {
    const plugins = PluginManagers.menu.plugins.email
    if (contactEmail === null || contactEmail === "") {
        return (
            <React.Fragment></React.Fragment>
        )
    }

    return (
        <DropDownCell
            friendly={"email"}
            value={contactEmail}
            copyFriendly={copyFriendly}
        >
            {whoisEmailMenuElement.getComponent(contactEmail)}
            {Object.keys(plugins).map((name, index) => (
                plugins[name].getComponent(contactEmail, index)
            ))}
        </DropDownCell>
    )
}

export const TelephoneCell = ({value: registrant_telephone, copyFriendly}) => {
    const plugins = PluginManagers.menu.plugins.telephone
    if (registrant_telephone === null || registrant_telephone === "") {
        return (
            <React.Fragment></React.Fragment>
        )
    }

    return (
        <DropDownCell
            friendly={"telephone"}
            value={registrant_telephone}
            copyFriendly={copyFriendly}
        >
           {whoisTelephoneMenuElement.getComponent(registrant_telephone)}
           {Object.keys(plugins).map((name, index) => (
                plugins[name].getComponent(registrant_telephone, index)
            ))}
        </DropDownCell>
    )
}