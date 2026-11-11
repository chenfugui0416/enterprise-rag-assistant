"""MimirQ REST API client for Route B (Microservice integration mode)."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


class MimirQClientError(Exception):
    """Raised when MimirQ API returns an error or is unreachable."""


class MimirQClient:
    """Thread-safe / async client for interacting with MimirQ backend services."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        username: str = "admin",
        password: str = "AdminPassword123!",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout_seconds

        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    async def _ensure_token(self, client: httpx.AsyncClient) -> str:
        """Authenticate or return existing non-expired access token."""
        now = time.time()
        # Refresh 30 seconds before actual expiration
        if self._access_token and now < self._token_expires_at - 30:
            return self._access_token

        login_url = f"{self.base_url}/api/v1/auth/login"
        payload = {
            "identifier": self.username,
            "password": self.password,
        }
        try:
            response = await client.post(login_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            token_info = data.get("token") or {}
            access_token = token_info.get("access_token")
            expires_in = token_info.get("expires_in", 3600)
            if not access_token:
                raise MimirQClientError(f"No access token in login response: {data}")

            self._access_token = access_token
            self._token_expires_at = now + float(expires_in)
            logger.info("Successfully authenticated to MimirQ as '%s'", self.username)
            return self._access_token
        except httpx.HTTPError as exc:
            raise MimirQClientError(f"Failed to authenticate with MimirQ: {exc}") from exc

    async def retrieve(
        self,
        query: str,
        *,
        dataset_id: str | UUID,
        top_k: int = 5,
        min_score: float = 0.0,
        retrieval_mode: str = "hybrid",
    ) -> list[dict[str, Any]]:
        """Query MimirQ retrieval engine for evidence chunks."""
        dataset_id_str = str(dataset_id)
        endpoint = f"{self.base_url}/api/v1/rag/retrieve"
        body = {
            "query": query,
            "dataset_id": dataset_id_str,
            "rag_config": {
                "top_k": top_k,
                "score_threshold": min_score,
                "retrieval_mode": retrieval_mode,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            token = await self._ensure_token(client)
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            try:
                response = await client.post(endpoint, json=body, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("citations") or []
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    # Token might have been revoked; invalidate and retry once
                    self._access_token = None
                    token = await self._ensure_token(client)
                    headers["Authorization"] = f"Bearer {token}"
                    retry_resp = await client.post(endpoint, json=body, headers=headers)
                    retry_resp.raise_for_status()
                    return retry_resp.json().get("citations") or []
                raise MimirQClientError(
                    f"MimirQ retrieve failed with status {exc.response.status_code}: "
                    f"{exc.response.text}"
                ) from exc
            except httpx.HTTPError as exc:
                raise MimirQClientError(f"Network error communicating with MimirQ: {exc}") from exc

    async def upload_document(
        self,
        file_bytes: bytes,
        filename: str,
        *,
        dataset_id: str | UUID,
    ) -> dict[str, Any]:
        """Upload and trigger document processing in MimirQ."""
        endpoint = f"{self.base_url}/api/v1/documents/upload"
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            token = await self._ensure_token(client)
            headers = {"Authorization": f"Bearer {token}"}
            files = {"file": (filename, file_bytes)}
            data = {"dataset_id": str(dataset_id)}
            try:
                response = await client.post(endpoint, files=files, data=data, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as exc:
                raise MimirQClientError(f"Failed to upload document to MimirQ: {exc}") from exc
