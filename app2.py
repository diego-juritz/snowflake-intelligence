import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import cortex_chat

# Load environment variables
load_dotenv()

# Snowflake Configuration
SNOW_ROLE = os.getenv("SNOW_ROLE")
SNOW_PAT = os.getenv("PAT")
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT")

# Slack Configuration
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
    """Handles mentions in channels. Only fires once."""
    process_query(event, say)

@app.message(re.compile(".*"))
def handle_direct_messages(event, say):
    """Handles messages in DMs only to avoid double-firing in channels."""
    # Only execute if the message is a Direct Message (im)
    if event.get('channel_type') == 'im':
        process_query(event, say)

def process_query(event, say):
    """Unified logic for processing queries via Snowflake Cortex."""
    raw_text = event.get('text', '').strip()
    
    # Clean the bot's mention from the text
    query = re.sub(r'<@\w+>', '', raw_text).strip()
    
    if not query:
        say("👋 Hi! I'm your Loans Assistant. How can I help you today?")
        return

    try:
        # Single feedback message
        say("❄️ _Querying Snowflake..._")
        
        # Call Cortex Analyst
        # Make sure SNOW_ROLE is passed correctly for RBAC
        response = CORTEX_APP.chat(query, role=SNOW_ROLE)
        
        if response.get('text'):
            final_answer = format_for_slack(response['text'])
            say(text=final_answer)
            
        if response.get('suggestions'):
            suggestion_list = "\n".join([f"• _{s}_" for s in response['suggestions'][:2]])
            say(text=f"*Suggestions:*\n{suggestion_list}")

    except Exception as e:
        print(f"Error processing query: {e}")
        say(f"⚠️ I encountered an error: `{str(e)}`.")

if __name__ == "__main__":
    CORTEX_APP = cortex_chat.CortexChat(AGENT_ENDPOINT, SNOW_PAT)
    print(f"🚀 Loans App is running for Role: {SNOW_ROLE}")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()