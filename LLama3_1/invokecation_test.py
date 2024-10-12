import boto3
from botocore.exceptions import ClientError
import json
import os
from dotenv import load_dotenv

load_dotenv()
client = boto3.client(
    "bedrock-runtime", 
    region_name="us-west-2", 
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID'), 
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
)


#LLama 3.1 8b 모델

model_id = "meta.llama3-1-8b-instruct-v1:0"

prompt = "안녕 친구. 너의 이름은 뭐냐?"

formatted_prompt = f"""
<|begin_of_text|>
<|start_header_id|>user<|end_header_id|>
{prompt}
<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
"""

native_request = {
    "prompt": formatted_prompt,
    "max_gen_len": 120,
    "temperature": 0.5
}
request = json.dumps(native_request)

response = client.invoke_model(
    modelId=model_id,
    body=request,
    contentType="application/json"
)

model_response = json.loads(response["body"].read())
response_text = model_response["generation"]
print(response_text)