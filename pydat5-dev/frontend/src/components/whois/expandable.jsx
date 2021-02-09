import React, {useState, useEffect} from 'react'


import Paper from '@material-ui/core/Paper'
import Tab from '@material-ui/core/Tab'
import Tabs from '@material-ui/core/Tabs'
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import Grid from '@material-ui/core/Grid'
import Dialog from '@material-ui/core/Dialog';
import DialogContent from '@material-ui/core/DialogContent';
import Button from '@material-ui/core/Button'
import IconButton from '@material-ui/core/IconButton';
import CloseIcon from '@material-ui/icons/Close';
import MuiDialogTitle from '@material-ui/core/DialogTitle';
import { withStyles } from '@material-ui/core/styles';
import Typography from '@material-ui/core/Typography';
import { Container, makeStyles } from '@material-ui/core'


import {domainFetcher} from '../helpers/fetchers'
import clsx from 'clsx';

const detailsDialogStyles = (theme) => ({
    root: {
      margin: 0,
      padding: theme.spacing(2),
    },
    closeButton: {
      position: 'absolute',
      right: theme.spacing(1),
      top: theme.spacing(1),
      color: theme.palette.grey[500],
    },
});

const DialogTitle = withStyles(detailsDialogStyles)((props) => {
    const { children, classes, onClose, ...other } = props;
    return (
      <MuiDialogTitle disableTypography className={classes.root} {...other}>
        <Typography variant="h6">{children}</Typography>
        {onClose ? (
          <IconButton aria-label="close" className={classes.closeButton} onClick={onClose}>
            <CloseIcon />
          </IconButton>
        ) : null}
      </MuiDialogTitle>
    );
  });

const FullDetailsDialog = ({data}) => {
    const [open, setOpen] = useState(false)

    const handleClickOpen = () => {
        setOpen(true)
    }

    const handleClose = () => {
        setOpen(false)
    }

    return (
        <React.Fragment>
            <Button onClick={handleClickOpen} variant="outlined" color="primary">
                Full Details
            </Button>
            <Dialog
                open={open}
                onClose={handleClose}
                fullWidth
                maxWidth={"md"}
            >
                <DialogTitle onClose={handleClose}>{`Domain "${data.domainName}"`}</DialogTitle>
                <DialogContent>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Name</TableCell>
                                <TableCell>Value</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {Object.keys(data).sort().map((name, index) => {
                                return (
                                    <TableRow key={index}>
                                        <TableCell>{`${name}`}</TableCell>
                                        <TableCell>{data[name]}</TableCell>
                                    </TableRow>
                                )
                            })}
                        </TableBody>
                    </Table>
                </DialogContent>
            </Dialog>
        </React.Fragment>
    )
}

const useDiffStyles = makeStyles({
    changed: {
        color: 'red'
    }
})

const DiffDetailsDialog = ({previous, current}) => {
    const [open, setOpen] = useState(false)
    const classes = useDiffStyles()

    const handleClickOpen = () => {
        setOpen(true)
    }

    const handleClose = () => {
        setOpen(false)
    }

    const createCompareRow = (name, previousEntry, currentEntry, index) => {
        return (
            <TableRow key={index}>
                <TableCell>{name}</TableCell>
                <TableCell
                    className={clsx(previousEntry !== currentEntry && classes.changed)}
                >
                    {previousEntry}
                </TableCell>
                <TableCell
                    className={clsx(previousEntry !== currentEntry && classes.changed)}
                >
                    {currentEntry}
                </TableCell>
            </TableRow>
        )
    }

    console.log(previous, current)

    return (
        <React.Fragment>
            <Button onClick={handleClickOpen} variant="outlined" color="primary">
                {`${previous.Version} -> ${current.Version}`}
            </Button>
            <Dialog
                open={open}
                onClose={handleClose}
                fullWidth
                maxWidth={"md"}
            >
                <DialogTitle onClose={handleClose}>
                    {`Domain "${current.domainName}" ${previous.Version} -> ${current.Version}`}
                </DialogTitle>
                <DialogContent>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Entry</TableCell>
                                <TableCell>{`Version: ${previous.Version}`}</TableCell>
                                <TableCell>{`Version: ${current.Version}`}</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {Object.keys(current).sort().map((name, index) => {
                                return createCompareRow(
                                    name,
                                    previous[name],
                                    current[name],
                                    index
                                )
                            })}
                        </TableBody>
                    </Table>
                </DialogContent>
            </Dialog>
        </React.Fragment>
    )
}

