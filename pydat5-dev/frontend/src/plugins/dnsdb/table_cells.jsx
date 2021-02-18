import React, { useMemo } from 'react'

import Grid from '@material-ui/core/Grid'
import DropDownCell from '../../components/helpers/dropdown_cell'
import { PluginManagers } from '../../components/plugins';

const cleanData = (data) => {
    // Remove trailing '.'
    if (data.slice(-1) === '.') {
        return data.slice(0, -1)
    } else {
        return data
    }
}

const cleanEntry = (entry) => {
    // clean a record and return it
}

const DomainMenu = ({value, copyFriendly}) => {
    let plugins = PluginManagers.menu.plugins.domain
    const cleanValue = cleanData(value)

    return (
        <DropDownCell
            friendly={"domain"}
            value={cleanValue}
            copyFriendly={copyFriendly}
        >
        {Object.keys(plugins).map((name, index) => (
            plugins[name].getComponent(cleanValue, index)
        ))}
        </DropDownCell>

    )
}

const IPMenu = ({value, copyFriendly}) => {
    let plugins = PluginManagers.menu.plugins.ip

    return (
        <DropDownCell
            friendly={"ip"}
            value={value}
            copyFriendly={copyFriendly}
        >
            {Object.keys(plugins).map((name, index) => (
                plugins[name].getComponent(value, index)
            ))}
        </DropDownCell>

    )
}

export const RRNameCell = ({row, copyFriendly}) => {
    return (
        <DomainMenu
            row={row}
            value={row.rrname}
            copyFriendly={copyFriendly}
        />
    )
}


export const RDataCell = ({row, copyFriendly}) => {
    const cleanedData = useMemo(() => {
        let data = []
        row.rdata.forEach((value) => {
            data.push(cleanData(value))
        })
        return data
    }, [row])

    if (!copyFriendly) {
        return (
            <Grid container>
                {cleanedData.map((value, index) => {
                    let data = value
                    if (['ns', 'cname', 'mx'].includes(row.rrtype.toLowerCase())) {
                        data = (
                            <DomainMenu
                                row={row}
                                value={value}
                                copyFriendly={copyFriendly}
                            />
                        )
                    } else if (['a', 'aaaa'].includes(row.rrtype.toLowerCase())) {
                        data = (
                            <IPMenu
                                row={row}
                                value={value}
                                copyFriendly={copyFriendly}
                            />
                        )
                    }

                    return (
                        <Grid item xs={12} key={index}>
                            {data}
                        </Grid>
                    )
                })}
            </Grid>
        )
    } else {
        return (
            <React.Fragment>
                {cleanedData.join()}
            </React.Fragment>
        )
    }
}