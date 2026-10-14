"""CAMEL-compatible OpenAI model with the same per-run limits and telemetry."""
import asyncio
from camel.models import ModelFactory, BaseModelBackend
from camel.types import ModelPlatformType
from research_runtime import inference_scope
from research_runtime.usage import tracked_request
from research_codex.transport import _request_slot
from ..config import Config


class ReviewedOpenAIModel(BaseModelBackend):
    def __init__(self, context):
        self.context = context
        name = context.model or Config.LLM_MODEL_NAME
        super().__init__(name, {})
        self.delegate = ModelFactory.create(model_platform=ModelPlatformType.OPENAI,
            model_type=name, api_key=Config.LLM_API_KEY, url=Config.LLM_BASE_URL)

    @property
    def token_counter(self):
        return self.delegate.token_counter

    @property
    def token_limit(self):
        return self.delegate.token_limit

    def _run(self, messages, response_format=None, tools=None):
        with inference_scope(self.context), tracked_request(self.context) as metrics, _request_slot(prefix='OPENAI', label='OpenAI') as queued:
            metrics['queue_seconds'] = queued
            result = self.delegate.run(messages, response_format=response_format, tools=tools)
            metrics['usage'] = getattr(result, 'usage', None)
            return result

    async def _arun(self, messages, response_format=None, tools=None):
        return await asyncio.to_thread(self._run, messages, response_format, tools)
