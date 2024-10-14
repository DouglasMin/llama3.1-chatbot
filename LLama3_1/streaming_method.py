import streamlit as st
import boto3
from botocore.exceptions import ClientError
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = boto3.client(
    "bedrock-runtime",
    region_name="us-west-2",
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

model_id = "meta.llama3-1-405b-instruct-v1:0"

#모델 request 양식 참고
def format_prompt(message):
    return f"""
<|begin_of_text|><|start_header_id|>user<|end_header_id|>
{message}
<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
"""

def generate_response(prompt):
    formatted_prompt = format_prompt(prompt)
    native_request = {
        "prompt": formatted_prompt,
        "max_gen_len": 512,
        "temperature": 0.5,
    }
    request = json.dumps(native_request)

    try:
        response = client.invoke_model_with_response_stream(
            modelId=model_id, body=request
        )
        return response
    except (ClientError, Exception) as e:
        st.error(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        return None

def stream_response(response):
    full_response = ""
    for event in response["body"]:
        chunk = json.loads(event["chunk"]["bytes"])
        if "generation" in chunk:
            full_response += chunk["generation"]
            yield full_response

st.title("Llama 3.1 기본 챗봇 구성")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What is your question?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    response = generate_response(prompt)
    if response:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            for response_chunk in stream_response(response):
                message_placeholder.markdown(response_chunk + "▌")
                full_response = response_chunk
            message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})