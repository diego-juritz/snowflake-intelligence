# Snowflake Intelligence: Bank Loan Demo ❄️🏦

This repository contains a **Proof of Concept (POC)** demonstrating the capabilities of **Snowflake Intelligence** and **Cortex Analyst**. This demo allows users to query complex banking data (loans, applications, and customer risk) using **natural language** through a **Slack** interface.

The project showcases how a well-defined **Semantic Model** and a **Star Schema** bridge the gap between technical data structures and business stakeholders while maintaining strict **Role-Based Access Control (RBAC)**.

[Image of a professional architecture diagram showing Slack integration with Snowflake Cortex Analyst, including roles, semantic models, and star schema tables]

---

## 🌟 Key Features

* **Natural Language Processing**: Interact with Snowflake data using plain English via Cortex Analyst.
* **Medallion Architecture**: Data is processed through `RAW` (Bronze), `SILVER`, and `GOLD` layers to ensure high data quality.
* **Star Schema Modeling**: The Gold layer is optimized for analytical queries with a central Fact table (`FACT_LOANS`) and specialized Dimension tables (`DIM_CUSTOMERS`, `DIM_OFFICERS`).
* **Enterprise Security (RBAC)**: Segregated access for `ROLE_RISK` and `ROLE_SALES` roles, ensuring users only see the data their role permits.
* **Slack Integration**: A Python-based bot that bridges user queries to the Snowflake Cortex Agent, displaying both text summaries and formatted data tables.

---

## 📁 Project Structure

* `SNOW_INTEL_BANK_DEMO.ipynb`: Snowflake Notebook to set up the Medallion architecture and star schema.
* `app.py`: The main Slack bot application using the Bolt framework. It handles events, calls Cortex, and executes SQL results.
* `cortex_chat.py`: Library to handle REST API calls and streaming responses from the Snowflake Cortex Agent.
* `cortex_response_parser.py`: Utility to parse complex responses and extract SQL and summary text.
* `.env`: Configuration file for credentials, roles, and agent endpoints.

---

## 🚀 Getting Started

### 1. Snowflake Preparation
**Crucial First Step**: You must execute the `SNOW_INTEL_BANK_DEMO` notebook or SQL script within your Snowflake environment before running the app.
* It creates the `LOAN_DEMO_DB` database and `GOLD` schema.
* It populates the tables with fictitious loan records.
* It configures the required roles: `ROLE_RISK` and `ROLE_SALES`.

### 2. Semantic Views Configuration
In the Snowflake UI (**AI & ML > Cortex Analyst**), create two Semantic Views:
1.  **RISK_SV**: Includes `FACT_LOANS` and `DIM_CUSTOMERS`.
2.  **SALES_SV**: Includes `FACT_LOANS` and `DIM_OFFICERS`.
* *Note*: Ensure you define the **Relationships** (Joins) between `CUST_ID` or `OFFICER_ID` to enable accurate AI reasoning.
* *Metrics*: Define metrics like `TOTAL_LOAN_AMOUNT` and `AVERAGE_DAYS_OPEN` to enable mathematical reasoning.

### 3. Slack App Setup
1.  Create an app at [api.slack.com](https://api.slack.com).
2.  Enable **Socket Mode**.
3.  Under **Event Subscriptions**, enable events and subscribe to `app_mention` and `message.im`.
4.  Add **Bot Token Scopes**: `app_mentions:read`, `chat:write`, `im:history`, `channels:history`.

---

## 🛠️ Installation & Usage

1. **Install dependencies**:
```bash
pip install slack_bolt snowflake-connector-python pandas python-dotenv
```

2. **Configure the Environment**:
Create a `.env` file in the root directory:
```env
# Snowflake Connection
ACCOUNT=<your_account_locator>
SNOW_USER=<your_user>
SNOW_ROLE=ROLE_RISK  # Use ROLE_SALES for sales testing
WAREHOUSE=<your_warehouse>
PAT=<your_programmatic_access_token>
AGENT_ENDPOINT=<your_cortex_agent_endpoint_url>

# Slack App
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

3. **Run the application**:
```bash
python app.py
```

4. **Interact in Slack**:
* **Direct Message**: Open a chat with the "Loans" bot and type your question directly.
* **Channels**: Invite the bot to a channel and use `@Loans [your question]`.

---

## 📊 Demo Scenarios: Testing RBAC

The following scenarios demonstrate how the `SNOW_ROLE` header ensures the AI only interacts with authorized data.

[Image of a data governance workflow showing a user's role determining which semantic view and subset of tables they can access]

| Role | Query | Expected Behavior |
| :--- | :--- | :--- |
| **Sales** | "Who are the top 3 officers by loan volume?" | **Success**: Returns a summary and a data table of officers. |
| **Sales** | "What is the average credit score?" | **Blocked**: Agent states it lacks access to credit data. |
| **Risk** | "Show average credit score for approved loans?" | **Success**: Joins loan and customer data to return the score. |
| **Risk** | "Which branch manages most loans?" | **Blocked**: Agent states it lacks access to branch or officer data. |

---

## 🔧 Troubleshooting

* **Double Responses**: Ensure you don't have redundant event handlers. Use separate logic for `app_mention` and `message.im` with a channel-type check.
* **Empty Data Tables**: The bot only displays a table if the agent generates a valid SQL query and returns more than one result.
* **Role Mismatch**: Verify that the `SNOW_ROLE` in `.env` matches the role used to create the Semantic View in Snowflake.
* **API Timeouts**: Streaming is enabled to handle long-running queries; ensure `cortex_chat.py` is configured with a sufficient timeout.

---

## 📝 Credits

This demo highlights the synergy between **Snowflake's Data Cloud** and **Generative AI**.
* **Engineered by**: Diego Juritz.
* **Powered by**: Snowflake Cortex Analyst and Slack Bolt SDK.
* **Special Thanks**: To the Snowflake community for semantic modeling best practices.
