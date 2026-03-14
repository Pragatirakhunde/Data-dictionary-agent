def generate_insights(schema, quality_report, relationships, data_dictionary):
    """
    Automatically generates smart insights
    about the database without user asking
    """
    insights = {
        "overview_insights": [],
        "quality_insights": [],
        "relationship_insights": [],
        "business_insights": [],
        "warnings": [],
        "recommendations": []
    }

    # ── Overview Insights ─────────────────────────────────────
    total_rows = sum(i["row_count"] for i in schema.values())
    total_tables = len(schema)
    total_cols = sum(len(i["columns"]) for i in schema.values())

    insights["overview_insights"].append({
        "icon": "🗃️",
        "title": "Database Size",
        "detail": (
            f"This database has {total_tables} tables, "
            f"{total_cols} columns and "
            f"{total_rows:,} total records"
        )
    })

    # Biggest table
    biggest = max(schema.items(), key=lambda x: x[1]["row_count"])
    insights["overview_insights"].append({
        "icon": "📊",
        "title": "Largest Table",
        "detail": (
            f"'{biggest[0]}' is the largest table "
            f"with {biggest[1]['row_count']:,} rows — "
            f"likely the core table of this database"
        )
    })

    # Smallest table
    smallest = min(schema.items(), key=lambda x: x[1]["row_count"])
    insights["overview_insights"].append({
        "icon": "📋",
        "title": "Smallest Table",
        "detail": (
            f"'{smallest[0]}' has only "
            f"{smallest[1]['row_count']:,} rows — "
            f"likely a reference or lookup table"
        )
    })

    # Average columns per table
    avg_cols = round(total_cols / total_tables, 1)
    insights["overview_insights"].append({
        "icon": "📌",
        "title": "Average Columns",
        "detail": (
            f"Each table has an average of {avg_cols} columns. "
            f"{'Well structured database!' if avg_cols < 15 else 'Some tables may be too wide.'}"
        )
    })

    # ── Quality Insights ──────────────────────────────────────
    all_null_cols = []
    zero_null_tables = []
    high_null_tables = []

    for table_name, info in schema.items():
        null_analysis = quality_report.get(
            table_name, {}
        ).get("null_analysis", {})

        table_nulls = [
            (col, stats["null_percent"])
            for col, stats in null_analysis.items()
            if stats["null_percent"] > 0
        ]

        if not table_nulls:
            zero_null_tables.append(table_name)
        else:
            all_null_cols.extend(table_nulls)

        high_nulls = [
            col for col, pct in table_nulls
            if pct > 30
        ]
        if high_nulls:
            high_null_tables.append({
                "table": table_name,
                "columns": high_nulls
            })

        # Duplicate check
        dup = quality_report.get(
            table_name, {}
        ).get("duplicate_analysis", {})
        if dup.get("duplicate_percent", 0) > 0:
            insights["warnings"].append({
                "icon": "⚠️",
                "title": f"Duplicates in {table_name}",
                "detail": (
                    f"{dup['duplicate_count']} duplicate rows found "
                    f"({dup['duplicate_percent']}%). "
                    f"Consider cleaning before analysis."
                )
            })

    if zero_null_tables:
        insights["quality_insights"].append({
            "icon": "✅",
            "title": "Clean Tables Found",
            "detail": (
                f"{len(zero_null_tables)} tables have zero null values: "
                f"{', '.join(zero_null_tables[:3])}. "
                f"Great data quality!"
            )
        })

    if high_null_tables:
        for item in high_null_tables[:3]:
            insights["warnings"].append({
                "icon": "🔴",
                "title": f"High Nulls in {item['table']}",
                "detail": (
                    f"Columns {item['columns']} have more than 30% "
                    f"missing values. These columns may not be "
                    f"reliable for analysis."
                )
            })

    if all_null_cols:
        worst_col = max(all_null_cols, key=lambda x: x[1])
        insights["quality_insights"].append({
            "icon": "🔍",
            "title": "Most Incomplete Column",
            "detail": (
                f"'{worst_col[0]}' has the highest null rate "
                f"at {worst_col[1]}%. "
                f"Consider whether this column is needed."
            )
        })

    # ── Relationship Insights ─────────────────────────────────
    verified = [r for r in relationships if r.get("verified")]
    unverified = [r for r in relationships if not r.get("verified")]

    if verified:
        insights["relationship_insights"].append({
            "icon": "🔗",
            "title": "Connected Tables",
            "detail": (
                f"Found {len(verified)} verified connections "
                f"between tables. This is a well-structured "
                f"relational database."
            )
        })

    if unverified:
        insights["relationship_insights"].append({
            "icon": "❓",
            "title": "Possible Connections",
            "detail": (
                f"{len(unverified)} possible relationships found "
                f"but could not be fully verified. "
                f"Manual review recommended."
            )
        })

    # Most connected table
    connection_count = {}
    for rel in verified:
        t = rel["from_table"]
        connection_count[t] = connection_count.get(t, 0) + 1

    if connection_count:
        most_connected = max(
            connection_count.items(),
            key=lambda x: x[1]
        )
        insights["relationship_insights"].append({
            "icon": "⭐",
            "title": "Central Table",
            "detail": (
                f"'{most_connected[0]}' is the most connected table "
                f"with {most_connected[1]} relationships — "
                f"likely the main/fact table of this database."
            )
        })

    # ── Business Insights ─────────────────────────────────────
    summary = data_dictionary.get("_business_summary", {})
    key_insights = summary.get("key_insights", [])

    for insight in key_insights:
        insights["business_insights"].append({
            "icon": "💡",
            "title": "Business Insight",
            "detail": insight
        })

    # ── Recommendations ───────────────────────────────────────
    if high_null_tables:
        insights["recommendations"].append({
            "icon": "🧹",
            "priority": "High",
            "title": "Clean Null Values",
            "detail": (
                "Several columns have high null rates. "
                "Consider filling missing values or "
                "removing incomplete records before analysis."
            )
        })

    if len(verified) < total_tables - 1:
        insights["recommendations"].append({
            "icon": "🔗",
            "priority": "Medium",
            "title": "Review Table Relationships",
            "detail": (
                "Not all tables appear to be connected. "
                "Verify that all tables have proper "
                "foreign key relationships defined."
            )
        })

    if any(
        quality_report.get(t, {}).get(
            "duplicate_analysis", {}
        ).get("duplicate_percent", 0) > 0
        for t in schema.keys()
    ):
        insights["recommendations"].append({
            "icon": "🔄",
            "priority": "High",
            "title": "Remove Duplicates",
            "detail": (
                "Duplicate rows found in some tables. "
                "Remove duplicates to ensure accurate "
                "counts and aggregations."
            )
        })

    insights["recommendations"].append({
        "icon": "📈",
        "priority": "Low",
        "title": "Add Indexes",
        "detail": (
            "For faster queries, consider adding database "
            "indexes on ID columns and frequently "
            "filtered columns."
        )
    })

    return insights