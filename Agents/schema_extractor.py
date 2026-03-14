import pandas as pd
import sqlalchemy as sa
import os
import json


def load_csvs_as_db(upload_folder):
    """
    Takes all CSV files from upload folder
    Loads them into an in-memory SQLite database
    Returns a SQLAlchemy engine
    """
    engine = sa.create_engine("sqlite:///:memory:")
    
    csv_files = [f for f in os.listdir(upload_folder) if f.endswith('.csv')]
    
    if not csv_files:
        raise ValueError("No CSV files found in upload folder!")
    
    print(f"Found {len(csv_files)} CSV files: {csv_files}")
    
    for csv_file in csv_files:
        file_path = os.path.join(upload_folder, csv_file)
        
        # Table name = filename without .csv
        table_name = csv_file.replace('.csv', '')
        
        # Read CSV into pandas dataframe
        df = pd.read_csv(file_path)
        
        # Save dataframe as a table in SQLite
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        
        print(f"Loaded: {csv_file} → table '{table_name}' ({len(df)} rows)")
    
    return engine


def extract_schema(engine):
    """
    Reads all tables and columns from the database
    Returns a dictionary with full schema info
    """
    inspector = sa.inspect(engine)
    schema_info = {}
    
    # Get all table names
    table_names = inspector.get_table_names()
    
    for table_name in table_names:
        columns = []
        
        # Get all columns for this table
        column_details = inspector.get_columns(table_name)
        
        for col in column_details:
            columns.append({
                "column_name": col["name"],
                "data_type": str(col["type"]),
                "nullable": col.get("nullable", True)
            })
        
        # Get primary keys
        pk_info = inspector.get_pk_constraint(table_name)
        primary_keys = pk_info.get("constrained_columns", [])
        
        # Get foreign keys
        fk_info = inspector.get_foreign_keys(table_name)
        foreign_keys = []
        for fk in fk_info:
            foreign_keys.append({
                "column": fk["constrained_columns"],
                "references_table": fk["referred_table"],
                "references_column": fk["referred_columns"]
            })
        
        # Get row count
        with engine.connect() as conn:
            result = conn.execute(sa.text(f"SELECT COUNT(*) FROM `{table_name}`"))
            row_count = result.scalar()
        
        schema_info[table_name] = {
            "columns": columns,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "row_count": row_count
        }
    
    return schema_info


def get_sample_data(engine, table_name, n=3):
    """
    Returns first 3 rows of a table as a list of dicts
    This helps the AI understand what kind of data is in each table
    """
    with engine.connect() as conn:
        result = conn.execute(sa.text(f"SELECT * FROM `{table_name}` LIMIT {n}"))
        rows = result.fetchall()
        columns = result.keys()
        
        sample = []
        for row in rows:
            sample.append(dict(zip(columns, row)))
    
    return sample


def extract_full_schema(upload_folder):
    """
    MAIN FUNCTION — call this from app.py
    Loads CSVs, extracts schema, gets sample data
    Returns everything in one dictionary
    """
    # Step 1: Load CSVs into database
    engine = load_csvs_as_db(upload_folder)
    
    # Step 2: Extract schema info
    schema = extract_schema(engine)
    
    # Step 3: Add sample data for each table
    for table_name in schema.keys():
        schema[table_name]["sample_data"] = get_sample_data(engine, table_name)
    
    return engine, schema


# ---- TEST IT ----
# Run this file directly to test it works
if __name__ == "__main__":
    # Change this path to where your CSV files are
    test_folder = "uploads"
    
    engine, schema = extract_full_schema(test_folder)
    
    # Pretty print the result
    print("\n===== SCHEMA EXTRACTED =====")
    for table, info in schema.items():
        print(f"\nTable: {table}")
        print(f"  Rows: {info['row_count']}")
        print(f"  Columns ({len(info['columns'])}):")
        for col in info['columns']:
            print(f"    - {col['column_name']} ({col['data_type']})")
        print(f"  Primary Keys: {info['primary_keys']}")
        print(f"  Sample Data: {info['sample_data'][0] if info['sample_data'] else 'empty'}")