from flask import Flask, request, jsonify
from google.cloud import firestore
import os
import traceback

PROJECT_ID = "eighth-pen-476811-f3"
DATABASE_ID = "customers"
app = Flask(__name__)

# db = firestore.Client(project=PROJECT_ID)
# _firestore_client = None

try:
    db = firestore.Client(project=PROJECT_ID, database=DATABASE_ID)
    print(f"Firestore client initialized for project: {PROJECT_ID}")
except Exception as e:
    # 如果初始化失败，打印致命错误并退出，这会在 Logs Explorer中显示 ERROR
    print(f"FATAL ERROR: Failed to initialize Firestore Client: {str(e)}")
    traceback.print_exc()
    # 强制退出，避免继续运行一个有问题的应用
    exit(1)

# def get_firestore_client():
#     """惰性初始化 Firestore 客户端，只在第一次调用时创建。"""
#     global _firestore_client
#     if _firestore_client is None:
#         # 尝试初始化客户端
#         _firestore_client = firestore.Client(project=PROJECT_ID)
#     return _firestore_client

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '3600'
}

@app.route("/", methods=["GET", "POST", "OPTIONS"])
def get_customer_data():
    if request.method == "OPTIONS":
        return ('', 204, CORS_HEADERS)

    customer_name = None
    if request.method == "POST":
        try:
            body = request.get_json(silent=True)
            if body and "customer_name" in body:
                customer_name = body["customer_name"]
        except Exception:
            pass

    if not customer_name:
        customer_name = request.args.get("customer_name")

    if not customer_name:
        return (jsonify({"error": "Missing required parameter: customer_name"}), 400, CORS_HEADERS)

    try:
        # db = get_firestore_client()

        doc_ref = db.collection("customers").document(customer_name)
        doc = doc_ref.get()
        if doc.exists:
            return (jsonify(doc.to_dict()), 200, CORS_HEADERS)
        else:
            return (jsonify({"error": f"Customer '{customer_name}' not found in Firestore.", "data": {}}), 404, CORS_HEADERS)
    except Exception as e:
        print("Error during Firestore query:")
        traceback.print_exc()
        return (jsonify({"error": f"Firestore query failed: {str(e)}"}), 500, CORS_HEADERS)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))