import os
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


def build_context(data_dictionary, relationships, quality_report):
    context = ""

    summary = data_dictionary.get("_business_summary", {})
    if summary:
        context += f"BUSINESS TYPE: {summary.get('business_type', '')}\n"
        context += f"SUMMARY: {summary.get('summary', '')}\n\n"

    context += "TABLES:\n"
    for table_name, info in data_dictionary.items():
        if table_name == "_business_summary":
            continue

        context += f"\nTable: {table_name}\n"
        context += f"Description: {info.get('table_description', '')}\n"
        context += f"Rows: {info.get('row_count', 0):,}\n"

        context += "Columns:\n"
        for col in info.get("columns", []):
            col_name = col["column_name"]
            col_desc = info.get(
                "column_descriptions", {}
            ).get(col_name, "")
            context += f"  - {col_name}: {col_desc}\n"

        null_analysis = quality_report.get(
            table_name, {}
        ).get("null_analysis", {})
        problem_cols = [
            col for col, stats in null_analysis.items()
            if stats.get("null_percent", 0) > 5
        ]
        if problem_cols:
            context += f"Quality issues in: {problem_cols}\n"

    context += "\nRELATIONSHIPS:\n"
    for rel in relationships:
        if rel.get("verified"):
            context += (
                f"  {rel['from_table']}.{rel['from_column']} "
                f"→ {rel['to_table']}.{rel['to_column']}\n"
            )

    return context


def chat_with_data(
    user_question,
    data_dictionary,
    relationships,
    quality_report,
    chat_history=[]
):
    context = build_context(
        data_dictionary, relationships, quality_report
    )

    system_prompt = f"""You are a friendly data analyst helping beginners understand their database.

{context}

Rules:
- Use simple plain English always
- Use bullet points for lists
- Be encouraging and beginner friendly
- Keep answers short and clear
- No technical jargon unless asked
"""

    messages = [{"role": "system", "content": system_prompt}]

    for msg in chat_history[-6:]:
        messages.append(msg)

    messages.append({
        "role": "user",
        "content": user_question
    })

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Sorry, error: {str(e)}"


def get_suggested_questions(data_dictionary):
    tables = [
        k for k in data_dictionary.keys()
        if k != "_business_summary"
    ]

    questions = [
        "What does this database store?",
        "Which table is the most important?",
        "What are all the tables and what do they do?",
        "Which columns have data quality issues?",
        "How are the tables connected to each other?",
    ]

    for table in tables[:2]:
        questions.append(f"What is the {table} table used for?")

    return questions