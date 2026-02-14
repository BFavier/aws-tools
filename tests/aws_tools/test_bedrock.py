import asyncio
import unittest
from aws_tools.bedrock import Bedrock, BedrockConverseRequest, BedrockConverseResponse, BedrockMessage, BedrockContentBlock, BedrockInferenceConfig


class TestBedrock(unittest.TestCase):

    def test_converse(self):
        async def test_converse_async():
            async with Bedrock(region="eu-west-1") as bedrock:
                response = await bedrock.converse_async(BedrockConverseRequest(
                    modelId="anthropic.claude-3-haiku-20240307-v1:0",
                    messages=[BedrockMessage(role="user", content=[BedrockContentBlock(text="Hello, how is it going ?")])],
                    inferenceConfig=BedrockInferenceConfig(maxTokens=100)
                ))
                assert isinstance(response, BedrockConverseResponse)
        asyncio.run(test_converse_async())

    def test_converse_stream(self):
        async def test_converse_stream():
            async with Bedrock(region="eu-west-1") as bedrock:
                async for event in bedrock.converse_stream(BedrockConverseRequest(
                            modelId="anthropic.claude-3-haiku-20240307-v1:0",
                            messages=[BedrockMessage(role="user", content=[BedrockContentBlock(text="Hello, how is it going ?")])],
                            inferenceConfig=BedrockInferenceConfig(maxTokens=100)
                        )):
                    pass
                assert isinstance(event, BedrockConverseResponse)
        asyncio.run(test_converse_stream())

if __name__ == "__main__":
    unittest.main()
