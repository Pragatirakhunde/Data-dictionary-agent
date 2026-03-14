import os
import json
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


import streamlit as st

def get_groq_client():
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except:
        api_key = os.getenv("GROQ_API_KEY")
    return Groq(api_key=api_key)

client = get_groq_client()

MODEL = "llama-3.3-70b-versatile"


def describe_table(table_name, columns, sample_data, quality_info=None):
    column_list = "\n".join([
        f"  - {col['column_name']} ({col['data_type']})"
        for col in columns
    ])

    sample_str = json.dumps(
        sample_data[:2], indent=2
    ) if sample_data else "No sample data"

    prompt = f"""
You are a data analyst expert. Analyze this database table.

Table Name: {table_name}

Columns:
{column_list}

Sample Data:
{sample_str}

Return ONLY this JSON format, nothing else:
{{
    "table_description": "2-3 sentence description of what this table stores",
    "column_descriptions": {{
        "column_name": "one line description"
    }}
}}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data documentation expert. Always respond with valid JSON only. No extra text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )

        response_text = response.choices[0].message.content.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        return json.loads(response_text)

    except json.JSONDecodeError:
        return {
            "table_description": f"Table containing data related to {table_name}",
            "column_descriptions": {
                col["column_name"]: f"Contains {col['column_name']} data"
                for col in columns
            }
        }
    except Exception as e:
        print(f"Error for {table_name}: {e}")
        return {
            "table_description": f"Table containing data related to {table_name}",
            "column_descriptions": {
                col["column_name"]: f"Contains {col['column_name']} data"
                for col in columns
            }
        }


def generate_business_summary(schema, relationships, quality_report):
    table_names = list(schema.keys())
    total_tables = len(table_names)
    total_rows = sum(info["row_count"] for info in schema.values())

    prompt = f"""
Analyze this database and return ONLY JSON:

- Tables: {", ".join(table_names)}
- Total Records: {total_rows:,}
- Relationships: {len(relationships)}

Return ONLY this JSON:
{{
    "business_type": "type of business system",
    "summary": "2-3 sentence summary",
    "main_entities": ["entity1", "entity2"],
    "data_flow": "how data flows between tables",
    "key_insights": ["insight1", "insight2", "insight3"]
}}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data analyst. Return valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=600
        )

        response_text = response.choices[0].message.content.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        return json.loads(response_text)

    except Exception as e:
        print(f"Summary error: {e}")
        return {
            "business_type": "Database System",
            "summary": f"A database with {total_tables} tables and {total_rows:,} records",
            "main_entities": table_names,
            "data_flow": "Data flows between tables via shared keys",
            "key_insights": [
                f"{total_tables} tables found",
                f"{total_rows:,} total records"
            ]
        }


def generate_full_descriptions(schema, relationships, quality_report):
    print("Generating AI descriptions using Groq (free)...")
    data_dictionary = {}

    print("  Generating business summary...")
    business_summary = generate_business_summary(
        schema, relationships, quality_report
    )
    data_dictionary["_business_summary"] = business_summary

    for i, (table_name, table_info) in enumerate(schema.items()):
        print(f"  Describing table {i+1}/{len(schema)}: {table_name}...")

        description = describe_table(
            table_name=table_name,
            columns=table_info["columns"],
            sample_data=table_info.get("sample_data", []),
            quality_info=quality_report.get(table_name, {})
        )

        data_dictionary[table_name] = {
            "table_description": description.get("table_description", ""),
            "column_descriptions": description.get("column_descriptions", {}),
            "columns": table_info["columns"],
            "row_count": table_info["row_count"],
            "primary_keys": table_info["primary_keys"],
            "foreign_keys": table_info["foreign_keys"],
            "quality": quality_report.get(table_name, {})
        }

        time.sleep(0.2)

    print(f"Done! Described {len(schema)} tables")
    return data_dictionary