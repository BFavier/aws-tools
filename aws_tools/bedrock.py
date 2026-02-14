import aioboto3
from base64 import b64decode, b64encode
from collections import defaultdict
from typing import Literal, Optional, Any, Annotated, Type, TypeVar
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


class AgentTool(BaseModel):
    """
    Derive this base class to implement a tool that LLMs can call.
    The description of the tool must be the class docstring.
    The arguments to be provided by the LLM must be fields of the class, the description of which is described with pydantic's 'argument = Field(..., description="the tool argument description")'.
    """

    async def __call__(self, **tool_secrets) -> Any:
        """
        Any documentation here is invisible to the LLM.
        The implementation of the actual tool is in the class' __call__ method.
        In addition to the tool args that are fields of this object,
        any additional kwarg passed to the __call__ method can be used for the logic while staying hidden from the LLM
        """
        raise NotImplementedError()
    
    @classmethod
    def definition(cls) -> BedrockToolConfig.BedrockTool:
        """
        """
        return BedrockToolConfig.BedrockTool(
            toolSpec=BedrockToolConfig.BedrockTool.BedrockToolSpec(
                inputSchema=cls.model_json_schema()
            ),
            name=cls.__name__,
            description="\n".join(s.strip() for s in cls.__doc__.split("\n") if len(s.strip()) > 0) if cls.__doc__ is not None else None
        )


T = TypeVar("T", bound=Type[AgentTool])


class Agent:
    """
    Derive this base class agent is an LLM with tools registered
    """
    tools: dict[str, Type[AgentTool]] = {}
    tool_config: BedrockToolConfig | None = None

    def __init_subclass__(cls, **kwargs):
        """
        Each derived class have a distinct set of 'tools' and 'tool_config' objects
        """
        super().__init_subclass__(**kwargs)
        cls.tools = {}
        cls.tool_config = None

    def __init__(self, bedrock_client: Bedrock, model_id: str, system_prompt: str | None):
        self.bedrock_client = bedrock_client
        self.model_id = model_id
        self.system_prompt = system_prompt

    @classmethod
    def register_tool(cls, new_tool: T) -> T:
        """
        A decorator to apply on top of new tool to register into an agent class
        """
        cls.tools[new_tool.__name__] = new_tool
        cls.bedrock_tool_config = BedrockToolConfig(
            tools=[T.definition() for T in cls.tools.values()]
        )
        return new_tool

    async def converse_async(self, conversation_id: str, history: list[BedrockMessage], user_message: BedrockContentBlock, inference_config: BedrockInferenceConfig | None = None, tool_secrets: dict[str, dict]=defaultdict(dict)) -> BedrockConverseResponse:
        """
        Returns a response from the LLM.
        """
        history.append(BedrockMessage(role="user"))
        while True:
            message = await self._agent_turn_async(inference_config)
            history.append(message)
            tool_uses = [block.toolUse for block in message.content if block.toolUse is not None]
            if len(tool_uses) == 0:
                break
            else:
                # TODO: logic for budget
                ...

    async def _agent_turn_async(self, inference_config: BedrockInferenceConfig | None) -> BedrockMessage:
        """
        """
        payload = BedrockConverseRequest(
            modelId=self.model_id,
            inferenceConfig=inference_config,
            system=BedrockSystemContentBlock(system=self.system_prompt),
            toolConfig=self.tool_config
        )
        response = await self.bedrock_client.converse_async(payload)
        return response.output.message

    async def _call_tool(self, tool_use: BedrockContentBlock.BedrockToolUse, tool_secrets: dict[str, dict]) -> BedrockContentBlock.BedrockToolResult:
        """
        """
        try:
            Tool = self.tools[tool_use.name]
            tool = Tool(**tool_use.input)
            result = await tool(**tool_secrets[tool_use.name])
        except Exception as e:
            return BedrockContentBlock.BedrockToolResult(
                content=[
                    BedrockContentBlock.BedrockToolResult.BedrockToolResultContent(json={})
                ],
                toolUseId=tool_use.toolUseId,
                status="error"
            )
        else:
            return BedrockContentBlock.BedrockToolResult(
                content=[
                    BedrockContentBlock.BedrockToolResult.BedrockToolResultContent(json={"result": result})
                ],
                toolUseId=tool_use.toolUseId,
                status="success"
            )
