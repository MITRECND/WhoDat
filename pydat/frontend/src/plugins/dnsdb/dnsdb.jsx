import React, {useEffect, useState, useContext} from 'react'
import { useLocation, useHistory } from 'react-router-dom'
import update from 'immutability-helper'
import qs from 'qs'

import Grid from '@material-ui/core/Grid'
import TextField from '@material-ui/core/TextField'
import Select from '@material-ui/core/Select'
import Button from '@material-ui/core/Button'
import InputLabel from '@material-ui/core/InputLabel'
import MenuItem from '@material-ui/core/MenuItem'
import FormControl from '@material-ui/core/FormControl';
import Input from '@material-ui/core/Input'
import Typography from '@material-ui/core/Typography'
import Container from '@material-ui/core/Container'
import Paper from '@material-ui/core/Paper'
import { Divider, InputAdornment, ListSubheader, makeStyles } from '@material-ui/core'
import SettingsIcon from '@material-ui/icons/Settings';

import DNSDBWebHandler from './web_handler'
import { BackdropLoader } from '../../components/helpers/loaders'
import {useUserPreferences} from '../../components/helpers/preferences'
import { useSnackbar } from 'notistack'



const dnsdbFetcher = async ({
    type,
    value,
    limit,
    rrtypes,
    tfb,
    tfa,
    tlb,
    tla,
    domainsearchtype,
}) => {

    let url;
    let data = {}
    if (type === 'domain') {
        url = '/api/plugin/passive/dnsdb/forward'

        switch (domainsearchtype) {
            case 'prefix-wildcard':
                data['domain'] = `*.${value}`
                break;
            case 'suffix-wildcard':
                data['domain'] = `${value}.*`
                break;
            default:
                data['domain'] = value
        }
    } else {
        url = '/api/plugin/passive/dnsdb/reverse'
        data['type'] = type
        data['value'] = value
    }

    data = {
        ...data,
        limit: parseInt(limit),
        rrtypes: rrtypes,
        time_first_before: tfb,
        time_first_after: tfa,
        time_last_before: tlb,
        time_last_after: tla,
    }

    const timeFields = [
        'time_first_before',
        'time_first_after',
        'time_last_before',
        'time_last_after'
    ];

    timeFields.forEach((name) => {
         if (data[name] === "") {
            delete data[name]
         } else {
            let parsed = data[name].split('-')
            let timestamp = Date.UTC(
                parsed[0],
                parseInt(parsed[1]) - 1,
                parsed[2]
            )
            data[name] = timestamp / 1000
         }
    })

    console.log(data)

    let response = await fetch (
        url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'

            },
            body: JSON.stringify(data)
    })

    console.log(response)

    if (response.status === 200) {
        let jresp = await response.json()
        return jresp
    } else {
        throw response
    }
}


// https://material-ui.com/components/selects/
const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;
const MenuProps = {
  PaperProps: {
    style: {
      maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
      width: 250,
    },
  },
  getContentAnchorEl: null
};


const DNSDBGeneralOptions = ({formData, setFormData}) => {
    const preferences = useUserPreferences('dnsdb')
    const AllRRTypesList = [
        'any',
        'a',
        'aaaa',
        'cname',
        'mx',
        'ns',
        'ptr',
        'soa',
        'txt',
        // DNSSEC Types
        'any-dnssec',
        'ds',
        'rrsig',
        'nsec',
        'dnskey',
        'nsec3',
        'nsec3param',
        'dlv'
    ]

    const IPRRTypesList = [
        'any',
        'a',
        'aaaa',
    ]

    const handleOnChange = (e) => {
        if (e.target.name == "domainsearchtype" && preferences.getPref("remember_domain_search_type")) {
            preferences.setPref("domain_search_type", e.target.value)
        }

        console.log(e.target)
        setFormData(update(formData, {
            [e.target.name]: {$set: e.target.value}
        }))


    }

    let RRTypesList = formData.type === 'ip' ? IPRRTypesList : AllRRTypesList

    return (
        <React.Fragment>
            <Grid item xs={1}>
                <TextField
                    label="Limit"
                    variant="outlined"
                    name="limit"
                    type="number"
                    value={formData.limit}
                    onChange={handleOnChange}
                />
            </Grid>
            <Grid item xs={2}>
                <TextField
                    label="First Seen Start"
                    name="tfa"
                    type="date"
                    InputLabelProps={{
                        shrink: true,
                    }}
                    onChange={handleOnChange}
                    value={formData.tfa}
                />
            </Grid>
            <Grid item xs={2}>
                <TextField
                    label="First Seen End"
                    name="tfb"
                    type="date"
                    InputLabelProps={{
                        shrink: true,
                    }}
                    onChange={handleOnChange}
                    value={formData.tfb}
                />
            </Grid>
            <Grid item xs={2}>
                <TextField
                    label="Last Seen Start"
                    name="tla"
                    type="date"
                    InputLabelProps={{
                        shrink: true,
                    }}
                    onChange={handleOnChange}
                    value={formData.tla}
                />
            </Grid>
            <Grid item xs={2}>
                <TextField
                    label="Last Seen End"
                    name="tlb"
                    type="date"
                    InputLabelProps={{
                        shrink: true,
                    }}
                    onChange={handleOnChange}
                    value={formData.tlb}
                />
            </Grid>
            <Grid item xs={2}>
                <FormControl>
                <InputLabel id="rrtypes-field-label">RRTypes</InputLabel>
                    <Select
                        name="rrtypes"
                        multiple
                        labelId="rrtypes-field-label"
                        id="rrtypes-field-select"
                        onChange={handleOnChange}
                        value={formData.rrtypes}
                        input={<Input />}
                        MenuProps={MenuProps}
                    >
                       {RRTypesList.map((rrtype, index) => {
                           return (
                            <MenuItem key={index} value={rrtype}>{rrtype}</MenuItem>
                           )
                        })}

                    </Select>
                    </FormControl>
            </Grid>
            {formData.type == 'domain' &&
                <Grid item xs={2}>
                    <FormControl>
                    <InputLabel id="domainsearchtype-label">Search Type</InputLabel>
                        <Select
                            name="domainsearchtype"
                            labelId="domainsearchtype-label"
                            id="domainsearchtype-select"
                            onChange={handleOnChange}
                            value={formData.domainsearchtype}
                        >
                            <MenuItem value={'prefix-wildcard'}>Prefix Wildcard</MenuItem>
                            <MenuItem value={'suffix-wildcard'}>Suffix Wildcard</MenuItem>
                            <MenuItem value={'absolute'}>Absolute</MenuItem>
                        </Select>
                        </FormControl>
                </Grid>
            }


        </React.Fragment>
    )
}

