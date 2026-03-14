import pandas as pd
import sqlalchemy as sa
from datetime import datetime


def check_null_values(engine, table_name, columns):
    """
    For each column, counts how many values are NULL/empty
    Returns null count and null percentage
    """
    null_stats = {}

    with engine.connect() as conn:
        for col in columns:
            col_name = col["column_name"]

            query = sa.text(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(`{col_name}`) as non_null
                FROM `{table_name}`
            """)

            result = conn.execute(query).fetchone()
            total = result[0]
            non_null = result[1]
            null_count = total - non_null

            null_percent = round((null_count / total * 100), 2) if total > 0 else 0

            # Flag as warning if more than 5% nulls
            status = "✅ Good"
            if null_percent > 30:
                status = "🔴 High nulls"
            elif null_percent > 5:
                status = "🟡 Some nulls"

            null_stats[col_name] = {
                "total_rows": total,
                "null_count": null_count,
                "null_percent": null_percent,
                "status": status
            }

    return null_stats


def check_duplicates(engine, table_name):
    """
    Checks if table has duplicate rows
    """
    with engine.connect() as conn:
        # Get total rows
        total = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM `{table_name}`")
        ).scalar()

        # Get distinct rows
        distinct = conn.execute(
            sa.text(f"SELECT COUNT(*) FROM (SELECT DISTINCT * FROM `{table_name}`)")
        ).scalar()

        duplicate_count = total - distinct
        duplicate_percent = round((duplicate_count / total * 100), 2) if total > 0 else 0

        status = "✅ No duplicates"
        if duplicate_percent > 5:
            status = "🔴 Many duplicates"
        elif duplicate_percent > 0:
            status = "🟡 Some duplicates"

    return {
        "total_rows": total,
        "duplicate_count": duplicate_count,
        "duplicate_percent": duplicate_percent,
        "status": status
    }


def check_data_freshness(engine, table_name, columns):
    """
    Looks for any timestamp/date columns
    Checks how old the latest data is
    """
    freshness_info = {}

    # Find columns that look like dates
    date_columns = [
        col["column_name"] for col in columns
        if any(keyword in col["column_name"].lower()
               for keyword in ["date", "time", "created", "updated", "timestamp"])
    ]

    if not date_columns:
        return {"message": "No date columns found"}

    with engine.connect() as conn:
        for col_name in date_columns:
            try:
                result = conn.execute(sa.text(f"""
                    SELECT 
                        MAX(`{col_name}`) as latest,
                        MIN(`{col_name}`) as earliest
                    FROM `{table_name}`
                    WHERE `{col_name}` IS NOT NULL
                """)).fetchone()

                latest = result[0]
                earliest = result[1]

                freshness_info[col_name] = {
                    "latest_value": str(latest),
                    "earliest_value": str(earliest),
                }

            except Exception as e:
                freshness_info[col_name] = {"error": str(e)}

    return freshness_info


def check_column_stats(engine, table_name, columns):
    """
    For numeric columns — gets min, max, average
    For text columns — gets number of unique values
    """
    stats = {}

    with engine.connect() as conn:
        for col in columns:
            col_name = col["column_name"]
            col_type = col["data_type"].upper()

            try:
                # Numeric columns
                if any(t in col_type for t in ["INT", "FLOAT", "REAL", "NUMERIC", "DOUBLE"]):
                    result = conn.execute(sa.text(f"""
                        SELECT 
                            MIN(`{col_name}`),
                            MAX(`{col_name}`),
                            AVG(`{col_name}`)
                        FROM `{table_name}`
                        WHERE `{col_name}` IS NOT NULL
                    """)).fetchone()

                    stats[col_name] = {
                        "type": "numeric",
                        "min": round(result[0], 2) if result[0] else None,
                        "max": round(result[1], 2) if result[1] else None,
                        "avg": round(result[2], 2) if result[2] else None
                    }

                # Text columns
                else:
                    result = conn.execute(sa.text(f"""
                        SELECT COUNT(DISTINCT `{col_name}`)
                        FROM `{table_name}`
                    """)).scalar()

                    stats[col_name] = {
                        "type": "text",
                        "unique_values": result
                    }

            except Exception as e:
                stats[col_name] = {"error": str(e)}

    return stats


def run_quality_check(engine, schema):
    """
    MAIN FUNCTION — call this from app.py
    Runs all quality checks on all tables
    Returns complete quality report
    """
    quality_report = {}

    for table_name, table_info in schema.items():
        print(f"Checking quality for: {table_name}...")

        columns = table_info["columns"]

        quality_report[table_name] = {
            "null_analysis": check_null_values(engine, table_name, columns),
            "duplicate_analysis": check_duplicates(engine, table_name),
            "freshness_analysis": check_data_freshness(engine, table_name, columns),
            "column_stats": check_column_stats(engine, table_name, columns)
        }

    return quality_report


# ---- TEST IT ----
if __name__ == "__main__":
    from schema_extractor import extract_full_schema

    engine, schema = extract_full_schema("../Uploads")
    quality_report = run_quality_check(engine, schema)

    print("\n===== QUALITY REPORT =====")
    for table, report in quality_report.items():
        print(f"\nTable: {table}")
        print("  Null Analysis:")
        for col, stats in report["null_analysis"].items():
            print(f"    {col}: {stats['null_percent']}% nulls {stats['status']}")
        print(f"  Duplicates: {report['duplicate_analysis']['status']}")
        print(f"  Freshness: {report['freshness_analysis']}")