"""LLM provider factory — returns the appropriate LangChain chat model.

SAKSHAM picks a **different model and temperature per agent role** so each
specialist is tuned for its job. When running Ollama you can point each agent
at a genuinely different model (e.g. deepseek-coder:6.7b for coding, llama3
for research, mistral for writing). When running a cloud provider, per-agent
model overrides (RESEARCH_MODEL, CODING_MODEL, etc.) and per-role temperature
defaults still produce meaningfully different outputs.

This is the core architectural differentiator vs. a plain "call one API"
chatbot wrapper.
"""

import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Provider defaults (used when per-agent envvar is empty) ──────────────
_PROVIDER_DEFAULTS = {
    "openai": {
        "research": ("gpt-4o-mini", 0.3),
        "coding":   ("gpt-4o-mini", 0.1),
        "email":    ("gpt-4o-mini", 0.7),
        "routing":  ("gpt-4o-mini", 0.0),
        "default":  ("gpt-4o-mini", 0.5),
    },
    "gemini": {
        "research": ("gemini-1.5-flash", 0.3),
        "coding":   ("gemini-1.5-flash", 0.1),
        "email":    ("gemini-1.5-flash", 0.7),
        "routing":  ("gemini-1.5-flash", 0.0),
        "default":  ("gemini-1.5-flash", 0.5),
    },
    "ollama": {
        "research": ("llama3", 0.3),
        "coding":   ("deepseek-coder:6.7b", 0.1),
        "email":    ("mistral", 0.7),
        "routing":  ("llama3", 0.0),
        "default":  ("llama3", 0.5),
    },
}

# Maps agent roles to env-var overrides
_AGENT_MODEL_ENVVAR = {
    "research": lambda: settings.RESEARCH_MODEL,
    "coding":   lambda: settings.CODING_MODEL,
    "email":    lambda: settings.EMAIL_MODEL,
    "routing":  lambda: settings.ROUTING_MODEL,
}


def _resolve_model_temp(
    agent_role: Optional[str],
    model_override: Optional[str],
    temp_override: Optional[float],
) -> tuple[str, float]:
    """Pick the model name and temperature for a given agent role."""
    provider = settings.LLM_PROVIDER.lower()
    defaults = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["openai"])
    role = agent_role or "default"
    default_model, default_temp = defaults.get(role, defaults["default"])

    # Priority: explicit param > per-agent envvar > provider default
    envvar_model = ""
    if role in _AGENT_MODEL_ENVVAR:
        envvar_model = _AGENT_MODEL_ENVVAR[role]() or ""

    model = model_override or envvar_model or default_model
    temp = temp_override if temp_override is not None else default_temp

    logger.debug(f"LLM resolve: role={role} model={model} temp={temp} provider={provider}")
    return model, temp


def _build_llm(model: str, temperature: float, streaming: bool):
    """Instantiate the LangChain chat model for the configured provider."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            streaming=streaming,
            api_key=settings.OPENAI_API_KEY,
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=settings.GOOGLE_API_KEY,
        )

    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=model,
            temperature=temperature,
            base_url=settings.OLLAMA_BASE_URL,
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def get_llm(
    model: str | None = None,
    temperature: float | None = None,
    streaming: bool = True,
    agent_role: str | None = None,
):
    """Return a LangChain ChatModel tuned for `agent_role`.

    Each agent role gets a purpose-specific model and temperature:
    - research: low temperature for factual accuracy
    - coding: very low temperature, code-tuned model when available
    - email: higher temperature for creative writing
    - routing: zero temperature for deterministic classification
    """
    resolved_model, resolved_temp = _resolve_model_temp(agent_role, model, temperature)
    return _build_llm(resolved_model, resolved_temp, streaming)


def get_routing_llm():
    """Smaller/faster model with temperature=0 for routing decisions."""
    return get_llm(streaming=False, agent_role="routing")