const DNSDBResults = (props) => {
    const [queryBlock, setQueryBlock] = useState(
        <React.Fragment> </React.Fragment>
    )
    const {enqueueSnackbar} = useSnackbar()

    useEffect(() => {
        setQueryBlock(
            <BackdropLoader />
        )
        console.log(props.queryData)
        fetchData()
    }, [props.queryData])

    const fetchData = () => {
        const asyncfetch = async () => {
            try {
                let results = await dnsdbFetcher({
                    type: props.queryData.type,
                    value: props.queryData.value,
                    limit: props.queryData.limit,
                    rrtypes: props.queryData.rrtypes,
                    tfb: props.queryData.tfb,
                    tfa: props.queryData.tfa,
                    tlb: props.queryData.tlb,
                    tla: props.queryData.tla,
                    domainsearchtype: props.queryData.domainsearchtype
                })

                let queryResults = {
                    results: results.data,
                    rate: results.rate
                }

                setQueryBlock(
                    <React.Fragment>
                        <DNSDBWebHandler
                            queryResults={queryResults}
                        />
                    </React.Fragment>
                )

            } catch (err) {
                if (err.status === 404) {
                    setQueryBlock(
                        <Container fixed>
                            <Typography variant="h2">No Results</Typography>
                        </Container>

                    )
                } else {
                    enqueueSnackbar("Unable to query DNSDB API", {variant: "error"})
                }
                console.log(err)
            }
        }

        asyncfetch()
    }

    return (
        <Grid item xs={12}>
            {queryBlock}
        </Grid>
    )

}

const useStyles = makeStyles((theme) => ({
    root: {
        flexGrow: 1
    },
    searchContainer: {
        paddingBottom: theme.spacing(2)
    },
    searchPaper: {
        padding: theme.spacing(2)
    }
}))

