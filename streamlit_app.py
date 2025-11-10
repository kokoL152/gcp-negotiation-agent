import streamlit as st
import os
import json
import requests
import base64
import re
import subprocess
import datetime
import matplotlib 

# GCP & GenAI
from google.cloud import firestore
from google import genai
from google.genai.types import Tool, FunctionDeclaration, Content, Part
from google.genai.errors import APIError
import google.auth 
import google.auth.transport.requests

# --- 1. Config ---
PROJECT_ID = "eighth-pen-476811-f3" 
DATABASE_ID = "customers"
REGION = "asia-northeast1" 
CUSTOMER_DATA_SERVICE_URL = "https://get-customer-data-func-ldthooojxq-an.a.run.app" 

# --- 2. Initialize ---
# Prevent reconnection everytime
@st.cache_resource
def init_clients():
   
    try:
        # 1. Firestore 
        db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)
        
        # 2. GenAI 
        credentials, project_or_none = google.auth.default()
        genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID, 
            location=REGION,
            credentials=credentials
        )
        st.success("✅ Successfully connect to Firestore & Vertex AI Gemini")
        return db, genai_client
    except Exception as e:
        st.error(f"❌ Failed initialized: {e}")
        st.stop()

# --- 3. get customer list  ---
# cache data for 10mins
@st.cache_data(ttl=600)
def get_customer_list(_db_client):
    """
    
    Get customer ID from Firestore
    """
    try:
        customers_ref = _db_client.collection("customers")
        customer_docs = customers_ref.stream()
        customer_names = [doc.id for doc in customer_docs]
        if not customer_names:
            st.warning("Firestore 'customers' not found")
            return []
        return customer_names
    except Exception as e:
        st.error(f"❌ Failed to get cumstomer data from Firestore: {e}")
        return []

# --- 4. Agent logic ---

def call_customer_data_service(customer_name: str, st_status_container) -> dict:
    url = f"{CUSTOMER_DATA_SERVICE_URL}?customer_name={customer_name}"
    st_status_container.write(f"Using tools: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        st_status_container.write("✅ tools succeed")
        return response.json() 
    except requests.exceptions.HTTPError as err:
        st_status_container.write(f"❌ HTTP error: {err.response.status_code}")
        return {"error": f"Tool execution failed with HTTP status {err.response.status_code}. Response: {err.response.text}"}
    except Exception as e:
        st_status_container.write(f"❌ tools unknown error: {str(e)}")
        return {"error": f"Tool execution failed with unknown error: {str(e)}"}

def run_agent_chat(client: genai.Client, prompt: str, st_status_container):
    """
    using Agent 1 logic
    """
    customer_data_tool_declaration = FunctionDeclaration(
        name="getCustomerData", 
        description="Retrieves comprehensive customer negotiation data, including purchase history, negotiation style, and pricing targets, needed to prepare a sales strategy.",
        parameters={
            "type": "OBJECT",
            "properties": {"customer_name": {"type": "STRING", "description": "The full name of the customer"}},
            "required": ["customer_name"]
        },
    )
    negotiation_tool = Tool(function_declarations=[customer_data_tool_declaration])

    system_instruction = ("You are a professional Sales Negotiation Strategy Expert. "
                          "You MUST perform all analysis and generate the FINAL report entirely IN ENGLISH. "
                          "You MUST use the 'getCustomerData' tool to retrieve customer data. "
                          "After retrieving the data, you must analyze the last deal's outcome and price targets "
                          "to generate a structured negotiation strategy focused on maximizing profit margin. "
                          "If the tool execution fails, you must inform the user and stop.")
    
    initial_content = [Content(role="user", parts=[Part(text=prompt)])]
    
    st_status_container.write("Agent 1 thinking now...")
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=initial_content,
            config={'tools': [negotiation_tool], 'system_instruction': system_instruction},
        )
    except APIError as e:
        st.error(f"❌ Agent 1 API error: {e}")
        return None
    
    while response.function_calls:
        tool_call = response.function_calls[0]
        st_status_container.write(f"Agent 1 using tool: {tool_call.name}")
            
        args = dict(tool_call.args)
        customer_name = args.get('customer_name')
        
        tool_response_data = call_customer_data_service(customer_name, st_status_container)
        
        tool_response_part = Part.from_function_response(
            name=tool_call.name,
            response=tool_response_data
        )

        contents_with_response = initial_content + [
            response.candidates[0].content,
            Content(role="tool", parts=[tool_response_part])
        ]

        st_status_container.write("Agent 1 analysing tool ...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents_with_response,
            config={'tools': [negotiation_tool]},
        )
        
    st_status_container.write("✅ Agent 1 generated result")
    return response.text

