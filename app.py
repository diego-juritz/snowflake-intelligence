import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import cortex_chat  # Custom module for Snowflake Cortex Analyst

# Load environment variables
load_dotenv()

# Snowflake Configuration
SNOW_USER = os.getenv("SNOW_USER")
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
    if not text:
        return ""
    # Convert **bold** to *bold* for Slack's mrkdwn
    return re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)

@app.event("app_mention")
@app.message(re.compile(".*"))
def handle_queries(event, say):
    """
    Main handler for both Direct Messages and App Mentions.
    Processes natural language queries using Snowflake Cortex Analyst.
    """
    raw_text = event.get('text', '').strip()
    
    # Remove the bot's user ID from the message text if it was a mention
    query = re.sub(r'<@\w+>', '', raw_text).strip()
    
    if not query:
        say("👋 Hi! I'm your Data Assistant. Ask me anything about loans or sales.")
        return

    try:
        # 1. Provide immediate feedback to the user
        say("❄️ _Querying Snowflake..._")
        
        # 2. Call the Cortex Analyst Agent
        # The 'role' parameter ensures Snowflake applies the correct Semantic View (RBAC)
        response = CORTEX_APP.chat(query, role=SNOW_ROLE)
        
        # 3. Deliver the final answer only
        if response.get('text'):
            final_answer = format_for_slack(response['text'])
            say(text=final_answer)
            
        # Optional: Display follow-up suggestions if available
        if response.get('suggestions'):
            suggestion_list = "\n".join([f"• _{s}_" for s in response['suggestions'][:2]])
            say(text=f"*Suggestions:*\n{suggestion_list}")

    except Exception as e:
        print(f"Error processing query: {e}")
        say(f"⚠️ I encountered an error while accessing the data: `{str(e)}`.")

def initialize_agent():
    """Initialize the Cortex Chat integration with endpoint and credentials."""
    print(f"🚀 Initializing Snowflake Agent...")
    print(f"👤 User: {SNOW_USER} | 🔐 Role: {SNOW_ROLE}")
    return cortex_chat.CortexChat(AGENT_ENDPOINT, SNOW_PAT)

if __name__ == "__main__":
    # Ensure the Cortex App is ready before starting Slack
    CORTEX_APP = initialize_agent()
    
    print("⚡ Slack Bot is running in Socket Mode...")
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()