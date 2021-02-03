import React from 'react'

import { makeStyles} from '@material-ui/core/styles';
import IconButton from '@material-ui/core/IconButton'
import TablePagination from '@material-ui/core/TablePagination'
import FirstPageIcon from '@material-ui/icons/FirstPage';
import KeyboardArrowLeft from '@material-ui/icons/KeyboardArrowLeft';
import KeyboardArrowRight from '@material-ui/icons/KeyboardArrowRight';
import LastPageIcon from '@material-ui/icons/LastPage';

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

export const Paginator = ({
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

export default Paginator