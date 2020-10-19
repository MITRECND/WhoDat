import React, {useEffect, useState} from 'react'
import { useLocation, useHistory } from 'react-router-dom'
import update from 'immutability-helper'
import qs from 'qs'

import Grid from '@material-ui/core/Grid'
import TextField from '@material-ui/core/TextField'
import Select from '@material-ui/core/Select'
import Button from '@material-ui/core/Button'
import InputLabel from '@material-ui/core/InputLabel'
import MenuItem from '@material-ui/core/MenuItem'
import CheckBox from '@material-ui/core/Checkbox'
import FormControlLabel from '@material-ui/core/FormControlLabel';
import FormControl from '@material-ui/core/FormControl';
import ListSubheader from '@material-ui/core/ListSubheader'
import Menu from '@material-ui/core/Menu'
import Input from '@material-ui/core/Input'
import Typography from '@material-ui/core/Typography'
import Container from '@material-ui/core/Container'

import DNSDBWebHandler from './web_handler'
import DNSDBTextHandler from './text_handler'
import { BackdropLoader } from '../../helpers/loaders'


const dnsdbFetcher = async ({
    type,
    value,
    limit,
    rrtypes,
    tfb,
    tfa,
    tlb,
    tla
}) => {

    let url;
    let data = {}
    if (type == 'domain') {
        url = '/api/plugin/passive/dnsdb/forward'
        data['domain'] = value
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
         if (data[name] == "") {
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

        </React.Fragment>
    )
}

const DNSDBResults = (props) => {
    const [queryBlock, setQueryBlock] = useState(
        <React.Fragment> </React.Fragment>
    )

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
                    tla: props.queryData.tla
                })

                let queryResults = {
                    results: results.data,
                    rate: results.rate
                }

                if (props.queryData.format == 'WEB') {
                    setQueryBlock(
                        <React.Fragment>
                            <DNSDBWebHandler
                                queryResults={queryResults}
                            />
                        </React.Fragment>
                    )
                } else {
                    setQueryBlock(
                        <React.Fragment>
                            <DNSDBTextHandler
                                queryResults={queryResults}
                            />
                        </React.Fragment>
                    )
                }
            } catch (err) {
                if (err.status === 404) {
                    setQueryBlock(
                        <Container fixed>
                            <Typography variant="h2">No Results</Typography>
                        </Container>

                    )
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

const DNSDB = ({}) => {
    const [formData, setFormData] = useState({
        value: "",
        format: "WEB",
        limit: 10000,
        field: "RRName",
        type: "domain",
        rrtypes: ['any'],
        tla: "",
        tlb: "",
        tfa: "",
        tfb: ""
    })

    const [queryData, setQueryData] = useState({
        ...formData
    })

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

    let location = useLocation()
    let history = useHistory()

    useEffect(() => {
        let query_params = qs.parse(location.search, {
            ignoreQueryPrefix: true
        })

        if (!!query_params) {
            if ('type' in query_params && 'value' in query_params) {
                let updated = update(formData, {
                    type: {$set: query_params.type},
                    value: {$set: query_params.value}
                })
                setFormData(updated)
                setQueryData(updated)
            }

        }
    }, [])


    const handleOnSubmit = (e) => {
        e.preventDefault()

        history.push({
            pathname: location.pathname,
            search: (
                `?type=${encodeURIComponent(formData.type)}&` +
                `value=${encodeURIComponent(formData.value)}`
            )
        })

        setQueryData({...formData})
    }

    const handleOnChangeValue = (e) => {
        setFormData(update(formData, {
            value: {$set: e.target.value}
        }))
    }

    const handleOnChangeFormat = (e) => {
        setFormData(update(formData, {
            format: {$set: e.targetvalue}
        }))
    }

    const handleOnChangeType = (e) => {
        setFormData(update(formData,{
            type: {$set: e.target.value}
        }))
    }

    return (
        <Grid container>
            <Grid item xs={12}>
                <form onSubmit={handleOnSubmit}>
                    <Grid container spacing={1}>
                        <Grid container item xs={11}>
                            <Grid item xs={1}>
                                <InputLabel id="passive-type-label">Type</InputLabel>
                                <Select
                                    name="type"
                                    labelId="passive-type-label"
                                    id="passive-type-select"
                                    onChange={handleOnChangeType}
                                    value={formData.type}
                                >
                                    {/* <ListSubheader>Forward</ListSubheader> */}
                                    {Object.keys(forwardQueryTypes).map((name, index) => {
                                        return (
                                            <MenuItem value={name} key={index}>
                                                {forwardQueryTypes[name]}
                                            </MenuItem>
                                        )
                                    })}
                                    {/* <ListSubheader>Reverse</ListSubheader> */}
                                    {Object.keys(reverseQueryTypes).map((name, index) => {
                                        return (
                                            <MenuItem value={name} key={index}>
                                                {reverseQueryTypes[name]}
                                            </MenuItem>
                                        )
                                    })}
                                </Select>
                            </Grid>
                            <Grid item xs={1}>
                                <InputLabel id="output-format-label">Format</InputLabel>
                                <Select
                                    name="format"
                                    labelId="output-format-label"
                                    id="output-format-select"
                                    onChange={handleOnChangeFormat}
                                    value={formData.format}
                                >
                                    <MenuItem value={'WEB'}>Web</MenuItem>
                                    <MenuItem value={'JSON'}>JSON</MenuItem>
                                    <MenuItem value={'CSV'}>CSV</MenuItem>
                                    <MenuItem value={'LIST'}>List</MenuItem>
                                </Select>
                            </Grid>
                            <Grid item xs={10}>
                                <TextField
                                    label={allQueryTypes[formData.type]}
                                    variant="outlined"
                                    name="value"
                                    value={formData.value}
                                    onChange={handleOnChangeValue}
                                    fullWidth
                                />
                            </Grid>
                        </Grid>
                        <Grid item xs={1}>
                            <Button variant="outlined" type="submit">
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
            </Grid>
            {!!queryData.value &&
                queryData.value != "" &&
                <DNSDBResults
                    queryData={queryData}
                />
            }
        </Grid>
    )
}

export default DNSDB