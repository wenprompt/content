from httpx import AsyncClient


async def test_generate_job(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "P"})
    pid = r.json()["id"]
    await client.post(f"/api/projects/{pid}/shots", json={"name": "S1"})
    await client.post(f"/api/projects/{pid}/shots", json={"name": "S2"})

    r = await client.post(f"/api/projects/{pid}/generate")
    assert r.status_code == 201
    assert r.json()["status"] == "pending"
    assert r.json()["total_shots"] == 2


async def test_get_job(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "P"})
    pid = r.json()["id"]
    r = await client.post(f"/api/projects/{pid}/generate")
    jid = r.json()["id"]

    r = await client.get(f"/api/jobs/{jid}")
    assert r.status_code == 200
    assert r.json()["status"] == "pending"


async def test_get_job_not_found(client: AsyncClient) -> None:
    r = await client.get("/api/jobs/nonexistent")
    assert r.status_code == 404


async def test_cancel_job(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "P"})
    pid = r.json()["id"]
    r = await client.post(f"/api/projects/{pid}/generate")
    jid = r.json()["id"]

    r = await client.post(f"/api/jobs/{jid}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


async def test_list_jobs(client: AsyncClient) -> None:
    r = await client.post("/api/projects", json={"name": "P"})
    pid = r.json()["id"]
    await client.post(f"/api/projects/{pid}/generate")
    await client.post(f"/api/projects/{pid}/generate")

    r = await client.get(f"/api/projects/{pid}/jobs")
    assert r.status_code == 200
    assert len(r.json()) == 2
