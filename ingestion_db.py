import pandas as pd
import os
from sqlalchemy import create_engine
import logging
import time


# =========================================================
# 1. CREATE LOGS FOLDER
# =========================================================

os.makedirs("logs", exist_ok=True)


# =========================================================
# 2. LOGGING CONFIGURATION
# =========================================================

logging.basicConfig(
    filename="logs/ingestion_db.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)


# =========================================================
# 3. CREATE DATABASE ENGINE
# =========================================================

engine = create_engine("sqlite:///inventory.db")


# =========================================================
# 4. FUNCTION TO INGEST DATA INTO DATABASE
# =========================================================

def ingest_db(df, table_name, engine, if_exists):
    """
    Insert a DataFrame into a SQLite database table.
    """

    df.to_sql(
        table_name,
        con=engine,
        if_exists=if_exists,
        index=False
    )


# =========================================================
# 5. LOAD RAW CSV DATA
# =========================================================

def load_raw_data():

    start = time.time()

    logging.info("========================================")
    logging.info("Starting database ingestion")
    logging.info("========================================")

    # Get all files from data folder
    for file in os.listdir("data"):

        # Process only CSV files
        if file.lower().endswith(".csv"):

            file_path = os.path.join("data", file)

            # Remove .csv to create table name
            table_name = os.path.splitext(file)[0]

            logging.info(f"Starting ingestion of: {file}")

            print(f"\nProcessing: {file}")

            # -------------------------------------------------
            # READ CSV IN CHUNKS
            # -------------------------------------------------

            chunk_number = 0
            total_rows = 0

            for df_chunk in pd.read_csv(
                file_path,
                chunksize=5000
            ):

                chunk_number += 1

                rows = len(df_chunk)
                total_rows += rows

                # -------------------------------------------------
                # FIRST CHUNK
                # Create/replace the table
                # -------------------------------------------------

                if chunk_number == 1:

                    ingest_db(
                        df_chunk,
                        table_name,
                        engine,
                        "replace"
                    )

                # -------------------------------------------------
                # REMAINING CHUNKS
                # Append to existing table
                # -------------------------------------------------

                else:

                    ingest_db(
                        df_chunk,
                        table_name,
                        engine,
                        "append"
                    )

                logging.info(
                    f"{file} - Chunk {chunk_number} - "
                    f"{rows} rows inserted"
                )

                print(
                    f"  Chunk {chunk_number}: "
                    f"{rows} rows inserted"
                )

                # Release chunk from memory
                del df_chunk

            logging.info(
                f"Completed {file} - "
                f"Total rows: {total_rows}"
            )

            print(
                f"Completed: {file} "
                f"({total_rows} rows)"
            )

    # =========================================================
    # 6. CALCULATE TOTAL TIME
    # =========================================================

    end = time.time()

    total_time = (end - start) / 60

    logging.info("========================================")
    logging.info("Ingestion Complete")
    logging.info(
        f"Total Time Taken: {total_time:.2f} minutes"
    )
    logging.info("========================================")

    print("\n========================================")
    print("INGESTION COMPLETE")
    print(f"Total Time Taken: {total_time:.2f} minutes")
    print("========================================")


# =========================================================
# 7. RUN PROGRAM
# =========================================================

if __name__ == "__main__":
    load_raw_data()