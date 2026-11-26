"""Dedicated process entry point for durable statement extraction."""

from app.services.statement_jobs import run_statement_worker


if __name__ == "__main__":
    run_statement_worker()
