import aiohttp
import asyncio
import uvicorn
from typing import Annotated, AsyncIterable
from contextlib import asynccontextmanager
from collections import defaultdict
from html_to_markdown import convert, ConversionOptions
from fastapi import FastAPI, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from aws_tools.bedrock import Bedrock, BedrockMessage, BedrockInferenceConfig, BedrockContentBlock, BedrockConverseStreamEventResponse, BedrockSystemContentBlock
from aws_tools.bedrock.agent import Agent, AgentTool


class MyAgent(Agent):
    pass


@MyAgent.register_tool
class GetWebPageContent(AgentTool):
    """
    Returns the content of a webpage as markdown text
    """
    url: str = Field(..., description="The url of the page to fetch")
    async def __call__(self, http: aiohttp.ClientSession) -> str:
        async with http.get(self.url) as response:
            response.raise_for_status()
            res = convert(html=await response.text(), options=ConversionOptions(skip_images=True, extract_metadata=False))
            return res


@asynccontextmanager
async def lifespan(app: FastAPI):
    bedrock = Bedrock(region="eu-west-1")
    app.state.bedrock = bedrock
    await bedrock.open()
    app.state.http = aiohttp.ClientSession()
    await app.state.http.__aenter__()
    app.state.agent = MyAgent(bedrock, "", "")
    yield
    await bedrock.close()
    await app.state.http.__aexit__()

app = FastAPI(
    lifespan=lifespan
)

async def _get_agent(request: Request) -> MyAgent:
    return request.app.state.agent


async def _get_http_session(request: Request) -> aiohttp.ClientSession:
    return request.app.state.http


class Body(BaseModel):
    history: list[BedrockMessage]
    inference_config: BedrockInferenceConfig


@app.put("/system-prompt")
def set_system_prompt(prompt: str, agent: Annotated[MyAgent, Depends(_get_agent)]):
    agent.system_prompt = prompt


@app.put("/model-id")
def set_model_id(id: str, agent: Annotated[MyAgent, Depends(_get_agent)]):
    agent.model_id = id


@app.post("/sendMessageStream")
async def chat_stream(body: Body, agent: Annotated[MyAgent, Depends(_get_agent)], http: Annotated[aiohttp.ClientSession, Depends(_get_http_session)]) -> StreamingResponse:
    async def stream() -> AsyncIterable[str]:
        async for event in agent.converse_stream(body.history, body.inference_config, tool_secrets=defaultdict(lambda: {"http": http})):
            if isinstance(event, BedrockConverseStreamEventResponse.ContentBlockDeltaEvent.ContentBlockDelta) and event.text is not None:
                yield event.text
    return StreamingResponse(stream(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
