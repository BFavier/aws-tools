import asyncio
import unittest
from aws_tools.bedrock import Bedrock, BedrockConverseRequest, BedrockConverseResponse, BedrockMessage, BedrockContentBlock, BedrockInferenceConfig


class TestSNS(unittest.TestCase):

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


if __name__ == "__main__":
    unittest.main()
