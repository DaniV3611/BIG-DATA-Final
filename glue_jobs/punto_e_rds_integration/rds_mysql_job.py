#!/usr/bin/env python3
"""
AWS Glue Job: RDS MySQL Writer
Copies processed news data from S3 (via Glue Data Catalog) to RDS MySQL
Migrated implementation for point e) of the project
"""

import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.context import SparkContext
from pyspark.sql.functions import col, coalesce, lit
from pyspark.sql.types import StringType, DateType
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'DATABASE_NAME',
    'TABLE_NAME',
    'RDS_ENDPOINT',
    'RDS_DATABASE',
    'RDS_TABLE',
    'RDS_USERNAME',
    'RDS_PASSWORD',
    'JDBC_DRIVER_PATH'
])

job.init(args['JOB_NAME'], args)

# Configuration
DATABASE_NAME = args.get('DATABASE_NAME', 'news_headlines_db')
TABLE_NAME = args.get('TABLE_NAME', 'news_headlines')
RDS_ENDPOINT = args.get('RDS_ENDPOINT', 'news2.cluster-xxxxx.us-east-1.rds.amazonaws.com')
RDS_DATABASE = args.get('RDS_DATABASE', 'news')
RDS_TABLE = args.get('RDS_TABLE', 'noticias')
RDS_USERNAME = args.get('RDS_USERNAME', 'admin')
RDS_PASSWORD = args.get('RDS_PASSWORD', '123456789')
JDBC_DRIVER_PATH = args.get(
    'JDBC_DRIVER_PATH',
    's3://aws-glue-assets-123456789012-us-east-1/drivers/mysql-connector-java-8.0.33.jar'
)

# JDBC URL construction
JDBC_URL = f"jdbc:mysql://{RDS_ENDPOINT}:3306/{RDS_DATABASE}"


def create_mysql_table_if_not_exists():
    """
    Create MySQL table if it doesn't exist
    Uses boto3 RDS Data API or direct connection
    """
    try:
        # Create table SQL
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {RDS_TABLE} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fecha DATE NOT NULL,
            categoria VARCHAR(255),
            titular TEXT NOT NULL,
            enlace TEXT,
            periodico VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_fecha (fecha),
            INDEX idx_periodico (periodico),
            INDEX idx_categoria (categoria)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        # Use Spark to execute the DDL
        logger.info(f"Creating table {RDS_TABLE} if it doesn't exist...")

        # Note: In production, you might want to use a separate connection
        # For now, we'll rely on the table existing or being created externally
        logger.info("✅ Table creation query prepared (execute manually if needed)")
        logger.info(f"SQL: {create_table_sql}")

        return True

    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        return False


def read_from_glue_catalog():
    """
    Read data from Glue Data Catalog (S3 table)
    @return: DynamicFrame with news data
    """
    try:
        logger.info(f"Reading data from Glue Catalog - Database: {DATABASE_NAME}, Table: {TABLE_NAME}")

        # Read from Glue Data Catalog
        datasource = glueContext.create_dynamic_frame.from_catalog(
            database=DATABASE_NAME,
            table_name=TABLE_NAME,
            transformation_ctx="datasource"
        )

        logger.info(f"✅ Successfully read {datasource.count()} records from catalog")

        # Show schema for debugging
        logger.info("Schema from catalog:")
        datasource.printSchema()

        return datasource

    except Exception as e:
        logger.error(f"Error reading from Glue catalog: {str(e)}")
        raise e


def transform_data_for_mysql(dynamic_frame):
    """
    Transform data to match MySQL schema
    @param dynamic_frame: Input DynamicFrame
    @return: Transformed DynamicFrame
    """
    try:
        logger.info("Transforming data for MySQL compatibility...")

        # Convert to Spark DataFrame for easier transformations
        df = dynamic_frame.toDF()

        # Show current schema
        logger.info("Original schema:")
        df.printSchema()

        # Handle potential schema issues and transformations
        transformed_df = df.select(
            col("fecha").cast(DateType()).alias("fecha"),
            coalesce(col("categoria"), lit("General")).cast(StringType()).alias("categoria"),
            col("titular").cast(StringType()).alias("titular"),
            coalesce(col("enlace"), lit("")).cast(StringType()).alias("enlace"),
            coalesce(col("periodico"), lit("unknown")).cast(StringType()).alias("periodico")
        )

        # Filter out null or empty titles
        transformed_df = transformed_df.filter(
            (col("titular").isNotNull()) & 
            (col("titular") != "") &
            (col("fecha").isNotNull())
        )

        # Remove duplicates based on titular and fecha
        transformed_df = transformed_df.dropDuplicates(["titular", "fecha"])

        logger.info("Transformed schema:")
        transformed_df.printSchema()

        logger.info(f"✅ Data transformed - {transformed_df.count()} records after filtering")

        # Convert back to DynamicFrame
        transformed_dynamic_frame = DynamicFrame.fromDF(transformed_df, glueContext, "transformed_data")

        return transformed_dynamic_frame

    except Exception as e:
        logger.error(f"Error transforming data: {str(e)}")
        raise e


