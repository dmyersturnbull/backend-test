import asyncio
import os
from functools import cached_property
from pathlib import Path
from typing import Any, Self

import psycopg_pool
from fastapi import FastAPI, HTTPException
from msgpack_asgi import MessagePackMiddleware
from psycopg_pool import AsyncConnectionPool
from starlette.background import BackgroundTasks
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware

from backend_test.etl import Etl

if os.name == "nt":
    # workaround for asyncio loop policy for Windows users
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# use get() instead of [] to allow testing parts of the API without Postgres
conn_info = os.environ.get("POSTGRES_URI")


class _ConnPool:
    @cached_property
    def instance(self: Self) -> AsyncConnectionPool:
        return psycopg_pool.AsyncConnectionPool(conninfo=conn_info, open=True)


POOL = _ConnPool()

app = FastAPI()

app.add_middleware(ServerErrorMiddleware)
app.add_middleware(ExceptionMiddleware)
app.add_middleware(MessagePackMiddleware)


async def execute(select: str, data: tuple[Any, ...]) -> None:
    """
    Executes a PostgreSQL query, returning nothing.
    """
    # row_factory=dict_row is broken
    async with POOL.instance.connection() as conn, conn.cursor() as cursor:
        await cursor.execute(select, data)


async def fetch_one(select: str, data: tuple[Any, ...]) -> tuple:
    """
    Executes a PostgreSQL query, returning the first result.
    """
    # row_factory=dict_row is broken
    async with POOL.instance.connection() as conn, conn.cursor() as cursor:
        await cursor.execute(select, data)
        return await cursor.fetchone()


@app.get("/")
def get() -> None:
    """
    Just tells a client where to go.
    """
    raise HTTPException(status_code=404, detail="Use GET /user/<id> or PUT /<directory>")


@app.get("/user/{user_id}")
async def get_features(user_id: int) -> dict:
    """
    Gets features for any particular user.
    """
    print(f"Received GET: '{user_id}'")
    data = await fetch_one(
        "SELECT n_experiments, top_compound, mean_experiment_run_time FROM user_metrics WHERE user_id=%s;",
        (user_id,),
    )
    if data is None:
        raise HTTPException(status_code=404, detail=f"No user with ID '{user_id}'")
    print(f"Sending {type(data)}: '{data}'")
    return dict(zip(["n_experiments", "top_compound", "mean_experiment_run_time"], data, strict=True))


async def etl(directory: Path) -> None:
    """
    Runs the ETL pipeline asynchronously.
    """
    metrics = Etl().run(Path(directory))
    for row in metrics.iter_rows():
        # we'll just let it fail if it already exists
        await execute("INSERT INTO user_metrics VALUES(%s, %s, %s, %s, %s)", row)
    # looks like the adbc engine is incomplete; this won't work
    # also, using any other engine requires Pandas as a dependency due to a bug
    # that greatly increased both the build and startup times
    # can uncomment at a later date if these upstream issues are fixed
    # metrics.write_database(table_name="user_metrics", connection_uri=conn_info, engine="adbc")


@app.post("/{directory}")
async def post_data(directory: str, background_tasks: BackgroundTasks) -> dict:
    """
    On POST, submits the data to the ETL pipeline, then returns automatically.
    """
    print(f"Received POST: '{directory}'")
    # FastAPI is smart enough to know to execute this async (because etl() is declared async)
    background_tasks.add_task(etl, Path(directory))
    return {"message": f"Processing {directory}"}
