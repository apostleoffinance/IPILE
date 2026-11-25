import base64
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register


PDF_STATEMENT = base64.b64decode(
    "JVBERi0xLjMKJZOMi54gUmVwb3J0TGFiIEdlbmVyYXRlZCBQREYgZG9jdW1lbnQgKG9wZW5zb3VyY2Up"
    "CjEgMCBvYmoKPDwKL0YxIDIgMCBSCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9CYXNlRm9udCAvSGVsdmV0"
    "aWNhIC9FbmNvZGluZyAvV2luQW5zaUVuY29kaW5nIC9OYW1lIC9GMSAvU3VidHlwZSAvVHlwZTEgL1R5"
    "cGUgL0ZvbnQKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL0NvbnRlbnRzIDcgMCBSIC9NZWRpYUJveCBbIDAg"
    "MCA1OTUuMjc1NiA4NDEuODg5OCBdIC9QYXJlbnQgNiAwIFIgL1Jlc291cmNlcyA8PAovRm9udCAxIDAg"
    "UiAvUHJvY1NldCBbIC9QREYgL1RleHQgL0ltYWdlQiAvSW1hZ2VDIC9JbWFnZUkgXQo+PiAvUm90YXRl"
    "IDAgL1RyYW5zIDw8Cgo+PiAKICAvVHlwZSAvUGFnZQo+PgplbmRvYmoKNCAwIG9iago8PAovUGFnZU1v"
    "ZGUgL1VzZU5vbmUgL1BhZ2VzIDYgMCBSIC9UeXBlIC9DYXRhbG9nCj4+CmVuZG9iago1IDAgb2JqCjw8"
    "Ci9BdXRob3IgKGFub255bW91cykgL0NyZWF0aW9uRGF0ZSAoRDoyMDI2MTEyNTEyMzI1MyswMCcwMCcp"
    "IC9DcmVhdG9yIChhbm9ueW1vdXMpIC9LZXl3b3JkcyAoKSAvTW9kRGF0ZSAoRDoyMDI2MTEyNTEyMzI1"
    "MyswMCcwMCcpIC9Qcm9kdWNlciAoUmVwb3J0TGFiIFBERiBMaWJyYXJ5IC0gXChvcGVuc291cmNlXCkp"
    "IAogIC9TdWJqZWN0ICh1bnNwZWNpZmllZCkgL1RpdGxlICh1bnRpdGxlZCkgL1RyYXBwZWQgL0ZhbHNl"
    "Cj4+CmVuZG9iago2IDAgb2JqCjw8Ci9Db3VudCAxIC9LaWRzIFsgMyAwIFIgXSAvVHlwZSAvUGFnZXMK"
    "Pj4KZW5kb2JqCjcgMCBvYmoKPDwKL0ZpbHRlciBbIC9BU0NJSTg1RGVjb2RlIC9GbGF0ZURlY29kZSBd"
    "IC9MZW5ndGggMjA3Cj4+CnN0cmVhbQpHYXJwI2gkU2EhJi1fIT1UQWoqVllWcmhoPGp0QSMiVTQ8JS9A"
    "cSIsNUhHVitxc11GWytrLXFFYD5RdEFUT0UsWUJhTyxgZWpmcDtrVCRaaiJiIjZSI0c3Tys+XmZWQ0o7"
    "Q0dfJWM3bldiXU1GKlpANWNEWURkUCIvIlk8UlJwME8rZTFSRzVkJlM4ZT1IN2YkMSlANTE5TzorRDlN"
    "IjRYRiNVOHI5cFVeV29SZCluOSRKK0UvMTlNITo9Kj41azA7RUNOJ1pxN2FHaVE0fj5lbmRzdHJlYW0K"
    "ZW5kb2JqCnhyZWYKMCA4CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDA2MSAwMDAwMCBuIAowMDAw"
    "MDAwMDkyIDAwMDAwIG4gCjAwMDAwMDAxOTkgMDAwMDAgbiAKMDAwMDAwMDQwMiAwMDAwMCBuIAowMDAw"
    "MDAwNDcwIDAwMDAwIG4gCjAwMDAwMDA3MzEgMDAwMDAgbiAKMDAwMDAwMDc5MCAwMDAwMCBuIAp0cmFp"
    "bGVyCjw8Ci9JRCAKWzw2NjY2Y2YzZTYxY2YxN2Y5NTIyODVjNDIyNzg2MTE3OT48NjY2NmNmM2U2MWNm"
    "MTdmOTUyMjg1YzQyMjc4NjExNzk+XQolIFJlcG9ydExhYiBnZW5lcmF0ZWQgUERGIGRvY3VtZW50IC0t"
    "IGRpZ2VzdCAob3BlbnNvdXJjZSkKCi9JbmZvIDUgMCBSCi9Sb290IDQgMCBSCi9TaXplIDgKPj4Kc3Rh"
    "cnR4cmVmCjEwODcKJSVFT0YK"
)


def test_pdf_statement_upload_previews_before_commit(client: TestClient) -> None:
    register(client, "pdf-import@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "200000.00"},
    ).json()

    preview = client.post(
        "/api/v1/imports/preview-upload",
        data={"account_id": account["id"]},
        files={"file": ("statement.pdf", PDF_STATEMENT, "application/pdf")},
    )
    assert preview.status_code == 201, preview.text
    assert preview.json()["status"] == "pending_review"
    assert preview.json()["result"]["row_count"] == 2
    assert client.get("/api/v1/transactions").json() == []
    assert Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"]) == Decimal(
        "200000.00"
    )

    committed = client.post(
        f"/api/v1/imports/jobs/{preview.json()['id']}/commit",
        json={"account_id": account["id"]},
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["status"] == "committed"
    assert committed.json()["created_count"] == 2
    transactions = client.get("/api/v1/transactions").json()
    assert {row["external_id"] for row in transactions} == {"pdf-pay-1", "pdf-pos-1"}
    assert Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"]) == Decimal(
        "238000.00"
    )
