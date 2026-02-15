import sys
import asyncio
import streamlit as st
from pydantic import Field
from streamlit.web import cli as stcli
from streamlit import runtime
from aws_tools.bedrock import Bedrock, BedrockMessage, BedrockInferenceConfig, BedrockContentBlock, BedrockConverseStreamEventResponse, BedrockSystemContentBlock
from aws_tools.bedrock.agent import Agent, AgentTool

def main():

    class MyAgent(Agent):
        pass


    @MyAgent.register_tool
    class GetTemperature(AgentTool):
        """
        Returns the temperature in °C in the given city
        """
        city: str = Field(..., description="The city to fetch the temparature in (all lower case). Exampels: 'paris', 'new-york'")

        def __call__(self, **secrets) -> float:
            """
            """
            return 20.2


    event_loop = asyncio.new_event_loop()

    async def init_agent() -> MyAgent:
        bedrock = Bedrock(region="eu-west-1")
        await bedrock.open()
        return MyAgent(bedrock, "", system_prompt="")


    async def converse_with_agent():
        agent: MyAgent = st.session_state.agent
        async for event in agent.converse_stream(st.session_state.history, st.session_state.inference_config):
            if isinstance(event, BedrockConverseStreamEventResponse.ContentBlockDeltaEvent.ContentBlockDelta):
                if event.text is not None:
                    st.write(event.text)


    if "agent" not in st.session_state:
        st.session_state.agent = event_loop.run_until_complete(init_agent())
    if "history" not in st.session_state:
        st.session_state.history = []
    if "inference_config" not in st.session_state:
        st.session_state.inference_config = BedrockInferenceConfig()

    with st.sidebar:
        model_id = st.text_input("Model ID", value="anthropic.claude-3-haiku-20240307-v1:0")
        if model_id is not None:
            st.session_state.agent.model_id = model_id
        system_prompt = st.text_input("System prompt", value="You are an helpful agent that speaks with cool slangs, in a relaxed atmosphere.")
        if system_prompt is not None:
            st.session_state.agent.system_prompt = system_prompt
        max_tokens = st.number_input("Max tokens", value=1_000)
        if max_tokens is not None:
            st.session_state.inference_config.maxTokens = max_tokens
        temperature = st.number_input("Temperature", value=0.0)
        if temperature is not None:
            st.session_state.inference_config.temperature = temperature


    for m in st.session_state.history:
        message: BedrockMessage = m
        for content in message.content:
            if content.text is not None:
                with st.chat_message(name=message.role):
                    st.write(content.text)

    input = st.chat_input()
    if input is not None:
        with st.chat_message(name="user"):
            st.session_state.history.append(BedrockMessage(role="user", content=[BedrockContentBlock(text=input)]))
            st.write(input)
        with st.chat_message(name="assistant"):
            event_loop.run_until_complete(converse_with_agent())


if __name__ == "__main__":
    if runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", __file__]
        sys.exit(stcli.main())
