import os
import re
import pandas as pd
import io

# --- FIX PARA EL ERROR DE MATPLOTLIB ---
import matplotlib
matplotlib.use('Agg') # Esto debe ir ANTES de importar pyplot
import matplotlib.pyplot as plt
# ---------------------------------------

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import snowflake.connector
import cortex_chat

load_dotenv()

# Configuración
SNOW_ROLE = os.getenv("SNOW_ROLE")
SNOW_PAT = os.getenv("PAT")
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

app = App(token=SLACK_BOT_TOKEN)

def format_for_slack(text: str) -> str:
    if not text: return ""
    return re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)

def generate_chart(df: pd.DataFrame):
    """Genera un gráfico basado en los datos del DataFrame"""
    try:
        # Detectar columnas
        num_cols = df.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'datetime']).columns.tolist()

        if not num_cols or not cat_cols:
            return None

        # Crear el gráfico
        fig, ax = plt.subplots(figsize=(10, 6))
        df.plot(kind='bar', x=cat_cols[0], y=num_cols[0], ax=ax, color='#29B5E8')
        
        ax.set_title(f"Análisis de {num_cols[0]}", fontsize=14, pad=20)
        ax.set_ylabel(num_cols[0])
        ax.set_xlabel(cat_cols[0])
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Guardar en memoria
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png')
        plt.close(fig) # Importante cerrar la figura para liberar memoria
        img_data.seek(0)
        return img_data
    except Exception as e:
        print(f"Error generando gráfico: {e}")
        return None

@app.event("app_mention")
def handle_app_mentions(event, say, client):
    process_query(event, say, client)

@app.message(re.compile(".*"))
def handle_direct_messages(event, say, client):
    if event.get('channel_type') == 'im':
        process_query(event, say, client)

def process_query(event, say, client):
    raw_text = event.get('text', '').strip()
    query = re.sub(r'<@\w+>', '', raw_text).strip()
    channel = event['channel']
    
    if not query:
        say("👋 Hi! I'm your Loans Assistant.")
        return

    try:
        # Restauramos el mensaje de espera
        say("❄️ _Querying Snowflake..._")
        
        response = CORTEX_APP.chat(query, role=SNOW_ROLE)
        blocks = []
        
        # 1. Resumen de texto
        if response.get('text'):
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": format_for_slack(response['text'])}
            })

        # 2. Lógica de Datos y Visualización
        sql_queries = response.get('sql_queries')
        if sql_queries:
            with CONN.cursor() as cur:
                cur.execute(sql_queries[0])
                df = pd.DataFrame(cur.fetchall(), columns=[col[0] for col in cur.description])
            
            if not df.empty:
                chart_img = generate_chart(df)
                
                if chart_img:
                    # Si hay gráfico, lo subimos y NO ponemos la tabla de texto
                    client.files_upload_v2(
                        channel=channel,
                        file=chart_img,
                        filename="chart.png"
                        #title="Resultados Visuales",
                        #initial_comment="📊 Aquí tienes el gráfico basado en los datos:"
                    )
                else:
                    # Si no hay gráfico (ej. son solo IDs), mostramos tabla simple
                    table_text = df.head(5).to_string(index=False)
                    blocks.append({
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"```\n{table_text}\n```"}
                    })

        # 3. Sugerencias compactas
        if response.get('suggestions'):
            suggs = " | ".join([f"_{format_for_slack(s)}_" for s in response['suggestions'][:2]])
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"*Suggestions:* {suggs}"}]
            })

        say(blocks=blocks, text="Respuesta de Loans Assistant")

    except Exception as e:
        say(f"⚠️ Error: `{str(e)}`")

def get_snowflake_conn():
    return snowflake.connector.connect(
        user=os.getenv("SNOW_USER"),
        password=SNOW_PAT,
        account=os.getenv("ACCOUNT"),
        warehouse=os.getenv("WAREHOUSE"),
        role=SNOW_ROLE
    )

if __name__ == "__main__":
    CONN = get_snowflake_conn()
    CORTEX_APP = cortex_chat.CortexChat(AGENT_ENDPOINT, SNOW_PAT)
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()