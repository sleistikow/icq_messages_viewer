# Copyright (c) 2025 Simon Leistikow
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import sqlite3


def get_column_names(db_path, table_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Use PRAGMA statement to get table info
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()

    # Extract column names
    column_names = [col[1] for col in columns]

    conn.close()
    return column_names


def open_qdb_file(file_path):
    """Open and read ICQ chat history from a .qdb file."""

    # Check if file exists
    if not os.path.exists(file_path):
        print(f"The file {file_path} does not exist.")
        return

    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()

        # List all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print("Tables found in the database:")
        for table in tables:
            print(table[0])

        # Fetch and display data from a likely table (replace 'messages' with actual table name if necessary)
        for table_name in tables:
            print(f"\nFetching data from table: {table_name[0]}")
            cursor.execute(f"SELECT * FROM {table_name[0]} LIMIT 100")  # Fetch a few rows
            rows = cursor.fetchall()
            for row in rows:
                print(row)

        # Close the database connection
        conn.close()

    except sqlite3.Error as e:
        print(f"An error occurred while accessing the database: {e}")


if __name__ == "__main__":

    file_path = 'Messages.qdb'

    # Probe the .qdb file to get a list of tables and their columns.
    open_qdb_file(file_path)

    table_name = "Participants"  # Specify the table name
    columns = get_column_names(file_path, table_name)
    print(f"Column names in the '{table_name}' table:")
    for column in columns:
        print(column)
