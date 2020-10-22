import React, {useState, useEffect, useContext} from 'react'
import { useHistory } from 'react-router-dom';
import update from 'immutability-helper'
import DataTable from 'react-data-table-component'

import ArrowDropDownIcon from '@material-ui/icons/ArrowDropDown';
import IconButton from '@material-ui/core/IconButton'
import Menu from '@material-ui/core/Menu';
import MenuItem from '@material-ui/core/MenuItem'
import Grid from '@material-ui/core/Grid'
import CircularProgress from '@material-ui/core/CircularProgress'

import BuildIcon from '@material-ui/icons/Build';

import {queryFetcher} from '../../helpers/fetchers'
import ExpandedEntryRow from './expandable'
import {UserPreferencesContext} from '../../helpers/preferences'
import { BackdropLoader } from '../../helpers/loaders';
import {
    JSONExporter,
    CSVExporter,
    ListExporter
} from '../../helpers/data_exporters'


const DropDownCell = (props) => {
    const [anchorEl, setAnchorEl] = useState(null)

    const handleClick = (e) => {
        setAnchorEl(e.currentTarget)
    }

    const handleClose = () => {
        setAnchorEl(null)
    }

    return (
        <React.Fragment>
            <IconButton
                aria-controls={`${props.friendly}-menu`}
                onClick={handleClick}
                size='small'
            >
                <ArrowDropDownIcon />
            </IconButton>
            <Menu
                anchorEl={anchorEl}
                keepMounted
                open={Boolean(anchorEl)}
                onClose={handleClose}
            >
                {props.children}
            </Menu>
            {props.value}
        </React.Fragment>

    )
}


const DomainNameCell = ({row, handleWebPivot}) => {
    let history = useHistory()

    return (
        <DropDownCell
             friendly={"domain"}
             value={row.domainName}
        >
            <MenuItem
                onClick={() => handleWebPivot(`dn:"${row.domainName}"`)}
            >
                Pivot Search
            </MenuItem>
            <MenuItem onClick={() => {
                let domain = `*.${row.domainName}`
                history.push(`/passive?type=domain&value=${encodeURIComponent(domain)}`)
                }}
            >
                Search Passive
            </MenuItem>
        </DropDownCell>
    )
}

const RegistrantCell = ({row, handleWebPivot}) => {
    return (
        <DropDownCell
            friendly={"registrantname"}
            value={row.registrant_name}
        >
            <MenuItem
                onClick={() => handleWebPivot(`registrant_name:"${row.registrant_name}"`)}
            >
                Pivot Search
            </MenuItem>
        </DropDownCell>
    )
}

const EmailCell = ({row, handleWebPivot}) => {
    return (
        <DropDownCell
            friendly={"email"}
            value={row.registrant_email}
        >
            <MenuItem
                onClick={() => handleWebPivot(`registrant_email:"${row.registrant_email}"`)}
            >
                Pivot Search
            </MenuItem>
        </DropDownCell>
    )
}

const TelephoneCell = ({row, handleWebPivot}) => {
    return (
        <DropDownCell
            friendly={"telephone"}
            value={row.registrant_telephone}
        >
            <MenuItem
                onClick={() => handleWebPivot(`registrant_telephone:"${row.registrant_telephone}"`)}
            >
                Pivot Search
            </MenuItem>
        </DropDownCell>
    )
}

const SearchTools = ({data, children}) => {
    const [anchorEl, setAnchorEl] = useState(null)
    const [openJSONDialog, setOpenJSONDialog] = useState(false)
    const [openCSVDialog, setOpenCSVDialog] = useState(false)
    const [openListDialog, setOpenListDialog] = useState(false)

    const handleClick = (e) => {
        setAnchorEl(e.currentTarget)
    }

    const handleClose = () => {
        setAnchorEl(null)
    }

    return (
        <React.Fragment>
            <IconButton
                onClick={handleClick}
                size='small'
            >
                <BuildIcon fontSize="small"/>
            </IconButton>
            <Menu
                anchorEl={anchorEl}
                keepMounted
                open={Boolean(anchorEl)}
                onClose={handleClose}
            >
                <MenuItem
                    onClick={() => {setOpenJSONDialog(true); handleClose()}}
                >
                    Export JSON
                </MenuItem>
                <JSONExporter
                    data={data}
                    open={openJSONDialog}
                    onClose={() => {setOpenJSONDialog(false)}}
                />
                <MenuItem
                    onClick={() => {setOpenCSVDialog(true); handleClose()}}
                >
                    Export CSV
                </MenuItem>
                <CSVExporter
                    data={data}
                    open={openCSVDialog}
                    onClose={() => {setOpenCSVDialog(false)}}
                />
                <MenuItem
                    onClick={() => {setOpenListDialog(true); handleClose()}}
                >
                    Export List
                </MenuItem>
                <ListExporter
                    field={'domainName'}
                    data={data}
                    open={openListDialog}
                    onClose={() => {setOpenListDialog(false)}}
                />
                {React.Children.map(children, (child) => {
                    const props = {
                        data: data,
                        handleClose: handleClose,
                    }
                    if (React.isValidElement(child)) {
                        return React.cloneElement(child, props)
                    } else {
                        return child
                    }
                })}
            </Menu>
        </React.Fragment>
    )
}

const WebHandler = (props) => {
    const preferences = useContext(UserPreferencesContext)

    const initialPageSize = preferences.getPref('whois', 'page_size', 50)
    const [pending, setPending] = useState(true)
    const [queryParams, setQueryParams] = useState({
        query: props.queryData.query,
        chunk_size: initialPageSize,
        offset: 0
    })

    const [queryResults, setQueryResults] = useState(null)

    const columns = [
        {
            name: 'Domain Name',
            selector: 'domainName',
            cell: (row) => (
                <DomainNameCell
                    row={row}
                    handleWebPivot={props.handleWebPivot}
                />
            )
        },
        {
            name: 'Registrant',
            selector: 'registrant_name',
            cell: (row) => (
                <RegistrantCell
                    row={row}
                    handleWebPivot={props.handleWebPivot}
                />
            )
        },
        {
            name: 'Email',
            selector: 'registrant_email',
            cell: (row) => (
                <EmailCell
                    row={row}
                    handleWebPivot={props.handleWebPivot}
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
                    handleWebPivot={props.handleWebPivot}
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
    ]

    useEffect(() => {
        setPending(true)
        setQueryResults(null)
        setQueryParams(update(queryParams, {
            query: {$set: props.queryData.query},
            chunk_size: {$set: initialPageSize},
            offset: {$set: 0}
        }))
    }, [props.queryData])

    useEffect(() => {
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
                pagination={true}
                paginationServer={true}
                paginationDefaultPage={1}
                paginationPerPage={queryParams.chunk_size}
                paginationRowsPerPageOptions={[50, 100, 1000, 10000]}
                paginationTotalRows={queryResults.total}
                progressPending={pending}
                progressComponent={<CircularProgress color="secondary"/>}
                striped
                highlightOnHover
                expandableRows
                noHeader={true}
                expandableRowsComponent={<ExpandedEntryRow/>}
                onChangeRowsPerPage={handleChunkChange}
                onChangePage={handlePageChange}
                subHeader
                subHeaderAlign="right"
                subHeaderComponent={
                    <SearchTools data={queryResults.results} />
                }
            />
        </React.Fragment>
    )
}

export default WebHandler