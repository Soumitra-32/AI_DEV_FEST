"""The model call itself, with a three-key failover pool.

One primary key and two backups. A backup is a *different credential on the same
OpenAI-compatible endpoint*, which is what covers the two failures that actually
happen on demo day: a revoked or exhausted primary key, and a transient 429/5xx.
Each key may carry its own base URL and model, so a backup can also be a
different provider entirely.

Why this is a module and not three lines in ``explain.py``: every LLM use in the
project (verbalizer, intent classifier, tip phrasing, trade-off wording) has to
fail over the same way, and the fallback rule is a *safety* rule -- a key that
errors must never turn into a 500 or an unguarded answer. Centralising it means
that rule is written once and tested once.

The pool is deliberately stateless and dependency-free apart from the OpenAI SDK,
which is imported lazily so the whole app still runs with no key and no network.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

logger = logging.getLogger("shonchoy.llm_client")

#: How many providers one request may burn through. Matches the three configured
#: keys, so a request never loops.
MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class Provider:
    """One credential: a name for logs, plus the connection details."""

    name: str
    api_key: str
    base_url: str
    model: str

    @property
    def label(self) -> str:
        """A log-safe label -- never the key itself."""
        return self.name


class AllProvidersFailed(RuntimeError):
    """Every configured provider errored or timed out.

    Carries the per-provider exception *types* (never messages, which can echo
    request content) so a caller can log something useful without leaking.
    """

    def __init__(self, failures: Sequence[tuple[str, str]]) -> None:
        self.failures = tuple(failures)
        summary = ",".join(f"{name}:{kind}" for name, kind in self.failures) or "none"
        super().__init__(f"all llm providers failed ({summary})")


def providers_from_settings(settings: Any) -> tuple[Provider, ...]:
    """The configured pool, in priority order, with empty keys dropped.

    Works with a :class:`backend.app.config.Settings`, a stub, or any object with
    the same attribute names -- the tests pass simple stand-ins.
    """
    candidates = (
        ("primary", getattr(settings, "llm_api_key", ""), getattr(settings, "llm_base_url", ""),
         getattr(settings, "llm_model", "")),
        ("backup-1", getattr(settings, "llm_backup_api_key_1", ""),
         getattr(settings, "llm_backup_base_url_1", "") or getattr(settings, "llm_base_url", ""),
         getattr(settings, "llm_backup_model_1", "") or getattr(settings, "llm_model", "")),
        ("backup-2", getattr(settings, "llm_backup_api_key_2", ""),
         getattr(settings, "llm_backup_base_url_2", "") or getattr(settings, "llm_base_url", ""),
         getattr(settings, "llm_backup_model_2", "") or getattr(settings, "llm_model", "")),
    )
    default_base = getattr(settings, "llm_base_url", "") or "https://api.openai.com/v1"
    default_model = getattr(settings, "llm_model", "") or "gpt-4o-mini"
    pool = [
        Provider(name=name, api_key=str(key).strip(), base_url=base or default_base,
                 model=model or default_model)
        for name, key, base, model in candidates
        if str(key or "").strip()
    ]
    return tuple(pool[:MAX_ATTEMPTS])


def _build(provider: Provider, timeout_seconds: float) -> Any:
    """Construct an OpenAI-compatible client for one provider.

    Imported here rather than at module scope: with no key configured the ``openai``
    package is never needed, and a missing optional dependency must not stop the
    app from booting on the template path.
    """
    from openai import OpenAI  # noqa: PLC0415 - optional dependency

    return OpenAI(
        api_key=provider.api_key,
        base_url=provider.base_url,
        timeout=timeout_seconds,
        # Failover is this module's job, so the SDK must not also retry silently:
        # one attempt per provider keeps the total bounded and observable.
        max_retries=0,
    )


def _extract(completion: Any) -> str:
    """Pull the assistant text out of a chat completion."""
    return completion.choices[0].message.content or ""


def complete(
    messages: Sequence[Mapping[str, str]],
    settings: Any,
    request_kwargs: Optional[Mapping[str, Any]] = None,
    client: Any = None,
) -> tuple[str, str]:
    """Run one chat completion, failing over between providers.

    Returns ``(raw_text, provider_label)``. ``client`` short-circuits the pool and
    is what the tests inject; a stub has ``.chat.completions.create``.

    Raises :class:`AllProvidersFailed` when nothing answered, so the caller can
    fall back to its template.
    """
    kwargs = dict(request_kwargs or {})
    if client is not None:
        # Injected client (tests, or a caller that owns its own transport). The
        # model still comes from settings so an injected transport is configured
        # identically to a real one.
        model = str(getattr(settings, "llm_model", "") or "") if settings is not None else ""
        completion = client.chat.completions.create(
            model=model, messages=list(messages), **kwargs
        )
        return _extract(completion), "injected"

    pool = providers_from_settings(settings)
    if not pool:
        raise AllProvidersFailed(())

    timeout = float(getattr(settings, "llm_timeout_seconds", 20.0) or 20.0)
    failures: list[tuple[str, str]] = []
    for provider in pool:
        try:
            active = _build(provider, timeout)
            completion = active.chat.completions.create(
                model=provider.model, messages=list(messages), **kwargs
            )
        except Exception as exc:  # auth, rate limit, timeout, network, bad SDK
            # Log the provider and the exception *type* only: a provider error
            # message can echo the request, and no user text is ever logged.
            logger.warning("llm provider %s failed: %s", provider.label, type(exc).__name__)
            failures.append((provider.label, type(exc).__name__))
            continue
        return _extract(completion), provider.label

    raise AllProvidersFailed(failures)


def enabled(settings: Any) -> bool:
    """True when the feature flag is on *and* at least one key is configured."""
    if not getattr(settings, "feature_llm", True):
        return False
    return bool(providers_from_settings(settings))
