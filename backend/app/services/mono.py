from __future__ import annotations

from typing import Any

import httpx

class MonoAPIError(RuntimeError):
    """Mono API rejected a request or returned an unusable response."""

class MonoReauthRequired(MonoAPIError):
    """Mono requires renewed customer authorisation."""

class MonoClient:
    BASE_URL = "https://api.withmono.com"

    def __init__(self, secret_key: str, *, transport: httpx.BaseTransport | None = None):
        self.client = httpx.Client(
            base_url=self.BASE_URL, timeout=httpx.Timeout(15.0, connect=5.0),
            transport=transport,
            headers={"accept": "application/json", "content-type": "application/json", "mono-sec-key": secret_key},
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        try:
            response = self.client.request(method, path, **kwargs)
            if response.status_code in {401, 403}:
                raise MonoReauthRequired("Mono requires the customer to re-authorise this account.")
            response.raise_for_status()
            payload = response.json()
        except MonoReauthRequired:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise MonoAPIError("Mono could not complete the requested operation.") from exc
        if not isinstance(payload, dict):
            raise MonoAPIError("Mono returned an invalid response.")
        if payload.get("status") in {"failed", "error"}:
            if "reauthor" in str(payload.get("message") or "").lower():
                raise MonoReauthRequired("Mono requires the customer to re-authorise this account.")
            raise MonoAPIError("Mono rejected the requested operation.")
        return payload

    @staticmethod
    def _link_url(payload: dict) -> str:
        data = payload.get("data") or {}
        url = data.get("mono_url") if isinstance(data, dict) else None
        if not isinstance(url, str) or not url.startswith("https://link.mono.co/"):
            raise MonoAPIError("Mono did not return a valid account-link URL.")
        return url

    def initiate_linking(self, *, customer_name: str, customer_email: str, reference: str, redirect_url: str) -> str:
        payload = self._request("POST", "/v2/accounts/initiate", json={
            "customer": {"name": customer_name, "email": customer_email},
            "scope": "auth", "meta": {"ref": reference}, "redirect_url": redirect_url,
        })
        return self._link_url(payload)

    def initiate_reauthorization(self, *, account_id: str, reference: str, redirect_url: str) -> str:
        payload = self._request("POST", "/v2/accounts/initiate", json={
            "account": account_id, "scope": "reauth", "meta": {"ref": reference}, "redirect_url": redirect_url,
        })
        return self._link_url(payload)

    def fetch_transactions(self, account_id: str, *, page: int = 1) -> tuple[list[dict], dict]:
        payload = self._request("GET", f"/v2/{account_id}/transactions", params={"page": page})
        data, meta = payload.get("data"), payload.get("meta") or {}
        if not isinstance(data, list) or not isinstance(meta, dict):
            raise MonoAPIError("Mono returned an invalid transaction page.")
        return [row for row in data if isinstance(row, dict)], meta

    def unlink_account(self, account_id: str) -> None:
        self._request("POST", f"/v2/accounts/{account_id}/unlink")

    def close(self) -> None:
        self.client.close()
