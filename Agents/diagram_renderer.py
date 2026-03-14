def render_mermaid(mermaid_code):
    """
    Renders Mermaid diagram inside Streamlit
    using a safe HTML + JS approach
    """

    # Escape backticks and backslashes in mermaid code
    safe_code = mermaid_code.replace("\\", "\\\\").replace("`", "\\`")

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            margin: 0;
            padding: 10px;
            background: white;
            font-family: sans-serif;
        }}
        #diagram-container {{
            width: 100%;
            overflow-x: auto;
            background: white;
            border-radius: 8px;
            padding: 10px;
        }}
        #error-box {{
            display: none;
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            color: #856404;
        }}
        .mermaid {{
            text-align: center;
        }}
        svg {{
            max-width: 100%;
            height: auto;
        }}
    </style>
</head>
<body>
    <div id="error-box">
        ⚠️ <strong>Diagram render error.</strong>
        Check the Mermaid Code tab for details.
        <pre id="error-msg" style="font-size:12px; margin-top:8px;"></pre>
    </div>

    <div id="diagram-container">
        <div class="mermaid" id="mermaid-diagram">
        </div>
    </div>

    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';

        mermaid.initialize({{
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'loose',
            er: {{
                diagramPadding: 30,
                layoutDirection: 'TB',
                minEntityWidth: 120,
                minEntityHeight: 50,
                entityPadding: 10,
                useMaxWidth: true
            }},
            fontFamily: 'arial, sans-serif',
            fontSize: 14
        }});

        const diagramCode = `{safe_code}`;

        try {{
            const {{ svg }} = await mermaid.render('mermaid-svg', diagramCode);
            document.getElementById('mermaid-diagram').innerHTML = svg;
        }} catch (err) {{
            document.getElementById('error-box').style.display = 'block';
            document.getElementById('error-msg').textContent = err.message || err;
            document.getElementById('diagram-container').style.display = 'none';
        }}
    </script>
</body>
</html>
"""
    return html