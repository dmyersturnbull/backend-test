# Backend example

ETL pipeline example.
Built with FastAPI, Hypercorn, PostgreSQL, Polars, and Docker Compose.

- Run: `docker compose up` (see `bin/run.sh`)
- Trigger ETL: `POST` to `/<directory>` (see `bin/post_data.sh`)
- Get loaded data: `GET` from `/user/<user_id>` (see `bin/get_data.sh`)
- Test: `hatch run test` (after `pip install hatch`)
- Lint: `hatch run lint`
