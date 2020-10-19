import React, {useState, useEffect} from 'react'
import update from 'immutability-helper'
import DataTable from 'react-data-table-component'

import ArrowDropDownIcon from '@material-ui/icons/ArrowDropDown';
import IconButton from '@material-ui/core/IconButton'
import Menu from '@material-ui/core/Menu';
import MenuItem from '@material-ui/core/MenuItem'
import Grid from '@material-ui/core/Grid'
import CircularProgress from '@material-ui/core/CircularProgress'
import { useHistory } from 'react-router-dom';

import {queryFetcher} from '../../helpers/fetchers'
import ExpandedEntryRow from './expandable'


const DropDownCell = (props) => {
    const [anchorEl, setAnchorEl] = useState(null)

    const handleClick = (e) => {
        setAnchorEl(e.currentTarget)
    }

    const handleClose = () => {
        setAnchorEl(null)
    }

    return (
        <Grid container direction="row" alignItems="center">
            <Grid item>
                <IconButton
                    aria-controls={`${props.friendly}-menu`}
                    onClick={handleClick}
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
            </Grid>
            <Grid item>
                {props.value}
            </Grid>
        </Grid>

    )
}

const DomainNameCell = ({row, handleWebPivot}) => {
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
            <MenuItem onClick={() => {}}>Search Passive</MenuItem>
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

const WebHandler = (props) => {
    const initialPageSize = 50
    const [pending, setPending] = useState(true)
    const [queryParams, setQueryParams] = useState({
        query: props.queryData.query,
        chunk_size: initialPageSize,
        offset: 0
    })

    const [queryResults, setQueryResults] = useState([])

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
            selector: 'Version'
        },
        {
            name: 'Score',
            selector: 'score'
        }
    ]

    useEffect(() => {
        setPending(true)
        setQueryResults([])
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
                expandableRowsComponent={<ExpandedEntryRow/>}
                onChangeRowsPerPage={handleChunkChange}
                onChangePage={handlePageChange}
            />
        </React.Fragment>
    )
}

export default WebHandler