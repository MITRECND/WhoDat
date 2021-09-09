import React, {useState, useEffect, useMemo} from 'react'
import Grid from '@material-ui/core/Grid'
import MenuItem from '@material-ui/core/MenuItem'
import Paper from '@material-ui/core/Paper'
import Typography from '@material-ui/core/Typography'
import InputLabel from '@material-ui/core/InputLabel'
import Select from '@material-ui/core/Select'
import {makeStyles} from '@material-ui/core/styles'
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemText from '@material-ui/core/ListItemText';
import Checkbox from '@material-ui/core/Checkbox';
import Button from '@material-ui/core/Button';
import FormControl from '@material-ui/core/FormControl'
import Input from '@material-ui/core/Input'

import { Parser as CSVParser } from 'json2csv'

import {FullScreenDialog} from '../layout/dialogs'

// TODO XXX FIXME Check whether preprocessor is function, add other error checking

export const JSONExporter = ({
    data,
    open,
    onClose,
    dataControl = null,
    preprocessor = null
}) => {

    const processedData = useMemo(() => {
        if (preprocessor !== null) {
            return preprocessor(data)
        } else {
            return data
        }
    }, [data])

    return (
        <FullScreenDialog
            open={open}
            onClose={onClose}
            title="JSON Exporter"
        >
            {open &&
                <React.Fragment>
                    {dataControl}
                    <Grid container spacing={2} style={{padding: '1rem'}}>
                        {processedData.map((entry, index) => {
                            return (
                                <Grid item xs={12} key={index}>
                                    <Typography>
                                        {JSON.stringify(entry, null, 1)}
                                    </Typography>

                                </Grid>
                            )
                        })}
                    </Grid>
                </React.Fragment>
            }
        </FullScreenDialog>
    )
}


// https://material-ui.com/components/transfer-list/#simple-transfer-list
const useTransferListStyles = makeStyles((theme) => ({
    root: {
      margin: 'auto',
    },
    paper: {
        minWidth: 200,
    //   width: 200,
      height: 150,
      overflow: 'auto',
    },
    button: {
      margin: theme.spacing(0.5, 0),
    },
  }));


function not(a, b) {
    return a.filter((value) => b.indexOf(value) === -1);
  }

  function intersection(a, b) {
    return a.filter((value) => b.indexOf(value) !== -1);
  }

  const TransferList = (props) => {
    const classes = useTransferListStyles();
    const [checked, setChecked] = React.useState([]);
    const [left, setLeft] = React.useState(props.left);
    const [right, setRight] = React.useState(props.right);

    const leftChecked = intersection(checked, left);
    const rightChecked = intersection(checked, right);

    useEffect(() => {
        props.setSelectedKeys(right)
    }, [right])

    const handleToggle = (value) => () => {
      const currentIndex = checked.indexOf(value);
      const newChecked = [...checked];

      if (currentIndex === -1) {
        newChecked.push(value);
      } else {
        newChecked.splice(currentIndex, 1);
      }

      setChecked(newChecked);
    };

    const handleAllRight = () => {
      setRight(right.concat(left));
      setLeft([]);
    };

    const handleCheckedRight = () => {
      setRight(right.concat(leftChecked));
      setLeft(not(left, leftChecked));
      setChecked(not(checked, leftChecked));
    };

    const handleCheckedLeft = () => {
      setLeft(left.concat(rightChecked));
      setRight(not(right, rightChecked));
      setChecked(not(checked, rightChecked));
    };

    const handleAllLeft = () => {
      setLeft(left.concat(right));
      setRight([]);
    };

    const customList = (items) => (
      <Paper className={classes.paper}>
        <List dense component="div" role="list">
          {items.map((value) => {
            const labelId = `transfer-list-item-${value}-label`;

            return (
              <ListItem key={value} role="listitem" button onClick={handleToggle(value)}>
                <ListItemIcon>
                  <Checkbox
                    checked={checked.indexOf(value) !== -1}
                    tabIndex={-1}
                    disableRipple
                    inputProps={{ 'aria-labelledby': labelId }}
                  />
                </ListItemIcon>
                <ListItemText id={labelId} primary={`${value}`} />
              </ListItem>
            );
          })}
          <ListItem />
        </List>
      </Paper>
    );

    return (
      <Grid container spacing={2} justifyContent="center" alignItems="center" className={classes.root}>
        <Grid item>{customList(left)}</Grid>
        <Grid item>
          <Grid container direction="column" alignItems="center">
            <Button
              variant="outlined"
              size="small"
              className={classes.button}
              onClick={handleAllRight}
              disabled={left.length === 0}
              aria-label="move all right"
            >
              ≫
            </Button>
            <Button
              variant="outlined"
              size="small"
              className={classes.button}
              onClick={handleCheckedRight}
              disabled={leftChecked.length === 0}
              aria-label="move selected right"
            >
              &gt;
            </Button>
            <Button
              variant="outlined"
              size="small"
              className={classes.button}
              onClick={handleCheckedLeft}
              disabled={rightChecked.length === 0}
              aria-label="move selected left"
            >
              &lt;
            </Button>
            <Button
              variant="outlined"
              size="small"
              className={classes.button}
              onClick={handleAllLeft}
              disabled={right.length === 0}
              aria-label="move all left"
            >
              ≪
            </Button>
          </Grid>
        </Grid>
        <Grid item>{customList(right)}</Grid>
      </Grid>
    );
  }



