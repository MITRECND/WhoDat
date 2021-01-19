import React, {useState, useEffect, useContext, useMemo} from 'react'
import update from 'immutability-helper'
import DataTable from 'react-data-table-component'
import qs from 'qs'
import {Link as RouterLink} from 'react-router-dom'

import ArrowDropDownIcon from '@material-ui/icons/ArrowDropDown';
import IconButton from '@material-ui/core/IconButton'
import Menu from '@material-ui/core/Menu';
import MenuItem from '@material-ui/core/MenuItem'
import CircularProgress from '@material-ui/core/CircularProgress'

import {queryFetcher} from '../helpers/fetchers'
import ExpandedEntryRow from './expandable'
import {UserPreferencesContext} from '../helpers/preferences'
import { BackdropLoader } from '../helpers/loaders';
import SearchTools from '../helpers/search_tools'
import DropDownCell from '../helpers/dropdown_cell'
import {PluginManagers} from '../plugins'


const createSearchString = (query) => {
    return(
        '?' + qs.stringify({
            query: query
        })
    )
}

const DomainNameCell = ({row}) => {
    const menu_plugins = PluginManagers.menu.plugins.tld
    const search_string = createSearchString(`dn:"${row.domainName}"`)

    return (
        <DropDownCell
             friendly={"domain"}
             value={row.domainName}
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
                    <Component domainName={row.domainName} key={index} />
                )
            })}
        </DropDownCell>
    )
}


const RegistrantCell = ({row}) => {
    const search_string = createSearchString(`registrant_name:"${row.registrant_name}"`)

    if (row.registrant_name === null || row.registrant_name === "") {
        return (
            <React.Fragment></React.Fragment>
        )
    }


    return (
        <DropDownCell
            friendly={"registrantname"}
            value={row.registrant_name}
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

const EmailCell = ({row}) => {
    const search_string = createSearchString(`registrant_email:"${row.registrant_email}"`)

    if (row.registrant_email === null || row.registrant_email === "") {
        return (
            <React.Fragment></React.Fragment>
        )
    }

    return (
        <DropDownCell
            friendly={"email"}
            value={row.registrant_email}
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

const TelephoneCell = ({row}) => {
    const search_string = createSearchString(`registrant_telephone:"${row.registrant_telephone}"`)

    if (row.registrant_telephone === null || row.registrant_telephone === "") {
        return (
            <React.Fragment></React.Fragment>
        )
    }

    return (
        <DropDownCell
            friendly={"telephone"}
            value={row.registrant_telephone}
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

const TableColumns = () => { return [
    {
        name: 'Domain Name',
        selector: 'domainName',
        cell: (row) => (
            <DomainNameCell
                row={row}
            />
        )
    },
    {
        name: 'Registrant',
        selector: 'registrant_name',
        cell: (row) => (
            <RegistrantCell
                row={row}
            />
        )
    },
    {
        name: 'Email',
        selector: 'registrant_email',
        cell: (row) => (
            <EmailCell
                row={row}
            />
        )
    },
    {
        name: 'Created',
        selector: 'createdDate'
    },
    {
        name: 'Telephone',
        selector: 'registrant_telephone',
        cell: (row) => (
            <TelephoneCell
                row={row}
            />
        )
    },
    {
        name: 'Version',
        selector: 'Version',
        maxWidth: "5vh"
    },
    {
        name: 'Score',
        selector: 'score',
        maxWidth: "10vh",
        cell: (row) => row.score.toFixed(3)
    }
]}

const WhoisTable = (props) => {
    const preferences = useContext(UserPreferencesContext)

    const initialPageSize = preferences.getPref('whois', 'page_size', 50)
    const [pending, setPending] = useState(true)
    const [queryParams, setQueryParams] = useState({
        query: props.queryData.query,
        chunk_size: initialPageSize,
        offset: 0
    })

    const [queryResults, setQueryResults] = useState(null)
    const columns = useMemo(() => TableColumns(), [])

    useEffect(() => {
        setQueryParams(update(queryParams, {
            query: {$set: props.queryData.query},
            chunk_size: {$set: initialPageSize},
            offset: {$set: 0}
        }))
    }, [props.queryData])

    useEffect(() => {
        setPending(true)
        fetchData()
    }, [queryParams])

    const handlePageChange = async (page) => {
        setQueryParams(update(queryParams, {
            offset: {$set: page - 1}
        }))
    }

    const handleChunkChange = async (perPage, page) => {
        setQueryParams(update(queryParams, {
            chunk_size: {$set: perPage},
            offset: {$set: page - 1}
        }))
        preferences.setPref('whois', 'page_size', perPage)
    }

    const fetchData = () => {
        const asyncfetch = async () => {
            try {
                let results = await queryFetcher({
                    query: queryParams.query,
                    chunk_size: queryParams.chunk_size,
                    offset: queryParams.offset
                })

                setQueryResults({
                    total: results.total,
                    page_size: queryParams.chunk_size,
                    results: results.results
                })
                setPending(false)

            } catch (err) {
                console.log(err)
            }
        }

        asyncfetch()
    }

    if (queryResults === null) {
        return (
            <BackdropLoader />
        )
    }

    return (
        <React.Fragment>
            <DataTable
                columns={columns}
                data={queryResults.results}
                // fixedHeader
                pagination
                paginationServer
                paginationDefaultPage={1}
                paginationPerPage={queryResults.page_size}
                paginationRowsPerPageOptions={[50, 100, 1000, 10000]}
                paginationTotalRows={queryResults.total}
                progressPending={pending}
                progressComponent={<CircularProgress color="secondary"/>}
                striped
                highlightOnHover
                expandableRows
                noHeader
                expandableRowsComponent={<ExpandedEntryRow/>}
                onChangeRowsPerPage={handleChunkChange}
                onChangePage={handlePageChange}
                subHeader
                subHeaderAlign="right"
                subHeaderComponent={
                    <SearchTools data={queryResults.results} defaultListField={'domainName'} />
                }
            />
        </React.Fragment>
    )
}

export default WhoisTable