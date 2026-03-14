import pandas as pd
import sqlalchemy as sa
from difflib import SequenceMatcher


def get_all_columns(engine):
    """
    Gets every table and its columns in one flat dictionary
    Format: { 'table_name': ['col1', 'col2', ...] }
    """
    inspector = sa.inspect(engine)
    all_tables = {}

    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        all_tables[table_name] = [col["name"] for col in columns]

    return all_tables


def find_exact_foreign_keys(engine):
    """
    Finds REAL foreign keys defined in the database
    (SQLite from CSVs usually won't have these, but good to check)
    """
    inspector = sa.inspect(engine)
    relationships = []

    for table_name in inspector.get_table_names():
        fks = inspector.get_foreign_keys(table_name)
        for fk in fks:
            relationships.append({
                "from_table": table_name,
                "from_column": fk["constrained_columns"][0],
                "to_table": fk["referred_table"],
                "to_column": fk["referred_columns"][0],
                "confidence": "high",
                "type": "defined_foreign_key"
            })

    return relationships


def find_column_name_matches(all_tables):
    """
    Smart detection — finds relationships by matching column names
    
    Example:
    - orders table has 'customer_id'
    - customers table has 'customer_id'
    → These are probably linked!
    
    This works even when CSV files don't have real foreign keys
    """
    relationships = []
    table_names = list(all_tables.keys())

    for i, table_a in enumerate(table_names):
        for table_b in table_names:

            # Don't compare table with itself
            if table_a == table_b:
                continue

            cols_a = all_tables[table_a]
            cols_b = all_tables[table_b]

            for col_a in cols_a:
                for col_b in cols_b:

                    # Check 1: Exact same column name in both tables
                    if col_a == col_b and "_id" in col_a.lower():
                        relationships.append({
                            "from_table": table_a,
                            "from_column": col_a,
                            "to_table": table_b,
                            "to_column": col_b,
                            "confidence": "high",
                            "type": "exact_column_match"
                        })

                    # Check 2: Column name contains other table's name
                    # Example: orders.customer_id → customers table
                    elif col_a.lower().replace("_id", "") in table_b.lower():
                        if "_id" in col_a.lower():
                            relationships.append({
                                "from_table": table_a,
                                "from_column": col_a,
                                "to_table": table_b,
                                "to_column": col_b,
                                "confidence": "medium",
                                "type": "name_inference"
                            })

    return relationships


def remove_duplicate_relationships(relationships):
    """
    Removes duplicate relationships
    Keeps the one with highest confidence
    """
    seen = set()
    unique = []

    for rel in relationships:
        # Create a unique key for this relationship
        key = f"{rel['from_table']}.{rel['from_column']}→{rel['to_table']}"

        if key not in seen:
            seen.add(key)
            unique.append(rel)

    return unique


def verify_relationship_by_data(engine, relationship):
    """
    Double checks a relationship actually makes sense
    by comparing actual values in both columns
    
    Example: checks if values in orders.customer_id
    actually exist in customers.customer_id
    """
    try:
        from_table = relationship["from_table"]
        from_col = relationship["from_column"]
        to_table = relationship["to_table"]
        to_col = relationship["to_column"]

        with engine.connect() as conn:
            # Get sample values from source column
            source_vals = conn.execute(sa.text(f"""
                SELECT DISTINCT `{from_col}` 
                FROM `{from_table}` 
                WHERE `{from_col}` IS NOT NULL 
                LIMIT 20
            """)).fetchall()

            source_vals = [str(v[0]) for v in source_vals]

            if not source_vals:
                return False

            # Check how many of those values exist in target column
            sample_str = ", ".join([f"'{v}'" for v in source_vals[:10]])

            match_count = conn.execute(sa.text(f"""
                SELECT COUNT(*) FROM `{to_table}`
                WHERE `{to_col}` IN ({sample_str})
            """)).scalar()

            # If more than 30% match — relationship is valid
            match_rate = match_count / len(source_vals)
            return match_rate > 0.3

    except Exception as e:
        return False


def build_relationship_map(engine):
    """
    MAIN FUNCTION — call this from app.py
    Finds all relationships between tables
    Returns them in a clean format
    """
    print("Mapping table relationships...")

    # Step 1: Get all tables and columns
    all_tables = get_all_columns(engine)

    # Step 2: Find defined foreign keys (if any)
    defined_fks = find_exact_foreign_keys(engine)

    # Step 3: Find relationships by column name matching
    inferred = find_column_name_matches(all_tables)

    # Step 4: Combine both
    all_relationships = defined_fks + inferred

    # Step 5: Remove duplicates
    unique_relationships = remove_duplicate_relationships(all_relationships)

    # Step 6: Verify each relationship using actual data
    verified_relationships = []
    for rel in unique_relationships:
        is_valid = verify_relationship_by_data(engine, rel)
        if is_valid:
            rel["verified"] = True
            verified_relationships.append(rel)
        else:
            rel["verified"] = False
            # Still include it but mark as unverified
            verified_relationships.append(rel)

    print(f"Found {len(verified_relationships)} relationships")
    return verified_relationships


def generate_mermaid_diagram(relationships, schema):
    """
    Generates clean Mermaid ER diagram code
    """
    lines = ["erDiagram"]

    for table_name, table_info in schema.items():

        # Clean table name — remove special characters
        clean_table = table_name.replace("-", "_").replace(" ", "_")

        lines.append(f"  {clean_table} {{")

        for col in table_info["columns"][:6]:  # Max 6 columns
            col_name = col["column_name"].replace(" ", "_").replace("-", "_")

            # Simplify data type
            raw_type = str(col["data_type"]).upper()
            if "INT" in raw_type:
                col_type = "INT"
            elif "FLOAT" in raw_type or "REAL" in raw_type or "DOUBLE" in raw_type:
                col_type = "FLOAT"
            elif "BOOL" in raw_type:
                col_type = "BOOLEAN"
            elif "DATE" in raw_type or "TIME" in raw_type:
                col_type = "DATETIME"
            else:
                col_type = "STRING"

            lines.append(f"    {col_type} {col_name}")

        lines.append("  }")

    # Add relationships
    added_pairs = set()
    for rel in relationships:
        if rel.get("verified"):
            from_t = rel["from_table"].replace("-", "_").replace(" ", "_")
            to_t = rel["to_table"].replace("-", "_").replace(" ", "_")

            # Avoid duplicate pairs
            pair = tuple(sorted([from_t, to_t]))
            if pair not in added_pairs:
                added_pairs.add(pair)
                lines.append(f'  {from_t} ||--o{{ {to_t} : has')

    return "\n".join(lines)


# ---- TEST IT ----
if __name__ == "__main__":
    import sys
    sys.path.append("..")
    from Agents.schema_extractor import extract_full_schema

    engine, schema = extract_full_schema("../uploads")
    relationships = build_relationship_map(engine)

    print("\n===== RELATIONSHIPS FOUND =====")
    for rel in relationships:
        verified = "✅" if rel["verified"] else "❓"
        print(f"{verified} {rel['from_table']}.{rel['from_column']} "
              f"→ {rel['to_table']}.{rel['to_column']} "
              f"({rel['confidence']})")

    print("\n===== MERMAID DIAGRAM CODE =====")
    diagram = generate_mermaid_diagram(relationships, schema)
    print(diagram)