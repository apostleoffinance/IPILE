"""Dedicated process entry point for durable statement extraction."""

if __name__ == "__main__":
    from app.services.statement_jobs import run_statement_worker

    run_statement_worker()
