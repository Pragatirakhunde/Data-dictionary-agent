import streamlit as st
import pandas as pd
import os
import json
import shutil
from dotenv import load_dotenv

load_dotenv()
import streamlit as st
def get_api_key():
    # Try Streamlit secrets first (cloud deployment)
    try:
        return st.secrets["GROQ_API_KEY"]
    except:
        # Fall back to .env for local development
        return os.getenv("GROQ_API_KEY")
    
from Agents.schema_extractor import extract_full_schema
from Agents.quality_checker import run_quality_check
from Agents.relationship_mapper import (
    build_relationship_map,
    generate_mermaid_diagram
)
from Agents.llm_describer import generate_full_descriptions

# ── Page Config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Data Dictionary Agent",
    page_icon="🗃️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Load CSS ─────────────────────────────────────────────────────
with open("static/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ── Helper Functions ─────────────────────────────────────────────
def save_uploaded_files(uploaded_files):
    upload_dir = "uploads"
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)
    os.makedirs(upload_dir)
    for file in uploaded_files:
        path = os.path.join(upload_dir, file.name)
        with open(path, "wb") as f:
            f.write(file.getbuffer())
    return upload_dir


def get_quality_color(null_percent):
    if null_percent == 0:
        return "🟢"
    elif null_percent < 5:
        return "🟡"
    elif null_percent < 30:
        return "🟠"
    else:
        return "🔴"


def save_results(data_dictionary, relationships):
    os.makedirs("output", exist_ok=True)
    with open("output/data_dictionary.json", "w") as f:
        json.dump(data_dictionary, f, indent=2, default=str)
    with open("output/relationships.json", "w") as f:
        json.dump(relationships, f, indent=2, default=str)


# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/database.png",
        width=70
    )
    st.title("Data Dictionary Agent")
    st.caption("AI-powered database documentation")
    st.markdown("---")

    # Beginner Guide
    st.markdown("### 🧭 How It Works")
    steps = [
        ("1️⃣", "Upload CSV files",
         "Your database tables as CSV files"),
        ("2️⃣", "Click Analyze",
         "AI reads everything automatically"),
        ("3️⃣", "Explore Results",
         "View docs, diagrams and insights"),
        ("4️⃣", "Ask Questions",
         "Chat with AI about your data"),
    ]
    for icon, title, desc in steps:
        st.markdown(f"""
        <div class="step-card">
            <b>{icon} {title}</b><br>
            <span style="font-size:0.85rem;color:#666;">
                {desc}
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Settings
    st.markdown("### ⚙️ Settings")
    use_ai = st.toggle(
        "Enable AI Descriptions",
        value=True,
        help="Uses Groq AI to generate plain English descriptions"
    )
    show_sample = st.toggle(
        "Show Sample Data",
        value=True,
        help="Shows first 3 rows of each table"
    )
    beginner_mode = st.toggle(
        "Beginner Mode",
        value=True,
        help="Shows extra explanations and tips throughout the app"
    )

    st.markdown("---")

    # Dataset link
    st.markdown("### 📦 Sample Dataset")
    st.markdown(
        "[Download Olist Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)"
    )
    st.caption(
        "9 CSV files, 100K+ orders — "
        "perfect for testing this app!"
    )

    if not get_api_key():
        st.error("⚠️ No Groq API key in .env file")


# ── Main Header ──────────────────────────────────────────────────
st.markdown(
    '<p class="main-header">🗃️ Data Dictionary Agent</p>',
    unsafe_allow_html=True
)
st.markdown(
    '<p class="sub-header">'
    'Upload your database → Get instant AI-powered documentation'
    '</p>',
    unsafe_allow_html=True
)

# Beginner tip
if "beginner_mode" not in st.session_state:
    st.session_state.beginner_mode = True

with st.expander(
    "👋 New here? Click to learn what this app does",
    expanded=False
):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        #### 🤔 The Problem
        You have a database with many tables
        and columns but no documentation.
        Understanding it takes hours manually.
        """)
    with col2:
        st.markdown("""
        #### ✨ The Solution
        Upload your CSV files and our AI
        automatically reads everything and
        writes documentation for you.
        """)
    with col3:
        st.markdown("""
        #### 📤 What You Get
        - Plain English descriptions
        - Visual ER diagram
        - Data quality report
        - AI chat assistant
        """)

st.markdown("---")