const DNSDB = () => {
    const preferences = useUserPreferences('dnsdb')
    const defaultFormFields = {
        type: "domain",
        value: "",
        limit: 10000,
        rrtypes: ['any'],
        tla: "",
        tlb: "",
        tfa: "",
        tfb: "",
        domainsearchtype: preferences.getPref("remember_domain_search_type") ? preferences.getPref("domain_search_type") : "prefix-wildcard"
    }

    const [formData, setFormData] = useState({...defaultFormFields})
    const [queryData, setQueryData] = useState({...formData})

    const forwardQueryTypes = {
        'domain': "Domain",
    }

    const reverseQueryTypes = {
        'ip': "IP",
        'name': "Name",
        'raw': "Raw"
    }

    const allQueryTypes = {
        ...forwardQueryTypes,
        ...reverseQueryTypes
    }

    const classes = useStyles()
    const {enqueueSnackbar} = useSnackbar()

    let location = useLocation()
    let history = useHistory()

    useEffect(() => {
        let query_params = qs.parse(location.search, {
            ignoreQueryPrefix: true
        })

        let updated = null
        if (Object.keys(query_params).length > 0) {
            if ('type' in query_params && 'value' in query_params) {
                let temp = {...formData}
                temp = update(temp, {
                    type: {$set: query_params.type},
                    value: {$set: query_params.value}
                })

                for (let name in query_params) {
                    if (name === "type" || name === "value") {
                        continue
                    }
                    if (name in formData) {
                        switch (name) {
                            case "tla":
                            case "tlb":
                            case "tfa":
                            case "tfb":
                            case "domainsearchtype":
                                temp = update(temp, {
                                    [name]: {$set: query_params[name]}
                                })
                                break
                            case "limit":
                                try {
                                    let limit = parseInt(query_params[name])
                                    temp = update(temp, {
                                        [name]: {$set: limit}
                                    })
                                } catch (err) {
                                    enqueueSnackbar(`Unable to parse number from limit in arguments`, {variant: 'error'})
                                }
                                break
                            case 'rrtypes':
                                try {
                                    let rrtypes = query_params[name].split(',')
                                    temp = update(temp, {
                                        [name]: {$set: rrtypes}
                                    })
                                } catch (err) {
                                    enqueueSnackbar(`Unable to parse rrtypes from arguments`, {variant: 'error'})
                                }
                                break
                            default:
                                enqueueSnackbar(`Unexpected paramater ${name} in arguments`, {variant: 'warning'})

                        }
                    } else {
                        enqueueSnackbar(`Unexpected paramater ${name} in arguments`, {variant: 'warning'})
                    }
                }
                updated = temp
            }
        } else {
            updated = {...defaultFormFields}
        }

        if (updated !== null) {
            setFormData(updated)
            setQueryData(updated)
        }
    }, [location])


    const handleOnSubmit = (e) => {
        e.preventDefault()

        let search_params = []

        for (let name in formData) {
            switch(name){
                case "rrtypes":
                    let rrtypes = formData.rrtypes.join(',')
                    search_params.push(
                        `${name}=${encodeURIComponent(rrtypes)}`
                    )
                    break
                default:
                    if (!!formData[name]){
                        search_params.push(
                            `${name}=${encodeURIComponent(formData[name])}`
                        )
                    }

            }
        }

        let search_string = `?${search_params.join('&')}`

        history.push({
            pathname: location.pathname,
            search: search_string
        })

        // setQueryData({...formData})
    }

    const handleOnChangeValue = (e) => {
        setFormData(update(formData, {
            value: {$set: e.target.value}
        }))
    }

    const handleOnChangeType = (e) => {
        if (e.target.value) {
            setFormData(update(formData,{
                type: {$set: e.target.value},
                value: {$set: ""}
            }))
        }
    }

    const typeSelect = (
        <React.Fragment>
            <FormControl>
                {/* <InputLabel id="passive-type-label">Type</InputLabel> */}
                <Select
                    name="type"
                    // labelId="passive-type-label"
                    id="passive-type-select"
                    onChange={handleOnChangeType}
                    value={formData.type}
                >
                    <ListSubheader>Forward</ListSubheader>
                    {Object.keys(forwardQueryTypes).map((name, index) => {
                        return (
                            <MenuItem value={name} key={index}>
                                {forwardQueryTypes[name]}
                            </MenuItem>
                        )
                    })}
                    <ListSubheader>Reverse</ListSubheader>
                    {Object.keys(reverseQueryTypes).map((name, index) => {
                        return (
                            <MenuItem value={name} key={index}>
                                {reverseQueryTypes[name]}
                            </MenuItem>
                        )
                    })}
                </Select>
            </FormControl>
        </React.Fragment>
    )

    return (
        <React.Fragment>
            <Container className={classes.searchContainer} maxWidth="xl">
                <Paper className={classes.searchPaper}>
                    <form onSubmit={handleOnSubmit}>
                        <Grid container spacing={1} direction="row" justifyContent="center" alignItems="flex-end">
                                <Grid item xs={11}>
                                    <TextField
                                        label={`Search ${allQueryTypes[formData.type]} Records`}
                                        variant="outlined"
                                        name="value"
                                        value={formData.value}
                                        onChange={handleOnChangeValue}
                                        fullWidth
                                        InputProps={{
                                            startAdornment: (
                                                <InputAdornment
                                                    position="start"
                                                >
                                                    {typeSelect}
                                                </InputAdornment>
                                            )
                                        }}

                                    />
                                </Grid>
                            <Grid item xs={1}>
                                <Button
                                    variant="outlined"
                                    type="submit"
                                    fullWidth
                                >
                                    Search
                                </Button>
                            </Grid>
                            <Grid container item xs={12}>
                                <Grid
                                    container
                                    direction="row"
                                    // alignItems="left"
                                    spacing={1}
                                >
                                    {
                                        <DNSDBGeneralOptions
                                            formData={formData}
                                            setFormData={setFormData}
                                        />
                                    }
                                </Grid>
                            </Grid>
                        </Grid>
                    </form>
                </Paper>
            </Container>
            {!!queryData.value &&
                queryData.value != "" &&
                <Paper>
                    <DNSDBResults
                        queryData={queryData}
                    />
                </Paper>
            }
        </React.Fragment>



    )
}

export default DNSDB