import React, {useState, useEffect, useRef, useContext} from 'react'
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
import Container from '@material-ui/core/Container'
import Paper from '@material-ui/core/Paper'

import WebHandler from './web_handler'
import {UserPreferencesContext} from '../helpers/preferences'
import {SearchSettings} from '../layout/dialogs'

export const GeneralOptions = ({ formData, setFormData }) => {
    const [fangStatus, setFangStatus] = useState(formData.fang)
    const preferences = useContext(UserPreferencesContext)

    useEffect(() => {
        setFangStatus(formData.fang)
    }, [formData.fang])

    const toggleFangOption = () => {
        setFangStatus(!fangStatus)
        setFormData(update(formData, {
            fang: {$set: !fangStatus}
        }))
        preferences.setPref('whois', 'fang', !fangStatus)
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
        // console.log(query)
        setQueryResults(
            <React.Fragment>
                <WebHandler
                    queryData={props.queryData}
                    handleWebPivot={props.handleWebPivot}
                />
            </React.Fragment>
        )
    }, [props.queryData])


    return (
        <Grid item xs={12}>
                {queryResults}
        </Grid>
    )
}



const WhoisHandler = (props) => {
    const preferences = useContext(UserPreferencesContext)
    const formPrefs = preferences.getPrefs('whois', {
        fang: true,
    })

    const [formData, setFormData] = useState({
        query: "",
        ...formPrefs
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

    return (
        <React.Fragment>
            <Container style={{paddingBottom: '1rem'}}>
                <form onSubmit={handleOnSubmit}>
                    <Grid container spacing={1} justify="center" alignItems="flex-end">
                        <Grid container item xs={11} justify="center" alignItems="flex-end">
                            <TextField
                                label="Query"
                                variant="outlined"
                                name="query"
                                value={formData.query}
                                onChange={handleOnChangeQuery}
                                fullWidth
                                InputProps={{
                                    endAdornment: (
                                        <SearchSettings title={"Search Settings"}>
                                            <GeneralOptions
                                                formData={formData}
                                                setFormData={setFormData}
                                            />
                                        </SearchSettings>
                                    )
                                }}
                            />
                        </Grid>
                        <Grid item xs={1}>
                            <Button variant="outlined" type="submit">
                                Search
                            </Button>
                        </Grid>
                    </Grid>
                </form>
            </Container>
            {!!queryData.query &&
                queryData.query != "" &&
                <Paper>
                    <WhoisResults
                        queryData={queryData}
                        handleWebPivot={handleWebPivot}
                    />
                </Paper>
            }
        </React.Fragment>
    )
}

export default WhoisHandler