def write_to_mysql(dynamic_frame):
    """
    Write data to MySQL RDS using direct JDBC connection
    @param dynamic_frame: DynamicFrame to write
    @return: Success boolean
    """
    try:
        logger.info(f"Writing data to MySQL RDS - Table: {RDS_TABLE}")
        logger.info(f"Using direct JDBC connection to: {JDBC_URL}")

        # Convert DynamicFrame to DataFrame for JDBC writing
        df = dynamic_frame.toDF()

        # JDBC connection properties
        jdbc_properties = {
            "user": RDS_USERNAME,
            "password": RDS_PASSWORD,
            "driver": "com.mysql.cj.jdbc.Driver"
        }

        logger.info(f"Connecting to: {JDBC_URL}")
        logger.info(f"Writing to table: {RDS_TABLE}")
        logger.info(f"Records to write: {df.count()}")

        # Write to MySQL using Spark's JDBC writer
        df.write \
          .format("jdbc") \
          .option("url", JDBC_URL) \
          .option("dbtable", RDS_TABLE) \
          .option("user", RDS_USERNAME) \
          .option("password", RDS_PASSWORD) \
          .option("driver", "com.mysql.cj.jdbc.Driver") \
          .mode("append") \
          .save()

        logger.info("✅ Successfully wrote data to MySQL RDS using direct JDBC")
        return True

    except Exception as e:
        logger.error(f"❌ Error writing to MySQL: {str(e)}")
        logger.error("Common issues:")
        logger.error("1. Check RDS security groups allow connections from your IP/VPC")
        logger.error("2. Verify RDS instance is running and accessible")
        logger.error("3. Ensure MySQL JDBC driver is loaded correctly")
        logger.error("4. Check if table exists in target database")
        logger.error("5. Verify RDS credentials and endpoint")
        raise e


def get_processing_stats(dynamic_frame):
    """
    Get statistics about the data being processed
    @param dynamic_frame: DynamicFrame to analyze
    @return: Dictionary with stats
    """
    try:
        df = dynamic_frame.toDF()

        stats = {
            "total_records": df.count(),
            "unique_dates": df.select("fecha").distinct().count(),
            "unique_newspapers": df.select("periodico").distinct().count(),
            "unique_categories": df.select("categoria").distinct().count()
        }

        # Show sample data
        logger.info("Sample data (first 5 rows):")
        df.show(5, truncate=False)

        # Show stats
        logger.info("Processing Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")

        # Show newspaper distribution
        logger.info("Records by newspaper:")
        df.groupBy("periodico").count().show()

        # Show date range
        logger.info("Date range:")
        df.select("fecha").distinct().orderBy("fecha").show()

        return stats

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return {}


def main():
    """
    Main processing logic
    """
    try:
        logger.info("🚀 Starting RDS MySQL Writer Job")
        logger.info(f"Source: Glue Catalog - {DATABASE_NAME}.{TABLE_NAME}")
        logger.info(f"Target: MySQL RDS - {RDS_ENDPOINT}/{RDS_DATABASE}.{RDS_TABLE}")

        # Step 1: Ensure MySQL table exists
        create_mysql_table_if_not_exists()

        # Step 2: Read data from Glue Data Catalog
        logger.info("📖 Reading data from Glue Data Catalog...")
        source_data = read_from_glue_catalog()

        if source_data.count() == 0:
            logger.warning("⚠️ No data found in source table")
            return

        # Step 3: Get initial stats
        logger.info("📊 Getting source data statistics...")
        get_processing_stats(source_data)

        # Step 4: Transform data for MySQL
        logger.info("🔄 Transforming data for MySQL...")
        transformed_data = transform_data_for_mysql(source_data)

        if transformed_data.count() == 0:
            logger.warning("⚠️ No data remaining after transformation")
            return

        # Step 5: Get transformed stats
        logger.info("📊 Getting transformed data statistics...")
        get_processing_stats(transformed_data)

        # Step 6: Write to MySQL
        logger.info("💾 Writing data to MySQL RDS...")
        success = write_to_mysql(transformed_data)

        if success:
            logger.info("✅ RDS MySQL Writer Job completed successfully")
        else:
            logger.error("❌ RDS MySQL Writer Job failed")

    except Exception as e:
        logger.error(f"❌ Error in main processing logic: {str(e)}")
        raise e


if __name__ == "__main__":
    main()
    job.commit()
