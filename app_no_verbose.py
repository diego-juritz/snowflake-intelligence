from typing import Any
import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import snowflake.connector
from snowflake.core import Root
from dotenv import load_dotenv
from snowflake.snowpark import Session
import cortex_chat

load_dotenv()

ACCOUNT = os.getenv("ACCOUNT")
HOST = os.getenv("HOST")
USER = os.getenv("DEMO_USER")
ROLE = os.getenv("DEMO_USER_ROLE")
WAREHOUSE = os.getenv("WAREHOUSE")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT")
PAT = os.getenv("PAT")

DEBUG = True

# Initializes app
app = App(token=SLACK_BOT_TOKEN)
messages = []


@app.event("app_mention")
def handle_app_mention(event, say, client, body):
    """Handle direct mentions of the bot."""
    handle_message_event(event, say, client, body)

@app.message(re.compile(".*"))
def handle_direct_message(message, say, client, body):
    """Handle direct messages to the bot."""
    # Only respond to direct messages (not in channels unless mentioned)
    if message.get('channel_type') == 'im':
        handle_message_event(message, say, client, body)

def handle_message_event(event, say, client, body):
    """Main handler for processing user messages with Cortex Agent."""
    try:
        user_message = event.get('text', '').strip()
        if not user_message:
            return
        
        # Remove bot mention if present
        user_message = re.sub(r'<@\w+>', '', user_message).strip()
        
        if not user_message:
            say("👋 Hi! Ask me any question about your data and I'll help you analyze it using Snowflake Cortex.")
            return
        
        # Initialize Cortex chat if not available
        global CORTEX_APP
        if not CORTEX_APP:
            say("❌ Cortex Agent not initialized. Please check your configuration.")
            return
  
        say("🤔 Thinking...")            
        
        # Get response without streaming
        response = CORTEX_APP.chat(user_message)
        
        # Display only final response
        display_agent_response(response, say)
        
    except Exception as e:
        error_info = f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        print(f"❌ Error in handle_message_event: {error_info}")
        say(f"❌ Sorry, there was an error processing your message: {str(e)}")

# Removed @app.action("show_planning_details") entirely, as no planning will be shown

@app.event("message")
def handle_message_events(ack, body, say):
    try:
        ack()
        prompt = body['event']['text']
        
        # Get response without streaming
        response = CORTEX_APP.chat(prompt)
        
        # Display final response
        display_agent_response(response, say)
        
    except Exception as e:
        error_info = f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        print(f"❌ Error in message handler: {error_info}")
        say(
            text="❌ Request failed",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *Request Failed*\n```{error_info}```"
                    }
                }
            ]
        )

def smart_truncate(text, max_length=300, suffix="..."):
    """Smart truncation that preserves word and sentence boundaries."""
    if len(text) <= max_length:
        return text
        
    # First try to truncate at sentence boundary
    sentences = text.split('. ')
    if len(sentences) > 1:
        truncated = ""
        for sentence in sentences:
            test_text = truncated + sentence + ". "
            if len(test_text) + len(suffix) <= max_length:
                truncated = test_text
            else:
                break
        if truncated.strip():
            return truncated.strip() + suffix
    
    # If no good sentence boundary, truncate at word boundary
    words = text.split()
    truncated = ""
    for word in words:
        test_text = truncated + word + " "
        if len(test_text) + len(suffix) <= max_length:
            truncated = test_text
        else:
            break
    
    return truncated.strip() + suffix if truncated.strip() else text[:max_length-len(suffix)] + suffix

def format_text_for_slack(text):
    """Convert markdown formatting to Slack's mrkdwn format."""
    if not text:
        return text
    
    try:
        # Convert **bold** to *bold* for Slack
        import re
        
        # Replace **text** with *text* (bold)
        text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
        
        # Replace __text__ with *text* (alternative bold syntax)
        text = re.sub(r'__(.*?)__', r'*\1*', text)
        
        # Replace *text* with _text_ (italics) - but only single asterisks
        # This is tricky because we don't want to mess with our bold conversion
        # So we'll handle this carefully by looking for single asterisks not preceded/followed by another asterisk
        text = re.sub(r'(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)', r'_\1_', text)
        
        return text
        
    except Exception as e:
        print(f"❌ Error formatting text: {e}")
        return text

