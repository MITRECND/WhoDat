import {createMuiTheme} from '@material-ui/core/styles'

const _color_palette = {
    primary: {
        main: '#212121'
    },
    secondary: {
        main: '#0288d1'
    },
}

const _defaultTheme = {
    palette: {
        ..._color_palette
    }
}

const _darkTheme = {
    palette: {
        type: 'dark',
        ..._color_palette
    }
}


export const defaultTheme = createMuiTheme(_defaultTheme)
export const darkTheme = createMuiTheme(_darkTheme)