import os
import re
import pandas as pd
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import snowflake.connector
import cortex_chat

# Load environment variables
load_dotenv()

SNOW_ROLE = os.getenv("SNOW_ROLE")
SNOW_PAT = os.getenv("PAT")
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

# Initialize Slack App
app = App(token=SLACK_BOT_TOKEN)

def format_for_slack(text: str) -> str:
    """Convert standard Markdown bold to Slack bold format."""
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
    """
    Unified logic that displays the AI summary AND executes the SQL 
    to show the actual data rows.
    """
    raw_text = event.get('text', '').strip()
    query = re.sub(r'<@\w+>', '', raw_text).strip()
    
    if not query:
        say("👋 Hi! I'm your Loans Assistant. How can I help you today?")
        return

    try:
        say("❄️ _Querying Snowflake..._")
        
        # 1. Get the AI summary and SQL from the Cortex Agent
        # Passing the role ensures RBAC is applied to the generated SQL
        response = CORTEX_APP.chat(query, role=SNOW_ROLE)
        
        # 2. Display the text explanation (The summary)
        if response.get('text'):
            say(text=format_for_slack(response['text']))
            
        # 3. Execute the SQL if the Agent provided one
        # Cortex Analyst returns the SQL in a list called 'sql_queries'
        sql_queries = response.get('sql_queries')
        if sql_queries:
            sql_to_run = sql_queries[0]
            
            # Use the existing Snowflake connection (CONN) to fetch the data
            with CONN.cursor() as cur:
                cur.execute(sql_to_run)
                columns = [col[0] for col in cur.description]
                rows = cur.fetchall()
                df = pd.DataFrame(rows, columns=columns)
            
            if not df.empty:
                # Limit rows to avoid Slack character limits (max 10-15 rows)
                limit = 10
                preview_df = df.head(limit)
                
                # Format as a code block (```) for monospaced alignment
                table_text = preview_df.to_string(index=False)
                say(text=f"```\n{table_text}\n```")
                
                if len(df) > limit:
                    say(f"_...showing first {limit} of {len(df)} rows._")
            else:
                say("_The query returned no results._")

        if response.get('suggestions'):
            suggestion_list = "\n".join([f"• _{s}_" for s in response['suggestions'][:2]])
            say(text=f"*Suggestions:*\n{suggestion_list}")

    except Exception as e:
        print(f"Error: {e}")
        say(f"⚠️ I encountered an error: `{str(e)}`.")

def get_snowflake_conn():
    """Establishes the base connection to Snowflake."""
    return snowflake.connector.connect(
        user=os.getenv("SNOW_USER"),
        password=SNOW_PAT,
        account=os.getenv("ACCOUNT"),
        warehouse=os.getenv("WAREHOUSE"),
        role=SNOW_ROLE
    )

if __name__ == "__main__":
    # Initialize both the Data connection and the AI Agent
    CONN = get_snowflake_conn()
    CORTEX_APP = cortex_chat.CortexChat(AGENT_ENDPOINT, SNOW_PAT)
    
    print(f"🚀 Loans App is running for Role: {SNOW_ROLE}")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()