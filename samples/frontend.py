import sys
import asyncio
import aiohttp
import streamlit as st
from streamlit.web import cli as stcli
from streamlit import runtime
from aws_tools.bedrock import Bedrock, BedrockMessage, BedrockInferenceConfig, BedrockContentBlock, BedrockConverseStreamEventResponse, BedrockSystemContentBlock
from aws_tools.bedrock.agent import Agent, AgentTool

def main():

    async def set_system_prompt_async(prompt: str):
        url = "http://localhost:8080/system-prompt"
        async with aiohttp.ClientSession() as session:
            async with session.put(url, params={"prompt": prompt}) as resp:
                resp.raise_for_status()

    async def set_model_id_async(id: str):
        url = "http://localhost:8080/model-id"
        async with aiohttp.ClientSession() as session:
            async with session.put(url, params={"id": id}) as resp:
                resp.raise_for_status()

    async def converse_with_agent_async(placeholder):
        buffer = ""
        url = "http://localhost:8080/sendMessageStream"
        json_body = {"history": [m.model_dump(mode="json") for m in st.session_state.history], "inference_config": st.session_state.inference_config.model_dump(mode="json")}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json_body) as resp:
                resp.raise_for_status()
                async for line_bytes in resp.content:
                    buffer += line_bytes.decode("utf-8")
                    text = line_bytes.decode("utf-8")
                    placeholder.markdown(buffer)


    if "history" not in st.session_state:
        st.session_state.history = []
    if "inference_config" not in st.session_state:
        st.session_state.inference_config = BedrockInferenceConfig()

    with st.sidebar:
        model_id = st.text_input("Model ID", value="anthropic.claude-3-haiku-20240307-v1:0")
        if model_id is not None:
            asyncio.run(set_model_id_async(model_id))
        system_prompt = st.text_input("System prompt", value="You are an helpful agent that speaks with cool slangs, in a relaxed atmosphere.")
        if system_prompt is not None:
            asyncio.run(set_system_prompt_async(system_prompt))
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
            placeholder = st.empty()
        asyncio.run(converse_with_agent_async(placeholder))


if __name__ == "__main__":
    if runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", __file__]
        sys.exit(stcli.main())
