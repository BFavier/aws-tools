import asyncio
import uvicorn
from typing import Annotated, AsyncIterable
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from aws_tools.bedrock import Bedrock, BedrockMessage, BedrockInferenceConfig, BedrockContentBlock, BedrockConverseStreamEventResponse, BedrockSystemContentBlock
from aws_tools.bedrock.agent import Agent, AgentTool


class MyAgent(Agent):
    pass


@MyAgent.register_tool
class GetTemperature(AgentTool):
    """
    Returns the temperature in °C in the given city
    """
    city: str = Field(..., description="The city to fetch the temparature in (all lower case). Exampels: 'paris', 'new-york'")

    async def __call__(self, **secrets) -> float:
        await asyncio.sleep(1.0)
        return 20.2


@asynccontextmanager
async def lifespan(app: FastAPI):
    bedrock = Bedrock(region="eu-west-1")
    app.state.bedrock = bedrock
    await bedrock.open()
    app.state.agent = MyAgent(bedrock, "", "")
    yield
    await bedrock.close()

app = FastAPI(
    lifespan=lifespan
)

async def _get_agent(request: Request) -> MyAgent:
    return request.app.state.agent


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
async def chat_stream(body: Body, agent: Annotated[MyAgent, Depends(_get_agent)]) -> StreamingResponse:
    async def stream() -> AsyncIterable[str]:
        async for event in agent.converse_stream(body.history, body.inference_config):
            if isinstance(event, BedrockConverseStreamEventResponse.ContentBlockDeltaEvent.ContentBlockDelta) and event.text is not None:
                yield event.text
    return StreamingResponse(stream(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
