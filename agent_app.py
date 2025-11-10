import os
import json
import requests
import base64
import matplotlib
import subprocess
import re
import datetime
from google import genai
from google.genai.types import Tool, FunctionDeclaration, Content, Part
from google.genai.errors import APIError
import google.auth 
import google.auth.transport.requests

# --- parameters ---
PROJECT_ID = "eighth-pen-476811-f3" 
REGION = "asia-northeast1" 
# Cloud URL
CUSTOMER_DATA_SERVICE_URL = "https://get-customer-data-func-ldthooojxq-an.a.run.app" 

# --- 1-3. Function Declaration (Report Agent 1 Tool)---
customer_data_tool_declaration = FunctionDeclaration(
    # names and description
    name="getCustomerData", 
    description="Retrieves comprehensive customer negotiation data, including purchase history, negotiation style, and pricing targets, needed to prepare a sales strategy.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "customer_name": {
                "type": "STRING",
                "description": "The full name of the customer for whom the negotiation data is needed (e.g., 'Customer A')."
            }
        },
        "required": ["customer_name"]
    },
)


negotiation_tool = Tool(function_declarations=[customer_data_tool_declaration])

# --- 4. logic based on models (get Cloud Run) ---
def call_customer_data_service(customer_name: str) -> dict:
   
    url = f"{CUSTOMER_DATA_SERVICE_URL}?customer_name={customer_name}"
    print(f"\n[Tool Execution: Calling Cloud Function at: {url}]")
    try:
        # usually we need extra headers like API Key，
        # but we authorized allUsers, so not necessary now
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json() 
        return data
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err.response.status_code}")
        return {"error": f"Tool execution failed with HTTP status {err.response.status_code}. Response: {err.response.text}"}
    except Exception as e:
        return {"error": f"Tool execution failed with unknown error: {str(e)}"}

# --- 5. Core Report Agent 1 Logic ---
def run_agent_chat(client: genai.Client, prompt: str):
    """
    logics for running Report Agent 1 conversation。
    """

    # try:
    #     # use GOOGLE_APPLICATION_CREDENTIALS
    #     credentials, project = google.auth.default()
        
    #     # pass to genai.Client
    #     client = genai.Client(
    #         vertexai=True,
    #         project=PROJECT_ID, 
    #         location=REGION,
    #         credentials=credentials # 传递凭证对象
    #     )
    # except Exception as e:
    #     print("\n--- Fail Authorization：Please check gcloud auth application-default login ---")
    #     print(f"Error: {e}")
    #     return
    
    
    system_instruction = ("You are a professional Sales Negotiation Strategy Expert. "
                          "You MUST perform all analysis and generate the FINAL report entirely IN ENGLISH. "
                          "Your primary task is to help the user prepare for negotiations. "
                          "You MUST use the 'getCustomerData' tool to retrieve customer data. "
                          "After retrieving the data, you must analyze the last deal's outcome and price targets "
                          "to generate a structured negotiation strategy focused on maximizing profit margin. "
                          "If the tool execution fails, you must inform the user and stop.")
    
   
   # Part
    system_part = Part(text=system_instruction)
    user_part = Part(text=prompt)
    
    # initial content：
    initial_content = [
        Content(role="user", parts=[user_part])
    ]
    
    print(f"User Prompt: {prompt}")
    
    # --- 1st round：model decides to use tools ---
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=initial_content,
            config={
                'tools': [negotiation_tool],
                'system_instruction': system_instruction
                },
            
        )
    except APIError as e:
        print(f"\n❌ Report Agent 1 API Error: {e}")
        return None
    
    # --- call tools ---
    while response.function_calls:
        
        tool_call = response.function_calls[0]
        function_name = tool_call.name
        
        print(f"[Model requested Tool Call: {function_name} with args: {dict(tool_call.args)}]")
            
        args = dict(tool_call.args)
        customer_name = args.get('customer_name')
        
        # call Cloud Run Services
        tool_response_data = call_customer_data_service(customer_name)
        
        # --- 2nd round：return results to model ---
        
        tool_response_part = Part.from_function_response(
            name=function_name,
            response=tool_response_data
        )

        # 2nd round contents
        contents_with_response = initial_content + [
            response.candidates[0].content,  # 1st FunctionCall
            Content(role="tool", parts=[tool_response_part])  # return results
        ]

        # call model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents_with_response,
            config={'tools': [negotiation_tool]},
        )
        
    # --- Reort ---
    print("\n--- Report Agent Final Report ---")
    print(response.text)
    print("----------------------")

    return response.text


