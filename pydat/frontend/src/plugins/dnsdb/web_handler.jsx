import React, {useState, useEffect, useMemo, useCallback} from 'react'

import { makeStyles} from '@material-ui/core/styles';
import Typography from '@material-ui/core/Typography'
import FormControl from '@material-ui/core/FormControl'
import Menu from '@material-ui/core/Menu';
import MenuItem from '@material-ui/core/MenuItem'
import Grid from '@material-ui/core/Grid'
import Button from '@material-ui/core/Button';
import Input from '@material-ui/core/Input'
import Select from '@material-ui/core/Select'
import Table from '@material-ui/core/Table'
import TableBody from '@material-ui/core/TableBody'
import TableCell from '@material-ui/core/TableCell'
import TableHead from '@material-ui/core/TableHead'
import TableRow from '@material-ui/core/TableRow'
import TableSortLabel from '@material-ui/core/TableSortLabel'
import TableFooter from '@material-ui/core/TableFooter'

import {
    useSortBy,
    useFilters,
    usePagination,
    useTable,
} from 'react-table'

import SearchTools from '../../components/helpers/search_tools'
import { BackdropLoader } from '../../components/helpers/loaders'
import {Paginator} from './table_pagination'
import {
    RRNameCell,
    RDataCell
} from './table_cells'
import { InputLabel } from '@material-ui/core';
import { useUserPreferences } from '../../components/helpers/preferences';

