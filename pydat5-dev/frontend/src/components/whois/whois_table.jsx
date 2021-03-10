import React, {useState, useEffect, useContext, useMemo, useCallback} from 'react'

import ArrowDropDownIcon from '@material-ui/icons/ArrowDropDown';
import ArrowRightIcon from '@material-ui/icons/ArrowRight'
import MenuItem from '@material-ui/core/MenuItem'
import TableContainer from '@material-ui/core/TableContainer'
import Table from '@material-ui/core/Table'
import TableBody from '@material-ui/core/TableBody'
import TableCell from '@material-ui/core/TableCell'
import TableHead from '@material-ui/core/TableHead'
import TableRow from '@material-ui/core/TableRow'
import TableSortLabel from '@material-ui/core/TableSortLabel'
import TableFooter from '@material-ui/core/TableFooter'
import Grid from '@material-ui/core/Grid'
import FormControl from '@material-ui/core/FormControl'
import InputLabel from '@material-ui/core/InputLabel'
import Select from '@material-ui/core/Select'

import {
    useSortBy,
    useExpanded,
    usePagination,
    useTable,
} from 'react-table'

import {useSnackbar} from 'notistack'

import {queryFetcher} from '../helpers/fetchers'
import ExpandedEntryRow from './expandable'
import {useUserPreferences} from '../helpers/preferences'
import { BackdropLoader } from '../helpers/loaders';
import SearchTools from '../helpers/search_tools'
import {Paginator} from './table_pagination'
import {
    DomainNameCell,
    RegistrantCell,
    EmailCell,
    TelephoneCell
} from './table_cells'


const TableColumns = () => { return [
    {
        Header: () => null,
        id: 'moreinfo',
        Cell: ({row, copyFriendly}) => (
            copyFriendly === false ?
                <span {...row.getToggleRowExpandedProps()}>
                    {row.isExpanded ? <ArrowDropDownIcon/> : <ArrowRightIcon/>}
                </span>
            : null
        ),
        className: 'expansion-cell',
        style: {
            padding: 'none'
        },
        disableSortBy: true,
        defaultCanSort: false,
    },
    {
        Header: 'Domain Name',
        accessor: 'domainName',
        Cell: (props) => (
            <DomainNameCell
                value={props.value}
                copyFriendly={props.copyFriendly}
            />
        ),
        className: 'dn-cell',
        style: {}
    },
    {
        Header: 'Registrant',
        accessor: 'registrant_name',
        Cell: (props) => (
            <RegistrantCell
                value={props.value}
                copyFriendly={props.copyFriendly}
            />
        ),
        className: 'rn-cell',
        style: {}
    },
    {
        Header: 'Email',
        accessor: 'contactEmail',
        Cell: (props) => (
            <EmailCell
                value={props.value}
                copyFriendly={props.copyFriendly}
            />
        ),
        className: 're-cell',
        style: {}
    },
    {
        Header: 'Created',
        accessor: 'standardRegCreatedDate',
        className: 'cd-cell',
        style: {}
    },
    {
        Header: 'Telephone',
        accessor: 'registrant_telephone',
        Cell: (props) => (
            <TelephoneCell
                value={props.value}
                copyFriendly={props.copyFriendly}
            />
        ),
        className: 'rt-cell',
        style: {}
    },
    {
        Header: 'Version',
        accessor: 'Version',
        className: 'version-cell',
        style: {
            maxWidth: "5vh",
        }
    },
    {
        Header: 'Score',
        accessor: 'score',
        Cell: ({value}) => value.toFixed(3),
        className: 'score-cell',
        style: {
            maxWidth: "10vh",
        }
    }
]}

