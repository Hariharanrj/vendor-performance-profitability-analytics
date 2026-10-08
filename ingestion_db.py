import pandas as pd
import os
from sqlalchemy import create_engine
import logging
import time

# SQLite database
engine = create_engine('sqlite:///inventory.db')

logger = logging.getLogger(__name__)


def ingest_db(df, table_name, engine, if_exists='append'):
    """
    Ingest dataframe into SQLite database.
    """
    df.to_sql(
        table_name,
        con=engine,
        if_exists=if_exists,
        index=False
    )


def load_raw_data():
    """
    Load CSV files into SQLite database in chunks
    to avoid MemoryError with very large files.
    """

    start = time.time()

    for file in os.listdir('data'):

        if file.lower().endswith('.csv'):

            file_path = os.path.join('data', file)
            table_name = file[:-4]

            logger.info(f'Starting ingestion: {file}')
            print(f'\nProcessing: {file}')

            first_chunk = True
            total_rows = 0

            # Read CSV in chunks
            for chunk in pd.read_csv(
                file_path,
                chunksize=10000,
                low_memory=False
            ):

                # First chunk replaces old/partial table
                if first_chunk:
                    ingest_db(
                        chunk,
                        table_name,
                        engine,
                        if_exists='replace'
                    )
                    first_chunk = False

                # Remaining chunks are appended
                else:
                    ingest_db(
                        chunk,
                        table_name,
                        engine,
                        if_exists='append'
                    )

                total_rows += len(chunk)

                print(
                    f'  {total_rows:,} rows loaded',
                    end='\r'
                )

            print(f'\nCompleted: {file} → {total_rows:,} rows')

            logger.info(
                f'Completed {file}: {total_rows} rows'
            )

    end = time.time()

    total_time = (end - start) / 60

    logger.info('----------Ingestion Complete----------')
    logger.info(
        f'Total Time Taken: {total_time:.2f} minutes'
    )

    print('\n---------- Ingestion Complete ----------')
    print(f'Total Time Taken: {total_time:.2f} minutes')


if __name__ == '__main__':

    logging.basicConfig(
        filename="logs/ingestion_db.log",
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filemode="a"
    )

    load_raw_data()