const CSVSelector = ({keys, selectedKeys, setSelectedKeys}) => {
    let left = []
    keys.forEach((key) => {
        if (!selectedKeys.includes(key)) {
            left.push(key)
        }
    })

    return (
        <React.Fragment>
            <TransferList
                left={left}
                right={selectedKeys}
                setSelectedKeys={setSelectedKeys}
            />
        </React.Fragment>
    )
}

export const CSVExporter = ({
    data,
    open,
    onClose,
    dataControl = null,
    preprocessor = null
}) => {

    const processedData = useMemo(() => {
        if (preprocessor !== null) {
            return preprocessor(data)
        } else {
            return data
        }
    }, [data])

    const keys = processedData.length > 0 ? Object.keys(processedData[0]) : []
    const [selectedKeys, setSelectedKeys] = useState(keys)


    let parser = new CSVParser({
        fields: selectedKeys,
    })
    let csv_data = []

    try {
        csv_data = parser.parse(processedData).split('\n')
    } catch (err) {
        console.error(err)
    }


    return (
        <FullScreenDialog
            open={open}
            onClose={onClose}
            title="CSV Builder/Exporter"
        >
            {open &&
            <React.Fragment>
                {dataControl}
                <Grid container spacing={2} style={{padding: '1rem'}}>
                    <Grid item>
                      <CSVSelector
                        keys={keys}
                        selectedKeys={selectedKeys}
                        setSelectedKeys={setSelectedKeys}
                      />
                    </Grid>
                </Grid>
                <Grid container spacing={1} style={{padding: '1rem'}}>
                    {csv_data.map((entry, index) => (
                        <Grid item xs={12} key={index}>
                            {entry}
                        </Grid>
                    ))}

                </Grid>
            </React.Fragment>
            }

        </FullScreenDialog>
    )
}

const ListSelector = ({keys, selectedKey, setSelectedKey}) => {
    const handleOnChange = (e) => {
        setSelectedKey(e.target.value)
    }

    return (
        <React.Fragment>
            <InputLabel id="list-field-label">Choose Field</InputLabel>
            <Select
                name="field"
                labelId="list-field-label"
                id="list-field-select"
                onChange={handleOnChange}
                value={selectedKey}
            >
                {keys.map((key, index) => (
                    <MenuItem key={index} value={key}>{key}</MenuItem>
                ))}
            </Select>
        </React.Fragment>
    )
}

export const ListExporter = ({
    field,
    data,
    open,
    onClose,
    dataControl = null,
    preprocessor = null
}) => {

    const processedData = useMemo(() => {
        if (preprocessor !== null) {
            return preprocessor(data)
        } else {
            return data
        }
    }, [data])

    const [selectedKey, setSelectedKey] = useState(field)
    const keys = processedData.length > 0 ? Object.keys(processedData[0]) : [field]

    return (
        <FullScreenDialog
            open={open}
            onClose={onClose}
            title="List Builder/Exporter"
        >
            {open &&
            <React.Fragment>
                {dataControl}
                <Grid container spacing={2} style={{padding: '1rem'}}>
                    <Grid item xs={2}>
                        <ListSelector
                            keys={keys}
                            selectedKey={selectedKey}
                            setSelectedKey={setSelectedKey}
                        />
                    </Grid>
                </Grid>
                <Grid container spacing={2} style={{padding: '1rem'}}>
                    {processedData.map((entry, index) => {
                        return (
                            <Grid item xs={12} key={index}>
                                {entry[selectedKey]}
                            </Grid>
                        )
                    })}
                </Grid>
            </React.Fragment>
            }
        </FullScreenDialog>
    )
}