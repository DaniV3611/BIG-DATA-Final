#!/usr/bin/env python3
"""
Classification Pipeline Script for EMR
Converts the Jupyter notebook classification pipeline into an executable script for EMR.

Usage:
    spark-submit --deploy-mode cluster classification_pipeline.py

Author: Data Engineering Team
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, regexp_replace
from pyspark.ml.feature import Tokenizer, StopWordsRemover, HashingTF, IDF, StringIndexer
from pyspark.ml.classification import LogisticRegression
from pyspark.ml import Pipeline
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fixed configuration - same as notebook
INPUT_PATH = "s3://final-gizmo/headlines/final/periodico=*/year=*/month=*/day=*/*.csv"
OUTPUT_BASE_PATH = "s3://final-gizmo/resultados"
NUM_FEATURES = 10000
MAX_ITER = 10
APP_NAME = "NewsClassificationPipeline"


def create_spark_session(app_name=APP_NAME):
    """Create and configure Spark session for EMR."""
    try:
        spark = SparkSession.builder \
            .appName(app_name) \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .getOrCreate()
        # Set log level to reduce noise
        spark.sparkContext.setLogLevel("WARN")
        logger.info(f"Spark session created successfully: {spark}")
        return spark
    except Exception as e:
        logger.error(f"Failed to create Spark session: {e}")
        sys.exit(1)


def load_data(spark, input_path=INPUT_PATH):
    """Load data from S3 CSV files."""
    try:
        logger.info(f"Loading data from: {input_path}")
        df = spark.read.option("header", "true").csv(input_path)
        # Log basic statistics
        count = df.count()
        logger.info(f"Loaded {count} records")
        logger.info(f"Schema: {df.columns}")
        return df
    except Exception as e:
        logger.error(f"Failed to load data from {input_path}: {e}")
        sys.exit(1)


def preprocess_data(df):
    """Clean and preprocess the data."""
    try:
        logger.info("Starting data preprocessing...")
        # Clean text: remove special characters, convert to lowercase
        df_clean = df.select(
            col("categoria").alias("label"),
            lower(regexp_replace(col("titular"), "[^a-zA-ZáéíóúñÁÉÍÓÚÑ ]", "")).alias("clean_text")
        ).na.drop()
        # Filter out empty text
        df_clean = df_clean.filter(col("clean_text") != "")
        clean_count = df_clean.count()
        logger.info(f"After cleaning: {clean_count} records")
        # Show category distribution
        logger.info("Category distribution:")
        df_clean.groupBy("label").count().orderBy(col("count").desc()).show(20)
        return df_clean
    except Exception as e:
        logger.error(f"Failed to preprocess data: {e}")
        sys.exit(1)


def create_ml_pipeline(num_features=NUM_FEATURES, max_iter=MAX_ITER):
    """Create the ML pipeline with TF-IDF and Logistic Regression."""
    try:
        logger.info(f"Creating ML pipeline with {num_features} features and {max_iter} iterations...")
        # Text processing stages
        tokenizer = Tokenizer(inputCol="clean_text", outputCol="words")
        remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")
        hashingTF = HashingTF(inputCol="filtered_words", outputCol="rawFeatures", numFeatures=num_features)
        idf = IDF(inputCol="rawFeatures", outputCol="features")
        # Label indexing
        indexer = StringIndexer(inputCol="label", outputCol="labelIndex")
        # Classifier
        lr = LogisticRegression(
            featuresCol="features",
            labelCol="labelIndex",
            maxIter=max_iter
        )
        # Create pipeline
        pipeline = Pipeline(stages=[tokenizer, remover, hashingTF, idf, indexer, lr])
        logger.info("ML pipeline created successfully")
        return pipeline
    except Exception as e:
        logger.error(f"Failed to create ML pipeline: {e}")
        sys.exit(1)


def train_model(pipeline, df_clean):
    """Train the machine learning model."""
    try:
        logger.info("Starting model training...")
        # Train the model on all data (like in original notebook)
        model = pipeline.fit(df_clean)
        logger.info("Model training completed")
        return model
    except Exception as e:
        logger.error(f"Failed to train model: {e}")
        sys.exit(1)


def generate_predictions(model, df_clean):
    """Generate predictions for all data."""
    try:
        logger.info("Generating predictions...")
        predictions = model.transform(df_clean)
        # Show sample predictions
        logger.info("Sample predictions:")
        predictions.select("clean_text", "label", "prediction", "probability") \
            .show(10, truncate=False)
        return predictions
    except Exception as e:
        logger.error(f"Failed to generate predictions: {e}")
        sys.exit(1)


def save_results(predictions, output_base_path=OUTPUT_BASE_PATH):
    """Save results to S3 - same format as original notebook."""
    try:
        logger.info(f"Saving results to: {output_base_path}")
        # Save main predictions (CSV format) - like original notebook
        predictions.select("clean_text", "label", "prediction") \
            .write.mode("overwrite") \
            .option("header", "true") \
            .csv(f"{output_base_path}/predicciones.csv")
        # Save with probabilities (CSV format) - like original notebook
        predictions.withColumn("probability_str", col("probability").cast("string")) \
            .select("clean_text", "label", "prediction", "probability_str") \
            .write.mode("overwrite") \
            .option("header", "true") \
            .csv(f"{output_base_path}/predicciones_prob.csv")
        # Save as Parquet - like original notebook
        predictions.write.mode("overwrite") \
            .parquet(f"{output_base_path}/predicciones_parquet/")
        logger.info("Results saved successfully")
        # Log some statistics
        total_predictions = predictions.count()
        logger.info(f"Total predictions generated: {total_predictions}")
        logger.info("Prediction distribution:")
        predictions.groupBy("prediction").count().orderBy("prediction").show()
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        sys.exit(1)


def main():
    """Main function to run the classification pipeline."""
    logger.info("=" * 60)
    logger.info("NEWS CLASSIFICATION PIPELINE STARTING")
    logger.info("=" * 60)
    logger.info(f"Input path: {INPUT_PATH}")
    logger.info(f"Output path: {OUTPUT_BASE_PATH}")
    logger.info(f"Number of features: {NUM_FEATURES}")
    logger.info(f"Max iterations: {MAX_ITER}")
    # Create Spark session
    spark = create_spark_session()
    try:
        # Step 1: Load data
        df = load_data(spark)
        # Step 2: Preprocess data
        df_clean = preprocess_data(df)
        # Step 3: Create ML pipeline
        pipeline = create_ml_pipeline()
        # Step 4: Train model
        model = train_model(pipeline, df_clean)
        # Step 5: Generate predictions
        predictions = generate_predictions(model, df_clean)
        # Step 6: Save results
        save_results(predictions)
        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
    finally:
        # Clean up
        spark.stop()
        logger.info("Spark session stopped")


if __name__ == "__main__":
    main() 