const convertTimestampToDate = (timestamp) => {
    let date = new Date(timestamp * 1000)
    let year = date.getUTCFullYear()
    let month = `0${date.getUTCMonth() + 1}`.slice(-2)
    let day = `0${date.getUTCDate() + 1}`.slice(-2)
    let hours = `0${date.getUTCHours()}`.slice(-2)
    let minutes = `0${date.getUTCMinutes()}`.slice(-2)
    let seconds = `0${date.getUTCSeconds()}`.slice(-2)

    let timestring = `${year}-${month}-${day} ${hours}:${minutes}:${seconds} UTC`

    return timestring
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

const useTypeFilterStyles = makeStyles((theme) => ({
    formControl: {
      margin: theme.spacing(1),
      minWidth: 120,
    },
    selectEmpty: {
      marginTop: theme.spacing(2),
    },
  }));

const TypeColumnFilter = ({
    column: {filterValue, setFilter, preFilteredRows, id}
}) => {

    const classes = useTypeFilterStyles()
    // TODO XXX Validate RRTypes?
    // const RRTypesList = [
    //     'a',
    //     'aaaa',
    //     'cname',
    //     'mx',
    //     'ns',
    //     'ptr',
    //     'soa',
    //     'txt',
    //     // DNSSEC Types
    //     'ds',
    //     'rrsig',
    //     'nsec',
    //     'dnskey',
    //     'nsec3',
    //     'nsec3param',
    //     'dlv'
    // ]

    const RRTypesList = useMemo(() => {
        let tl = new Set()
        preFilteredRows.forEach((row) => {
            tl.add(row.original.rrtype.toLowerCase())
        })
        return Array.from(tl)
    }, [preFilteredRows])

    return (
        <React.Fragment>
            <FormControl className={classes.formControl}>
                <InputLabel>Filter</InputLabel>
                <Select
                    label="Types"
                    name="rrtypes"
                    // multiple
                    displayEmpty
                    onChange={e => {setFilter(e.target.value || undefined)}}
                    // renderValue = {(selected) => {
                    //     if (selected.length === 0) {
                    //         return <em>Type Filter</em>
                    //     }

                    //     return selected.join(', ')
                    // }}
                    value={filterValue || ''}
                    input={<Input />}
                    MenuProps={MenuProps}
                >
                    <MenuItem value="">&nbsp;</MenuItem>
                    {RRTypesList.map((rrtype, index) => {
                        return (
                        <MenuItem key={index} value={rrtype}>{rrtype}</MenuItem>
                        )
                    })}
                </Select>
            </FormControl>
            {/* <Button type="button" onClick={e => {setFilter(undefined)}}>X</Button> */}
        </React.Fragment>
    )
}

const typeColumnFilterFn = (rows, columnIds, filterValue) => {
    let postFiltered = []

    rows.forEach((row) => {
        if (row.original.rrtype.toLowerCase() == filterValue){
            postFiltered.push(row)
        }
    })

    return postFiltered
}

const ToggleCopyMenuItem = ({copyFriendly, toggleCopyFriendly, handleClose}) => {
    return (
        <MenuItem
            selected={copyFriendly}
            onClick={() => {toggleCopyFriendly(); handleClose()}}
        >
            Copy Friendly
        </MenuItem>
    )
}

const csvPreprocessor = (data) => {
    let dataout = []
    data.forEach((row) => {
        let newrow = {...row}
        if (newrow.hasOwnProperty('rdata') && Array.isArray(newrow.rdata)) {
            newrow.rdata = newrow.rdata.join(';')
        }
        dataout.push(newrow)
    })
    return dataout
}

const ExportDataControl = ({
    exportSize,
    setExportSize,
    validPageSizes = [50, 100, 1000, 2500]
}) => {
    return (
        <React.Fragment>
            <Grid container spacing={2} style={{padding: '1rem'}}>
                <Grid item>
                    <FormControl>
                        <InputLabel>Size</InputLabel>
                        <Select
                            label="Size"
                            name="size"
                            displayEmpty
                            onChange={e => {setExportSize(e.target.value)}}
                            value={exportSize}
                        >
                        {validPageSizes.map((value, index) => (
                            <MenuItem key={index} value={value}>{value}</MenuItem>
                        ))}
                        </Select>
                    </FormControl>
                </Grid>
            </Grid>
        </React.Fragment>
    )
}

const DNSDBTableContainer = ({
    columns,
    data,
    rateInfo
}) => {
    const preferences = useUserPreferences('dnsdb')
    const initialPageSize = preferences.getPref("remember_page_size") ? preferences.getPref('page_size') : 100
    const validPageSizes = [50, 100, 500, 1000, 2500]
    const [copyFriendly, setCopyFriendly] = useState(false)

    const toggleCopyFriendly = useCallback(() => {
        setCopyFriendly(!copyFriendly)
    })

    const {
        getTableProps,
        getTableBodyProps,
        headerGroups,
        prepareRow,
        allColumns,
        visibleColumns,
        rows: filteredRows,
        // Pagination
        page,
        canPreviousPage,
        canNextPage,
        pageOptions,
        pageCount,
        gotoPage,
        nextPage,
        previousPage,
        setPageSize,
        state: {pageIndex, pageSize}
    } = useTable(
        {
            columns,
            data,
            initialState: {
                pageSize: initialPageSize,
                pageIndex: 0
            },
        },
        useFilters,
        useSortBy,
        usePagination,
    )

    const filteredData = useMemo(() => {
        let data = []
        filteredRows.forEach((row) => {
            data.push(row.original)
        })
        return data
    }, [filteredRows])

    const [exportSize, setExportSize] = useState(50)
    const exporterData = useMemo(
        () => (
            filteredData.slice(0, exportSize)
        ),[exportSize]
    )

    return (
        <React.Fragment>
            <div
                // onKeyDown={handleKeyPressEvent}
                // tabIndex={-1}
            >
                <Table {...getTableProps()}>
                    <TableHead>
                        <TableRow>
                            <TableCell
                                colSpan={2}
                                padding='none'
                            >
                                {allColumns[0].render("Filter")}
                            </TableCell>
                            <TableCell
                                colSpan={visibleColumns.length - 2}
                                align='right'

                            >
                                <Typography>
                                    Rate Limit: {rateInfo.remaining}/{rateInfo.limit}
                                </Typography>
                            </TableCell>
                        </TableRow>
                        <TableRow>
                            <TableCell colSpan={1}>
                                <SearchTools
                                    data={exporterData}
                                    dataControl={
                                        <ExportDataControl
                                            exportSize={exportSize}
                                            setExportSize={setExportSize}
                                            validPageSizes={validPageSizes}
                                        />
                                    }
                                    defaultListField={'rrname'}
                                    csvPreprocessor={csvPreprocessor}
                                >
                                    <ToggleCopyMenuItem
                                        copyFriendly={copyFriendly}
                                        toggleCopyFriendly={toggleCopyFriendly}
                                    />
                                </SearchTools>
                            </TableCell>
                            <Paginator
                                gotoPage={gotoPage}
                                previousPage={previousPage}
                                nextPage={nextPage}
                                pageCount={pageCount}
                                rowCount={filteredRows.length}
                                pageOptions={pageOptions}
                                setPageSize={setPageSize}
                                pageIndex={pageIndex}
                                pageSize={pageSize}
                                canNextPage={canNextPage}
                                canPreviousPage={canPreviousPage}
                                columnLength={visibleColumns.length - 1}
                                validPageSizes={validPageSizes}
                            />
                        </TableRow>
                        {headerGroups.map(headerGroup => (
                            <TableRow {...headerGroup.getHeaderGroupProps()}>
                                {headerGroup.headers.map(column => (
                                    <TableCell {
                                        ...column.getHeaderProps(
                                            column.getSortByToggleProps())
                                    }>
                                        {column.canSort
                                        ?
                                            <TableSortLabel
                                                active={column.isSorted}
                                                direction={
                                                    column.isSortedDesc
                                                    ?
                                                        'desc'
                                                    :
                                                        'asc'
                                                }
                                                hideSortIcon={column.isSorted}
                                            >
                                                {column.render('Header')}
                                            </TableSortLabel>
                                        :
                                            column.render('Header')
                                        }
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))}
                    </TableHead>
                    <TableBody {...getTableBodyProps()}>
                        {page.map((row, i) => {
                            prepareRow(row)
                            return (
                                <TableRow {...row.getRowProps([{key: `data${i}`}])}>
                                    {row.cells.map(cell => {
                                        return (
                                            <TableCell {...cell.getCellProps([
                                                {
                                                    className: cell.column.className,
                                                    style: cell.column.style
                                                }

                                            ])}>
                                                {cell.render('Cell',
                                                    {copyFriendly: copyFriendly})}
                                            </TableCell>
                                        )
                                    })}
                                </TableRow>
                            )
                        })}
                    </TableBody>
                    <TableFooter>
                        <TableRow>
                            <Paginator
                                gotoPage={gotoPage}
                                previousPage={previousPage}
                                nextPage={nextPage}
                                pageCount={pageCount}
                                rowCount={filteredRows.length}
                                pageOptions={pageOptions}
                                setPageSize={setPageSize}
                                pageIndex={pageIndex}
                                pageSize={pageSize}
                                canNextPage={canNextPage}
                                canPreviousPage={canPreviousPage}
                                columnLength={visibleColumns.length}
                                validPageSizes={validPageSizes}
                            />
                        </TableRow>
                    </TableFooter>
                </Table>
            </div>
        </React.Fragment>
    )
}

const DNSDBWebHandler = (props) => {
    const data = useMemo(
        () => {
            if (props.queryResults == null) {
                return null
            }

            let data_out = []
            Object.keys(props.queryResults.results).forEach((record_type) => {
                props.queryResults.results[record_type].forEach((entry) => {
                    data_out.push(entry)
                })
            })

            return data_out
        },
        [props.queryResults]
    )

    const columns = useMemo(() => ([
        {
            Header: 'Type',
            accessor: 'rrtype',
            maxWidth: '5vw',
            disableSortBy: true,
            Filter: TypeColumnFilter,
            filter: typeColumnFilterFn,
            className: 'rrtype-cell',
            style: {}
        },
        {
            Header: 'RRName',
            accessor: 'rrname',
            maxWidth: '20vw',
            Cell: (props) => (
                <RRNameCell
                    row={props.row.original}
                    copyFriendly={props.copyFriendly}
                />
            ),
            className: 'rrname-cell',
            style: {}
        },
        {
            Header: 'RData',
            accessor: 'rdata',
            allowOverflow: true,
            Cell: (props) => (
                <RDataCell
                    row={props.row.original}
                    copyFriendly={props.copyFriendly}
                />
            ),
            className: 'rdata-cell',
            style: {}
        },
        {
            Header: 'First Seen',
            accessor: 'time_first',
            maxWidth: '10vw',
            Cell: (props) => (
                convertTimestampToDate(props.value)
            ),
            className: 'fs-cell',
            style: {}
        },
        {
            Header: 'Last Seen',
            accessor: 'time_last',
            maxWidth: '10vw',
            Cell: (props) => (
                convertTimestampToDate(props.value)
            ),
            className: 'ls-cell',
            style: {}
        },
        {
            Header: 'Count',
            accessor: 'count',
            maxWidth: '10vw',
            canFilter: false,
            disableSortBy: true,
            className: 'cnt-cell',
            style: {}
        },
    ]))


    if (props.queryResults === null) {
        return (<BackdropLoader />)
    }

    return (
        <React.Fragment>
            <DNSDBTableContainer
                columns={columns}
                data={data}
                rateInfo={props.queryResults.rate}
            />

        </React.Fragment>
    )
}

export default DNSDBWebHandler