def test_global(client):
    response = client.get("/api/v2/session/global")
    assert response.status_code == 200


def test_put(client):
    response = client.put(
        '/api/v2/session/global',
        json={
            'pi': 3, 'name': 'global!', 'development': True
        })
    print(response.get_json())
    assert response.status_code == 200
    response = client.get('/api/v2/session/global')
    json_data = response.get_json()
    assert json_data['name'] == 'global!'
