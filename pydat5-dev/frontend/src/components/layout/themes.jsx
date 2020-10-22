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

const _darkTheme = {
    palette: {
        type: 'dark'
    }
}


export const defaultTheme = createMuiTheme(_defaultTheme)
export const darkTheme = createMuiTheme(_darkTheme)