import os
import re
import pandas as pd
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

@app.event("app_mention")
def handle_app_mentions(event, say):
    process_query(event, say)

@app.message(re.compile(".*"))
def handle_direct_messages(event, say):
    if event.get('channel_type') == 'im':
        process_query(event, say)

def process_query(event, say):
    raw_text = event.get('text', '').strip()
    query = re.sub(r'<@\w+>', '', raw_text).strip()
    
    if not query:
        say("👋 Hi! I'm your Loans Assistant.")
        return

    try:
        say("❄️ _Querying Snowflake..._")
        response = CORTEX_APP.chat(query, role=SNOW_ROLE)
        
        blocks = []
        
        # 1. Preparar el resumen de texto
        if response.get('text'):
            summary = format_for_slack(response['text'])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": summary}
            })

        # 2. Lógica Inteligente para la Tabla
        sql_queries = response.get('sql_queries')
        if sql_queries:
            with CONN.cursor() as cur:
                cur.execute(sql_queries[0])
                df = pd.DataFrame(cur.fetchall(), columns=[col[0] for col in cur.description])
            
            # Solo mostrar tabla si hay más de un dato o es una lista
            # Si el resultado es una sola celda (ej. un Total), el texto suele ser suficiente
            if not df.empty and df.size > 1:
                limit = 10
                table_text = df.head(limit).to_string(index=False)
                
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"```\n{table_text}\n```"}
                })
                
                if len(df) > limit:
                    blocks.append({
                        "type": "context",
                        "elements": [{"type": "mrkdwn", "text": f"_Showing first {limit} of {len(df)} rows._"}]
                    })

        # 3. Sugerencias
        if response.get('suggestions'):
            suggs = "\n".join([f"• _{format_for_slack(s)}_" for s in response['suggestions'][:2]])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Suggestions:*\n{suggs}"}
            })

        # Enviar un único mensaje consolidado
        say(blocks=blocks, text="New data response")

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