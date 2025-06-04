import boto3
import json
import logging
import time
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda function to launch EMR cluster, execute classification pipeline, and terminate cluster.

    Args:
        event: Lambda event (can be empty or contain configuration overrides)
        context: Lambda context

    Returns:
        dict: Response with status and cluster information
    """

    try:
        # Configuration
        config = get_config(event)

        # Initialize AWS clients
        emr_client = boto3.client('emr', region_name=config['aws_region'])
        s3_client = boto3.client('s3', region_name=config['aws_region'])

        # Step 1: Upload script to S3
        script_s3_path = upload_script_to_s3(s3_client, config)
        logger.info(f"Script uploaded to: {script_s3_path}")

        # Step 2: Launch EMR cluster
        cluster_id = launch_emr_cluster(emr_client, config, script_s3_path)
        logger.info(f"EMR cluster launched: {cluster_id}")

        # Step 3: Monitor cluster and wait for completion
        success = monitor_cluster_execution(emr_client, cluster_id, config)

        # Step 4: Terminate cluster (cleanup)
        terminate_cluster(emr_client, cluster_id)

        # Prepare response
        response = {
            'statusCode': 200 if success else 500,
            'body': json.dumps({
                'message': 'EMR classification pipeline completed successfully' if success else 'Pipeline failed',
                'cluster_id': cluster_id,
                'timestamp': datetime.utcnow().isoformat(),
                'script_location': script_s3_path
            })
        }

        return response

    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }


def get_config(event):
    """Get configuration with defaults and overrides from event."""

    # Default configuration
    config = {
        'aws_region': 'us-east-1',
        'cluster_name': f'news-classification-{int(time.time())}',
        'emr_release': 'emr-6.15.0',
        'master_instance_type': 'm5.xlarge',
        'core_instance_type': 'm5.xlarge',
        'core_instance_count': 2,
        'ec2_key_pair': None,  # Optional - set if you want SSH access
        'subnet_id': None,     # Optional - set for specific VPC
        'bucket_name': 'final-gizmo',
        'script_key': 'scripts/classification_pipeline.py',
        'log_uri': 's3://final-gizmo/emr-logs/',
        'service_role': 'EMR_DefaultRole',
        'job_flow_role': 'EMR_EC2_DefaultRole',
        'timeout_minutes': 60,  # Max execution time
        'auto_terminate': True
    }

    # Override with event parameters if provided
    if event and isinstance(event, dict):
        config.update(event)

    return config


def upload_script_to_s3(s3_client, config):
    """Upload classification script to S3."""

    try:
        # Script content (embedded in Lambda)
        script_content = get_classification_script()

        # Upload to S3
        s3_client.put_object(
            Bucket=config['bucket_name'],
            Key=config['script_key'],
            Body=script_content,
            ContentType='text/plain'
        )

        script_s3_path = f"s3://{config['bucket_name']}/{config['script_key']}"
        logger.info(f"Script uploaded to S3: {script_s3_path}")

        return script_s3_path

    except Exception as e:
        logger.error(f"Failed to upload script to S3: {str(e)}")
        raise


def launch_emr_cluster(emr_client, config, script_s3_path):
    """Launch EMR cluster with Spark step."""

    try:
        # Define cluster configuration
        cluster_config = {
            'Name': config['cluster_name'],
            'ReleaseLabel': config['emr_release'],
            'Applications': [
                {'Name': 'Spark'},
                {'Name': 'Hadoop'}
            ],
            'Instances': {
                'InstanceGroups': [
                    {
                        'Name': "Master",
                        'Market': 'ON_DEMAND',
                        'InstanceRole': 'MASTER',
                        'InstanceType': config['master_instance_type'],
                        'InstanceCount': 1,
                    },
                    {
                        'Name': "Core",
                        'Market': 'ON_DEMAND',
                        'InstanceRole': 'CORE',
                        'InstanceType': config['core_instance_type'],
                        'InstanceCount': config['core_instance_count'],
                    }
                ],
                'KeepJobFlowAliveWhenNoSteps': False,  # Auto-terminate when done
            },
            'Steps': [
                {
                    'Name': 'News Classification Pipeline',
                    'ActionOnFailure': 'TERMINATE_CLUSTER',
                    'HadoopJarStep': {
                        'Jar': 'command-runner.jar',
                        'Args': [
                            'spark-submit',
                            '--deploy-mode', 'cluster',
                            '--driver-memory', '4g',
                            '--executor-memory', '4g',
                            '--executor-cores', '2',
                            '--num-executors', '3',
                            script_s3_path
                        ]
                    }
                }
            ],
            'LogUri': config['log_uri'],
            'ServiceRole': config['service_role'],
            'JobFlowRole': config['job_flow_role'],
            'VisibleToAllUsers': True,
            'Tags': [
                {
                    'Key': 'Project',
                    'Value': 'BigDataFinal'
                },
                {
                    'Key': 'Component',
                    'Value': 'MLPipeline'
                },
                {
                    'Key': 'LaunchedBy',
                    'Value': 'Lambda'
                }
            ]
        }

        # Add optional configurations
        if config.get('ec2_key_pair'):
            cluster_config['Instances']['Ec2KeyName'] = config['ec2_key_pair']

        if config.get('subnet_id'):
            cluster_config['Instances']['Ec2SubnetId'] = config['subnet_id']

        # Launch cluster
        response = emr_client.run_job_flow(**cluster_config)
        cluster_id = response['JobFlowId']

        logger.info(f"EMR cluster launched successfully: {cluster_id}")
        return cluster_id

    except Exception as e:
        logger.error(f"Failed to launch EMR cluster: {str(e)}")
        raise


def monitor_cluster_execution(emr_client, cluster_id, config):
    """Monitor cluster execution and wait for completion."""

    try:
        timeout_seconds = config['timeout_minutes'] * 60
        start_time = time.time()

        logger.info(f"Monitoring cluster {cluster_id} with timeout of {config['timeout_minutes']} minutes")

        while True:
            # Check timeout
            if time.time() - start_time > timeout_seconds:
                logger.error(f"Cluster execution timed out after {config['timeout_minutes']} minutes")
                return False

            try:
                # Get cluster status
                response = emr_client.describe_cluster(ClusterId=cluster_id)

                # Debug: log the full response structure
                logger.info(f"EMR describe_cluster response: {json.dumps(response, default=str)}")

                # Check if response has expected structure
                if 'Cluster' not in response:
                    logger.error(f"Unexpected response structure: {response}")
                    return False

                cluster = response['Cluster']
                if 'State' not in cluster:
                    logger.error(f"Cluster object missing State: {cluster}")
                    return False

                cluster_state = cluster['State']
                logger.info(f"Cluster {cluster_id} state: {cluster_state}")

                if cluster_state in ['COMPLETED', 'TERMINATED']:
                    # Check step status
                    steps_response = emr_client.list_steps(ClusterId=cluster_id)
                    steps = steps_response.get('Steps', [])

                    if steps:
                        step_state = steps[0]['Status']['State']
                        logger.info(f"Step state: {step_state}")

                        if step_state == 'COMPLETED':
                            logger.info("Pipeline completed successfully!")
                            return True
                        else:
                            logger.error(f"Pipeline failed with step state: {step_state}")
                            return False
                    else:
                        logger.error("No steps found in cluster")
                        return False

                elif cluster_state in ['TERMINATED_WITH_ERRORS', 'TERMINATING']:
                    logger.error(f"Cluster failed with state: {cluster_state}")
                    return False
                elif cluster_state in ['STARTING', 'BOOTSTRAPPING', 'RUNNING', 'WAITING']:
                    logger.info(f"Cluster is in progress: {cluster_state}")
                else:
                    logger.warning(f"Unknown cluster state: {cluster_state}")

            except Exception as inner_e:
                logger.error(f"Error getting cluster status: {str(inner_e)}")
                # Try to get more information about the cluster
                try:
                    list_response = emr_client.list_clusters(
                        ClusterStates=[
                            'STARTING',
                            'BOOTSTRAPPING',
                            'RUNNING',
                            'WAITING',
                            'TERMINATING',
                            'TERMINATED',
                            'TERMINATED_WITH_ERRORS'
                        ]
                    )
                    logger.info(f"Available clusters: {json.dumps(list_response, default=str)}")
                except Exception as list_e:
                    logger.error(f"Failed to list clusters: {str(list_e)}")
                return False

            # Wait before next check
            time.sleep(30)

    except Exception as e:
        logger.error(f"Error monitoring cluster: {str(e)}")
        return False


def terminate_cluster(emr_client, cluster_id):
    """Terminate EMR cluster."""

    try:
        logger.info(f"Terminating cluster: {cluster_id}")
        emr_client.terminate_job_flows(JobFlowIds=[cluster_id])
        logger.info(f"Cluster {cluster_id} termination initiated")

    except Exception as e:
        logger.error(f"Failed to terminate cluster {cluster_id}: {str(e)}")
        # Don't raise - this is cleanup


def get_classification_script():
    """Return the classification script content."""

    # This is the script we created earlier
    script_content = '''#!/usr/bin/env python3
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
        spark = SparkSession.builder \\
            .appName(app_name) \\
            .config("spark.sql.adaptive.enabled", "true") \\
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \\
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \\
            .getOrCreate()

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

        df_clean = df.select(
            col("categoria").alias("label"),
            lower(regexp_replace(col("titular"), "[^a-zA-ZáéíóúñÁÉÍÓÚÑ ]", "")).alias("clean_text")
        ).na.drop()

        df_clean = df_clean.filter(col("clean_text") != "")

        clean_count = df_clean.count()
        logger.info(f"After cleaning: {clean_count} records")

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

        tokenizer = Tokenizer(inputCol="clean_text", outputCol="words")
        remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")
        hashingTF = HashingTF(inputCol="filtered_words", outputCol="rawFeatures", numFeatures=num_features)
        idf = IDF(inputCol="rawFeatures", outputCol="features")
        indexer = StringIndexer(inputCol="label", outputCol="labelIndex")

        lr = LogisticRegression(
            featuresCol="features",
            labelCol="labelIndex",
            maxIter=max_iter
        )

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

        logger.info("Sample predictions:")
        predictions.select("clean_text", "label", "prediction", "probability").show(10, truncate=False)

        return predictions
    except Exception as e:
        logger.error(f"Failed to generate predictions: {e}")
        sys.exit(1)


def save_results(predictions, output_base_path=OUTPUT_BASE_PATH):
    """Save results to S3 - same format as original notebook."""
    try:
        logger.info(f"Saving results to: {output_base_path}")

        predictions.select("clean_text", "label", "prediction") \\
                  .write.mode("overwrite") \\
                  .option("header", "true") \\
                  .csv(f"{output_base_path}/predicciones.csv")

        predictions.withColumn("probability_str", col("probability").cast("string")) \\
                  .select("clean_text", "label", "prediction", "probability_str") \\
                  .write.mode("overwrite") \\
                  .option("header", "true") \\
                  .csv(f"{output_base_path}/predicciones_prob.csv")

        predictions.write.mode("overwrite") \\
                  .parquet(f"{output_base_path}/predicciones_parquet/")

        logger.info("Results saved successfully")

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

    spark = create_spark_session()

    try:
        df = load_data(spark)
        df_clean = preprocess_data(df)
        pipeline = create_ml_pipeline()
        model = train_model(pipeline, df_clean)
        predictions = generate_predictions(model, df_clean)
        save_results(predictions)

        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
    finally:
        spark.stop()
        logger.info("Spark session stopped")


if __name__ == "__main__":
    main()
'''

    return script_content
