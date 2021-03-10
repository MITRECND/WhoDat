import React, {createContext, useState} from 'react'
import {Link as RouterLink, matchPath} from 'react-router-dom'

import MenuItem from '@material-ui/core/MenuItem'
import Link from '@material-ui/core/Link'
import IconButton from '@material-ui/core/IconButton'
import Tooltip from '@material-ui/core/Tooltip'


const DesktopOption = ({
    icon,
    optionsContext,
    handleClick = null,
    childComponent = null,
    tooltip = null,
}) => {
    const [anchorEl, setAnchorEl] = useState(null)
    const [open, setOpen] = useState(false)
    const onClose = () => {
        setAnchorEl(null)
        setOpen(false)
    }

    let iconProps = {}
    if (handleClick !== null) {
        iconProps.onClick = (e) => {
            setAnchorEl(e.currentTarget)
            handleClick({
                optionsContext: optionsContext
            })
        }
    }

    if (childComponent !== null) {
        iconProps.onClick = () => {
            setOpen(true)
        }
    }

    const button = (
        <React.Fragment>
            <IconButton
                color="inherit"
                {...iconProps}
            >
                {icon}
            </IconButton>
            {childComponent && (
                React.cloneElement(childComponent, {
                    open: open,
                    onClose: onClose,
                    anchorEl: anchorEl
                }))
            }
        </React.Fragment>
    )

    if (tooltip !== null) {
        return (
            <Tooltip title={tooltip} placement="bottom">
                {button}
            </Tooltip>
        )
    } else {
        return button
    }
}

const MobileOption = ({
    icon,
    text,
    optionsContext,
    handleClick = null,
    childComponent = null,
}) => {
    return (
        <span
            onClick={() => {
                handleClick({
                    optionsContext
                })
            }}
        >
            <IconButton color="inherit">
                {icon}
            </IconButton>
            {text}
        </span>
    )
}
export class OptionElement {
    constructor({
        icon,
        text,
        handleClick = null,
        tooltip=null,
        childComponent=null
    }) {
        this.icon = icon
        this.text = text
        this.handleClick = handleClick
        this.tooltip = tooltip
        this.childComponent = childComponent

        if (childComponent !== null) {
            if (!(React.isValidElement(childComponent))) {
                throw TypeError("childComponent must be a valid React Component")
            }
        }
    }

    getDesktopElement({optionsContext, index = null}) {
        return (
            <DesktopOption
                key={index}
                icon={this.icon}
                handleClick={this.handleClick}
                childComponent={this.childComponent}
                optionsContext={optionsContext}
            />
        )
    }

    getMobileElement({optionsContext, index = null}) {
        return (
            <MobileOption
                key={index}
                icon={this.icon}
                text={this.text}
                handleClick={this.handleClick}
                childComponent={this.childComponent}
                optionsContext={optionsContext}
            />
        )

    }

}
export class RouteElement {
    constructor({path, title, component, extra = {}, options = []}) {
        this.path = path
        this.title = title
        this.component = component
        this.extra = extra
        this.options = options
    }

    matchRoute(current_path) {
        return matchPath(current_path,
            {
                path: this.path,
                exact: true
            })
    }
}

export class NavigationElement {
    constructor ({title, path, text = null}) {
        this.title = title
        this.path = path
        this.text = text
    }
}

export class MenuElement {
    constructor ({path, text, external = false}) {
        this.path = path
        this.text = text
        this.external = external
    }

    getComponent(data, key = null) {
        let link_props

        //https://stackoverflow.com/questions/5999998/check-if-a-variable-is-of-function-type
        let cpath = this.path
        if (this.path && {}.toString.call(this.path) === '[object Function]'){
            cpath = this.path(data)
        }

        if (this.external) {
            link_props = {
                component: Link,
                href: cpath,
                target: "_blank",
                rel: "noreferrer"
            }
        } else {
            link_props = {
                component: RouterLink,
                to: cpath,
            }
        }

        return (
            <MenuItem {...link_props} key={key}>
                {this.text}
            </MenuItem>
        )
    }
}

export const OptionsContext = createContext()