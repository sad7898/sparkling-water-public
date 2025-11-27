#!/usr/bin/env python3

import sys
import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, col, count, when, isnan, isnull, max as F_max, min as F_min
from pyspark.sql.types import *


def create_spark_session(app_name="RedditDataProcessor"):
    """Create and configure Spark session"""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()


def read_reddit_data(spark, input_path):
    """Read Reddit data from S3 input path"""
    try:
        # Try to read as JSON first (most common format for Reddit data)
        df = spark.read.option("multiline", "true").json(input_path)
        print(f"Successfully read data from {input_path}")
        print(f"Number of records: {df.count()}")
        return df
    except Exception as e:
        print(f"Error reading JSON data: {e}")
        try:
            # Fallback to reading as CSV
            df = spark.read.option("header", "true").option("inferSchema", "true").csv(input_path)
            print(f"Successfully read CSV data from {input_path}")
            print(f"Number of records: {df.count()}")
            return df
        except Exception as e2:
            print(f"Error reading CSV data: {e2}")
            raise Exception(f"Could not read data from {input_path} as JSON or CSV")


def calculate_average_upvotes(df):
    """Calculate average upvotes from Reddit data"""
    # Reddit data schema field names for upvotes (prioritize 'upvotes' based on provided schema)
    upvote_columns = ['upvotes', 'ups', 'score', 'upvote_ratio']
    
    # Check which upvote column exists in the data
    upvote_col = None
    for col_name in upvote_columns:
        if col_name in df.columns:
            upvote_col = col_name
            break
    
    if upvote_col is None:
        # If no standard upvote column found, list available columns
        print("Available columns:", df.columns)
        raise ValueError(f"No upvote column found. Expected one of: {upvote_columns}")
    
    print(f"Using column '{upvote_col}' for upvotes calculation")
    
    # Clean the data - remove null/nan values and ensure numeric type
    # For Reddit data, upvotes can be 0 or positive integers
    clean_df = df.filter(
        (col(upvote_col).isNotNull()) & 
        (~isnan(col(upvote_col))) &
        (col(upvote_col) >= 0)  # Reddit upvotes are non-negative
    )
    
    # Calculate statistics
    total_posts = df.count()
    clean_posts = clean_df.count()
    
    if clean_posts == 0:
        raise ValueError("No valid upvote data found after cleaning")
    
    # Calculate average upvotes
    avg_upvotes = clean_df.agg(avg(col(upvote_col)).alias("average_upvotes")).collect()[0]["average_upvotes"]
    
    # Additional statistics including posts with different upvote ranges
    stats_df = clean_df.agg(
        avg(col(upvote_col)).alias("average_upvotes"),
        count(col(upvote_col)).alias("total_posts_with_upvotes"),
        F_max(col(upvote_col)).alias("max_upvotes"),
        F_min(col(upvote_col)).alias("min_upvotes")
    )
    
    # Calculate upvote distribution
    upvote_distribution = clean_df.select(
        count(when(col(upvote_col) == 0, 1)).alias("posts_with_0_upvotes"),
        count(when((col(upvote_col) >= 1) & (col(upvote_col) <= 10), 1)).alias("posts_with_1_to_10_upvotes"),
        count(when((col(upvote_col) >= 11) & (col(upvote_col) <= 100), 1)).alias("posts_with_11_to_100_upvotes"),
        count(when(col(upvote_col) > 100, 1)).alias("posts_with_100_plus_upvotes")
    )
    
    return {
        "average_upvotes": round(avg_upvotes, 2),
        "total_posts": total_posts,
        "posts_with_valid_upvotes": clean_posts,
        "upvote_column_used": upvote_col
    }, stats_df, upvote_distribution


def save_results(spark, results_dict, stats_df, upvote_distribution, output_path):
    """Save results to S3 output path"""
    # Create a DataFrame with the results
    results_data = [
        ("metric", "value"),
        ("average_upvotes", str(results_dict["average_upvotes"])),
        ("total_posts", str(results_dict["total_posts"])),
        ("posts_with_valid_upvotes", str(results_dict["posts_with_valid_upvotes"])),
        ("upvote_column_used", results_dict["upvote_column_used"])
    ]
    
    results_df = spark.createDataFrame(results_data, ["metric", "value"])
    
    # Save summary results
    results_df.coalesce(1).write.mode("overwrite").option("header", "true").csv(f"{output_path}/summary")
    
    # Save detailed statistics
    stats_df.coalesce(1).write.mode("overwrite").option("header", "true").csv(f"{output_path}/detailed_stats")
    
    # Save upvote distribution
    upvote_distribution.coalesce(1).write.mode("overwrite").option("header", "true").csv(f"{output_path}/upvote_distribution")
    
    print(f"Results saved to {output_path}")


def main():
    
    
    print(f"Starting Reddit data processing...")
    print(f"Input path: {sys.argv[1]}")
    print(f"Output path: {sys.argv[2]}")
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    # Create Spark session
    spark = create_spark_session("examaple")
    
    try:
        # Read Reddit data
        df = read_reddit_data(spark, input_path)
        
        # Show sample data structure
        print("Data schema:")
        df.printSchema()
        print("Sample data (first 5 rows):")
        df.show(5, truncate=False)
        
        # Calculate average upvotes
        results, stats_df, upvote_distribution = calculate_average_upvotes(df)
        
        # Print results
        print("\n" + "="*50)
        print("REDDIT DATA ANALYSIS RESULTS")
        print("="*50)
        print(f"Average upvotes: {results['average_upvotes']}")
        print(f"Total posts: {results['total_posts']}")
        print(f"Posts with valid upvotes: {results['posts_with_valid_upvotes']}")
        print(f"Upvote column used: {results['upvote_column_used']}")
        print("="*50)
        
        # Save results to S3
        save_results(spark, results, stats_df, upvote_distribution, output_path)
        
        print("Job completed successfully!")
        
    except Exception as e:
        print(f"Error processing Reddit data: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()