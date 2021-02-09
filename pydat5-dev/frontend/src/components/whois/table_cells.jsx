import React from 'react'
import qs from 'qs'
import {Link as RouterLink} from 'react-router-dom'

import MenuItem from '@material-ui/core/MenuItem'
import DropDownCell from '../helpers/dropdown_cell'
import {PluginManagers} from '../plugins'


const createSearchString = (query) => {
    return(
        '?' + qs.stringify({
            query: query
        })
    )
}

export const DomainNameCell = ({value: domainName, copyFriendly}) => {
    const menu_plugins = PluginManagers.menu.plugins.tld
    const search_string = createSearchString(`dn:"${domainName}"`)

    return (
        <DropDownCell
             friendly={"domain"}
             value={domainName}
             copyFriendly={copyFriendly}
        >
            <MenuItem
                component={RouterLink}
                to={`/whois${search_string}` }
            >
                Pivot Search
            </MenuItem>
            {Object.keys(menu_plugins).map((name, index) => {
                let Component = menu_plugins[name]
                return (
                    <Component domainName={domainName} key={index} />
                )
            })}
        </DropDownCell>
    )
}

export const RegistrantCell = ({value: registrant_name, copyFriendly}) => {
    const search_string = createSearchString(`registrant_name:"${registrant_name}"`)

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

            <MenuItem
                component={RouterLink}
                to={`/whois${search_string}`}
            >
                Pivot Search
            </MenuItem>
        </DropDownCell>
    )
}

export const EmailCell = ({value: contactEmail, copyFriendly}) => {
    const search_string = createSearchString(`contactEmail:"${contactEmail}"`)

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
            <MenuItem
                component={RouterLink}
                to={`/whois${search_string}`}
            >
                Pivot Search
            </MenuItem>
        </DropDownCell>
    )
}

export const TelephoneCell = ({value: registrant_telephone, copyFriendly}) => {
    const search_string = createSearchString(`registrant_telephone:"${registrant_telephone}"`)

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
            <MenuItem
                component={RouterLink}
                to={`/whois${search_string}`}
            >
                Pivot Search
            </MenuItem>
        </DropDownCell>
    )
}