def generate_html_report(customer_name: str, report_html: str, image_base64: str) -> str:
    """
    generated HTML report
    """
    generation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Negotiation Strategy Report: {customer_name}</title>
        <style>
            body {{ font-family: 'Arial', sans-serif; line-height: 1.6; padding: 20px; background-color: #f9f9f9; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 0 20px rgba(0,0,0,0.1); position: relative; }}
            .timestamp {{ position: absolute; top: 10px; right: 30px; font-size: 0.9em; color: #777; }}
            h1 {{ color: #1a73e8; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            h2 {{ color: #333; margin-top: 30px; }}
            .report-content {{ background: #fdfdfd; padding: 15px; border: 1px solid #eee; border-radius: 5px; white-space: normal; }}
            .report-content ul {{ padding-left: 20px; }}
            .report-content mark {{ background-color: #fcf8e3; padding: 2px 4px; border-radius: 3px; }}
            .visualization {{ text-align: center; margin-top: 20px; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }}
            .visualization img {{ max-width: 100%; height: auto; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="timestamp">Generated: {generation_time}</div>
            <h1>📊 Negotiation Strategy Report: {customer_name}</h1>
            <h2>✅ AI Text Analysis (Agent 1 & 2)</h2>
            {report_html} 
            <h2>🖼️ Data Visualization (Agent 2)</h2>
            <div class="visualization">
                <img src="data:image/png;base64,{image_base64}" alt="Data Visualization Chart (Generation failed or not supported)">
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

def run_visualization_agent(client: genai.Client, customer_name: str, report_text: str, st_status_container) -> str:
    """
    run Agent 2 
    """
    image_base64 = ""
    
    # --- Mission 1: Generating charts ---
    st_status_container.write("Agent 2 generating chart(mission 1)...")
   
    visualization_prompt = f"""
    Take the following raw negotiation strategy report. The report contains data on 'purchase_history' (with dates and prices), a 'current_target_price', and a 'current_cost_price' (or 'Baseline_Price_USD').
    Your task is to generate a self-contained Python script using 'matplotlib.pyplot' to create ONE clear, professional line and area chart.

    Chart Requirements:
    1.  X-Axis: Dates from 'purchase_history' (must parse strings to datetime).
    2.  Y-Axis: Price ($).
    3.  Historical Prices: Plot 'price_achieved' from 'purchased_price' as a line with markers.
    4.  Target Line: Draw a horizontal dashed line for 'current_target_price' (or 'Target_Price_USD').
    5.  Cost Line: Draw a horizontal dashed line for 'current_cost_price' (or 'Baseline_Price_USD').
    6.  Profit Zone: Create a shaded green area (using plt.fill_between) between the cost and target lines.

    Python Script Requirements:
    1.  Code Only: Respond ONLY with Python code in ```python ... ```.
    2.  Library: Use 'matplotlib.pyplot' and 'datetime'.
    3.  Save to File: Save the chart to 'chart.png'.
    4.  No Display: Do not use plt.show().

    Input Report:
    ---
    {report_text}
    ---
    """
    
    try:
        vis_response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[Content(role="user", parts=[Part(text=visualization_prompt)])],
            config={'temperature': 0.1}
        )
        
        code_match = re.search(r"```python\n(.*?)\n```", vis_response.text, re.DOTALL)
        if not code_match:
            st_status_container.write("⚠️ Agent 2 warning: could not generate cahrt code")
        else:
            python_code = code_match.group(1)
            fixed_python_code = "import matplotlib\nmatplotlib.use('Agg')\n" + python_code
            fixed_python_code = fixed_python_code.replace("plt.show()", "")

            with open("generate_chart.py", "w", encoding="utf-8") as f:
                f.write(fixed_python_code)
            
            # --- code running details ---
            try:
                st_status_container.write("Agent 2 executing code for charts...")
                # 我们添加 check=True，这样脚本失败时会抛出异常
                process = subprocess.run(
                    ['python', 'generate_chart.py'], 
                    capture_output=True, 
                    text=True, 
                    timeout=15,
                    check=True # 如果 returncode != 0，则引发 CalledProcessError
                )
                
                # --- if successful ---
                try:
                    with open("chart.png", "rb") as img_file:
                        image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                    st_status_container.write("✅ Agent 2 successfully generated charts")
                    os.remove("chart.png") # 成功后清理
                    os.remove("generate_chart.py") # 成功后清理
                except FileNotFoundError:
                    st_status_container.write("⚠️ Agent 2 warning: 'chart.png' not created")

            # --- not successful ---
            except subprocess.TimeoutExpired as e:
                st_status_container.write(f"❌ Agent 2 Error: Overtime (15s)!")
                st_status_container.write("Diagnose: code may contain 'plt.show()' ")
                st_status_container.write("DEBUG: 'generate_chart.py' was saved，please check in VS Code ")

            except subprocess.CalledProcessError as e:
                # 这是最有用的！捕获所有Python脚本错误 (e.g., KeyError, TypeError)
                st_status_container.write("❌ Agent 2 Error: Failed in executing code")
                st_status_container.write("--- Wrong messages (STDERR) ---")
                # 使用 st.code() 来格式化显示错误
                st.code(e.stderr, language="bash")
                st_status_container.write("DEBUG: 'generate_chart.py' was saved，please check in VS Code")
            # --- end checking ---
            # st_status_container.write("Agent 2 generating code for chart...")
            # process = subprocess.run(['python', 'generate_chart.py'], capture_output=True, text=True, timeout=15)
            
            # if process.returncode != 0:
            #     st_status_container.write("⚠️ Agent 2 warning: failed generating code for chart")
            #     print(f"--- Agent 2 STDERR ---\n{process.stderr}")
            # else:
            #     try:
            #         with open("chart.png", "rb") as img_file:
            #             image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            #         st_status_container.write("✅ Agent 2 succeeded generation")
            #         os.remove("chart.png") # 清理
            #         os.remove("generate_chart.py") # 清理
            #     except FileNotFoundError:
            #         st_status_container.write("⚠️ Agent 2 warning: 'chart.png' not created")

    except Exception as e:
        st_status_container.write(f"❌ Agent 2 failed generated charts: {e}")

    # --- Mission 2: formating ---
    st_status_container.write("Agent 2 forming text...")
    styling_prompt = f"""
    Take the following raw negotiation strategy report (written in Markdown). 
    Your task is to convert it into a clean, professional HTML block.
    Requirements:
    1.  Respond ONLY with the HTML block. Do not add "```html" or any explanatory text.
    2.  Use `<ul>` and `<li>` for bullet points.
    3.  Use `<strong>` or `<b>` for bold text.
    4.  Use `<mark>` tags for all key numerical data and key strategic phrases (e.g., "Walk-away Price").
    5.  Wrap the entire output in a single `<div>` with class "report-content".
    Input Report:
    ---
    {report_text}
    ---
    """
    
    styled_report_html = f"<div class='report-content'><pre>{report_text}</pre></div>" # 默认值

    try:
        style_response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[Content(role="user", parts=[Part(text=styling_prompt)])],
            config={'temperature': 0.1} 
        )
        styled_report_html = style_response.text
        st_status_container.write("✅ Agent 2 succeeded generation")
    except Exception as e:
        st_status_container.write(f"❌ Agent 2 failed generation: {e}")
        
    # --- output： return HTML ---
    return generate_html_report(customer_name, styled_report_html, image_base64)

# --- 5. Streamlit interface ---
st.set_page_config(layout="wide")
st.title("Sales Negotiation Strategy Agent 📈")
st.markdown("This tool connects to Google Firestore database，using Gemini Agent analysing customer data，and generate a negotiation strategy report with charts")


try:
    db_client, genai_client = init_clients()
except Exception:
    st.error("Can not initialize, please check your GCP authentication (gcloud auth application-default login) ")
    st.stop()

# --- 侧边栏：输入控件 ---
with st.sidebar:
    st.header("📊 Negotiation Report Generator")
    
    
    customer_list = get_customer_list(db_client)
    if not customer_list:
        st.error("Can not load customer list, please check Firestore connection and content")
    else:
        selected_customer = st.selectbox(
            "1. choose target customer",
            options=customer_list,
            index=0,
            help="This list collects from your Firestore 'customers' collection"
        )
        
        # Negotiation purpose Textbox
        purpose = st.text_input(
            "2. input purpose",
            value="Focus on maximizing profit margin",
            help="Example：'Focus on upselling high-tier products', 'Prioritize closing the deal quickly'"
        )

        # Run button
        generate_button = st.button("🚀 Generate negotiation report", type="primary", use_container_width=True)

# --- Show results ---
if generate_button and 'selected_customer' in locals():
    # 1. final Prompt
    final_prompt = f"""
    Generate a negotiation strategy report for {selected_customer}.
    The negotiation purpose is: {purpose}.
    """
    
    # 2. 运行 Agent 流程
    # st.status 提供了一个很好的 "正在运行" 状态框
    with st.status("Generating report, please wait...", expanded=True) as status:
        try:
            # 运行 Agent 1
            status.write("Activate Agent 1 (Text Analysis)...")
            report_text = run_agent_chat(genai_client, final_prompt, status)
            
            if report_text:
                # 运行 Agent 2
                status.write("Activate Agent 2 (Visualization)...")
                html_report = run_visualization_agent(genai_client, selected_customer, report_text, status)
                
                # 3. save results
            
                st.session_state.html_report = html_report
                st.session_state.report_customer = selected_customer
                
                status.update(label="Finished generating report", state="complete")
                st.balloons()
            else:
                status.update(label="Agent 1 failed to return report", state="error")

        except Exception as e:
            status.update(label=f"Failed generating report: {e}", state="error")

# 4. 在按钮点击之外显示报告 (这样它会保持在页面上)
if 'html_report' in st.session_state:
    st.header(f"Strategy Report: {st.session_state.report_customer}")
    
    # 提供下载按钮
    st.download_button(
        label="📥 Download HTML Report",
        data=st.session_state.html_report,
        file_name=f"Negotiation_Report_{st.session_state.report_customer}.html",
        mime="text/html"
    )
    
    # 渲染 HTML 报告
    st.components.v1.html(st.session_state.html_report, height=1000, scrolling=True)