import React, {useState} from 'react'

import IconButton from '@material-ui/core/IconButton'
import Menu from '@material-ui/core/Menu';
import MenuItem from '@material-ui/core/MenuItem'
import BuildIcon from '@material-ui/icons/Build';

import {
    JSONExporter,
    CSVExporter,
    ListExporter
} from './data_exporters'

export const SearchTools = ({data, children, defaultListField}) => {
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
                    field={defaultListField}
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

export default SearchTools