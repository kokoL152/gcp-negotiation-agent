# 💰 GCP Negotiation Agent & Data Service

This project deploys an AI-driven Sales Negotiation Preparation Agent on Google Cloud Platform (GCP). The agent utilizes the Gemini model's Function Calling capability to integrate with a custom Cloud Run service for real-time customer data retrieval from Firestore.

## 🎯 Core Features

* **Gemini Agent (agent_app.py):** Receives negotiation prompts and automatically determines when to fetch necessary customer data.
* **Function Calling:** The Gemini model calls the deployed `getCustomerData` service.
* **Cloud Run Data Service:** A containerized service (`app.py`) securely retrieves customer negotiation data, purchase history, and price targets from Firestore.
* **Terraform Infrastructure as Code (IaC):** Manages all core GCP resources (Cloud Run Service, Service Account, IAM permissions).

## 🌐 System Architecture Overview

The diagram below illustrates the flow of a user request through the system:

```mermaid
graph TD
    A[Agent App (Local/Client)] -->|1. User Prompt (e.g., "Prepare for Customer C")| B(Google Gemini API)
    B -->|2. Function Call: getCustomerData('Customer C')| C{Cloud Run Service}
    C -->|3. Get Data (Firestore Client)| D[Firestore Database ID: 'customers']
    D -->|4. Return Customer Data| C
    C -->|5. Return Tool Output (Data)| B
    B -->|6. Generate Final Strategy Report| A
    end
```
### Component Description:

* **Agent App (agent_app.py):** The local Python script running the multi-turn chat and tool logic.

* **Google Gemini API:** The core AI, deciding when and how to call the external tool.

* **Cloud Run Service (get-customer-data-func):** The containerized Flask application serving as the negotiation data tool.

* **Firestore Database:** Stores customer negotiation records. The Database ID is configured as customers.

## ⚙️ Deployment and Setup
**Prerequisites**
* Terraform Installed

* Git Installed

* gcloud CLI Installed and configured

* Authentication performed via gcloud auth application-default login.

1. Initialize and Deploy Terraform
Navigate to the project root directory and run:

        Bash
        
        # Initialize the project and download providers
        terraform init
        
        # Deploy GCP resources (Service Account, IAM roles, Cloud Run structure)
        terraform apply
2. Build and Deploy Docker Image
The service relies on a Docker image containing the app.py logic.

    Bash
    
        # IMPORTANT: Use a unique tag to force Cloud Run to deploy a new revision.
        LATEST_TAG="v20251109-final" 
        
        # 1. Build and push the image to GCR
        gcloud builds submit --tag gcr.io/[YOUR_GCP_PROJECT_ID]/get-customer-data-func:$LATEST_TAG .
        
        # 2. Update the image tag in main.tf and re-apply Terraform 
        #    If you used the :final-fix tag during the troubleshooting process, ensure the main.tf is set to this tag.
            terraform apply
**🧪 Local Agent Test**
Once the Cloud Run service is deployed with the correct image, run the local Agent to test the end-to-end functionality:

        Bash
        
        python agent_app.py
The agent should successfully call the Cloud Run service, retrieve the required customer data, and generate the final negotiation strategy report.
