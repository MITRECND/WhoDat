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


import { BackdropLoader } from '../../helpers/loaders'

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

const RDataCell = ({row}) => {
    return (
        <Grid container>
            {row.rdata.map((value, index) => (
                <Grid item xs={12} key={index}>
                    {cleanData(value)}
                </Grid>
            ))}
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
    const [displayData, setDisplayData] = useState([])
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
            cell: (row) => cleanData(row.rrname)
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

    const subHeaderComponentMemo = React.useMemo(() => {
        const handleClear = () => {
            if (filterItems.length > 0) {
                setResetPaginationToggle(!resetPaginationToggle)
                setFilterItems([])
            }
        }

        return (
            <TableFilter
                onFilter={e => setFilterItems(e.target.value)}
                onClear={handleClear}
                filterItems={filterItems}
            />
        )
    }, [filterItems, resetPaginationToggle])

    if (props.queryResults === null) {
        return (<BackdropLoader />)
    }

    return (
        <React.Fragment>
            <DataTable
                columns={columns}
                data={displayData}
                // fixedHeader
                pagination
                paginationResetDefaultPage={resetPaginationToggle}
                subHeader
                subHeaderComponent={subHeaderComponentMemo}
                striped
                highlightOnHover
            />
        </React.Fragment>
    )
}

export default DNSDBWebHandler