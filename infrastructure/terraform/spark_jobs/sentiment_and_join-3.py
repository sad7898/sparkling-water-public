import os
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import sys
from pyspark.sql import SparkSession, DataFrame, functions, types
from pyspark.sql.functions import col, pandas_udf, PandasUDFType
from pyspark.sql.types import StructType, StructField, StringType, FloatType
import argparse

RAW_REDDIT_PATH = "raw/reddit/cryptocurrency"
COIN_ALIASES = {
    "bitcoin": ["bitcoin", "btc", "₿"],
    "ethereum": ["ethereum", "eth", "ether"],
    "solana": ["solana", "sol"],
    "dogecoin": ["dogecoin", "doge"],
    "cardano": ["cardano", "ada"],
}


def initialize_spark(app_name: str):
    # Initialize Spark
    spark = SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.execution.pyspark.udf.faulthandler.enabled", "true") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
    return spark

def build_sentiment_udf():

    # Define the schema for the UDF output
    sentiment_schema = StructType([
        StructField("sentiment_label", StringType()),
        StructField("sentiment_score", FloatType())
    ])

    # Iterator-style pandas UDF
    # @pandas_udf(sentiment_schema, functionType="iterator")
    @pandas_udf(sentiment_schema, functionType=PandasUDFType.SCALAR_ITER)
    def sentiment_udf(texts_iter):
        import pandas as pd
        from transformers import pipeline

        model = pipeline(
            "sentiment-analysis",
            model="./hf_model",
            tokenizer="./hf_model",
            device=-1,
        )  # load once per worker
        for texts in texts_iter:
            labels, scores = [], []
            for t in texts.fillna(""):
                if not t.strip():
                    labels.append("neutral")
                    scores.append(0.0)
                else:
                    result = model(t[:512])[0]
                    labels.append(result["label"].lower())
                    scores.append(float(result["score"]))
            yield pd.DataFrame({"sentiment_label": labels, "sentiment_score": scores})

    return sentiment_udf


def parse_legacy_args(argv):
    input_s3 = argv[0]

    # Strip scheme and split: bucket/raw/reddit/.../YYYY/MM/DD/HH
    path = input_s3[len("s3://"):]
    parts = path.split("/")

    bucket = parts[0]
    year, month, day, hour = parts[-4:]
    start = f"{year}-{month}-{day}"
    end = start
    return bucket, start, end

@functions.udf(returnType=types.StringType())
def infer_coin(subreddit: str, title: str, text: str):
    s = (subreddit or "").lower()
    t = f"{title or ''} {text or ''}".lower()
    
    for coin, aliases in COIN_ALIASES.items():
        if s == coin:
            return coin
        for alias in aliases:
            if f" {alias} " in f" {t} ":
                return coin
    return None

def prepare_reddit(reddit_df: DataFrame):
    df = reddit_df

    if "timestamp" in df.columns:
        df = df.withColumn("created_utc", functions.to_timestamp("timestamp"))
    elif "created_utc" in df.columns:
        df = df.withColumn("created_utc", functions.to_timestamp("created_utc"))
    else:
        raise ValueError("No timestamp or created_utc column found in Reddit data")
    
    df = df.withColumn("ts_hour", functions.date_trunc("hour", functions.col("created_utc")))
    df = df.drop("created_utc")

    df = df.withColumn("coin", infer_coin(
            functions.col("subreddit"),
            functions.col("title"),
            functions.col("text")
        )
    )
 
    if "sentiment" in df.columns and "sentiment_label" not in df.columns:
        df = df.withColumnRenamed("sentiment", "sentiment_label")

    if "sentiment_score" not in df.columns:
        df = df.withColumn("sentiment_score", functions.lit(None).cast("double"))

    return df

