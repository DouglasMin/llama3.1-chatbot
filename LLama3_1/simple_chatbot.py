import json
import boto3
import streamlit as st
import dotenv
import os

dotenv.load_dotenv()

st.title("Chatbot powered by LLaMA 3.1 using AWS Bedrock")

# Initialize AWS Bedrock client
client = boto3.client(
    "bedrock-runtime",
    region_name="us-west-2",
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

# Initialize session state if there are no messages
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.token_count = 0

# Function to estimate the number of tokens in a message
def count_tokens(text):
    return len(text.split())

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def clear_screen():
    st.session_state.messages = []
    st.session_state.token_count = 0

# Sidebar
with st.sidebar:
    st.title('Streamlit Chat')
    st.subheader('Powered by AWS Bedrock with LLaMA 3.1')
    st.button('Clear Screen', on_click=clear_screen)
    st.write(f"Total Tokens: {st.session_state.token_count}")

# User input
if user_prompt := st.chat_input("Ask something..."):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.session_state.token_count += count_tokens(user_prompt)

    # Display user message
    with st.chat_message("user"):
        st.write(user_prompt)

    # Prepare the conversation history for the model
    conversation_history = ""
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            conversation_history += f"<|start_header_id|>user<|end_header_id|>\n{content}\n<|eot_id|>\n"
        elif role == "assistant":
            conversation_history += f"<|start_header_id|>assistant<|end_header_id|>\n{content}\n<|eot_id|>\n"

    # Format the prompt with special tokens as per your reference code
    formatted_prompt = f"<|begin_of_text|>\n{conversation_history}<|start_header_id|>assistant<|end_header_id|>\n"

    # Prepare the request payload
    native_request = {
        "prompt": formatted_prompt,
        "max_gen_len": 520,
        "temperature": 0.1
    }
    request_body = json.dumps(native_request)

    # Invoke the LLaMA 3.1 model without streaming
    response = client.invoke_model(
        modelId="meta.llama3-1-8b-instruct-v1:0",
        body=request_body,
        contentType="application/json"
    )

    # Parse the model's response
    model_response = json.loads(response["body"].read())
    response_text = model_response["generation"]

    # Display assistant's response
    with st.chat_message("assistant"):
        st.markdown(response_text)

    # Store the assistant's response
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.session_state.token_count += count_tokens(response_text)

# Update token count in the sidebar
with st.sidebar:
    st.write(f"Total Tokens: {st.session_state.token_count}")
