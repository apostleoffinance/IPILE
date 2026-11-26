# ruff: noqa: I001
from datetime import date
from decimal import Decimal

from app.services.statement_extraction.models import (
    ExtractionMethod,
    ExtractionResult,
    ExtractionStatus,
    ExtractedTransaction,
    StatementAccountSection,
    StatementMetadata,
    TransactionDirection,
)

from fastapi.testclient import TestClient

from tests.conftest import register


PDF_STATEMENT = bytes.fromhex(
    """
    255044462d312e330a25938c8b9e205265706f72744c61622047656e6572617465642050444620646f63756d656e7420286f70656e736f75726365290a312030206f626a0a3c3c0a2f46312032203020520a3e3e0a656e646f626a0a322030206f626a0a3c3c0a2f42617365466f6e74202f48656c766574696361202f456e636f64696e67202f57696e416e7369456e636f64696e67202f4e616d65202f4631202f53756274797065202f5479706531202f54797065202f466f6e740a3e3e0a656e646f626a0a332030206f626a0a3c3c0a2f436f6e74656e7473203720302052202f4d65646961426f78205b20302030203539352e32373536203834312e38383938205d202f506172656e74203620302052202f5265736f7572636573203c3c0a2f466f6e74203120302052202f50726f63536574205b202f504446202f54657874202f496d61676542202f496d61676543202f496d61676549205d0a3e3e202f526f746174652030202f5472616e73203c3c0a0a3e3e200a20202f54797065202f506167650a3e3e0a656e646f626a0a342030206f626a0a3c3c0a2f506167654d6f6465202f5573654e6f6e65202f5061676573203620302052202f54797065202f436174616c6f670a3e3e0a656e646f626a0a352030206f626a0a3c3c0a2f417574686f722028616e6f6e796d6f757329202f4372656174696f6e446174652028443a32303236313132353132333235332b30302730302729202f43726561746f722028616e6f6e796d6f757329202f4b6579776f726473202829202f4d6f64446174652028443a32303236313132353132333235332b30302730302729202f50726f647563657220285265706f72744c616220504446204c696272617279202d205c286f70656e736f757263655c2929200a20202f5375626a6563742028756e73706563696669656429202f5469746c652028756e7469746c656429202f54726170706564202f46616c73650a3e3e0a656e646f626a0a362030206f626a0a3c3c0a2f436f756e742031202f4b696473205b203320302052205d202f54797065202f50616765730a3e3e0a656e646f626a0a372030206f626a0a3c3c0a2f46696c746572205b202f415343494938354465636f6465202f466c6174654465636f6465205d202f4c656e677468203230370a3e3e0a73747265616d0a47617270236824536121262d5f213d54416a2a5659567268683c6a7441232255343c252f4071222c354847562b71735d465b2b6b2d7145603e517441544f452c5942614f2c60656a66703b6b54245a6a22622236522347374f2b3e5e6656434a3b43475f2563376e57625d4d462a5a4035634459446450222f22593c525270304f2b653152473564265338653d483766243129403531394f3a2b44394d22345846235538723970555e576f5264296e39244a2b452f31394d213a3d2a3e356b303b45434e275a713761476951347e3e656e6473747265616d0a656e646f626a0a787265660a3020380a303030303030303030302036353533352066200a30303030303030303631203030303030206e200a30303030303030303932203030303030206e200a30303030303030313939203030303030206e200a30303030303030343032203030303030206e200a30303030303030343730203030303030206e200a30303030303030373331203030303030206e200a30303030303030373930203030303030206e200a747261696c65720a3c3c0a2f4944200a5b3c36363636636633653631636631376639353232383563343232373836313137393e3c36363636636633653631636631376639353232383563343232373836313137393e5d0a25205265706f72744c61622067656e6572617465642050444620646f63756d656e74202d2d2064696765737420286f70656e736f75726365290a0a2f496e666f2035203020520a2f526f6f742034203020520a2f53697a6520380a3e3e0a7374617274787265660a313038370a2525454f460a
    """
)




def _fake_extraction(rows):
    from app.services.statement_intelligence.schema import ExtractionResult
    from app.services.statement_intelligence.validation import validate_statement

    return ExtractionResult(
        rows=rows,
        extraction_method="test_pdf_layout",
        validation=validate_statement(rows),
        confidence=1.0,
    )