const ExportDataControl = ({
    pageSize,
    setPageSize,
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
                            onChange={e => {setPageSize(e.target.value)}}
                            value={pageSize}
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

const WhoisTableContainer = ({
    columns,
    data,
    queryData,
    pageCount: controlledPageCount,
    totalRecords,
    fetchData,
    loading
}) => {

    const preferences = useUserPreferences('whois')
    const initialPageSize = preferences.getPref("remember_page_size") ? preferences.getPref('page_size') : 100
    const [copyFriendly, setCopyFriendly] = useState(false)
    const validPageSizes = [50, 100, 1000, 2500]

    const toggleCopyFriendly = useCallback(() => {
        setCopyFriendly(!copyFriendly)
    })

    // const handleKeyPressEvent = (event) => {
    //     console.log(event.keyCode)
    //     if (event.keyCode === 67 ) {
    //         toggleCopyFriendly()
    //     }
    // }

    const {
        getTableProps,
        getTableBodyProps,
        headerGroups,
        prepareRow,
        visibleColumns,
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
        state: {pageIndex, pageSize, sortBy},
    } = useTable(
        {
            columns,
            data,
            initialState: {
                pageSize: initialPageSize,
                pageIndex: 0
            },
            manualPagination: true,
            pageCount: controlledPageCount,
            manualSortBy: true,
        },
        useSortBy,
        useExpanded,
        usePagination,
    )

    useEffect(() => {
        fetchData({pageIndex, pageSize, sortBy})
    }, [queryData, pageIndex, pageSize, sortBy])


    if (!Array.isArray(data) || !data.length) {
        return (
            <BackdropLoader/>
        )
    }

    return (
        <React.Fragment>
            <div
                // onKeyDown={handleKeyPressEvent}
                // tabIndex={-1}
            >
                <Table {...getTableProps()}>
                    <TableHead>
                        <TableRow>
                            <TableCell colSpan={1}>
                                <SearchTools
                                    data={data}
                                    defaultListField={'domainName'}
                                    dataControl={
                                        <ExportDataControl
                                            pageSize={pageSize}
                                            setPageSize={setPageSize}
                                            validPageSizes={validPageSizes}
                                        />
                                    }
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
                                totalRecords={totalRecords}
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
                        {loading ?
                        <TableRow>
                            <TableCell colSpan={visibleColumns.length}>
                                &nbsp;
                            </TableCell>
                        </TableRow>
                        :
                        page.map((row, i) => {
                            prepareRow(row)
                            return (
                                <React.Fragment key={i}>
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
                                    {row.isExpanded ? (
                                        <TableRow {...row.getRowProps([{key: `ex${i}`}])}>
                                            <TableCell colSpan={visibleColumns.length}>
                                                <ExpandedEntryRow data={row.original}/>
                                            </TableCell>
                                        </TableRow>
                                    ): null}

                                </React.Fragment>
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
                                totalRecords={totalRecords}
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

const WhoisTable = ({queryData}) => {
    const [pending, setPending] = useState(true)

    const columns = useMemo(() => TableColumns(), [])
    const [data, setData] = useState([])
    const [resultMeta, setResultMeta] = useState({
        page_count: 0,
        total_records: 0
    })
    const {enqueueSnackbar} = useSnackbar()

    const fetchData = useCallback(({pageSize, pageIndex, sortBy=[]}) => {
        const asyncfetch = async () => {
            let sort_keys = []
            sortBy.forEach((sortData) => {
                let direction = "asc"
                if (sortData.desc) {
                    direction = "desc"
                }
                sort_keys.push({
                    name: sortData.id,
                    dir: direction
                })
            })

            try {
                let results = await queryFetcher({
                    query: queryData.query,
                    chunk_size: pageSize,
                    offset: pageIndex,
                    sort_keys: sort_keys
                })

                setResultMeta({
                    page_count: Math.ceil(results.total / pageSize),
                    total_records: results.total
                })
                setData(results.results)
                setPending(false)

            } catch (err) {
                enqueueSnackbar("Unable to fetch data from backend", {variant: 'error'})
                console.log(err)
            }
        }

        setPending(true)
        asyncfetch()
    })

    return (
        <WhoisTableContainer
            columns={columns}
            queryData={queryData}
            data={data}
            fetchData={fetchData}
            loading={pending}
            pageCount={resultMeta.page_count}
            totalRecords={resultMeta.total_records}
        />

    )
}

export default WhoisTable