def aggregate_sentiment(reddit_df: DataFrame):
   df = reddit_df.filter(functions.col("coin").isNotNull())


   agg = df.groupBy("coin").agg(
       functions.sum(functions.when(functions.col("sentiment_label") == "positive", 1).otherwise(0)).alias("positive_count"),
       functions.sum(functions.when(functions.col("sentiment_label") == "negative", 1).otherwise(0)).alias("negative_count"),
       functions.avg(functions.col("sentiment_score")).alias("sentiment_score"),
   )


   agg = agg.withColumn(
       "sentiment_label",
       functions.when(functions.col("sentiment_score") >= 0.2, functions.lit("positive"))
                .when(functions.col("sentiment_score") <= -0.2, functions.lit("negative"))
                .otherwise(functions.lit("neutral")),
   )

   return agg.select("coin", "sentiment_label", "sentiment_score", "positive_count", "negative_count")

def load_coingecko_data(spark: SparkSession, input_s3: str) -> DataFrame:

    path_parts = input_s3.rstrip('/').split('/')
    year, month, day, hour = path_parts[-4:]
    bucket = path_parts[2]  # Extract bucket name from s3://bucket/...
    coingecko_path = f"s3://{bucket}/raw/coingecko/*/{year}/{month}/{day}/{hour}"
    

    df = spark.read.option("recursiveFileLookup", "true") \
         .option("mode", "PERMISSIVE") \
         .option("columnNameOfCorruptRecord", "corrupt_record") \
         .json(coingecko_path)
    
    df = df.withColumn("price_timestamp", functions.to_timestamp("timestamp")) \
           .filter(functions.col("price_timestamp").isNotNull())

    filtered_count = df.count()

    schema = types.StructType([
        types.StructField("coin", types.StringType()),
        types.StructField("ts_hour", types.TimestampType()),
        types.StructField("price_usd", types.DoubleType()),
        types.StructField("price_sample_count", types.LongType()),
    ])
    if filtered_count == 0:
        return spark.createDataFrame([], schema = schema)

    
    df = df.withColumn("ts_hour", functions.date_trunc("hour", "price_timestamp")) \
           .groupBy("coin", "ts_hour") \
           .agg(functions.avg("price_usd").alias("price_usd"), functions.count("*").alias("price_sample_count")) \
           .orderBy("coin", "ts_hour")

    return df


def join_sentiment_with_price(reddit_df: DataFrame, price_df: DataFrame):
    r = reddit_df.alias("r")
    p = price_df.alias("p")

    joined_df = r.join(p, on=["coin"], how="inner")

    joined = joined_df.select(
        functions.col("coin"),
        functions.col("p.price_usd").alias("price_usd"),
        functions.col("p.price_sample_count").alias("price_sample_count"),
        functions.col("r.sentiment_label").alias("sentiment_label"),
        functions.col("r.sentiment_score").alias("sentiment_score"),
    )
    return joined

def run_job(input_s3: str, output_s3: str):
    spark = initialize_spark("SentimentAndJoin")
    
    reddit_df = spark.read.option("recursiveFileLookup", "true").json(input_s3)
    sentiment_udf = build_sentiment_udf()
    reddit_sentiment_df = reddit_df.withColumn(
        "sentiment",
        sentiment_udf(col("text"))
    ).select(
        "*",
        col("sentiment.sentiment_label").alias("sentiment_label"),
        col("sentiment.sentiment_score").alias("sentiment_score"))
    
    reddit_prepared = prepare_reddit(reddit_sentiment_df)
    reddit_agg = aggregate_sentiment(reddit_prepared)
    price_df = load_coingecko_data(spark, input_s3)

    joined = join_sentiment_with_price(reddit_agg, price_df)
    path_parts = input_s3.rstrip('/').split('/')
    bucket = path_parts[2]
    year, month, day, hour = path_parts[-4:]
    output_path = f"s3a://{bucket}/processed/joined/"

    out = (
        joined
        .withColumn("date", functions.lit(f"{year}-{month}-{day}"))
        .withColumn("hour", functions.lit(hour))
    )

    (out
        .repartition("date", "hour", "coin")
           .write
           .mode("append")
           .partitionBy("date", "hour", "coin")
           .parquet(output_path)
    )

    print(f"Wrote joined data to {output_path}")
    spark.stop()

def main():
    # Example input: s3://sparkling-water-dev-data-bucket/raw/reddit/cryptocurrency/2025/11/25/21
    input_s3 = sys.argv[1]
    output_s3 = sys.argv[2]

    run_job(input_s3, output_s3)


if __name__ == "__main__":
    main()