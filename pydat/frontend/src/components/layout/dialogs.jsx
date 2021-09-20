import React, {useState} from 'react';
import { makeStyles } from '@material-ui/core/styles';
import Dialog from '@material-ui/core/Dialog';
import AppBar from '@material-ui/core/AppBar';
import Toolbar from '@material-ui/core/Toolbar';
import IconButton from '@material-ui/core/IconButton';
import Typography from '@material-ui/core/Typography';
import CloseIcon from '@material-ui/icons/Close';
import Slide from '@material-ui/core/Slide';
import InputAdornment from '@material-ui/core/InputAdornment'
import SettingsIcon from '@material-ui/icons/Settings';
import Container from '@material-ui/core/Container'

// https://material-ui.com/components/dialogs/#full-screen-dialogs

const useStyles = makeStyles((theme) => ({
  appBar: {
    position: 'relative',
  },
  title: {
    marginLeft: theme.spacing(2),
    flex: 1,
  },
  regularDialog: {
      marginTop: '1rem',
      minHeight: '5vh'
  }
}));

// const Transition = React.forwardRef(function Transition(props, ref) {
//   return <Slide direction="up" ref={ref} {...props} />;
// });

export const FullScreenDialog = ({open, onClose, title, children}) => {
  const classes = useStyles();

  const handleClose = () => {
    onClose()
  };

  return (
    <React.Fragment>
        <Dialog
            fullScreen
            open={open}
            onClose={handleClose}
            maxWidth="xl"
            fullWidth
        >
            <AppBar className={classes.appBar}>
                <Toolbar variant="dense">
                    <IconButton edge="start" color="inherit" onClick={handleClose} aria-label="close">
                        <CloseIcon />
                    </IconButton>
                    <Typography variant="h6" className={classes.title}>
                        {title}
                    </Typography>
                </Toolbar>
            </AppBar>
            <Container>
                {children}
            </Container>
        </Dialog>
    </React.Fragment>
  );
}

export const RegularDialog = ({open, onClose, title, children}) => {
    const classes = useStyles();

    const handleClose = () => {
      onClose()
    };

    return (
      <React.Fragment>
          <Dialog
              open={open}
              onClose={handleClose}
              maxWidth="md"
              fullWidth
          >
              <AppBar className={classes.appBar}>
                  <Toolbar variant="dense">
                      <IconButton edge="start" color="inherit" onClick={handleClose} aria-label="close">
                          <CloseIcon />
                      </IconButton>
                      <Typography variant="h6" className={classes.title}>
                          {title}
                      </Typography>
                  </Toolbar>
              </AppBar>
              <Container className={classes.regularDialog}>
                  {children}
              </Container>
          </Dialog>
      </React.Fragment>
    );
  }


export const SearchSettings = (props) => {
  const [open, setOpen] = useState(false)

  const handleClick = (e) => {
      e.preventDefault()
      setOpen(true)
  }

  const handleMouseDown = (e) => {
      e.preventDefault()
  }

  const handleClose = () => {
      setOpen(false)
  }

  return (
      <React.Fragment>
          <InputAdornment
              position="end">
              <IconButton
                  onClick={handleClick}
                  onMouseDown={handleMouseDown}
                  edge="end"
              >
                  <SettingsIcon />
              </IconButton>
          </InputAdornment>
          <Dialog
              onClose={handleClose}
              aria-labelledby="options-dialog-title"
              open={open}
              maxWidth="md"
              fullWidth
          >
              <AppBar style={{position: "relative"}} >
                  <Toolbar variant="dense">
                      <IconButton edge="start" color="inherit" onClick={handleClose} aria-label="close">
                          <CloseIcon />
                      </IconButton>
                      <Typography variant="h6">
                          {props.title}
                      </Typography>
                  </Toolbar>
              </AppBar>
              <Container>
                  {props.children}
              </Container>

          </Dialog>
      </React.Fragment>
  )
}