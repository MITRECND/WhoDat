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

const MenuDialogWrapper = (props) => {
    const [open, setOpen] = useState(false)

    const onClose = () => {
        setOpen(false)
    }

    const handleOnClick = (e) => {
        e.preventDefault()
        setOpen(true)
    }

    let menuProps = {...props}
    delete menuProps.dialogProps

    return (
        <React.Fragment>
            <MenuItem {...menuProps} onClick={handleOnClick}>
                {props.dialogProps.text}
            </MenuItem>
            {open &&
                React.cloneElement(props.dialogProps.RenderComponent, {
                    data: props.dialogProps.data,
                    open: open,
                    onClose: onClose,
            })}
        </React.Fragment>
    )
}

export class MenuElement {
    constructor ({
            text,
            path = null,
            RenderComponent = null,
            external = false
    }) {
        this.text = text
        this.RenderComponent = RenderComponent
        this.path = path
        this.external = external
        this._getLinkComponent.bind(this)
        this._getDialogComponent.bind(this)
        this.getComponent.bind(this)

        if (RenderComponent === null && path === null){
            throw TypeError("Either 'path' or 'RenderComponent' must be defined")
        }

        if (RenderComponent !== null && !React.isValidElement(RenderComponent)) {
            throw TypeError("RenderComponent must be a valid React element")
        }
    }

    _getLinkComponent(data, key = null) {
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

    _getDialogComponent(data, key = null) {
        return (
            <MenuDialogWrapper
                dialogProps={{
                    text: this.text,
                    RenderComponent: this.RenderComponent,
                    data: data
                }}
                key={key}
            />
        )
    }

    getComponent(data, key = null) {
        if (this.path !== null) {
            return this._getLinkComponent(data, key)
        } else {
            return this._getDialogComponent(data, key)
        }

    }
}

export const OptionsContext = createContext()