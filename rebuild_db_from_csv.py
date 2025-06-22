import os
import pandas as pd
from datetime import datetime
from database import RedditDB
import ast

def rebuild_database_from_csvs(output_dir='output/these', new_db_path='reddit_sentiment_rebuilt.db'):
    """
    Rebuilds the SQLite database from a directory of analysis CSV files.
    """
    # 1. Delete the old database file if it exists to start fresh
    if os.path.exists(new_db_path):
        os.remove(new_db_path)
        print(f"Removed existing database: {new_db_path}")

    # 2. Initialize a new, clean database and create the schema
    db = RedditDB(db_path=new_db_path)
    print(f"Created new database: {new_db_path}")

    # 3. Find all analysis CSV files in the specified directory
    try:
        csv_files = [f for f in os.listdir(output_dir) if f.startswith('reddit_analysis_complete_') and f.endswith('.csv')]
        if not csv_files:
            print(f"No CSV files found in '{output_dir}'. Exiting.")
            return
    except FileNotFoundError:
        print(f"Error: Directory not found at '{output_dir}'. Exiting.")
        return

    print(f"Found {len(csv_files)} CSV files to process.")

    # 4. Process each CSV file
    for file_name in sorted(csv_files):
        file_path = os.path.join(output_dir, file_name)
        
        # Extract the date from the filename (YYYYMMDD)
        try:
            date_str = file_name.split('_')[3]
            run_date = datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
            print(f"\nProcessing {file_name} for date: {run_date}...")
        except (IndexError, ValueError):
            print(f"Could not parse date from filename: {file_name}. Skipping.")
            continue

        # Read the CSV into a DataFrame
        df = pd.read_csv(file_path)

        # The 'mentioned_tickers' column is stored as a string representation of a list.
        # The database saving function can handle this string, but it's good practice
        # to convert it back if we were doing other processing.
        # For this script, we can leave it as is, since db._save_posts_raw handles it.
        
        print(f"  - Read {len(df)} rows from CSV.")
        
        # 5. Save the DataFrame to the database for the extracted date
        db.save_daily_data(df, date=run_date)

    print("\n✅ Database rebuild complete.")
    print("Running final export to update web data...")
    db.export_for_web()
    print("✅ Web data exported successfully.")
    print(f"\nYour new database is ready: '{new_db_path}'")
    print("The web dashboard data has been updated from this new database.")

if __name__ == "__main__":
    rebuild_database_from_csvs() 