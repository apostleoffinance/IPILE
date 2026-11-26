"""Dedicated process entry point for durable statement extraction."""

import logging


if __name__ == "__main__":
    from app.services.statement_jobs import run_statement_worker

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run_statement_worker()