def format_dataframe_for_slack(df):
    """Format DataFrame for better display in Slack with proper alignment."""
    try:
        # Limit the display for very large datasets
        display_df = df.head(20) if len(df) > 20 else df
        
        # Create a more readable format
        if len(df) > 20:
            table_str = display_df.to_string(index=False, max_colwidth=30)
            table_str += f"\n\n... and {len(df) - 20} more rows"
        else:
            table_str = display_df.to_string(index=False, max_colwidth=30)
        
        return table_str
    
    except Exception as e:
        print(f"❌ Error formatting DataFrame: {e}")
        return "Error formatting data for display"

def display_agent_response(content, say):
    """Enhanced response display with SQL execution and improved formatting."""
    try:
        
        # Display the final agent response text
        if content.get('text'):
            formatted_text = format_text_for_slack(content['text'])
            say(
                text=formatted_text,  # Solo el texto principal como mensaje plano
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": formatted_text  # Sin header extra si no lo quieres; ajusta si prefieres
                        }
                    }
                ]
            )
        
        # Removed storage for verification and SQL, as no planning/details will be shown
        
        # Display citations if present
        if content.get('citations') and content['citations']:
            formatted_citations = format_text_for_slack(content['citations'])
            say(
                text="📚 Citations",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*📚 Citations:*\n_{formatted_citations}_"
                        }
                    }
                ]
            )
        
        # Display suggestions if present
        if content.get('suggestions'):
            # Format each suggestion individually 
            formatted_suggestions = [format_text_for_slack(suggestion) for suggestion in content['suggestions'][:3]]
            suggestions_text = "\n".join(f"• {suggestion}" for suggestion in formatted_suggestions)
            say(
                text="💡 Suggestions",
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*💡 Follow-up Suggestions:*\n{suggestions_text}"
                        }
                    }
                ]
            )
            
    except Exception as e:
        error_info = f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        print(f"❌ Error in display_agent_response: {error_info}")
        say(
            text="❌ Display error",
            blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"❌ *Error displaying response*\n```{error_info}```"
                }
            }]
        )

def get_snowflake_connection():
    """Create Snowflake connection using PAT authentication."""
    try:
        print("🔗 Attempting Snowflake connection with PAT authentication...")
        
        # Get account from host if not set
        account = ACCOUNT
        if not account:
            if HOST:
                account = HOST.split('.')[0]
                print(f"   📋 Extracted account from host: {account}")
        
        # Try PAT authentication first
        try:
            conn = snowflake.connector.connect(
                user=USER,
                password=PAT,
                account=account,
                warehouse=WAREHOUSE,
                role=ROLE
            )
            
            # Test connection
            cursor = conn.cursor()
            cursor.execute("SELECT CURRENT_VERSION()")
            result = cursor.fetchone()
            cursor.close()
            
            print(f"   ✅ PAT authentication successful! Snowflake version: {result[0]}")
            return conn
            
        except Exception as pat_error:
            print(f"   ❌ PAT authentication failed: {pat_error}")
            return None
                
    except Exception as e:
        print(f"   ❌ Failed to connect to Snowflake: {e}")
        return None

def init():
    """Initialize Snowflake connection and Cortex chat."""
    conn = get_snowflake_connection()

    cortex_app = cortex_chat.CortexChat(
        AGENT_ENDPOINT, 
        PAT
    )

    print("🚀 Initialization complete")
    return conn, cortex_app

# Start app
if __name__ == "__main__":
    CONN, CORTEX_APP = init()
    if CONN:
        Root = Root(CONN)
        SocketModeHandler(app, SLACK_APP_TOKEN).start()