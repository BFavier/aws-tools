import aioboto3
from base64 import b64decode, b64encode
from collections import defaultdict
from typing import Literal, Optional, Any, Annotated, Type, TypeVar, Self, AsyncIterable
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


A = TypeVar("A")


def _add_nullables(x: A | None, y: A | None, zero: A=A()) -> A | None:
    """
    Sum two nullable objects
    """
    return None if (x is None and y is None) else (x or zero) + (y or zero)


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

            def __add__(self, other: Self) -> Self:
                return type(self)(bytes=_add_nullables(self.bytes, other.bytes), s3Location=_add_nullables(self.s3Location, other.s3Location))

        format: Literal["png", "jpeg", "gif", "webp"]
        source: BedrockImageSource

    class BedrockToolUse(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolUseBlock.html
        """
        input: dict
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

    class CitationsContentBlock(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_CitationsContentBlock.html
        """
        citations: list[Any] | None = None
        content: Any | None = None

    document: BedrockDocumentBlock | None = None
    image: BedrockImage | None = None
    text: str | None = None
    toolUse: BedrockToolUse | None = None
    toolResult: BedrockToolResult | None = None
    citationsContent: CitationsContentBlock | None = None

    def __iadd__(self, other: "BedrockConverseStreamEventResponse.ContentBlockDeltaEvent") -> Self:
        self.citation =_add_nullables(self.citation, other.citation),
        self.image = _add_nullables(self.image, other.image),
        self.reasoning =_add_nullables(self.reasoning, other.reasoning),
        self.text =_add_nullables(self.text, other.text),
        self.toolResult =_add_nullables(self.toolResult, other.toolResult),
        self.toolUse =_add_nullables(self.toolUse, other.toolUse, zero=BedrockConverseStreamEventResponse.ContentBlockDeltaEvent.ContentBlockDelta.ToolUseBlockDelta(""))
        return self


class BedrockSystemContentBlock(BaseModel):
    """
    https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_SystemContentBlock.html
    """

    class BedrockCachePointBlock(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_CachePointBlock.html
        """
        type: Literal["default"]
        ttl: Literal["5m", "1h"] | None = None
    
    class BedrockGuardrailConverseContentBlock(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_GuardrailConverseContentBlock.html
        TODO: I did not dig deeper yet in the structure
        """
        image: Any
        text: Any

    cachePoint: BedrockCachePointBlock | None = None
    guardContent: BedrockGuardrailConverseContentBlock | None = None
    system: str | None = None


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
    system: BedrockSystemContentBlock
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

        def __iadd__(self, other: Self) -> Self:
            self.inputTokens += other.inputTokens
            self.outputTokens += other.outputTokens
            self.totalTokens += other.totalTokens
            return self
        
        def __add__(self, other: Self) -> Self:
            copied = self.model_copy()
            copied += other
            return copied

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

    metrics: BedrockConverseMetrics
    output: BedrockConverseOutput
    stopReason: Literal["end_turn", "tool_use", "max_tokens", "stop_sequence", "guardrail_intervened", "content_filtered", "malformed_model_output", "malformed_tool_use", "model_context_window_exceeded"]
    usage: BedrockTokenUsage
    additionalModelResponseFields: dict | None = None
    performanceConfig: BedrockPerformanceConfiguration | None = None
    serviceTier: BedrockServiceTier | None = None
    trace: BedrockConverseTrace | None = None


class BedrockConverseStreamEventResponse(BaseModel):
    """
    https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseStream.html#API_runtime_ConverseStream_ResponseElements
    """

    class ContentBlockStartEvent(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ContentBlockStartEvent.html
        """

        class ContentBlockStart(BaseModel):
            """
            https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ContentBlockStart.html
            """

            class ImageBlockStart(BaseModel):
                """
                https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageBlockStart.html
                """
                format: Literal["png", "jpeg", "gif", "webp"]

            class ToolResultBlockStart(BaseModel):
                """
                https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolResultBlockStart.html
                """
                toolUseId: str
                status: Literal["error", "success"]
                type: str | None = None
            
            class ToolUseBlockStart(BaseModel):
                """
                https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolUseBlockStart.html
                """
                name: str
                toolUseId: str
                type: Literal["server_tool_use"]

            image: ImageBlockStart | None = None
            toolUse: ToolUseBlockStart | None = None
            toolResult: ToolResultBlockStart | None = None

            def as_block(self) -> BedrockContentBlock:
                """
                Returns a BedrockContentBlock
                """
                return BedrockContentBlock(
                    document=None,
                    image=None if self.image is None else BedrockContentBlock.BedrockImage(format=self.image.format, source=BedrockContentBlock.BedrockImage.BedrockImageSource()),
                    text=None,
                    toolUse=None if self.toolUse is None else BedrockContentBlock.BedrockToolUse(toolUseId=self.toolUse.toolUseId, name=self.toolUse.name, input=dict()),
                    toolResult=None if self.toolResult else BedrockContentBlock.BedrockToolResult(toolUseId=self.toolResult.toolUseId, status=self.toolResult.status, content=list())
                )
    
        start: ContentBlockStart
        contentBlockIndex: int

    class ContentBlockDeltaEvent(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ContentBlockDeltaEvent.html
        """

        class ContentBlockDelta(BaseModel):
            """
            https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ContentBlockDelta.html
            """

            class ToolUseBlockDelta(BaseModel):
                """
                https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolUseBlockDelta.html
                """
                input: str

                def __add__(self, other: Self) -> Self:
                    return type(self)(input=self.input+other.input)

            class ToolResultBlockDelta(BaseModel):
                """
                https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolResultBlockDelta.html
                """
                json: str | None = None
                text: str | None = None

                def __add__(self, other: Self) -> Self:
                    return type(self)(
                        json=_add_nullables(self.json, other.json, ""),
                        text=_add_nullables(self.text, other.text, "")
                    )
            
            class ReasoningContentBlockDelta(BaseModel):
                """
                https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ReasoningContentBlockDelta.html
                """
                redactedContent: Base64Bytes | None = None
                text: str | None = None
                signature: str | None = None

                def __add__(self, other: Self) -> Self:
                    return type(self)(
                        redactedContent=_add_nullables(self.redactedContent, other.redactedContent, b""),
                        text=_add_nullables(self.text, other.text, ""),
                        signature=_add_nullables(self.signature, other.signature, ""),
                    )
            
            class ImageBlockDelta(BaseModel):
                """
                https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageBlockDelta.html
                """

                class ErrorBlock(BaseModel):
                    """
                    https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ErrorBlock.html
                    """
                    message: str

                error: Any | None = None
                imageSource: BedrockContentBlock.BedrockImage.BedrockImageSource | None = None

                def __add__(self, other: Self) -> Self:
                    return type(self)(
                        error=self.error or other.error,
                        imageSource=_add_nullables(self.imageSource, other.imageSource, BedrockContentBlock.BedrockImage.BedrockImageSource(bytes=None, s3Location=None)),
                    )

            class CitationDelta(BaseModel):
                """
                https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_CitationsDelta.html

                TODO: implement this one deeper ?
                """
                location: Any | None = None
                source: str | None = None
                sourceContent: Any | None = None
                title: str | None = None

                def __add__(self, other: Self) -> Self:
                    # TODO : this is a dummy implementation, I do not use this feature
                    return other

            citation: CitationDelta | None = None
            image: ImageBlockDelta | None = None
            reasoning: ReasoningContentBlockDelta | None = None
            text: str | None = None
            toolResult: ToolResultBlockDelta | None = None
            toolUse: ToolUseBlockDelta | None = None

        delta: ContentBlockDelta
        contentBlockIndex: int

    class ContentBlockStopEvent(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ContentBlockStopEvent.html
        """
        contentBlockIndex: int

    class MessageStartEvent(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_MessageStartEvent.html
        """
        role: Literal["user", "assistant"]

    class MessageStopEvent(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_MessageStopEvent.html
        """
        stopReason: Literal["end_turn", "tool_use", "max_tokens", "stop_sequence", "guardrail_intervened", "content_filtered", "malformed_model_output", "malformed_tool_use", "model_context_window_exceeded"]
        additionalModelResponseFields: dict | None = None

    class Metadata(BaseModel):
        """
        https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseStreamMetadataEvent.html
        """
        metrics: BedrockConverseResponse.BedrockConverseMetrics
        usage: BedrockConverseResponse.BedrockTokenUsage
        performanceConfig: Any | None = None
        serviceTier: BedrockConverseResponse.BedrockServiceTier | None = None
        trace: BedrockConverseResponse.BedrockConverseTrace | None = None

    contentBlockDelta: ContentBlockDeltaEvent | None = None
    contentBlockStart: ContentBlockStartEvent | None = None
    contentBlockStop: ContentBlockStopEvent | None = None
    messageStart: MessageStartEvent | None = None
    messageStop: MessageStopEvent | None = None
    metadata: Metadata | None = None

    def content(self) -> ContentBlockDeltaEvent | ContentBlockStartEvent | ContentBlockStopEvent | MessageStartEvent | MessageStopEvent | Metadata | None:
        for name, value in self:
            if value is not None:
                return value
        return None
