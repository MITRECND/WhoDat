import React from 'react'
import {Link as RouterLink, useRouteMatch} from 'react-router-dom'

import MenuItem from '@material-ui/core/MenuItem'
import Link from '@material-ui/core/Link'
import IconButton from '@material-ui/core/IconButton'
import Tooltip from '@material-ui/core/Tooltip'

export class OptionElement {
    constructor({icon, text, handleClick, tooltip=null}) {
        this.icon = icon
        this.text = text
        this.handleClick = handleClick
        this.tooltip = tooltip
    }

    getDesktopElement(index = null) {
        const button = (
            <IconButton
                key={index}
                onClick={this.handleClick}
                color="inherit"
            >
                {this.icon}
            </IconButton>
        )

        if (this.tooltip !== null) {
            return (
                <Tooltip title={this.tooltip} placement="bottom">
                    {button}
                </Tooltip>
            )
        } else {
            return button
        }
    }

    getMobileElement(index = null) {
        return (
            <MenuItem
                key={index}
                onClick={this.handleClick}
            >
                <IconButton color="inherit">
                    {this.icon}
                </IconButton>
                {this.text}
            </MenuItem>
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

    matchRoute() {
        return useRouteMatch({path: this.path, exact: true})
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