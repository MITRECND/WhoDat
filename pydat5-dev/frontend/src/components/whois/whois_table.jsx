import React, {useState, useEffect, useContext, useMemo, useCallback} from 'react'
import update from 'immutability-helper'
import qs from 'qs'
import {Link as RouterLink} from 'react-router-dom'

import { makeStyles} from '@material-ui/core/styles';
import ArrowDropDownIcon from '@material-ui/icons/ArrowDropDown';
import ArrowRightIcon from '@material-ui/icons/ArrowRight'
import IconButton from '@material-ui/core/IconButton'
import Menu from '@material-ui/core/Menu';
import MenuItem from '@material-ui/core/MenuItem'
import CircularProgress from '@material-ui/core/CircularProgress'
import TableContainer from '@material-ui/core/TableContainer'
import Table from '@material-ui/core/Table'
import TableBody from '@material-ui/core/TableBody'
import TableCell from '@material-ui/core/TableCell'
import TableHead from '@material-ui/core/TableHead'
import TableRow from '@material-ui/core/TableRow'
import TableSortLabel from '@material-ui/core/TableSortLabel'
import TableFooter from '@material-ui/core/TableFooter'
import TablePagination from '@material-ui/core/TablePagination'
import Backdrop from '@material-ui/core/Backdrop'
import FirstPageIcon from '@material-ui/icons/FirstPage';
import KeyboardArrowLeft from '@material-ui/icons/KeyboardArrowLeft';
import KeyboardArrowRight from '@material-ui/icons/KeyboardArrowRight';
import LastPageIcon from '@material-ui/icons/LastPage';


import {
    // useSortBy,
    useExpanded,
    usePagination,
    useTable,
} from 'react-table'

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

const DomainNameCell = ({value: domainName, copyFriendly}) => {
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


const RegistrantCell = ({value: registrant_name, copyFriendly}) => {
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

const EmailCell = ({value: registrant_email, copyFriendly}) => {
    const search_string = createSearchString(`registrant_email:"${registrant_email}"`)

    if (registrant_email === null || registrant_email === "") {
        return (
            <React.Fragment></React.Fragment>
        )
    }

    return (
        <DropDownCell
            friendly={"email"}
            value={registrant_email}
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

const TelephoneCell = ({value: registrant_telephone, copyFriendly}) => {
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
        }
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
        accessor: 'registrant_email',
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
        accessor: 'createdDate',
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

const usePaginationStyles = makeStyles((theme) => ({
    root: {
        flexShrink: 0,
        marginLeft: theme.spacing(2.5),
    }
}))

const TablePaginationActions = ({
    pageCount,
    gotoPage,
    previousPage,
    nextPage,
    canNextPage,
    canPreviousPage,
    // paginationProps,
}) => {

    const classes = usePaginationStyles();

    return (
      <div className={classes.root}>
        <IconButton
          onClick={() => gotoPage(0)}
          disabled={!canPreviousPage}
          aria-label="first page"
        >
            <FirstPageIcon />
        </IconButton>
        <IconButton
            onClick={() => previousPage()}
            disabled={!canPreviousPage}
            aria-label="previous page"
        >
            <KeyboardArrowLeft />
        </IconButton>
        <IconButton
          onClick={() => nextPage()}
          disabled={!canNextPage}
          aria-label="next page"
        >
            <KeyboardArrowRight />
        </IconButton>
        <IconButton
          onClick={() => gotoPage(pageCount - 1)}
          disabled={!canNextPage}
          aria-label="last page"
        >
            <LastPageIcon />
        </IconButton>
      </div>
    );
  }

const Paginator = ({
    gotoPage,
    previousPage,
    nextPage,
    pageCount,
    pageOptions,
    setPageSize,
    pageIndex,
    pageSize,
    canNextPage,
    canPreviousPage,
    columnLength,
}) => {

    const handleChangePage = (event, newPage) => {
        gotoPage(newPage)
      };

    const handleChangeRowsPerPage = (event) => {
        setPageSize(parseInt(event.target.value))
    };

    return (
        <React.Fragment>
            <TablePagination
              rowsPerPageOptions={[50, 100, 1000, 2500]}
              colSpan={columnLength}
              count={-1}
              rowsPerPage={pageSize}
              page={pageIndex}
              SelectProps={{
                inputProps: { 'aria-label': 'rows per page' },
                native: true,
              }}
              onChangePage={handleChangePage}
              onChangeRowsPerPage={handleChangeRowsPerPage}
              ActionsComponent={
                  (props) => (
                    <TablePaginationActions
                        gotoPage={gotoPage}
                        previousPage={previousPage}
                        nextPage={nextPage}
                        pageCount={pageCount}
                        canNextPage={canNextPage}
                        canPreviousPage={canPreviousPage}
                        paginationProps={props}
                    />
                )}
            />
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
    fetchData,
    loading
}) => {

    const preferences = useContext(UserPreferencesContext)
    const initialPageSize = preferences.getPref('whois', 'page_size', 50)
    const [copyFriendly, setCopyFriendly] = useState(false)

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
        state: {pageIndex, pageSize, expanded}
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
        },
        useExpanded,
        // useFlexLayout,
        usePagination,
    )

    useEffect(() => {
        fetchData({pageIndex, pageSize})
    }, [queryData, pageIndex, pageSize])

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
                                <SearchTools data={data} defaultListField={'domainName'}>
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
                                pageOptions={pageOptions}
                                setPageSize={setPageSize}
                                pageIndex={pageIndex}
                                pageSize={pageSize}
                                canNextPage={canNextPage}
                                canPreviousPage={canPreviousPage}
                                columnLength={visibleColumns.length - 1}
                            />
                        </TableRow>
                        {headerGroups.map(headerGroup => (
                            <TableRow {...headerGroup.getHeaderGroupProps()}>
                                {headerGroup.headers.map(column => (
                                    <TableCell {...column.getHeaderProps()}>
                                        {column.render('Header')}
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
                                pageOptions={pageOptions}
                                setPageSize={setPageSize}
                                pageIndex={pageIndex}
                                pageSize={pageSize}
                                canNextPage={canNextPage}
                                canPreviousPage={canPreviousPage}
                                columnLength={visibleColumns.length}
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
    const [pageCount, setPageCount] = useState(0)

    const fetchData = useCallback(({pageSize, pageIndex}) => {
        const asyncfetch = async () => {
            try {
                let results = await queryFetcher({
                    query: queryData.query,
                    chunk_size: pageSize,
                    offset: pageIndex
                })

                setPageCount(Math.ceil(results.total / pageSize))
                setData(results.results)
                setPending(false)

            } catch (err) {
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
            pageCount={pageCount}
        />

    )
}

export default WhoisTable