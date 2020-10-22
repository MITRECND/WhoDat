import React, {useState, useEffect} from 'react'
import update from 'immutability-helper'
import DataTable from 'react-data-table-component'

import ArrowDropDownIcon from '@material-ui/icons/ArrowDropDown';
import IconButton from '@material-ui/core/IconButton'
import Menu from '@material-ui/core/Menu';
import MenuItem from '@material-ui/core/MenuItem'
import Grid from '@material-ui/core/Grid'
import Button from '@material-ui/core/Button';
import Input from '@material-ui/core/Input'
import InputLabel from '@material-ui/core/InputLabel'
import Select from '@material-ui/core/Select'
import Toolbar from '@material-ui/core/Toolbar'
import AppBar from '@material-ui/core/AppBar'

import SearchTools from '../../helpers/search_tools'

import { BackdropLoader } from '../../helpers/loaders'
import { useHistory } from 'react-router-dom';
import { Typography } from '@material-ui/core';

const convertTimestampToDate = (timestamp) => {
    let date = new Date(timestamp * 1000)
    let year = date.getFullYear()
    let month = `0${date.getMonth() + 1}`.slice(-2)
    let day = `0${date.getDay()}`.slice(-2)

    let timestring = `${year}-${month}-${day}`

    return timestring
}

const cleanData = (data) => {
    // Remove trailing '.'
    if (data.slice(-1) == '.') {
        return data.slice(0, -1)
    } else {
        return data
    }
}

const cleanEntry = (entry) => {
    // clean a record and return it
}

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

const DomainMenu = ({value}) => {
    let history = useHistory()

    return (
        <DropDownCell
            friendly={"domain"}
            value={cleanData(value)}
        >
            <MenuItem
                onClick={() => {history.push(`/whois?query=dn%3A${encodeURIComponent(cleanData(value))}`)}}
            >
                Search WhoIs
            </MenuItem>
        </DropDownCell>

    )
}

const IPMenu = ({value}) => {
    let history = useHistory()

    return (
        <DropDownCell
            friendly={"ip"}
            value={value}
        >
            <MenuItem
                onClick={() => {history.push(`/passive?type=ip&value=${encodeURIComponent(value)}`)}}
            >
                Search Passive
            </MenuItem>
        </DropDownCell>

    )
}

const RRNameCell = ({row}) => {
    return (
        <Grid item xs={12}>
            <DomainMenu row={row} value={row.rrname} />
        </Grid>
    )
}


const RDataCell = ({row}) => {
    return (
        <Grid container>
            {row.rdata.map((value, index) => {
                let data = cleanData(value)
                if (['ns', 'cname', 'mx'].includes(row.rrtype.toLowerCase())) {
                    data = (<DomainMenu row={row} value={data} />)
                } else if (['a', 'aaaa'].includes(row.rrtype.toLowerCase())) {
                    data = (<IPMenu row={row} value={data} />)
                }

                return (
                    <Grid item xs={12} key={index}>
                        {data}
                    </Grid>
                )
            })}
        </Grid>
    )
}

// https://material-ui.com/components/selects/
const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;
const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
      width: 250,
    },
  },
  getContentAnchorEl: null
};

const TableFilter = ({filterItems, onFilter, onClear}) => {
    const RRTypesList = [
        'a',
        'aaaa',
        'cname',
        'mx',
        'ns',
        'ptr',
        'soa',
        'txt',
        // DNSSEC Types
        'ds',
        'rrsig',
        'nsec',
        'dnskey',
        'nsec3',
        'nsec3param',
        'dlv'
    ]

    return (
        <React.Fragment>
            <Select
                label="Types"
                name="rrtypes"
                multiple
                displayEmpty
                onChange={onFilter}
                renderValue = {(selected) => {
                    if (selected.length === 0) {
                        return <em>Type Filter</em>
                    }

                    return selected.join(', ')
                }}
                value={filterItems}
                input={<Input />}
                MenuProps={MenuProps}
            >
                {RRTypesList.map((rrtype, index) => {
                    return (
                    <MenuItem key={index} value={rrtype}>{rrtype}</MenuItem>
                    )
                })}
            </Select>
            <Button type="button" onClick={onClear}>X</Button>
        </React.Fragment>
    )
}

const DNSDBWebHandler = (props) => {
    const [pageSize, setPageSize] = useState(100)
    const [displayData, setDisplayData] = useState([])
    const [displaySlice, setDisplaySlice] = useState([])
    const [resetPaginationToggle, setResetPaginationToggle] = useState(false);
    const [filterItems, setFilterItems] = useState([])

    useEffect(() => {
        if (props.queryResults == null) {
            return
        }

        let data = []
        Object.keys(props.queryResults.results).map((record_type) => {
            if (filterItems.length === 0 || filterItems.includes(record_type.toLowerCase())) {
                props.queryResults.results[record_type].map((entry) => {
                    data.push(entry)
                })
            }

        })

        setDisplayData(data)
        setDisplaySlice(data.slice(0, pageSize))
    }, [props.queryResults, filterItems])

    const columns = [
        {
            name: 'Type',
            selector: 'rrtype',
            maxWidth: '5vw',
            sortable: true
        },
        {
            name: 'RRName',
            selector: 'rrname',
            maxWidth: '20vw',
            cell: (row) => <RRNameCell row={row} />
        },
        {
            name: 'RData',
            selector: 'rdata',
            allowOverflow: true,
            cell: (row) => <RDataCell row={row} />
        },
        {
            name: 'First Seen',
            selector: 'time_first',
            maxWidth: '10vw',
            sortable: true,
            cell: (row) => convertTimestampToDate(row.time_first)
        },
        {
            name: 'Last Seen',
            selector: 'time_last',
            maxWidth: '10vw',
            sortable: true,
            cell: (row) => convertTimestampToDate(row.time_last)
        },
        {
            name: 'Count',
            selector: 'count',
            maxWidth: '10vw',
        },
    ]

    const handlePageChange = async (page) => {
        let start = (page - 1) * pageSize
        let end = start + pageSize
        setDisplaySlice(displayData.slice(start, end))
    }

    const handleChunkChange = async (perPage, page) => {
        setPageSize(perPage)
        let start = (page - 1) * perPage
        let end = start + perPage
        setDisplaySlice(displayData.slice(start, end))
    }

    const subHeaderComponentMemo = React.useMemo(() => {
        const handleClear = () => {
            if (filterItems.length > 0) {
                setResetPaginationToggle(!resetPaginationToggle)
                setFilterItems([])
            }
        }

        return (
            <React.Fragment>
                <TableFilter
                    onFilter={e => setFilterItems(e.target.value)}
                    onClear={handleClear}
                    filterItems={filterItems}
                />
                <SearchTools data={displaySlice} defaultListField={'rrname'} />
            </React.Fragment>

        )
    }, [filterItems, resetPaginationToggle, displaySlice])

    if (props.queryResults === null) {
        return (<BackdropLoader />)
    }

    return (
        <React.Fragment>
            <DataTable
                columns={columns}
                data={displaySlice}
                pagination
                paginationServer
                paginationDefaultPage={1}
                paginationPerPage={pageSize}
                paginationRowsPerPageOptions={[50, 100, 200, 500, 1000]}
                paginationTotalRows={displayData.length}
                paginationResetDefaultPage={resetPaginationToggle}
                subHeader
                subHeaderComponent={subHeaderComponentMemo}
                // subHeaderAlign="right"
                striped
                highlightOnHover
                noHeader
                onChangeRowsPerPage={handleChunkChange}
                onChangePage={handlePageChange}
            />
        </React.Fragment>
    )
}

export default DNSDBWebHandler