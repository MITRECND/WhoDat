import React, {useState} from 'react'
import clsx from 'clsx'

import ArrowDropDownIcon from '@material-ui/icons/ArrowDropDown';
import IconButton from '@material-ui/core/IconButton'
import Menu from '@material-ui/core/Menu';
import { makeStyles } from '@material-ui/core';


const useStyles = makeStyles((theme) => ({
    linkCell: {
        cursor: 'pointer'
    },
    buttonRoot: {
        display: 'inline-flex',
        alignItems: 'flex-start',
        flexWrap: 'wrap',
    },
    buttonLabel: {
        width: '100%',
        display: 'inline-flex',
    }
}))

export const DropDownCell = (props) => {
    const classes = useStyles()
    const [anchorEl, setAnchorEl] = useState(null)
    // TODO cleanup implemention and pick one
    const useDropDownIcon = false

    const handleClick = (e) => {
        setAnchorEl(e.currentTarget)
    }

    const handleClose = () => {
        setAnchorEl(null)
    }

    const copyFriendly = props.copyFriendly || false

    if (useDropDownIcon) {
        return (
            <React.Fragment>
                {copyFriendly === false &&
                    <React.Fragment>
                        <IconButton
                            classes={{
                                root: classes.buttonRoot,
                                label: classes.buttonLabel
                            }}
                            aria-controls={`${props.friendly}-menu`}
                            onClick={handleClick}
                            size='small'
                        >
                            <ArrowDropDownIcon />
                        </IconButton>
                        {anchorEl !== null &&
                            <Menu
                                anchorEl={anchorEl}
                                keepMounted
                                open={Boolean(anchorEl)}
                                onClose={handleClose}
                            >
                                {props.children}
                            </Menu>
                        }
                    </React.Fragment>
                }
                {props.value}
            </React.Fragment>

        )
    } else {
        return (
            <React.Fragment>
                <span
                    onClick={handleClick}
                    className={clsx(classes.linkCell, classes.buttonRoot)}
                >
                    {copyFriendly === false &&
                        <ArrowDropDownIcon/>
                    }
                    {props.value}
                </span>
                {anchorEl !== null &&
                    <Menu
                        anchorEl={anchorEl}
                        keepMounted
                        open={Boolean(anchorEl)}
                        onClose={handleClose}
                    >
                        {props.children}
                    </Menu>
                }
            </React.Fragment>
        )
    }
}

export default DropDownCell