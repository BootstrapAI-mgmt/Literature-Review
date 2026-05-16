"""
Unified LLM Client Interface

Provides a consistent interface for making LLM calls regardless of provider.
Abstracts away provider-specific API differences.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from literature_review.config.model_config import (
    ModelConfig, ModelProvider, get_model_config
)

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def get_token_counts(self) -> Dict[str, int]:
        """Get token counts from last call."""
        pass


class GeminiClient(LLMClient):
    """Client for Google Gemini models."""
    
    def __init__(self, config: ModelConfig):
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError(
                "google-genai package not installed. Install with: pip install google-genai"
            )
        
        self.config = config
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not set: {config.api_key_env}")
        
        self.client = genai.Client(api_key=api_key)
        self._last_usage = {"input": 0, "output": 0}

        # NOTE on thinking_budget=0:
        # The session-call policy (feedback_top_tier_subagents.md) requires
        # maximum-reasoning effort on the *primary* top-tier model (Opus 4.7).
        # Gemini Flash is intentionally the cheap fallback tier — it only
        # runs when Claude Code + Anthropic API are both unavailable. We
        # deliberately keep thinking disabled here to preserve Flash's role
        # as a fast, low-cost safety net rather than turning it into another
        # high-effort path. If you want Gemini Pro with thinking enabled,
        # switch via MODEL_NAME=gemini-pro and update gemini_pro() config.
        thinking_config = types.ThinkingConfig(thinking_budget=0)
        self.json_config = types.GenerateContentConfig(
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_tokens,
            response_mime_type="application/json",
            thinking_config=thinking_config
        )
        self.text_config = types.GenerateContentConfig(
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_tokens,
            thinking_config=thinking_config
        )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        config = self.json_config if json_mode else self.text_config
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = self.client.models.generate_content(
            model=self.config.model_name,
            contents=full_prompt,
            config=config
        )
        
        # Track usage
        if hasattr(response, 'usage_metadata'):
            self._last_usage = {
                "input": getattr(response.usage_metadata, 'prompt_token_count', 0),
                "output": getattr(response.usage_metadata, 'candidates_token_count', 0)
            }
        
        return response.text
    
    def get_token_counts(self) -> Dict[str, int]:
        return self._last_usage


class OpenAIClient(LLMClient):
    """Client for OpenAI models."""
    
    def __init__(self, config: ModelConfig):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. Install with: pip install openai"
            )
        
        self.config = config
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not set: {config.api_key_env}")
        
        self.client = OpenAI(api_key=api_key)
        self._last_usage = {"input": 0, "output": 0}
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response_format = None
        if json_mode:
            response_format = {"type": "json_object"}
        
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format=response_format
        )
        
        # Track usage
        if response.usage:
            self._last_usage = {
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens
            }
        
        return response.choices[0].message.content
    
    def get_token_counts(self) -> Dict[str, int]:
        return self._last_usage


class AnthropicClient(LLMClient):
    """Client for Anthropic Claude models."""
    
    def __init__(self, config: ModelConfig):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Install with: pip install anthropic"
            )
        
        self.config = config
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not set: {config.api_key_env}")
        
        self.client = Anthropic(api_key=api_key)
        self._last_usage = {"input": 0, "output": 0}
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        # Per session-call policy (feedback_top_tier_subagents.md, 2026-05-01):
        # every Opus 4.7 dispatch MUST prepend the literal word `ultrathink`
        # as the first line of the prompt. The Claude Code keyword maps to
        # the API's extended-thinking feature, which we enable below for
        # any model whose config declares supports_thinking_mode=True.
        # See: ../memory/feedback_session_call_policy.md
        user_message = f"ultrathink\n\n{prompt}"

        # Claude doesn't have native JSON mode; add instruction
        if json_mode:
            user_message = f"{user_message}\n\nRespond with valid JSON only."

        create_kwargs: Dict[str, Any] = {
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "system": system_prompt or "",
            "messages": [{"role": "user", "content": user_message}],
        }

        if getattr(self.config, "supports_thinking_mode", False):
            # Anthropic extended-thinking contract:
            #   - budget_tokens must be < max_tokens
            #   - temperature must be 1.0 when thinking is enabled
            # We allocate up to half of max_tokens to the thinking budget,
            # capped at 8192 to leave generous room for the visible response.
            budget = max(1024, min(8192, self.config.max_tokens // 2))
            create_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget,
            }
            create_kwargs["temperature"] = 1.0  # required when thinking is on
        else:
            create_kwargs["temperature"] = self.config.temperature

        response = self.client.messages.create(**create_kwargs)

        # Track usage
        self._last_usage = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens
        }

        # When thinking is enabled, the response contains both thinking and
        # text blocks. We only return the visible-text portion to callers
        # (the JSON parser, etc.) — thinking content is internal.
        for block in response.content:
            block_type = getattr(block, "type", None)
            if block_type == "text" or hasattr(block, "text"):
                if hasattr(block, "text"):
                    return block.text
        # Fallback: legacy shape with a single content[0]
        return response.content[0].text

    def get_token_counts(self) -> Dict[str, int]:
        return self._last_usage


class ClaudeCodeClient(LLMClient):
    """Client for Claude routed through Claude Code (subscription-backed).

    Uses the official ``claude-agent-sdk`` Python package. Instead of
    billing per token against an Anthropic API key, calls consume the
    user's Claude Code / Max-plan hourly quota.

    Auth: the SDK reads credentials from the same location as the local
    ``claude`` CLI (typically ``~/.claude/credentials.json``). No API
    key is passed; ``ANTHROPIC_API_KEY`` is *not* used by this path.

    Rate limits: an ``HourlyRateLimiter`` enforces the configured
    ``requests_per_hour`` cap (set per ModelConfig, overridable via the
    ``CLAUDE_CODE_RPH`` env var). The limiter uses a continuous
    sliding-window strategy so the pipeline interleaves cleanly with
    any interactive Claude Code use on the same account.

    Concurrency: the SDK is async. The synchronous ``generate`` wraps
    each query in ``anyio.run`` so callers don't have to refactor.
    Concurrent calls from multiple threads serialize on the rate
    limiter; this matches the pipeline's existing sequential batch
    semantics.
    """

    def __init__(self, config: ModelConfig):
        try:
            from claude_agent_sdk import (  # noqa: F401 — lazy presence check
                query, ClaudeAgentOptions,
            )
        except ImportError as e:
            raise ImportError(
                "claude-agent-sdk is required for the CLAUDE_CODE provider. "
                "Install with: pip install 'claude-agent-sdk>=0.1.0'. "
                f"Original error: {e}"
            )
        # Defer the rate limiter import to avoid a circular dependency
        from literature_review.utils.hourly_rate_limiter import HourlyRateLimiter

        self.config = config
        self._last_usage = {"input": 0, "output": 0}
        # Per-model RPH override falls through to env var, then default
        rph = config.requests_per_hour or None
        self._rate_limiter = HourlyRateLimiter(limit_per_hour=rph, name=config.model_name)
        logger.info(
            "ClaudeCodeClient ready: model=%s rph_cap=%d remaining=%d",
            config.model_name, self._rate_limiter.limit, self._rate_limiter.remaining(),
        )

    def _build_options(self, system_prompt: Optional[str], json_mode: bool):
        """Construct the ClaudeAgentOptions for a one-shot query."""
        from claude_agent_sdk import ClaudeAgentOptions  # local import

        # Disable all tools for pipeline use — paper content is arbitrary
        # text and we don't want the agent reading/writing files or
        # running bash. Pure text-in / text-out only.
        kwargs = {
            "allowed_tools": [],
            "permission_mode": "bypassPermissions",
            "max_turns": 1,
            "model": self.config.model_name,
        }
        if system_prompt:
            # `system_prompt` accepts either a string (treated as additive
            # instructions) or a SystemPromptPreset. We use the string form.
            kwargs["system_prompt"] = system_prompt
        # JSON-mode coaxing happens at the prompt layer (see ``generate``).
        return ClaudeAgentOptions(**kwargs)

    async def _run_query(self, prompt: str, system_prompt: Optional[str], json_mode: bool) -> str:
        from claude_agent_sdk import query  # local import

        options = self._build_options(system_prompt, json_mode)
        text_buf = []
        async for message in query(prompt=prompt, options=options):
            # Each message is one of: SystemMessage, AssistantMessage,
            # UserMessage, ResultMessage. We only care about assistant
            # text output.
            content = getattr(message, "content", None)
            if not content:
                continue
            for block in content:
                block_text = getattr(block, "text", None)
                if block_text:
                    text_buf.append(block_text)
            # ResultMessage carries usage metrics on some SDK versions
            usage = getattr(message, "usage", None)
            if usage:
                self._last_usage = {
                    "input": getattr(usage, "input_tokens", 0) or 0,
                    "output": getattr(usage, "output_tokens", 0) or 0,
                }
        return "".join(text_buf)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs,
    ) -> str:
        import anyio  # required by claude-agent-sdk; safe to import alongside it

        # Per session-call policy (feedback_top_tier_subagents.md, 2026-05-01):
        # every Opus 4.7 dispatch MUST prepend the literal word `ultrathink`
        # as the first line of the prompt. This is the Claude Code operator
        # keyword for maximum thinking-budget allocation; without it we ship
        # the model at default reasoning, which violates the policy.
        # See: ../memory/feedback_session_call_policy.md
        effective_prompt = f"ultrathink\n\n{prompt}"

        # Coax JSON output at the prompt level — the SDK has no native
        # JSON-mode equivalent.
        if json_mode:
            effective_prompt = (
                f"{effective_prompt}\n\n"
                "Respond with valid JSON only. Do not include any commentary, "
                "markdown fences, or text outside the JSON object."
            )

        # Block until the hourly window has capacity.
        waited = self._rate_limiter.acquire()
        if waited > 0:
            logger.info("Claude Code call resumed after %.1fs rate-limit wait", waited)

        return anyio.run(self._run_query, effective_prompt, system_prompt, json_mode)

    def get_token_counts(self) -> Dict[str, int]:
        return self._last_usage

    def remaining_in_window(self) -> int:
        """Diagnostic: how many calls left in the current rolling hour."""
        return self._rate_limiter.remaining()


class LocalClient(LLMClient):
    """Client for local models via Ollama."""
    
    def __init__(self, config: ModelConfig):
        import requests
        
        self.config = config
        self.base_url = os.environ.get(config.api_key_env, "http://localhost:11434")
        self._last_usage = {"input": 0, "output": 0}
        
        # Verify connection
        try:
            requests.get(f"{self.base_url}/api/version", timeout=2)
        except Exception as e:
            logger.warning(f"Ollama not available at {self.base_url}: {e}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        **kwargs
    ) -> str:
        import requests
        
        if json_mode:
            prompt = f"{prompt}\n\nRespond with valid JSON only."
        
        payload = {
            "model": self.config.model_name,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {
                "temperature": self.config.temperature
            }
        }
        
        if json_mode:
            payload["format"] = "json"
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Track usage (Ollama provides token counts)
        self._last_usage = {
            "input": result.get("prompt_eval_count", 0),
            "output": result.get("eval_count", 0)
        }
        
        return result["response"]
    
    def get_token_counts(self) -> Dict[str, int]:
        return self._last_usage


# =============================================================================
# Client Factory
# =============================================================================

def get_llm_client(config: Optional[ModelConfig] = None) -> LLMClient:
    """
    Get an LLM client for the given or current configuration.
    
    Args:
        config: Optional model configuration. If None, uses current global config.
    
    Returns:
        Appropriate LLMClient instance for the provider.
    """
    if config is None:
        config = get_model_config()
    
    client_map = {
        ModelProvider.GEMINI: GeminiClient,
        ModelProvider.OPENAI: OpenAIClient,
        ModelProvider.ANTHROPIC: AnthropicClient,
        ModelProvider.CLAUDE_CODE: ClaudeCodeClient,
        ModelProvider.LOCAL: LocalClient,
    }
    
    client_class = client_map.get(config.provider)
    if not client_class:
        raise ValueError(f"Unsupported provider: {config.provider}")
    
    return client_class(config)
