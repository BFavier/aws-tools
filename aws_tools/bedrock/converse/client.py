import asyncio
import aioboto3
from typing import AsyncIterable
from aws_tools.bedrock.converse.entities import BedrockConverseRequest, BedrockConverseResponse, BedrockConverseStreamEventResponse, BedrockMessage, BedrockContentBlock


class Bedrock:
    """
    Bedrock client that handles async converse API
    """

    def __init__(self, region: str | None = None):
        self.session = aioboto3.Session()
        if region is None:
            self._region = self.session._session.get_config_variable("region")
        else:
            self._region = region
        self._client = None

    async def open(self):
        self._client = await self.session.client("bedrock-runtime", region_name=self._region).__aenter__()

    async def close(self):
        await self._client.__aexit__(None, None, None)
        self._client = None

    async def __aenter__(self) -> "Bedrock":
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def converse_async(self, payload: BedrockConverseRequest) -> BedrockConverseResponse:
        return BedrockConverseResponse(**await self._client.converse(**payload.model_dump(mode="json", exclude_none=True)))

    async def converse_stream(self, payload: BedrockConverseRequest) -> AsyncIterable[str | BedrockConverseResponse]:
        """
        Stream the LLM text answer to a request, then finally yield the complete response object
        """
        response = await self._client.converse_stream(**payload.model_dump(mode="json", exclude_none=True))
        message_start = BedrockConverseStreamEventResponse.MessageStartEvent(role="assistant")
        block_content_by_index: dict[int, BedrockContentBlock] = {}
        async for event in response["stream"]:
            content = BedrockConverseStreamEventResponse(**event).content()
            if isinstance(content, BedrockConverseStreamEventResponse.MessageStartEvent):
                message_start = content
            if isinstance(content, BedrockConverseStreamEventResponse.ContentBlockStartEvent):
                block_content_by_index[content.contentBlockIndex] = content.start
            elif isinstance(content, BedrockConverseStreamEventResponse.ContentBlockDeltaEvent):
                if content.delta.text is not None:
                    yield content.delta
                block_content_by_index[content.contentBlockIndex] += content.delta
            elif isinstance(content, BedrockConverseStreamEventResponse.Metadata):
                yield BedrockConverseResponse(
                    usage=content.usage,
                    metrics=content.metrics,
                    output=BedrockConverseResponse.BedrockConverseOutput(
                        message=BedrockMessage(
                            role=message_start.role,
                            content=[
                                BedrockContentBlock()
                                for i, block in sorted(block_content_by_index)
                            ]
                        )
                    )
                )
                return
            else:
                asyncio.sleep(0.0)
        raise RuntimeError("No metadata block encountered")

