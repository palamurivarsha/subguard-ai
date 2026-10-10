from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, upper, trim, when


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "clean_transactions.parquet"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "normalized_transactions.parquet"
)


spark = (
    SparkSession.builder
    .master("local[1]")
    .appName("SubGuard-Merchant-Normalization")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

try:
    # Read Parquet using PyArrow to avoid Windows Hadoop issues
    arrow_table = pq.read_table(str(INPUT_PATH))
    pandas_df = arrow_table.to_pandas()

    # Remove ground-truth labels from transformation inputs
    ground_truth_columns = [
        "merchant_ground_truth",
        "is_subscription_ground_truth",
        "event_type_ground_truth",
    ]

    labels_df = pandas_df[
        ["transaction_id", "merchant_ground_truth"]
    ].copy()

    features_df = pandas_df.drop(
        columns=ground_truth_columns,
        errors="ignore"
    )

    # Use Spark for merchant normalization
    df = spark.createDataFrame(features_df)

    description = upper(trim(col("description")))


    normalized_df = df.withColumn(
        "normalized_merchant",
        when(description.contains("NETFLIX"), "NETFLIX")
        .when(description.contains("SPOTIFY"), "SPOTIFY")
        .when(description.contains("ADOBE"), "ADOBE")
        .when(
            description.contains("ICLOUD")
            | description.contains("APPLE.COM/BILL"),
            "ICLOUD"
        )
        .when(
            description.contains("PLANET FITNESS")
            | description.contains("PLANETFITNESS")
            | description.rlike(r"\bPF MEMBERSHIP\b"),
            "PLANET FITNESS"
        )
        .when(description.contains("CANVA"), "CANVA")
            .when(
        description.contains("MICROSOFT 365")
        | description.contains("MSFT"),
        "MICROSOFT 365"
    )
        .when(description.contains("MICROSOFT"), "MICROSOFT")
        .when(description.contains("WALMART"), "WALMART SUPERCENTER")
        .when(description.contains("TARGET"), "TARGET")
        .when(description.contains("AMAZON"), "AMAZON MARKETPLACE")
        .when(description.contains("STARBUCKS"), "STARBUCKS")
        .when(description.contains("SHELL"), "SHELL OIL")
        .when(description.contains("CHIPOTLE"), "CHIPOTLE")
        .when(description.contains("CVS"), "CVS PHARMACY")
        .when(description.contains("WALGREENS"), "WALGREENS")
        .when(description.contains("KROGER"), "KROGER")
        .when(description.contains("UBER"), "UBER")
        .when(description.contains("DOORDASH"), "DOORDASH")
        .when(description.contains("HOME DEPOT"), "HOME DEPOT")
        .otherwise("UNKNOWN")
    )


    print("\n========== MERCHANT NORMALIZATION ==========")

    normalized_df.select(
        "description", "normalized_merchant"
    ).show(20, truncate=False)

    # Convert to Pandas only for local Parquet output
    result_df = normalized_df.toPandas()

    # Reattach ground truth strictly for offline evaluation
    result_df = result_df.merge(
        labels_df,
        on="transaction_id",
        how="left",
        validate="one_to_one",
    )

    # Save the normalized dataset
    table = pa.Table.from_pandas(
        result_df,
        preserve_index=False
    )

    pq.write_table(table, str(OUTPUT_PATH))

    print(f"\nTransactions processed: {len(result_df)}")
    print(f"Saved to: {OUTPUT_PATH}")

    # Evaluate merchant normalization
    matches = (
        result_df["normalized_merchant"].astype(str).str.upper()
        == result_df["merchant_ground_truth"].astype(str).str.upper()
    )

    accuracy = matches.mean() * 100

    print(f"Merchant normalization accuracy: {accuracy:.2f}%")

    print("\n========== NORMALIZATION COMPLETE ==========")

finally:
    spark.stop()
