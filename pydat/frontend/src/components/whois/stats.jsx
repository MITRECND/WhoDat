import React, {useContext, useEffect, useState} from 'react'
import update from 'immutability-helper'
import Typography from '@material-ui/core/Typography'

import {OptionsContext} from '../layout'
import {FullScreenDialog} from '../layout/dialogs'


const StatsPage = ({open, onClose}) => {
    const optionsContext = useContext(OptionsContext)

    return (
        <React.Fragment>
            <FullScreenDialog
                open={open}
                onClose={onClose}
                title="Whois Stats"
            >
                {open &&
                    <React.Fragment>
                    </React.Fragment>
                }
            </FullScreenDialog>

        </React.Fragment>
    )
}

export default StatsPage