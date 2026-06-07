import boto3
import json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 300,
    "messages": [
        {
            "role": "user",
            "content": "You are Aegis Review. Reply only with: Aegis Review is ready."
        }
    ]
}

response = client.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    body=json.dumps(body)
)

response_body = json.loads(response["body"].read())
print(response_body["content"][0]["text"])