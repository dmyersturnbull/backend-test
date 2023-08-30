from io import StringIO
from pathlib import Path
from typing import Self

import polars as pl


def _read_csv(path: Path) -> pl.DataFrame:
    # because Polars can't take a multi-char delimiter:
    # read in, remove tabs, then load using , as the delimiter
    contents = path.read_text(encoding="utf-8").replace("\t", "")
    return pl.read_csv(StringIO(contents))


class Etl:
    def run(self: Self, directory: Path) -> pl.DataFrame:
        """
        Extracts, transforms, and loads data from the directory.
        Transforms the data and saves a Parquet file in the same directory (for extracting additional features).
        Then extracts established features, saves a Parquet file (again, for caching), and returns.

        Arguments:
            directory: A directory containing `compounds.csv`,`users.csv`, and `user_experiments.csv`

        Returns:
            A polars DataFrame
        """
        metrics_file = directory / "user_metrics.parquet"
        data_file = directory / "data.parquet"
        if metrics_file.exists():
            return pl.read_parquet(metrics_file)
        if data_file.exists():
            data = pl.read_parquet(data_file)
        else:
            data = self._merge(directory)
            data.write_parquet(directory / "data.parquet")
        metrics = self._extract_user_metrics(data)
        # technically not needed, but maybe we'll want to extract other features in the future
        metrics.write_parquet(metrics_file)
        return metrics

    def _merge(self: Self, directory: Path) -> pl.DataFrame:
        compounds = _read_csv(directory / "compounds.csv")
        experiments = _read_csv(directory / "user_experiments.csv")
        # just join the user and experiment frames to get user_name
        users = _read_csv(directory / "users.csv")
        users = users.rename({"name": "user_name"}).select("user_id", "user_name")
        experiments = experiments.rename({"experiment_compound_ids": "c_ids"})
        experiments = experiments.join(users, on="user_id")
        # split compound_id by ; and explode by it to get multiple rows for faster processing
        experiments = (
            experiments.select(
                "user_id",
                "user_name",
                "experiment_id",
                "experiment_run_time",
                pl.col("c_ids").str.split(";").list.eval(pl.element().cast(pl.Int32)),
            )
            .explode("c_ids")
            .rename({"c_ids": "compound_id"})
        )
        # map compound IDs to their names and structures
        c_id_to_structure = dict(compounds.select("compound_id", "compound_structure").iter_rows())
        c_id_to_name = dict(compounds.select("compound_id", "compound_name").iter_rows())
        experiments = experiments.with_columns(
            pl.col("compound_id").apply(c_id_to_structure.__getitem__).alias("compound_structure"),
            pl.col("compound_id").apply(c_id_to_name.__getitem__).alias("compound_name"),
        )
        return experiments

    def _extract_user_metrics(self: Self, df: pl.DataFrame) -> pl.DataFrame:
        # get N experiments per user
        n_experiments = (
            df.select("user_id", "user_name", "experiment_id").groupby(["user_id", "user_name"]).n_unique()
        ).rename({"experiment_id": "n_experiments"})
        # Get most-used compound per user
        top_compounds = (df.groupby(["user_id", "user_name"]).agg(pl.col("compound_structure").mode().first())).rename(
            {"compound_structure": "top_compound"},
        )
        # Get mean run time per user
        run_times = (
            df.select("user_id", "user_name", "experiment_run_time")
            .groupby(["user_id", "user_name"])
            .agg(pl.mean("experiment_run_time").alias("mean_experiment_run_time"))
        )
        # Join the three metric tables together; keep user_id and user_name
        user_metrics = n_experiments.join(top_compounds, on=["user_id", "user_name"])
        user_metrics = user_metrics.join(run_times, on=["user_id", "user_name"])
        return user_metrics