def _queue_worker(monkeypatch):
    from tests.conftest import TestingSessionLocal
    import app.services.statement_jobs as statement_jobs

    monkeypatch.setattr(statement_jobs, "SessionLocal", TestingSessionLocal)
    return statement_jobs


def test_statement_upload_is_queued_and_committed_only_after_review(
    client: TestClient, monkeypatch,
) -> None:
    from app.services.import_adapters import _make_row

    register(client, "pdf-import@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "200000.00"},
    ).json()
    rows = [
        _make_row(
            raw_date="2026-09-10",
            amount=Decimal("50000.00"),
            tx_type="expense",
            description="Market payment",
            external_id="pdf-pay-1",
            row_index=1,
        ),
        _make_row(
            raw_date="2026-09-11",
            amount=Decimal("12000.00"),
            tx_type="income",
            description="Refund",
            external_id="pdf-pos-1",
            row_index=2,
        ),
    ]
    worker = _queue_worker(monkeypatch)
    monkeypatch.setattr(worker, "extract_statement", lambda *_args: _fake_extraction(rows))

    queued = client.post(
        "/api/v1/imports/preview-upload",
        data={"account_id": account["id"]},
        files={"file": ("statement.pdf", PDF_STATEMENT, "application/pdf")},
    )
    assert queued.status_code == 202, queued.text
    assert queued.json()["status"] == "processing"
    assert client.get("/api/v1/transactions").json() == []
    assert worker.process_next_statement_task() is True

    preview = client.get(f"/api/v1/imports/jobs/{queued.json()['id']}")
    assert preview.status_code == 200, preview.text
    assert preview.json()["status"] == "pending_review"
    assert preview.json()["result"]["row_count"] == 2
    assert client.get("/api/v1/transactions").json() == []
    assert Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"]) == Decimal(
        "200000.00"
    )

    committed = client.post(
        f"/api/v1/imports/jobs/{queued.json()['id']}/commit",
        json={"account_id": account["id"]},
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["status"] == "committed"
    assert committed.json()["created_count"] == 2
    transactions = client.get("/api/v1/transactions").json()
    assert {row["external_id"] for row in transactions} == {"pdf-pay-1", "pdf-pos-1"}


def test_background_worker_requires_explicit_selection_for_multi_account_statement(
    client: TestClient, monkeypatch,
) -> None:
    from app.services.import_adapters import _make_row

    register(client, "multi-section-import@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "OPay Wallet", "type": "bank", "current_balance": "5000.00"},
    ).json()
    rows = [
        _make_row(
            raw_date="2026-01-01", amount=Decimal("100.00"), tx_type="expense",
            description="Wallet debit", external_id="wallet-ref", row_index=1,
            account_section="Wallet Account",
        ),
        _make_row(
            raw_date="2026-01-02", amount=Decimal("200.00"), tx_type="income",
            description="Savings credit", external_id="savings-ref", row_index=2,
            account_section="Savings Account",
        ),
    ]
    worker = _queue_worker(monkeypatch)
    monkeypatch.setattr(worker, "extract_statement", lambda *_args: _fake_extraction(rows))

    needs_choice = client.post(
        "/api/v1/imports/preview-upload",
        data={"account_id": account["id"]},
        files={"file": ("statement.pdf", b"pdf", "application/pdf")},
    )
    assert needs_choice.status_code == 202, needs_choice.text
    worker.process_next_statement_task()
    choice = client.get(f"/api/v1/imports/jobs/{needs_choice.json()['id']}").json()
    assert choice["status"] == "needs_section_selection"
    assert choice["result"]["available_sections"] == ["Savings Account", "Wallet Account"]
    assert client.get("/api/v1/transactions").json() == []

    selected = client.post(
        "/api/v1/imports/preview-upload",
        data={"account_id": account["id"], "account_section": "Wallet Account"},
        files={"file": ("statement.pdf", b"pdf", "application/pdf")},
    )
    assert selected.status_code == 202, selected.text
    worker.process_next_statement_task()
    preview = client.get(f"/api/v1/imports/jobs/{selected.json()['id']}").json()
    assert preview["status"] == "pending_review"
    assert preview["result"]["account_section"] == "Wallet Account"
    assert preview["result"]["row_count"] == 1
    assert preview["result"]["rows"][0]["external_id"] == "wallet-ref"
    assert client.get("/api/v1/transactions").json() == []
