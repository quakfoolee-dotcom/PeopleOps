import asyncio
import base64

import httpx

from app.main import app


def test_text_attachment_is_extracted_without_persistence() -> None:
    async def post_attachment() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/attachments/extract",
                json={
                    "filename": "remote-work-details.txt",
                    "media_type": "text/plain",
                    "content_base64": base64.b64encode(
                        b"Destination: Germany\nDuration: six weeks"
                    ).decode("ascii"),
                },
            )

    response = asyncio.run(post_attachment())

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "remote-work-details.txt"
    assert "Germany" in payload["extracted_text"]
    assert payload["truncated"] is False


def test_attachment_endpoint_rejects_unsupported_and_invalid_content() -> None:
    async def post(payload: dict[str, str]) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/attachments/extract", json=payload)

    unsupported = asyncio.run(
        post(
            {
                "filename": "employee-data.csv",
                "media_type": "text/plain",
                "content_base64": base64.b64encode(b"name,value").decode("ascii"),
            }
        )
    )
    invalid_base64 = asyncio.run(
        post(
            {
                "filename": "notes.txt",
                "media_type": "text/plain",
                "content_base64": "not-valid-base64",
            }
        )
    )

    assert unsupported.status_code == 422
    assert invalid_base64.status_code == 422
