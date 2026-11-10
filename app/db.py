import os

import psycopg
from psycopg.rows import dict_row


def get_conn():
    # Opens a database connection; rows come back as dictionaries (column name -> value)
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)