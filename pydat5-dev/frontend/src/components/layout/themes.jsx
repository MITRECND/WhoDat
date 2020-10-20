import {createMuiTheme} from '@material-ui/core/styles'

const _defaultTheme = {
    palette: {
        primary: {
            main: '#212121'
        },
        secondary: {
            main: '#0288d1'
        },
    }
}

export const defaultTheme = createMuiTheme(_defaultTheme)