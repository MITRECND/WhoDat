export const queryFetcher = async ({
    query,
    chunk_size,
    offset}
) => {

    let data = {
        'query': query,
        'chunk_size': chunk_size,
        'offset': offset
    }

    let response = await fetch (
        '/api/v2/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'

            },
            body: JSON.stringify(data)
    })

    // console.log(response)

    if (response.status === 200) {
        let jresp = await response.json()
        return jresp
    } else {
        throw response
    }
}

export const domainFetcher = async ({
    domainName
}) => {

    let data = {
        value: domainName
    }

    let response = await fetch (
        '/api/v2/domains/domainName', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'

            },
            body: JSON.stringify(data)
    })

    // console.log(response)

    if (response.status === 200) {
        let jresp = await response.json()
        return jresp
    } else {
        throw response
    }
}

