import aioboto3
from base64 import b64decode, b64encode
from typing import Literal, Optional, Any, Annotated
from pydantic import BaseModel, Field, BeforeValidator, SerializerFunctionWrapHandler, SerializationInfo
from pydantic.functional_serializers import WrapSerializer


def base64_serializer(value: bytes, handler: SerializerFunctionWrapHandler, info: SerializationInfo) -> bytes | str:
    """
    Serialize bytes as base64 string for "json" dump mode, keep as bytes for "python" dump mode
    """
    if info.mode == "json":
        return b64encode(value).decode()
    else:
        return value


# Custom type for bytes that auto-encodes/decodes base64
Base64Bytes = Annotated[
    bytes,
    WrapSerializer(base64_serializer, return_type=bytes | str),
    BeforeValidator(lambda x: b64decode(x) if isinstance(x, str) else x)
]


class BedrockInferenceConfig(BaseModel):
    """
    https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InferenceConfiguration.html
    """
    maxTokens: Optional[int] = None
    temperature: Optional[float] = None
    topP: Optional[float] = None
    stopSequences: Optional[list[str]] = None


class BedrockContentBlock(BaseModel):
    """
    https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ContentBlock.html
    """

    class S3Location(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_S3Location.html
        """
        uri: str

    class BedrockDocumentBlock(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_DocumentBlock.html
        """

        class BedrockDocumentSource(BaseModel):
            """
            https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_DocumentSource.html
            """

            bytes: Optional[Base64Bytes] = None
            s3Location: Optional["BedrockContentBlock.S3Location"] = None
            text: Optional[str] = None

        name: str
        source: BedrockDocumentSource
        format: Literal["pdf", "csv", "doc", "docx", "xls", "xlsx", "html", "txt", "md"]


    class BedrockImage(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageBlock.html
        """

        class BedrockImageSource(BaseModel):
            """
            https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageSource.html
            """
            bytes: Optional[Base64Bytes] = None
            s3Location: Optional["BedrockContentBlock.S3Location"] = None

        format: Literal["png", "jpeg", "gif", "webp"]
        source: BedrockImageSource

    class BedrockToolUse(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolUseBlock.html
        """
        input: Any
        name: str
        toolUseId: str

    class BedrockToolResult(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolResultBlock.html
        """

        class BedrockToolResultContent(BaseModel):
            """
            https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolResultContentBlock.html
            """
            json_: Optional[Any] = Field(None, alias="json")
            text: Optional[str] = None
            document: Optional["BedrockContentBlock.BedrockDocumentBlock"] = None
            image: Optional["BedrockContentBlock.BedrockImage"] = None

        content: list[BedrockToolResultContent]
        toolUseId: str
        status: Literal["success", "error"]

    document: Optional[BedrockDocumentBlock] = None
    image: Optional[BedrockImage] = None
    text: Optional[str] = None
    toolUse: Optional[BedrockToolUse] = None
    toolResult: Optional[BedrockToolResult] = None


class BedrockMessage(BaseModel):
    """
    https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Message.html
    """
    role: Literal["user", "assistant"]
    content: list[BedrockContentBlock]


class BedrockToolConfig(BaseModel):
    """
    https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolConfiguration.html
    """

    class BedrockTool(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Tool.html
        """

        class BedrockToolSpec(BaseModel):
            """
            https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolSpecification.html
            """

            class BedrockToolInputSchema(BaseModel):
                """
                https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolInputSchema.html
                """
                json_: dict = Field(..., alias="json")  # JSON schema

            inputSchema: BedrockToolInputSchema
            name: str
            description: Optional[str] = None

        toolSpec: BedrockToolSpec

    tools: list[BedrockTool]


class BedrockConverseRequest(BaseModel):
    """
    https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html#API_runtime_Converse_RequestBody
    """
    modelId: str
    messages: list[BedrockMessage]
    inferenceConfig: Optional[BedrockInferenceConfig] = None
    toolConfig: Optional[BedrockToolConfig] = None

    @property
    def dump(self) -> dict:
        """
        Dump into json serialisable object, making sure that document data are bytes
        """
        payload = self.model_dump(mode="python", by_alias=True, exclude_none=True)
        return payload


class BedrockConverseResponse(BaseModel):
    """
    https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html#API_runtime_Converse_ResponseElements
    """

    class BedrockTokenUsage(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_TokenUsage.html
        """
        inputTokens: int
        outputTokens: int
        totalTokens: int

    class BedrockConverseMetrics(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseMetrics.html
        """
        latencyMs: int

    class BedrockPerformanceConfiguration(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_PerformanceConfiguration.html
        """
        latencyOptimized: Literal["standard ", "optimized"] | None = None

    class BedrockServiceTier(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ServiceTier.html
        """
        tier: Literal["priority", "default", "flex", "reserved"]

    class BedrockConverseTrace(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseTrace.html
        """

        class BedrockGuardrailTrace(BaseModel):
            """
            https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_GuardrailTraceAssessment.html
            """

            class BedrockGuardrailAssesment(BaseModel):
                """
                https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_GuardrailAssessment.html
                this is getting deep, I give up mapping this object for now
                """
                appliedGuardrailDetails : Any | None = None
                automatedReasoningPolicy : Any | None = None
                contentPolicy : Any | None = None
                contextualGroundingPolicy : Any | None = None
                invocationMetrics : Any | None = None
                sensitiveInformationPolicy : Any | None = None
                topicPolicy : Any | None = None
                wordPolicy : Any | None = None

            actionReason : str | None = None
            inputAssessment : dict[str, list[BedrockGuardrailAssesment]] | None = None
            modelOutput : list[str] | None = None
            outputAssessments : dict[str, list[BedrockGuardrailAssesment]] | None = None

        class BedrockPromptRouterTrace(BaseModel):
            """
            https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_PromptRouterTrace.html
            """
            invokedModelId: str | None = None

        guardrail: str | None = None
        promptRouter: BedrockPromptRouterTrace | None = None

    class BedrockConverseOutput(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseOutput.html
        """
        message: BedrockMessage

    additionalModelResponseFields: dict
    metrics: BedrockConverseMetrics
    output: BedrockConverseOutput
    performanceConfig: BedrockPerformanceConfiguration
    serviceTier: BedrockServiceTier
    stopReason: Literal["end_turn", "tool_use", "max_tokens", "stop_sequence", "guardrail_intervened", "content_filtered", "malformed_model_output", "malformed_tool_use", "model_context_window_exceeded"]
    trace: BedrockConverseTrace
    usage: BedrockTokenUsage


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
        self._client = await self.session.client("s3", region_name=self._region).__aenter__()

    async def close(self):
        await self._client.__aexit__(None, None, None)
        self._client = None

    async def __aenter__(self) -> "Bedrock":
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def converse_async(self, payload: BedrockConverseRequest) -> BedrockConverseResponse:
        return BedrockConverseResponse(**await self._client.converse(payload.model_dump(mode="json")))
