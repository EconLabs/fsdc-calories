from datetime import datetime
from .jp_imports.src.data.data_process import DataTrade
import altair as alt
import polars as pl
import os
import pandas as pd


class DataCal(DataTrade):
    def __init__(
        self,
        saving_dir: str = "data/",
        database_file: str = "data.ddb",
        log_file: str = "data_process.log",
    ):
        super().__init__(saving_dir, database_file, log_file)

    def gen_nuti_data(self) -> pl.DataFrame:
        if not os.path.exists(f"{self.saving_dir}external/nutri_matrix.parquet"):
            self.pull_file(
                url="https://github.com/EconLabs/fsdc-calories/raw/refs/heads/master/data/external/nutri_matrix.parquet",
                filename=f"{self.saving_dir}external/nutri_matrix.parquet",
            )
        nutri_df = pl.read_parquet(f"{self.saving_dir}external/nutri_matrix.parquet")
        df = self.process_int_org(time_frame="monthly", level="hts").to_polars()
        nutri_df = nutri_df.rename({"schedule_b": "hts_code"}).drop("description")
        df = df.with_columns(hts_code=pl.col("hts_code").str.slice(0, 4)).drop(
            pl.col("hts_id")
        )

        df = df.join(nutri_df, on="hts_code", how="inner")
        df = df.with_columns(
            total_calories=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("calories"),
            total_fats=(pl.col("qty_imports") - pl.col("qty_exports")) * pl.col("fats"),
            total_sugars=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("sugars"),
            total_protein=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("protein"),
            total_saturated_fat_g=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("saturated_fat_g"),
            total_cholesterol_mg=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("cholesterol_mg"),
            total_sodium_mg=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("sodium_mg"),
            total_carbohydrate_g=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("carbohydrate_g"),
            total_fiber_g=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("fiber_g"),
            total_sugar_g=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("sugar_g"),
            total_vitamin_d_iu=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("vitamin_d_iu"),
            total_calcium_mg=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("calcium_mg"),
            total_potassium_mg=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("potassium_mg"),
            total_iron_mg=(pl.col("qty_imports") - pl.col("qty_exports"))
            * pl.col("iron_mg"),
        )
        cols = [
            "total_calories",
            "total_fats",
            "total_sugars",
            "total_protein",
            "total_saturated_fat_g",
            "total_cholesterol_mg",
            "total_sodium_mg",
            "total_carbohydrate_g",
            "total_fiber_g",
            "total_sugar_g",
            "total_vitamin_d_iu",
            "total_calcium_mg",
            "total_potassium_mg",
            "total_iron_mg",
        ]
        df = df.with_columns(
            **{
                f"{x}_ecdf": pl.int_range(1, pl.len() + 1).sort_by(pl.arg_sort_by(x))
                / pl.len()
                for x in cols  # change df.columns to list of columns for subset only
            }
        )
        df = df.filter(pl.col("total_fats_ecdf") < 0.9999)
        df = df.filter(pl.col("total_sugars_ecdf") < 0.9999)
        df = df.filter(pl.col("total_protein_ecdf") < 0.9999)
        df = df.filter(pl.col("total_saturated_fat_g_ecdf") < 0.9999)
        df = df.filter(pl.col("total_sodium_mg_ecdf") < 0.9999)
        df = df.filter(pl.col("total_cholesterol_mg_ecdf") < 0.9999)
        df = df.filter(pl.col("total_carbohydrate_g_ecdf") < 0.9999)
        df = df.filter(pl.col("total_fiber_g_ecdf") < 0.9999)
        df = df.filter(pl.col("total_sugar_g_ecdf") < 0.9999)
        df = df.filter(pl.col("total_vitamin_d_iu_ecdf") < 0.9999)
        df = df.filter(pl.col("total_calcium_mg_ecdf") < 0.9999)
        df = df.filter(pl.col("total_potassium_mg_ecdf") < 0.9999)
        df = df.filter(pl.col("total_iron_mg_ecdf") < 0.9999)
        df = df.group_by(["year", "month"]).agg(pl.all().sum())
        df = df.with_columns(datetime=pl.datetime(pl.col("year"), pl.col("month"), 1))

        return df

    def gen_price_rankings(self) -> pl.DataFrame:
        
        df = self.process_price(agriculture_filter=True).to_pandas()
        
        month = datetime.now().month if datetime.now().month != 1 else 12
        year = datetime.now().year if datetime.now().month != 1 else datetime.now().year - 1
        
        # Handle case where latest available data is older than last month
        month = min(df["date"].max().month, month)
        year = min(df["date"].max().year, year)
        
        filter = (df['date'].dt.month == month) & (df['date'].dt.year == year)
        df = df[filter]
        
        cols = ["hs4", "date", "prev_year_imports", "prev_year_exports"]
        df = df[cols]

        return df

    def gen_graphs(self):
        cols = [
            "total_calories",
            "total_fats",
            "total_sugars",
            "total_protein",
            "total_saturated_fat_g",
            "total_cholesterol_mg",
            "total_sodium_mg",
            "total_carbohydrate_g",
            "total_fiber_g",
            "total_sugar_g",
            "total_vitamin_d_iu",
            "total_calcium_mg",
            "total_potassium_mg",
            "total_iron_mg",
        ]
        dropdown = alt.binding_select(options=cols, name="Y-axis column ")
        ycol_param = alt.param(value="total_iron_mg", bind=dropdown)
        chart = (
            alt.Chart(self.gen_nuti_data().sort(pl.col("datetime")))
            .mark_line()
            .encode(x="datetime:T", y=alt.Y("y:Q").title(""))
            .transform_calculate(y=f"datum[{ycol_param.name}]")
            .add_params(ycol_param)
            .properties(width="container")
        )

        return chart
