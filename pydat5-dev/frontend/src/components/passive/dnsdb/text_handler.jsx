import React, {useState, useEffect} from 'react'
import update from 'immutability-helper'
import Grid from '@material-ui/core/Grid'
import TextField from '@material-ui/core/TextField'
import Select from '@material-ui/core/Select'
import InputLabel from '@material-ui/core/InputLabel'
import MenuItem from '@material-ui/core/MenuItem'


export const TextOptions = ({formData, setFormData}) => {

    const handleOnChange = (e) => {
        console.log(e.target)
        setFormData(update(formData, {
            [e.target.name]: {$set: e.target.value}
        }))
    }

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
            {formData.format === 'LIST' &&
            <Grid item xs={2}>
                <InputLabel id="list-field-label">Filter</InputLabel>
                    <Select
                        name="field"
                        labelId="list-field-label"
                        id="list-field-select"
                        onChange={handleOnChange}
                        value={formData.field}
                    >
                        <MenuItem value={'rrname'}>RRName</MenuItem>
                        <MenuItem value={'rdata'}>RData</MenuItem>
                    </Select>
            </Grid>

            }
        </React.Fragment>
    )
}


const JSONHandler = ({data}) => {
    return (
        <Grid container>
            {data.map((entry, index) => {
                return (
                    <Grid item xs={12} key={index}>
                        {JSON.stringify(entry)}
                    </Grid>
                )
            })}
        </Grid>
    )
}

const CSVHandler = ({data}) => {
    return (
        <Grid container>
            {data.map((entry, index) => {
                return (
                    <Grid item xs={12}>
                        CSV DATA
                    </Grid>
                )
            })}
        </Grid>
    )
}

const ListHandler = ({field, data}) => {
    return (
        <Grid container>
            {data.map((entry, index) => {
                return (
                    <Grid item xs={12} key={index}>
                        {entry[field]}
                    </Grid>
                )
            })}
        </Grid>
    )
}

const DNSDBTextHandler = (props) => {
    console.log(props)
    const [queryParams, setQueryParams] = useState({
        query: props.queryData.query,
        chunk_size: props.queryData.limit,
        format: props.queryData.format,
        offset: 0
    })

    const [queryResults, setQueryResults] = useState(null)

    useEffect(() => {
        setQueryParams(update(queryParams, {
            query: {$set: props.queryData.query},
            chunk_size: {$set: props.queryData.limit},
            format: {$set: props.queryData.format},
            offset: {$set: 0}
        }))
    }, [props.queryData])

    useEffect(() => {
        fetchData()
    }, [queryParams])


    const fetchData = () => {
        const asyncfetch = async () => {

        }

        asyncfetch()
    }

    if (queryResults == null) {
        return <React.Fragment>Loading</React.Fragment>
    }

    if (queryParams.format === 'JSON') {
        return <JSONHandler data={queryResults.results}/>
    } else if (queryParams.format === 'CSV') {
        return <CSVHandler data={queryResults.results} />
    } else if (queryParams.format === 'LIST') {
        return <ListHandler data={queryResults.results} field={props.queryData.field} />
    } else {
        return (
            <React.Fragment>

            </React.Fragment>
        )
    }

}

export default DNSDBTextHandler