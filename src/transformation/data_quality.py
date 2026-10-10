from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when


# --------------------------------------------------
# Project paths
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = PROJECT_ROOT / "data" / "synthetic" / "bank_transactions.csv"

OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "clean_transactions"


# --------------------------------------------------
# Create Spark session
# --------------------------------------------------
spark = (
    SparkSession.builder
    .appName("SubGuard-Data-Quality")
    .master("local[*]")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")
spark.sparkContext._jsc.hadoopConfiguration().set(
    "fs.file.impl",
    "org.apache.hadoop.fs.RawLocalFileSystem"
)

spark.sparkContext._jsc.hadoopConfiguration().set(
    "fs.file.impl.disable.cache",
    "true"
)

print("\n========== SUBGUARD DATA QUALITY PIPELINE ==========")

print(f"\nReading data from:\n{INPUT_PATH}")


# --------------------------------------------------
# Load raw transaction data
# --------------------------------------------------
df = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .csv(str(INPUT_PATH))
)

print(f"\nRaw transaction count: {df.count()}")

print("\nSchema:")
df.printSchema()


# --------------------------------------------------
# Null-value analysis
# --------------------------------------------------
print("\nNull values by column:")

null_counts = df.select(
    [
        count(
            when(
                col(column).isNull(),
                column
            )
        ).alias(column)
        for column in df.columns
    ]
)

null_counts.show(truncate=False)


# --------------------------------------------------
# Duplicate transaction_id detection
# --------------------------------------------------
duplicate_ids = (
    df.groupBy("transaction_id")
    .count()
    .filter(col("count") > 1)
)

duplicate_id_count = duplicate_ids.count()

print(
    f"\nDuplicate transaction IDs found: "
    f"{duplicate_id_count}"
)


# --------------------------------------------------
# Exact duplicate-row detection
# --------------------------------------------------
total_rows = df.count()
distinct_rows = df.distinct().count()

exact_duplicate_count = total_rows - distinct_rows

print(
    f"Exact duplicate rows found: "
    f"{exact_duplicate_count}"
)


# --------------------------------------------------
# Required field validation
# --------------------------------------------------
required_columns = [
    "transaction_id",
    "transaction_date",
    "description",
    "amount",
    "transaction_type",
]

invalid_required_rows = df.filter(
    col("transaction_id").isNull()
    | col("transaction_date").isNull()
    | col("description").isNull()
    | col("amount").isNull()
    | col("transaction_type").isNull()
)

invalid_count = invalid_required_rows.count()

print(
    f"Rows missing required values: "
    f"{invalid_count}"
)


# --------------------------------------------------
# Remove invalid rows
# --------------------------------------------------
clean_df = df.dropna(
    subset=required_columns
)


# --------------------------------------------------
# Remove exact duplicate rows
# --------------------------------------------------
clean_df = clean_df.dropDuplicates()


print(
    f"Rows after data-quality cleaning: "
    f"{clean_df.count()}"
)


# --------------------------------------------------
# Save processed dataset as Parquet
# --------------------------------------------------
import pyarrow as pa
import pyarrow.parquet as pq

# Convert the cleaned Spark DataFrame to Pandas
pandas_df = clean_df.toPandas()

# Convert Pandas to an Arrow table
arrow_table = pa.Table.from_pandas(
    pandas_df,
    preserve_index=False
)

# Save Parquet without using Spark's Hadoop writer
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

parquet_file = OUTPUT_PATH.parent / "clean_transactions.parquet"

pq.write_table(arrow_table, str(parquet_file))

print(f"Saved {len(pandas_df)} transactions to Parquet")

print(
    f"\nClean dataset saved to:\n{OUTPUT_PATH}"
)

print("\n========== DATA QUALITY COMPLETE ==========\n")


spark.stop()