const RecordDetailsTab = (props) => {
    console.log(props.data)

    const dateEntries =  {
        Created: 'createdDate',
        Updated: 'updatedDate',
        Expires: 'expiresDate'
    }

    let registrant_contact_rows = []
    let registrant_contact_final = ""
    let administrative_contact_rows = []
    let administrative_contact_final = ""
    let date_rows = [];

    [
        'name',
        'organization',
        'street1',
        'street2',
        'street3',
        'street4'
    ].forEach((field, index) => {
        let fieldData = props.data[`registrant_${field}`]
        if (!!fieldData) {
            registrant_contact_rows.push(
                <TableRow key={index}>
                    <TableCell>
                        {fieldData}
                    </TableCell>
                </TableRow>
            )
        }

        fieldData = props.data[`administrativeContact_${field}`]
        if (!!fieldData) {
            administrative_contact_rows.push(
                <TableRow key={index}>
                    <TableCell>
                        {fieldData}
                    </TableCell>
                </TableRow>
            )
        }

    });

    [
        'city',
        'state',
        'postalCode',
        'country'
    ].forEach((field) => {
        let fieldData = props.data[`registrant_${field}`]
        if(!!fieldData) {
            registrant_contact_final += ` ${fieldData}`
        }

        fieldData = props.data[`administrativeContact_${field}`]
        if(!!fieldData) {
            administrative_contact_final += ` ${fieldData}`
        }

    });

    Object.keys(dateEntries).forEach((name, index) => {
        date_rows.push(
            <TableRow key={index}>
                <TableCell>
                    <Grid container>
                        <Grid item xs={6}>
                            {name}
                        </Grid>
                        <Grid>
                            {props.data[dateEntries[name]]}
                        </Grid>
                    </Grid>
                </TableCell>
            </TableRow>
        )
    })


    return (
        props.index === props.value && (
        <React.Fragment>
            <Grid container spacing={1}>
                <Grid item xs={3}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Registrant Contact</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {registrant_contact_rows}
                            <TableRow>
                                <TableCell>
                                    {registrant_contact_final}
                                </TableCell>
                            </TableRow>
                        </TableBody>
                    </Table>
                </Grid>
                <Grid item xs={3}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Administrative Contact</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {administrative_contact_rows}
                            <TableRow>
                                <TableCell>
                                    {administrative_contact_final}
                                </TableCell>
                            </TableRow>
                        </TableBody>
                    </Table>
                </Grid>
                <Grid item xs={3}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Significant Dates</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {date_rows}
                        </TableBody>
                    </Table>
                </Grid>
            </Grid>
            <Grid container>
                <Grid item>
                    <FullDetailsDialog data={props.data}/>
                </Grid>
            </Grid>
        </React.Fragment>
    ))
}


const HistoricalTab = (props) => {
    const [domainInfo, setDomainInfo] = useState(null)

    useEffect(() => {
        if (props.index === props.value && domainInfo == null) {
            fetchData()
        }
    })

    const fetchData = () => {
        const asyncfetch = async () => {
            try {
                let results = await domainFetcher({
                    domainName: props.data.domainName,
                })

                setDomainInfo(results.results)

            } catch (err) {
                console.log(err)
            }
        }

        asyncfetch()
    }

    let entry_rows = []
    if (domainInfo != null) {
        domainInfo.forEach((entry, index) => {
            let diffCell = <React.Fragment>&nbsp;</React.Fragment>

            if (index > 0) {
                let previousEntry = domainInfo[index - 1]
                diffCell = (
                    <DiffDetailsDialog
                        previous={previousEntry}
                        current={entry}
                    />)
            }

            entry_rows.push(
                <TableRow key={index}>
                    <TableCell>{entry.Version}</TableCell>
                    <TableCell>{entry.registrant_name}</TableCell>
                    <TableCell>{entry.contactEmail}</TableCell>
                    <TableCell>{entry.createdDate}</TableCell>
                    <TableCell>{entry.registrant_telephone}</TableCell>
                    <TableCell> <FullDetailsDialog data={entry} /> </TableCell>
                    <TableCell>{diffCell}</TableCell>
                </TableRow>
            )
        })

    }


    return (
        props.index === props.value &&
        domainInfo != null && (
        <React.Fragment>
            <Table>
                <TableHead>
                    <TableRow>
                        <TableCell>Version</TableCell>
                        <TableCell>Registrant</TableCell>
                        <TableCell>Email</TableCell>
                        <TableCell>Created</TableCell>
                        <TableCell>Telephone</TableCell>
                        <TableCell>Details</TableCell>
                        <TableCell>Diff</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {entry_rows}
                </TableBody>
            </Table>
        </React.Fragment>
    ))
}

const ExpandedEntryRow = ({data}) => {
    const [selectedTab, setSelectedTab] = useState(0)

    const handleTabChange = (event, newTab) => {
        setSelectedTab(newTab)
    }

    return (
        <React.Fragment>
            <Paper>
                <Tabs
                    value={selectedTab}
                    onChange={handleTabChange}
                >
                    <Tab label="Record Details"/>
                    <Tab label="Historical Records"/>
                </Tabs>

                <Container maxWidth={"xl"} >
                    <RecordDetailsTab
                        value={selectedTab}
                        index={0}
                        data={data}
                    />
                    <HistoricalTab
                        value={selectedTab}
                        index={1}
                        data={data}
                    />
                </Container>

            </Paper>

        </React.Fragment>
    )
}

export default ExpandedEntryRow