from pathlib import Path

from datasets import Dataset
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, expr, lower, regexp_replace


def run_etl_pipeline():
    print("Starting Spark ETL...")

    spark = (
        SparkSession.builder.appName("FakeNews_ETL")
        .config("spark.driver.memory", "4g")
        .getOrCreate()
    )

    try:
        latest_training_csv = Path("data/datasets/latest/training_dataset.csv")
        raw_glob = "data/raw/*.csv"

        if latest_training_csv.exists():
            input_path = str(latest_training_csv)
            print(f"Using dataset: {input_path}")
        else:
            input_path = raw_glob
            print(f"Using raw files: {input_path}")

        df = (
            spark.read.option("header", "true")
            .option("multiLine", "true")
            .option("quote", '"')
            .option("escape", '"')
            .csv(input_path)
        )

        required = {"title", "content", "label"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df_clean = df.select(
            regexp_replace(lower(col("title")), r"[^a-zA-Z0-9\s]", "").alias("title"),
            regexp_replace(lower(col("content")), r"[^a-zA-Z0-9\s]", "").alias("content"),
            expr("try_cast(label as int)").alias("label"),
        )

        df_clean = df_clean.dropna(subset=["title", "content", "label"])

        parquet_path = Path("data/processed/training_ready.parquet")
        pandas_df = df_clean.toPandas()

        try:
            df_clean.write.mode("overwrite").parquet(str(parquet_path))
            print("Parquet dataset created with Spark.")
        except Exception as spark_write_error:
            print(f"Spark parquet write failed, using pandas fallback: {spark_write_error}")
            parquet_path.parent.mkdir(parents=True, exist_ok=True)
            fallback_path = parquet_path.parent / "training_ready_fallback.parquet"
            pandas_df.to_parquet(fallback_path, index=False)
            print(f"Parquet dataset created with pandas: {fallback_path}")

        hf_ds = Dataset.from_pandas(pandas_df)
        hf_ds.save_to_disk("data/processed/hf_dataset")

        print("Data lake enriched and ready for training.")

    except Exception as e:
        import traceback

        print(f"ETL failed: {e}")
        traceback.print_exc()

    finally:
        spark.stop()


if __name__ == "__main__":
    run_etl_pipeline()
