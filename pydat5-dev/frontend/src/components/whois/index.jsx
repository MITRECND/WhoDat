import React, {useState, useEffect, useRef} from 'react'
import {useHistory, useLocation, useParams, withRouter} from 'react-router-dom'
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

import WebHandler from './web_handler'
import TextHandler, {TextOptions} from './text_handler'

export const GeneralOptions = ({ formData, setFormData }) => {
    const [fangStatus, setFangStatus] = useState(formData.fang)

    const toggleFangOption = () => {
        setFangStatus(!fangStatus)
        setFormData(update(formData, {
            fang: {$set: !fangStatus}
        }))
    }

    return (
        <Grid item xs={1}>
            <FormControl component="fieldset">
                <FormControlLabel
                    value="fang"
                    control={
                        <CheckBox
                            color="primary"
                            checked={fangStatus}
                            onClick={toggleFangOption}
                        />}
                    label="ReFang"
                    labelPlacement="end"
                />
            </FormControl>
        </Grid>
    )
}

const WhoisResults = (props) => {
    const [queryResults, setQueryResults] = useState(
        <React.Fragment> </React.Fragment>
    )

    useEffect(() => {
        if (props.queryData.format === 'WEB') {
            // console.log(query)
            setQueryResults(
                <React.Fragment>
                    <WebHandler
                        queryData={props.queryData}
                        handleWebPivot={props.handleWebPivot}
                    />
                </React.Fragment>
            )
        } else {
            setQueryResults(
                <React.Fragment>
                    <TextHandler
                        queryData={props.queryData}
                    />
                </React.Fragment>
            )
        }
    }, [props.queryData])


    return (
        <Grid item xs={12}>
                {queryResults}
        </Grid>
    )
}

const WhoisHandler = (props) => {
    const [formData, setFormData] = useState({
        query: "",
        format: 'WEB',
        limit: 1000,
        field: "domainName",
        fang: true,
    })

    const [queryData, setQueryData] = useState({
        ...formData
    })

    let location = useLocation()
    let history = useHistory()

    useEffect(() => {
        let query_param = qs.parse(location.search, {
            ignoreQueryPrefix: true
        }).query

        if (!!query_param) {
            let updated = update(formData, {
                query: {$set: query_param}
            })

            setFormData(updated)
            setQueryData(updated)
        }

    }, [])

    const handleWebPivot = (newQuery) => {
        let updated = update(formData, {
            query: {$set: newQuery}
        })

        setFormData(updated)

        history.push({
            pathname: '/whois',
            search: `?query=${encodeURIComponent(newQuery)}`
        })

        setQueryData(updated)
    }

    const handleOnSubmit = (e) => {
        e.preventDefault()

        let updated = formData

        console.log(formData)

        if (formData.fang) {
            let refanged = formData.query.replace('[.]', '.')
            if (refanged !== formData.query) {
                updated = update(formData, {
                    query: {$set: refanged}
                })
                setFormData(updated)
            }
        }

        history.push({
            pathname: '/whois',
            search: `?query=${encodeURIComponent(updated.query)}`
        })

        setQueryData(updated)
    }

    const handleOnChangeQuery = (e) => {
        setFormData(update(formData, {
            query: {$set: e.target.value}
        }))

    }

    const handleOnChangeFormat = (e) => {
        // Reset/delete queryData
        setQueryData(update(queryData, {
            query: {$set: ""}
        }))

        setFormData(update(formData, {
            format: {$set: e.target.value}
        }))

    }

    let queryOptions = (<React.Fragment> </React.Fragment>)

    if (formData.format !== 'WEB') {
        queryOptions = (
            <React.Fragment>
                <TextOptions
                    formData={formData}
                    setFormData={setFormData}
                />
            </React.Fragment>
        )
    }

    return (
        <Grid container>
            <Grid item xs={12}>
                <form onSubmit={handleOnSubmit}>
                    <Grid container spacing={1}>
                        <Grid container item xs={11}>
                            <Grid item xs={1}>
                                <InputLabel id="query-format-label">Format</InputLabel>
                                <Select
                                    name="format"
                                    labelId="query-format-label"
                                    id="query-format-select"
                                    onChange={handleOnChangeFormat}
                                    value={formData.format}
                                >
                                    <MenuItem value={'WEB'}>Web</MenuItem>
                                    <MenuItem value={'JSON'}>JSON</MenuItem>
                                    <MenuItem value={'CSV'}>CSV</MenuItem>
                                    <MenuItem value={'LIST'}>List</MenuItem>
                                </Select>
                            </Grid>
                            <Grid item xs={11}>
                                <TextField
                                    label="Query"
                                    variant="outlined"
                                    name="query"
                                    value={formData.query}
                                    onChange={handleOnChangeQuery}
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
                                <GeneralOptions
                                    formData={formData}
                                    setFormData={setFormData}
                                />
                                {queryOptions}
                            </Grid>

                        </Grid>
                    </Grid>
                </form>
            </Grid>
            {!!queryData.query &&
                queryData.query != "" &&
                <WhoisResults
                    queryData={queryData}
                    handleWebPivot={handleWebPivot}
                />
            }
        </Grid>
    )
}

export default WhoisHandler