# ── Upload Section ───────────────────────────────────────────────
st.markdown("### 📁 Step 1: Upload Your CSV Files")

if beginner_mode:
    st.markdown("""
    <div class="upload-hint">
        💡 <b>What is a CSV file?</b>
        A CSV file is a spreadsheet saved as plain text.
        Each CSV file = one database table.
        Upload multiple CSVs to see how tables connect!
    </div>
    """, unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Drop your CSV files here",
    type=["csv"],
    accept_multiple_files=True,
    help=(
        "Upload one or more CSV files. "
        "Each file becomes a table in your database."
    )
)

if uploaded_files:
    # Show uploaded files nicely
    st.markdown("**Files ready to analyze:**")
    file_cols = st.columns(min(len(uploaded_files), 4))
    for i, f in enumerate(uploaded_files):
        with file_cols[i % 4]:
            size_kb = round(f.size / 1024, 1)
            st.markdown(f"""
            <div style="
                background:#f0f4ff;
                color:black;
                border-radius:10px;
                padding:10px;
                text-align:center;
                border:1px solid #667eea44;
                margin-bottom:8px;
            ">
                📄 <b>{f.name}</b><br>
                <span style="font-size:0.8rem;color:#888;">
                    {size_kb} KB
                </span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### 🚀 Step 2: Analyze Your Database")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_btn = st.button(
            "🔍 Analyze Database",
            type="primary",
            use_container_width=True
        )

    if analyze_btn:
        with st.spinner("Analyzing your database..."):

            progress = st.progress(0, text="Starting...")

            # Save files
            progress.progress(10, text="📁 Saving files...")
            upload_dir = save_uploaded_files(uploaded_files)

            # Extract schema
            progress.progress(25, text="🔍 Reading table structures...")
            try:
                engine, schema = extract_full_schema(upload_dir)
            except Exception as e:
                st.error(f"❌ Could not read files: {e}")
                st.stop()

            # Quality check
            progress.progress(45, text="📊 Checking data quality...")
            quality_report = run_quality_check(engine, schema)

            # Relationships
            progress.progress(60, text="🔗 Finding table connections...")
            relationships = build_relationship_map(engine)
            mermaid_code = generate_mermaid_diagram(
                relationships, schema
            )

            # AI descriptions
            if use_ai and get_api_key():
                progress.progress(
                    75,
                    text="🤖 Generating AI descriptions..."
                )
                data_dictionary = generate_full_descriptions(
                    schema, relationships, quality_report
                )
            else:
                data_dictionary = {}
                for table_name, info in schema.items():
                    data_dictionary[table_name] = {
                        "table_description": (
                            f"Table with {info['row_count']:,} records"
                        ),
                        "column_descriptions": {},
                        "columns": info["columns"],
                        "row_count": info["row_count"],
                        "primary_keys": info["primary_keys"],
                        "foreign_keys": info["foreign_keys"],
                        "quality": quality_report.get(table_name, {})
                    }

            # Save results
            progress.progress(95, text="💾 Saving results...")
            save_results(data_dictionary, relationships)
            progress.progress(100, text="✅ Done!")

        st.success(
            f"🎉 Analysis complete! "
            f"Found {len(schema)} tables with "
            f"{sum(i['row_count'] for i in schema.values()):,} "
            f"total records."
        )

        # Store in session
        st.session_state.data_dictionary = data_dictionary
        st.session_state.relationships = relationships
        st.session_state.mermaid_code = mermaid_code
        st.session_state.schema = schema
        st.session_state.quality_report = quality_report


# ── Results ──────────────────────────────────────────────────────
if "data_dictionary" in st.session_state:
    data_dictionary = st.session_state.data_dictionary
    relationships = st.session_state.relationships
    mermaid_code = st.session_state.mermaid_code
    schema = st.session_state.schema
    quality_report = st.session_state.quality_report

    st.markdown("---")
    st.markdown("### 📊 Step 3: Explore Your Results")

    # Business summary banner
    summary = data_dictionary.get("_business_summary", {})
    if summary:
        st.info(
            f"🏢 **{summary.get('business_type', 'Database')}** — "
            f"{summary.get('summary', '')}"
        )

    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "📋 Tables",
            len(schema),
            help="Total number of tables in your database"
        )
    with col2:
        total_rows = sum(
            i["row_count"] for i in schema.values()
        )
        st.metric(
            "📝 Records",
            f"{total_rows:,}",
            help="Total number of rows across all tables"
        )
    with col3:
        verified = sum(
            1 for r in relationships if r.get("verified")
        )
        st.metric(
            "🔗 Connections",
            verified,
            help="Number of verified relationships between tables"
        )
    with col4:
        total_cols = sum(
            len(i["columns"]) for i in schema.values()
        )
        st.metric(
            "📌 Columns",
            total_cols,
            help="Total number of columns across all tables"
        )

    st.markdown("---")

    # ── Tabs ─────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📖 Data Dictionary",
        "🔗 ER Diagram",
        "📊 Quality Report",
        "💡 Insights",
        "💬 Ask AI",
        "⬇️ Download"
    ])

    # ── TAB 1: Data Dictionary ────────────────────────────────
    with tab1:
        st.markdown("### 📖 Data Dictionary")

        if beginner_mode:
            st.info(
                "💡 **What is a Data Dictionary?** "
                "It's a document that explains every table "
                "and column in plain English. "
                "Click any table below to expand it!"
            )

        # Search bar
        search = st.text_input(
            "🔍 Search columns or tables",
            placeholder="Type a column name like 'customer_id'...",
            help="Search across all tables and columns"
        )

        for table_name, table_info in data_dictionary.items():
            if table_name == "_business_summary":
                continue

            # Filter by search
            if search:
                cols_match = any(
                    search.lower() in c["column_name"].lower()
                    for c in table_info.get("columns", [])
                )
                name_match = search.lower() in table_name.lower()
                if not cols_match and not name_match:
                    continue

            with st.expander(
                f"📋 {table_name}   "
                f"({table_info.get('row_count', 0):,} rows)",
                expanded=False
            ):
                if table_info.get("table_description"):
                    st.markdown(
                        f"**What this table stores:** "
                        f"{table_info['table_description']}"
                    )

                st.markdown("---")

                col_data = []
                for col in table_info.get("columns", []):
                    col_name = col["column_name"]
                    col_type = col["data_type"]

                    ai_desc = table_info.get(
                        "column_descriptions", {}
                    ).get(col_name, "—")

                    null_info = quality_report.get(
                        table_name, {}
                    ).get("null_analysis", {}).get(col_name, {})

                    null_pct = null_info.get("null_percent", 0)
                    quality_icon = get_quality_color(null_pct)
                    is_pk = col_name in table_info.get(
                        "primary_keys", []
                    )

                    col_data.append({
                        "Column Name": col_name,
                        "Data Type": col_type,
                        "Key": "🔑 Primary Key" if is_pk else "",
                        "Missing Data": f"{null_pct}% {quality_icon}",
                        "Plain English Description": ai_desc
                    })

                if col_data:
                    st.dataframe(
                        pd.DataFrame(col_data),
                        use_container_width=True,
                        hide_index=True
                    )

                if show_sample:
                    sample = schema.get(
                        table_name, {}
                    ).get("sample_data", [])
                    if sample:
                        st.markdown("**Sample Data (first 3 rows):**")
                        if beginner_mode:
                            st.caption(
                                "💡 This shows you what real data "
                                "in this table looks like"
                            )
                        st.dataframe(
                            pd.DataFrame(sample),
                            use_container_width=True,
                            hide_index=True
                        )

    # ── TAB 2: ER Diagram ─────────────────────────────────────
    with tab2:
        from Agents.diagram_renderer import render_mermaid
        import streamlit.components.v1 as components

        st.markdown("### 🔗 Entity Relationship Diagram")

        if beginner_mode:
            st.info(
                "💡 **What is an ER Diagram?** "
                "It's a visual map showing how all your "
                "tables connect to each other. "
                "Lines between tables = they share data!"
            )

        view_mode = st.radio(
            "View as:",
            ["🖼️ Visual Diagram", "📝 Mermaid Code"],
            horizontal=True
        )

        if view_mode == "🖼️ Visual Diagram":
            st.markdown("#### Live ER Diagram")
            with st.expander("🔍 View raw Mermaid code"):
                st.code(mermaid_code, language="text")
            mermaid_html = render_mermaid(mermaid_code)
            components.html(
                mermaid_html,
                height=600,
                scrolling=True
            )
        else:
            st.code(mermaid_code, language="text")

        st.markdown("---")
        st.markdown("### 🔗 Relationships Found")

        if relationships:
            rel_data = []
            for rel in relationships:
                rel_data.append({
                    "From Table": rel["from_table"],
                    "From Column": rel["from_column"],
                    "→": "links to",
                    "To Table": rel["to_table"],
                    "To Column": rel["to_column"],
                    "Confidence": rel["confidence"],
                    "Verified": (
                        "✅ Yes" if rel.get("verified")
                        else "❓ Unverified"
                    )
                })
            st.dataframe(
                pd.DataFrame(rel_data),
                use_container_width=True,
                hide_index=True
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "✅ Verified",
                    sum(
                        1 for r in relationships
                        if r.get("verified")
                    )
                )
            with col2:
                st.metric(
                    "🎯 High Confidence",
                    sum(
                        1 for r in relationships
                        if r["confidence"] == "high"
                    )
                )
            with col3:
                st.metric("🔗 Total Found", len(relationships))
        else:
            st.warning(
                "No relationships found. "
                "Try uploading multiple related tables."
            )

    # ── TAB 3: Quality Report ─────────────────────────────────
    with tab3:
        from Agents.visualizer import (
            calculate_health_score,
            get_health_color,
            get_health_label,
            create_health_score_chart,
            create_null_heatmap,
            create_table_size_chart,
            create_column_type_chart,
            create_null_bar_chart
        )

        st.markdown("### 📊 Data Quality Dashboard")

        if beginner_mode:
            st.info(
                "💡 **What is Data Quality?** "
                "It measures how complete and reliable "
                "your data is. "
                "High score = clean data ready for analysis!"
            )

        all_scores = [
            calculate_health_score(quality_report, t)
            for t in schema.keys()
        ]
        overall_score = int(
            sum(all_scores) / len(all_scores)
        )
        health_color = get_health_color(overall_score)
        health_label = get_health_label(overall_score)

        st.markdown(f"""
        <div style="
            background:{health_color}22;
            border:2px solid {health_color};
            border-radius:16px;
            padding:24px;
            text-align:center;
            margin-bottom:24px;
        ">
            <div style="
                font-size:3rem;
                font-weight:700;
                color:{health_color};
            ">{overall_score}/100</div>
            <div style="
                font-size:1.3rem;
                color:{health_color};
                margin-top:4px;
            ">Overall Database Health: {health_label}</div>
            <div style="
                font-size:0.9rem;
                color:#666;
                margin-top:8px;
            ">
                Based on missing values,
                duplicates and completeness
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        total_cols_q = sum(
            len(i["columns"]) for i in schema.values()
        )
        total_nulls = sum(
            sum(
                s.get("null_count", 0)
                for s in quality_report.get(
                    t, {}
                ).get("null_analysis", {}).values()
            )
            for t in schema.keys()
        )
        with col1:
            st.metric("📋 Total Columns", total_cols_q)
        with col2:
            st.metric(
                "⚠️ Missing Cells",
                f"{total_nulls:,}",
                help="Total empty/null values across all tables"
            )
        with col3:
            st.metric(
                "✅ Healthy Tables",
                sum(1 for s in all_scores if s >= 80)
            )
        with col4:
            st.metric(
                "🔴 Problem Tables",
                sum(1 for s in all_scores if s < 60)
            )

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(
                create_health_score_chart(
                    quality_report, schema
                ),
                use_container_width=True
            )
        with col2:
            st.plotly_chart(
                create_table_size_chart(schema),
                use_container_width=True
            )

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(
                create_column_type_chart(schema),
                use_container_width=True
            )
        with col2:
            heatmap = create_null_heatmap(
                quality_report, schema
            )
            if heatmap:
                st.plotly_chart(
                    heatmap,
                    use_container_width=True
                )

        st.markdown("---")
        st.markdown("### 🔍 Drill Down by Table")

        for table_name in schema.keys():
            score = calculate_health_score(
                quality_report, table_name
            )
            label = get_health_label(score)

            with st.expander(
                f"{label}  {table_name}  —  "
                f"Score: {score}/100"
            ):
                col1, col2, col3 = st.columns(3)
                dup = quality_report.get(
                    table_name, {}
                ).get("duplicate_analysis", {})

                with col1:
                    st.metric("Health Score", f"{score}/100")
                with col2:
                    st.metric(
                        "Duplicate Rows",
                        dup.get("duplicate_count", 0)
                    )
                with col3:
                    st.metric(
                        "Total Rows",
                        f"{dup.get('total_rows', 0):,}"
                    )

                null_fig = create_null_bar_chart(
                    quality_report, table_name
                )
                if null_fig:
                    st.plotly_chart(
                        null_fig,
                        use_container_width=True
                    )

    # ── TAB 4: Insights ───────────────────────────────────────
    with tab4:
        from Agents.insights_generator import generate_insights

        st.markdown("### 💡 Smart Database Insights")

        if beginner_mode:
            st.info(
                "💡 These insights are automatically generated "
                "by analyzing your database. "
                "No SQL knowledge needed!"
            )

        insights = generate_insights(
            schema,
            quality_report,
            relationships,
            data_dictionary
        )

        if insights["warnings"]:
            st.markdown("### ⚠️ Warnings — Action Needed")
            for w in insights["warnings"]:
                st.warning(
                    f"**{w['title']}** — {w['detail']}"
                )

        st.markdown("### 🗃️ Database Overview")
        cols = st.columns(2)
        for i, insight in enumerate(
            insights["overview_insights"]
        ):
            with cols[i % 2]:
                st.markdown(f"""
                <div class="insight-card" style="
                    border-left:4px solid #4e79a7;
                ">
                    <div style="font-size:1.5rem;">
                        {insight['icon']}
                    </div>
                    <div style="
                        font-weight:600;
                        margin:6px 0 4px;
                    ">{insight['title']}</div>
                    <div style="color:#555;font-size:0.9rem;">
                        {insight['detail']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        if insights["quality_insights"]:
            st.markdown("### 🔍 Data Quality Insights")
            cols = st.columns(2)
            for i, insight in enumerate(
                insights["quality_insights"]
            ):
                with cols[i % 2]:
                    st.markdown(f"""
                    <div class="insight-card" style="
                        border-left:4px solid #28a745;
                    ">
                        <div style="font-size:1.5rem;">
                            {insight['icon']}
                        </div>
                        <div style="
                            font-weight:600;
                            margin:6px 0 4px;
                        ">{insight['title']}</div>
                        <div style="
                            color:#555;font-size:0.9rem;
                        ">{insight['detail']}</div>
                    </div>
                    """, unsafe_allow_html=True)

        if insights["relationship_insights"]:
            st.markdown("### 🔗 Relationship Insights")
            cols = st.columns(2)
            for i, insight in enumerate(
                insights["relationship_insights"]
            ):
                with cols[i % 2]:
                    st.markdown(f"""
                    <div class="insight-card" style="
                        border-left:4px solid #fd7e14;
                    ">
                        <div style="font-size:1.5rem;">
                            {insight['icon']}
                        </div>
                        <div style="
                            font-weight:600;
                            margin:6px 0 4px;
                        ">{insight['title']}</div>
                        <div style="
                            color:#555;font-size:0.9rem;
                        ">{insight['detail']}</div>
                    </div>
                    """, unsafe_allow_html=True)

        if insights["business_insights"]:
            st.markdown("### 💼 Business Insights")
            for insight in insights["business_insights"]:
                st.info(
                    f"**{insight['icon']} "
                    f"{insight['title']}** "
                    f"— {insight['detail']}"
                )

        st.markdown("### 🚀 Recommendations")
        for rec in insights["recommendations"]:
            priority_color = {
                "High": "🔴",
                "Medium": "🟡",
                "Low": "🟢"
            }.get(rec["priority"], "⚪")

            st.markdown(f"""
            <div class="insight-card">
                <div style="
                    display:flex;
                    justify-content:space-between;
                ">
                    <b>{rec['icon']} {rec['title']}</b>
                    <span>
                        Priority: {priority_color}
                        {rec['priority']}
                    </span>
                </div>
                <div style="
                    color:#555;
                    font-size:0.9rem;
                    margin-top:8px;
                ">{rec['detail']}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── TAB 5: Ask AI ─────────────────────────────────────────
    with tab5:
        from Agents.chat_agent import (
            chat_with_data,
            get_suggested_questions
        )

        st.markdown("### 💬 Ask AI About Your Database")

        if beginner_mode:
            st.info(
                "💡 Ask anything in plain English! "
                "No SQL or technical knowledge needed. "
                "Try clicking one of the suggested "
                "questions below to get started."
            )

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "messages_display" not in st.session_state:
            st.session_state.messages_display = []

        st.markdown("#### 💡 Suggested Questions")
        suggested = get_suggested_questions(data_dictionary)
        cols = st.columns(2)
        for i, question in enumerate(suggested[:6]):
            with cols[i % 2]:
                if st.button(
                    question,
                    key=f"suggest_{i}",
                    use_container_width=True
                ):
                    st.session_state.pending_question = question

        st.markdown("---")
        st.markdown("#### 🗨️ Conversation")

        for msg in st.session_state.messages_display:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input(
            "Ask me anything about your database..."
        )

        if "pending_question" in st.session_state:
            user_input = st.session_state.pending_question
            del st.session_state.pending_question

        if user_input:
            with st.chat_message("user"):
                st.markdown(user_input)

            st.session_state.messages_display.append({
                "role": "user",
                "content": user_input
            })

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = chat_with_data(
                        user_question=user_input,
                        data_dictionary=data_dictionary,
                        relationships=relationships,
                        quality_report=quality_report,
                        chat_history=st.session_state.chat_history
                    )
                st.markdown(response)

            st.session_state.messages_display.append({
                "role": "assistant",
                "content": response
            })
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_input
            })
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response
            })
            st.rerun()

        if st.session_state.messages_display:
            st.markdown("---")
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.session_state.messages_display = []
                st.rerun()

    # ── TAB 6: Download ───────────────────────────────────────
    with tab6:
        st.markdown("### ⬇️ Download Your Reports")

        if beginner_mode:
            st.info(
                "💡 Download your documentation to "
                "share with your team or use offline!"
            )

        col1, col2 = st.columns(2)

        with col1:
            if os.path.exists("output/data_dictionary.json"):
                with open(
                    "output/data_dictionary.json", "r"
                ) as f:
                    json_data = f.read()
                st.download_button(
                    "📄 Download Data Dictionary (JSON)",
                    data=json_data,
                    file_name="data_dictionary.json",
                    mime="application/json",
                    use_container_width=True
                )

        with col2:
            st.download_button(
                "📊 Download ER Diagram (Mermaid)",
                data=mermaid_code,
                file_name="er_diagram.mmd",
                mime="text/plain",
                use_container_width=True
            )

        st.markdown("---")

        # Markdown report
        md = "# Data Dictionary Report\n\n"
        if summary:
            md += f"## Summary\n{summary.get('summary', '')}\n\n"

        for t, info in data_dictionary.items():
            if t == "_business_summary":
                continue
            md += f"## {t}\n"
            md += f"**Rows:** {info.get('row_count', 0):,}\n\n"
            md += (
                f"**Description:** "
                f"{info.get('table_description', '')}\n\n"
            )
            md += "| Column | Type | Description |\n"
            md += "|--------|------|-------------|\n"
            for col in info.get("columns", []):
                cn = col["column_name"]
                ct = col["data_type"]
                desc = info.get(
                    "column_descriptions", {}
                ).get(cn, "—")
                md += f"| {cn} | {ct} | {desc} |\n"
            md += "\n"

        st.download_button(
            "📝 Download Full Report (Markdown)",
            data=md,
            file_name="data_dictionary_report.md",
            mime="text/markdown",
            use_container_width=True
        )

# ── Empty State ───────────────────────────────────────────────────
else:
    st.markdown("### 👇 Get Started — Upload CSV Files Above")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="insight-card" style="
            border-left:4px solid #667eea;
            text-align:center;
        ">
            <div style="font-size:2rem;">📖</div>
            <b>Data Dictionary</b><br>
            <span style="font-size:0.85rem;color:#666;">
                Plain English docs for every
                table and column
            </span>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="insight-card" style="
            border-left:4px solid #28a745;
            text-align:center;
        ">
            <div style="font-size:2rem;">📊</div>
            <b>Quality Report</b><br>
            <span style="font-size:0.85rem;color:#666;">
                Health scores, null analysis
                and recommendations
            </span>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="insight-card" style="
            border-left:4px solid #fd7e14;
            text-align:center;
        ">
            <div style="font-size:2rem;">💬</div>
            <b>AI Chat</b><br>
            <span style="font-size:0.85rem;color:#666;">
                Ask anything about your
                data in plain English
            </span>
        </div>
        """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    Built with ❤️ using Streamlit + Groq AI
    | Data Dictionary Agent
</div>
""", unsafe_allow_html=True)