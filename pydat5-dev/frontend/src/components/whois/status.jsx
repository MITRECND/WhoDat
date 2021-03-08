import React, {useState, useEffect} from 'react'

import {makeStyles} from '@material-ui/core/styles'
import Grid from '@material-ui/core/Grid'
import Typography from '@material-ui/core/Typography'
import Tooltip from '@material-ui/core/Tooltip'
import Badge from '@material-ui/core/Badge'
import StorageIcon from '@material-ui/icons/Storage';
import CircularProgress from '@material-ui/core/CircularProgress'

import {statusFetcher} from '../helpers/fetchers'


const useStatusStyles = makeStyles(() => ({
    clusterGreenStatusBadge: {
        backgroundColor: "green"
    },
    clusterYellowStatusBadge: {
        backgroundColor: "yellow"
    },
    clusterRedStatusBadge: {
        backgroundColor: "red"
    },
    clusterUnknownStatusBadge: {
        backgroundColor: "gray"
    }
}))

const ClusterStatus = ({}) => {
    const statusClasses = useStatusStyles()
    const [fetching, setFetching] = useState(false)
    const [loaded, setLoaded] = useState(false)
    const [clusterStatus, setClusterStats] = useState({timestamp: 0})
    const timeout = 30 * 10000 // convert to ms

    const fetchStatus = () => {
        const asyncfetch = async () => {
            try {
                let results = await statusFetcher()

                let clusterstatus = {
                    last: results.last,
                    records: results.records,
                }

                switch (results.health) {
                    case "green":
                        clusterstatus.color = statusClasses.clusterGreenStatusBadge
                        clusterstatus.color_string = "Green"
                        break;
                    case "yellow":
                        clusterstatus.color = statusClasses.clusterYellowStatusBadge
                        clusterstatus.color_string = "Yellow"
                        break;
                    case "red":
                        clusterstatus.color = statusClasses.clusterRedStatusBadge
                        clusterstatus.color_string = "Red"
                        break;
                    default:
                        clusterstatus.color = statusClasses.clusterUnknownStatusBadge
                        clusterstatus.color_string = "Unknown"
                }

                setClusterStats({
                    ...clusterstatus,
                    timestamp: Date.now()
                })
                setLoaded(true)
            } catch (err) {
                console.log(err)
            } finally {
                setFetching(false)
            }
        }

        asyncfetch()
    }

    useEffect(() => {
        if (!fetching && Date.now() - clusterStatus.timestamp > timeout){
            setLoaded(false)
            setFetching(true)
            fetchStatus()
        }
    })

    return (
        <React.Fragment>
            {!loaded &&
                <CircularProgress
                    size={"1.5rem"}
                />
            }
            {loaded &&
            <Grid container spacing={1} justify="flex-start">
                <Grid item xs={12}>
                    <React.Fragment>
                        <Tooltip title={`Cluster Status: ${clusterStatus.color_string}`} placement="left">
                            <Badge
                                overlap="circle"
                                variant="dot"
                                badgeContent=" "
                                classes={{badge: clusterStatus.color}}
                            >
                                <StorageIcon/>
                            </Badge>
                        </Tooltip>

                        <Typography display='inline'>
                            &nbsp; Last Ingest: {clusterStatus.last}  Records: {clusterStatus.records}
                        </Typography>
                    </React.Fragment>
                </Grid>
            </Grid>
            }
        </React.Fragment>
    )

}


export default ClusterStatus