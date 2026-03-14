import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def calculate_health_score(quality_report, table_name):
    """
    Calculates a health score 0-100 for a table
    100 = perfect data, 0 = terrible data
    """
    score = 100
    table_quality = quality_report.get(table_name, {})

    # Deduct points for nulls
    null_analysis = table_quality.get("null_analysis", {})
    if null_analysis:
        avg_null = sum(
            v.get("null_percent", 0)
            for v in null_analysis.values()
        ) / len(null_analysis)

        if avg_null > 30:
            score -= 40
        elif avg_null > 10:
            score -= 20
        elif avg_null > 5:
            score -= 10

    # Deduct points for duplicates
    dup = table_quality.get("duplicate_analysis", {})
    dup_pct = dup.get("duplicate_percent", 0)
    if dup_pct > 10:
        score -= 30
    elif dup_pct > 5:
        score -= 15
    elif dup_pct > 0:
        score -= 5

    return max(0, min(100, score))


def get_health_color(score):
    """Returns color based on health score"""
    if score >= 80:
        return "#28a745"   # Green
    elif score >= 60:
        return "#ffc107"   # Yellow
    elif score >= 40:
        return "#fd7e14"   # Orange
    else:
        return "#dc3545"   # Red


def get_health_label(score):
    """Returns label based on health score"""
    if score >= 80:
        return "Excellent ✅"
    elif score >= 60:
        return "Good 🟡"
    elif score >= 40:
        return "Fair 🟠"
    else:
        return "Poor 🔴"


def create_health_score_chart(quality_report, schema):
    """
    Creates a horizontal bar chart showing
    health score for each table
    """
    table_names = []
    scores = []
    colors = []
    labels = []

    for table_name in schema.keys():
        score = calculate_health_score(quality_report, table_name)
        table_names.append(table_name)
        scores.append(score)
        colors.append(get_health_color(score))
        labels.append(get_health_label(score))

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=table_names,
        x=scores,
        orientation='h',
        marker_color=colors,
        text=[f"{s}/100 — {l}" for s, l in zip(scores, labels)],
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Health Score: %{x}/100<extra></extra>"
    ))

    fig.update_layout(
        title="📊 Table Health Scores",
        xaxis_title="Health Score (0-100)",
        yaxis_title="",
        xaxis=dict(range=[0, 120]),
        height=max(300, len(table_names) * 60),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        margin=dict(l=20, r=20, t=50, b=20)
    )

    return fig


def create_null_heatmap(quality_report, schema):
    """
    Creates a heatmap showing null percentages
    across all tables and columns
    """
    data = []

    for table_name in schema.keys():
        null_analysis = quality_report.get(
            table_name, {}
        ).get("null_analysis", {})

        for col_name, stats in null_analysis.items():
            data.append({
                "Table": table_name,
                "Column": col_name,
                "Null %": stats.get("null_percent", 0)
            })

    if not data:
        return None

    df = pd.DataFrame(data)

    # Pivot for heatmap
    try:
        pivot = df.pivot(
            index="Table",
            columns="Column",
            values="Null %"
        ).fillna(0)

        fig = px.imshow(
            pivot,
            color_continuous_scale=[
                [0, "#28a745"],
                [0.05, "#ffc107"],
                [0.3, "#fd7e14"],
                [1, "#dc3545"]
            ],
            title="🔥 Null Value Heatmap (Red = More Nulls)",
            labels=dict(color="Null %"),
            aspect="auto"
        )

        fig.update_layout(
            height=max(300, len(pivot) * 80),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            margin=dict(l=20, r=20, t=50, b=20)
        )

        return fig

    except Exception:
        return None


def create_table_size_chart(schema):
    """
    Creates a pie chart showing
    how many rows each table has
    """
    tables = []
    row_counts = []

    for table_name, info in schema.items():
        tables.append(table_name)
        row_counts.append(info["row_count"])

    fig = go.Figure(data=[
        go.Pie(
            labels=tables,
            values=row_counts,
            hole=0.4,
            textinfo='label+percent',
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Rows: %{value:,}<br>"
                "Share: %{percent}<extra></extra>"
            )
        )
    ])

    fig.update_layout(
        title="🗃️ Data Distribution Across Tables",
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=True
    )

    return fig


def create_column_type_chart(schema):
    """
    Shows breakdown of data types
    across all columns in the database
    """
    type_counts = {}

    for table_name, info in schema.items():
        for col in info["columns"]:
            raw_type = str(col["data_type"]).upper()

            if "INT" in raw_type:
                col_type = "Integer"
            elif "FLOAT" in raw_type or "REAL" in raw_type:
                col_type = "Float"
            elif "DATE" in raw_type or "TIME" in raw_type:
                col_type = "DateTime"
            elif "BOOL" in raw_type:
                col_type = "Boolean"
            else:
                col_type = "Text"

            type_counts[col_type] = type_counts.get(col_type, 0) + 1

    fig = go.Figure(data=[
        go.Bar(
            x=list(type_counts.keys()),
            y=list(type_counts.values()),
            marker_color=[
                "#4e79a7", "#f28e2b",
                "#e15759", "#76b7b2", "#59a14f"
            ][:len(type_counts)],
            text=list(type_counts.values()),
            textposition='outside',
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Count: %{y}<extra></extra>"
            )
        )
    ])

    fig.update_layout(
        title="📌 Column Data Types Breakdown",
        xaxis_title="Data Type",
        yaxis_title="Number of Columns",
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        margin=dict(l=20, r=20, t=50, b=20)
    )

    return fig


def create_null_bar_chart(quality_report, table_name):
    """
    Creates a bar chart for null % per column
    for a single table
    """
    null_analysis = quality_report.get(
        table_name, {}
    ).get("null_analysis", {})

    if not null_analysis:
        return None

    columns = list(null_analysis.keys())
    null_pcts = [
        v.get("null_percent", 0)
        for v in null_analysis.values()
    ]
    colors = [get_health_color(100 - p) for p in null_pcts]

    fig = go.Figure(data=[
        go.Bar(
            x=columns,
            y=null_pcts,
            marker_color=colors,
            text=[f"{p}%" for p in null_pcts],
            textposition='outside',
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Null: %{y}%<extra></extra>"
            )
        )
    ])

    fig.update_layout(
        title=f"Null % per Column — {table_name}",
        xaxis_title="Column",
        yaxis_title="Null %",
        yaxis=dict(range=[0, max(null_pcts) * 1.3 + 5]),
        height=350,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
        margin=dict(l=20, r=20, t=50, b=80),
        xaxis_tickangle=-45
    )

    return fig