# --- 6. HTML generation function ---
def generate_html_report(customer_name: str, report_html: str, image_base64: str):
    """Generate Visualized HTML documents"""
    
    # Get current time
    generation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # HTML template
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Negotiation Strategy Report: {customer_name}</title>
        <style>
            body {{ font-family: 'Arial', sans-serif; line-height: 1.6; padding: 20px; background-color: #f9f9f9; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
            # time template
            .timestamp {{
                position: absolute;
                top: 10px;
                right: 30px;
                font-size: 0.9em;
                color: #777;
            }}
            
            h1 {{ color: #1a73e8; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            h2 {{ color: #333; margin-top: 30px; }}

            .report-content {{ 
                background: #fdfdfd; 
                padding: 15px; 
                border: 1px solid #eee; 
                boder-radius: 5px;
                white-space: normal;
                }}
            .report-content ul {{ padding-left: 20px; }}
            .report-content mark {{ background-color: #fcf8e3; padding: 2px 4px; border-radius: 3px; }}
            .visualization {{ text-align: center; margin-top: 20px; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }}
            .visualization img {{ max-width: 100%; height: auto; border-radius: 5px; }}
            .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #777; font-size: 0.9em; }}
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
                <p>Generated by Visualization Agent based on the strategy report.</p>
            </div>

            <div class="footer">
                Report generated by Gemini Agent System.
            </div>
        </div>
    </body>
    </html>
    """
    
    file_name = f"Negotiation_Report_{customer_name}.html"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"\n🎉 Successfully Generated Report: {file_name}")
    print("Please double click the file，and select 'print' -> 'Save it as PDF' to local file")

# --- 7. Visual Agent 2 logic ---
def run_visualization_agent(client: genai.Client, customer_name: str, report_text: str):
    """
    Run Agent 2 (Visualization Agent) and generate HTML
    two missions:
    1. generates charts
    2. change text result to html with highlights
    """
    print("\n[Agent 2: Data Visualization (Model: gemini-2.5-flash)]")
    
    # --- Mission 1: Generate Charts ---
    visualization_prompt = f"""
        Take the following raw negotiation strategy report. Your task is to generate a self-contained Python script using 'matplotlib.pyplot' to create ONE clear, professional data visualization (e.g., bar chart, line chart) that summarizes the key numerical data.

        Your task is to generate a self-contained Python script using 'matplotlib.pyplot' to create ONE clear, professional **line and area chart** that visualizes the negotiation strategy.

        **Chart Requirements:**
        1.  **X-Axis:** Dates from the 'purchase_history'.
        2.  **Y-Axis:** Price ($).
        3.  **Historical Prices:** Plot the 'price_achieved' from 'purchase_history' as a **line or scatter plot** (with markers).
        4.  **Target Line:** Draw a horizontal dashed line for the 'current_target_price'.
        5.  **Cost Line:** Draw a horizontal dashed line for the 'current_cost_price'.
        6.  **Profit Zone (IMPORTANT):** Create a shaded green area (using `plt.fill_between`) between the 'cost_price' and 'target_price' lines. Label this area 'Target Profit Zone'.
        7.  **Predicted Range (Optional):** If you can infer a predicted range, plot it as a vertical shaded bar on the far right. If not, omit this. (AI 也许无法处理“虚拟”预测，但前 6 点是必须的)

        **Python Script Requirements:**
        1.  Code Only: Respond ONLY with Python code in ```python ... ```.
        2.  Library: Use ONLY 'matplotlib.pyplot'.
        3.  Save to File: The script MUST save the chart to 'chart.png'.
        4.  Clarity: Include a title, axis labels, and a legend.
        5.  No Display: Do not use `plt.show()`.

        **Input Report:**
        ---
        {report_text}
        ---
        """

    try:
        #  Gemini
        vis_response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[Content(role="user", parts=[Part(text=visualization_prompt)])],
            config={
                'temperature': 0.1 
            }
        )
        
        # 1. get code
        code_match = re.search(r"```python\n(.*?)\n```", vis_response.text, re.DOTALL)
        if not code_match:
            print("\n⚠️ Visualization Agent Failed: Did not generate valid Python code block.")
            generate_html_report(customer_name, report_text, "") # generate report without graph
            return

        python_code = code_match.group(1)
        # 调试：打印出 AI 生成的代码
        print("\n[Agent 2: Generated Code (Saving to generate_chart.py)]")
        print("--------------------------------------------------")
        print(python_code)
        print("--------------------------------------------------")

        # 
        # --- 这是关键的修复 ---
        # 1. 强制使用 'Agg' 后端 (必须在 import pyplot 之前)
        # 2. 强行移除 plt.show()
        #
        fixed_python_code = "import matplotlib\nmatplotlib.use('Agg')\n" + python_code
        fixed_python_code = fixed_python_code.replace("plt.show()", "")

        # 2. 将 *修复后* 的代码写入临时文件
        with open("generate_chart.py", "w", encoding="utf-8") as f:
            f.write(fixed_python_code)
        
            
        # 3. run script
        print("\n[Agent 2: Executing generated Python code...]")
        # make sure matplotlib available
        # matplotlib.use('Agg') 
        
        #  subprocess script
        process = subprocess.run(['python', 'generate_chart.py'], capture_output=True, text=True, timeout=15)
        
        if process.returncode != 0:
            print("\n⚠️ Visualization Agent Error during code execution:")
            print(process.stderr)
            generate_html_report(customer_name, report_text, "")
            return

        print("\n[Agent 2: Code execution successful, 'chart.png' created.]")

        # 4. read image and code into Base64
        image_base64 = "" 

        try:
            with open("chart.png", "rb") as img_file:
                image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            print("\n✅ Visualization Agent Success: Image encoded for HTML.")
        except FileNotFoundError:
            print("\n⚠️ Visualization Agent Failed: 'chart.png' was not created by the script.")
    
    except Exception as e:
            print(f"\n❌ Visualization Agent Error: {e}")
            
            image_base64 = "" # if error, use null

    # --- Mission 2 : text -> HTML ---
    print("\n[Agent 2: Mission 2 convert text begins...]")
    
    
    styling_prompt = f"""
    Take the following raw negotiation strategy report (written in Markdown). 
    Your task is to convert it into a clean, professional HTML block.

    **Requirements:**
    1.  Respond ONLY with the HTML block. Do not add "```html" or any explanatory text.
    2.  Use `<ul>` and `<li>` for bullet points (like those starting with '*').
    3.  Use `<strong>` or `<b>` for text enclosed in `**` (bold).
    4.  Use `<mark>` tags (HTML highlight) for all key numerical data (e.g., prices like $80,000, percentages) and key strategic phrases (e.g., "Walk-away Price", "Profit Margin").
    5.  Wrap the entire output in a single `<div>` with class "report-content".

    **Input Report:**
    ---
    {report_text}
    ---
    """
        
    styled_report_html = f"<div class='report-content'><pre>{report_text}</pre></div>" # 默认值，以防出错

    try:
        style_response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=[Content(role="user", parts=[Part(text=styling_prompt)])],
            config={'temperature': 0.1} 
        )
        styled_report_html = style_response.text
        print("\n✅ Visualization Agent (convert text) succeed")

    except Exception as e:
        print(f"\n❌ Visualization Agent (convert text) failed: {e}")
        
    # --- output： HTML  ---
    generate_html_report(customer_name, styled_report_html, image_base64)


if __name__ == "__main__":
    
    try:
        credentials, project = google.auth.default()
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID, 
            location=REGION,
            credentials=credentials
        )
        print("--- Gemini Client Initialized ---")
    except Exception as e:
        print("\n--- Fail Authorization：Please check gcloud auth application-default login ---")
        print(f"Error: {e}")
        exit(1) 

   # --- Test 1: Customer C ---
    customer_name_1 = "Customer C"
    test_prompt_1 = "Generate a negotiation strategy report for Customer C, focusing on profit maximization."
    
    # 1. Run Agent 1
    report_text_1 = run_agent_chat(client, test_prompt_1)
    
    # 2. If Agent 1 succeeded，run Agent 2
    if report_text_1:
        run_visualization_agent(client, customer_name_1, report_text_1)
    
    print("\n" + "="*50 + "\n")
    
    # --- Test 2: ACME TECH ---
    customer_name_2 = "ACME TECH"
    test_prompt_2 = "I need to prepare for ACME TECH negotiation"
    
    # 1. Run Agent 1
    report_text_2 = run_agent_chat(client, test_prompt_2)
    
    # 2. If Agent 1 succeeded，run Agent 2
    if report_text_2:
        run_visualization_agent(client, customer_name_2, report_text_2)