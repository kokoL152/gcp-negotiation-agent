import os
import json
import requests
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

# --- 1-3. Function Declaration ---
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

# --- 5. Core Agent Logic ---
def run_agent_chat(prompt: str):
    """
    logics for running Agent conversation。
    """

    try:
        # use GOOGLE_APPLICATION_CREDENTIALS
        credentials, project = google.auth.default()
        
        # pass to genai.Client
        client = genai.Client(
            vertexai=True,
            project=PROJECT_ID, 
            location=REGION,
            credentials=credentials # 传递凭证对象
        )
    except Exception as e:
        print("\n--- Fail Authorization：Please check gcloud auth application-default login ---")
        print(f"Error: {e}")
        return
    
    
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
        # Content(role="system", parts=[system_part]),
        Content(role="user", parts=[user_part])
    ]
    
    print(f"User Prompt: {prompt}")
    
    # --- 1st round：model decides to use tools ---
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=initial_content,
        config={
            'tools': [negotiation_tool],
            'system_instruction': system_instruction
            },
        
    )
    
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
    print("\n--- Agent Final Report ---")
    print(response.text)
    print("----------------------")


if __name__ == "__main__":
    
    # 1.successfully generate reports (Customer C)
    test_prompt_1 = "Generate a negotiation strategy report for Customer C, focusing on profit maximization."
    run_agent_chat(test_prompt_1)
    
    print("\n" + "="*50 + "\n")
    
    # 2. error, return default data (模型应根据返回的 error 和 default 数据生成报告)
    test_prompt_2 = "I need to prepare for ACME TECH negotiation"
    run_agent_chat(test_prompt_2)