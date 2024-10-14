import boto3
import os
import json
from langchain.llms.base import LLM
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor, ZeroShotAgent
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from typing import Optional, List, Any
import wikipedia

# AWS Bedrock 클라이언트 생성
bedrock_client = boto3.client(
    "bedrock-runtime",
    region_name="us-west-2",
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

# BedrockLLM 클래스 정의
class BedrockLLM(LLM):
    client: Any
    model_id: str
    temperature: float = 0.5
    max_gen_len: int = 512

    @property
    def _llm_type(self) -> str:
        return "aws_bedrock_stream"

    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        formatted_prompt = self.format_prompt(prompt)
        native_request = {
            "prompt": formatted_prompt,
            "max_gen_len": self.max_gen_len,
            "temperature": self.temperature,
        }
        request = json.dumps(native_request)

        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id, body=request
            )
            generated_text = self.process_response_stream(response)
            return generated_text
        except Exception as e:
            print(f"Error invoking model: {e}")
            return ""

    def format_prompt(self, prompt: str) -> str:
        # 필요한 경우 프롬프트를 포맷팅합니다.
        return prompt

    def process_response_stream(self, response) -> str:
        # 스트림 응답을 처리하여 생성된 텍스트를 추출합니다.
        chunks = []
        for event in response['body']:
            event_payload = event['chunk']['bytes']
            chunk = json.loads(event_payload)
            chunks.append(chunk.get('generation', ''))
        return ''.join(chunks)

# 모델 ID 설정 (동작하는 모델 ID로 변경)
model_id = "meta.llama3-1-70b-instruct-v1:0"

# BedrockLLM 인스턴스 생성
llm = BedrockLLM(client=bedrock_client, model_id=model_id)

# # 툴 정의
# class CalculatorTool(BaseTool):
#     name: str = "Calculator"
#     description: str = "수학 계산을 수행합니다."

#     def _run(self, query: str) -> str:
#         try:
#             result = eval(query)
#             return str(result)
#         except Exception as e:
#             return f"계산 오류: {e}"

#     async def _arun(self, query: str) -> str:
#         raise NotImplementedError("비동기 실행은 지원되지 않습니다.")

class WikipediaTool(BaseTool):
    name: str = "Wikipedia"
    description: str = "위키백과에서 정보를 검색합니다."

    def _run(self, query: str) -> str:
        try:
            summary = wikipedia.summary(query, sentences=2)
            return summary
        except Exception as e:
            return f"검색 오류: {e}"

    async def _arun(self, query: str) -> str:
        raise NotImplementedError("비동기 실행은 지원되지 않습니다.")

# 툴 리스트 생성
tools = [WikipediaTool()]

# 프롬프트 템플릿 설정
prompt_template = ZeroShotAgent.create_prompt(
    tools=tools,
    prefix="당신은 다음 도구에 접근할 수 있는 지능형 에이전트입니다:",
    suffix="질문: {input}\n{agent_scratchpad}",
    input_variables=["input", "agent_scratchpad"]
)

# LLMChain 생성
llm_chain = LLMChain(llm=llm, prompt=prompt_template)

# 에이전트 생성
agent = ZeroShotAgent(llm_chain=llm_chain, tools=tools)
agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, verbose=True)

# 에이전트 실행
user_input = "서울 연희동의 맛집을 알려줘"
response = agent_executor.run(user_input)

print("에이전트의 응답:")
print(response)
