from pathlib import Path
from typing import Self

import polars as pl
import pytest
from backend_test.etl import Etl

DATA_DIR = Path(__file__).parent.parent / "data"


class TestEtl:
    def test_etl(self: Self) -> None:
        etl = Etl()
        etl.run(Path("data"))
        df = pl.read_parquet(DATA_DIR / "user_metrics.parquet")
        assert df.columns == ["user_id", "user_name", "n_experiments", "top_compound", "mean_experiment_run_time"]
        alice = df.row(by_predicate=pl.col("user_name") == "Alice")
        # Alice is a good test case because there are 2 experiments and a single most frequent compound
        # Alice tested C20H25N3O once, C21H30O2 ** twice, and C8H11NO2 once
        #                     user  exps compound   runtime
        assert alice == (1, "Alice", 2, "C21H30O2", (10 + 15) / 2)


if __name__ == "__main__":
    pytest.main()
