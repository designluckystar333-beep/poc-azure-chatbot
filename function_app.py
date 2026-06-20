import azure.functions as func
import json
import os

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    try:
        from azure.keyvault.secrets import SecretClient
        from azure.identity import DefaultAzureCredential
        from openai import AzureOpenAI

        req_body = req.get_json()
        user_message = req_body.get("message", "")

        if not user_message:
            return func.HttpResponse(
                json.dumps({"error": "message is required"}),
                status_code=400,
                mimetype="application/json"
            )

        kv_name = os.environ.get("KeyVaultName")
        if not kv_name:
            return func.HttpResponse(
                json.dumps({"error": "KeyVaultName is not set"}),
                status_code=500,
                mimetype="application/json"
            )

        kv_url = f"https://{kv_name}.vault.azure.net/"
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=kv_url, credential=credential)

        openai_key = secret_client.get_secret("openai-key").value
        openai_endpoint = secret_client.get_secret("openai-endpoint").value

        client = AzureOpenAI(
            api_key=openai_key,
            api_version="2024-02-15-preview",
            azure_endpoint=openai_endpoint
        )

        response = client.chat.completions.create(
            model="gpt-35-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant for company documents. Answer in Japanese."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            temperature=0.7,
            max_tokens=500
        )

        answer = response.choices[0].message.content

        return func.HttpResponse(
            json.dumps(
                {"answer": answer, "status": "success"},
                ensure_ascii=False
            ),
            status_code=200,
            mimetype="application/json; charset=utf-8"
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}, ensure_ascii=False),
            status_code=500,
            mimetype="application/json"
        )