"""Run every SkillManager injection with live services and Grafana telemetry."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from typing import Any, TypedDict
from uuid import uuid4

from _otel import (
    OpenTelemetryFeedbackSink,
    OpenTelemetryMCPMetrics,
    OpenTelemetryRefreshHandler,
    OpenTelemetrySkillSink,
)
from _postgres import PostgresSkillRegistry, PostgresSkillSource
from feedback_manager import FeedbackManager, FeedbackQuery
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient, StreamableHttpConnection
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph_xai import ObservabilityProvider, OpenTelemetryObservability, XAIRuntime
from mcp_capability_router import MCPRuntime
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource as TelemetryResource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from refresh_engine import (
    DiscoveryResult,
    EventPublisher,
    RefreshEngine,
    RefreshMode,
    Resource,
    ResourceSnapshot,
    TriggerSource,
)

from skill_manager import (
    DefaultSkillValidator,
    ExactDiscoveryProvider,
    LexicalSkillRetriever,
    ScoreSkillReranker,
    Skill,
    SkillCapability,
    SkillManager,
    SkillManagerConfig,
    SkillMetadata,
    SkillOrigin,
    SkillProvenance,
)


class GraphState(TypedDict, total=False):
    response: str
    skill_id: str


class CatalogRefreshSource:
    async def discover(self) -> DiscoveryResult:
        async def resources() -> AsyncIterator[Resource]:
            yield Resource("live-skill-catalog")

        return DiscoveryResult(resources())

    async def snapshot(self, resource: Resource) -> ResourceSnapshot:
        return ResourceSnapshot(resource.resource_id, content={"source": "postgres"})


async def apply_refresh(
    resource: Resource | None,
    snapshot: ResourceSnapshot | None,
    action: Any,
    request: Any,
) -> None:
    del resource, snapshot, action, request


def build_tracing() -> tuple[TracerProvider, Any]:
    endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "http://127.0.0.1:4318/v1/traces",
    )
    provider = TracerProvider(
        resource=TelemetryResource.create({"service.name": "skill-manager-live"})
    )
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    return provider, provider.get_tracer("skill-manager.live-example")


async def main() -> None:
    required = ("EXPLABS_API_KEY", "SKILL_MANAGER_POSTGRES_DSN", "SKILL_MANAGER_MCP_URL")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError("missing required environment variables: " + ", ".join(missing))

    provider, tracer = build_tracing()
    events = EventPublisher()
    events.subscribe(OpenTelemetryRefreshHandler(tracer))
    refresh_engine = RefreshEngine(CatalogRefreshSource(), apply_refresh, events=events)
    xai_runtime = XAIRuntime(application_id="skill-manager-live")
    xai_runtime.register(
        ObservabilityProvider,
        OpenTelemetryObservability(tracer),
    )
    feedback_manager = FeedbackManager(
        xai_runtime=xai_runtime,
        observability_sink=OpenTelemetryFeedbackSink(tracer),
    )
    source = PostgresSkillSource(os.environ["SKILL_MANAGER_POSTGRES_DSN"])
    registry = PostgresSkillRegistry(os.environ["SKILL_MANAGER_POSTGRES_DSN"])
    await source.open()
    await registry.open()
    for existing in await registry.all():
        if existing.metadata.name.startswith("live-pr-analysis-"):
            await registry.remove(existing.skill_id)
            await source.delete(existing.skill_id)

    server_name = os.getenv("SKILL_MANAGER_MCP_SERVER", "tools")
    connection: StreamableHttpConnection = {
        "transport": "streamable_http",
        "url": os.environ["SKILL_MANAGER_MCP_URL"],
    }
    mcp_client = MultiServerMCPClient({server_name: connection})
    mcp_runtime = MCPRuntime(metrics=OpenTelemetryMCPMetrics(tracer))
    await mcp_runtime.register_mcp_client(server_name, mcp_client)
    await mcp_runtime.refresh_server(server_name)
    capabilities = await mcp_runtime.retrieve("read pull request details", limit=5)
    if not capabilities:
        raise RuntimeError("the live MCP server did not expose the expected tool")
    capability = capabilities[0]

    model = ChatOpenAI(
        model=os.getenv("SKILL_MANAGER_MODEL", "gpt-5.6-luna"),
        base_url=os.getenv("SKILL_MANAGER_LLM_BASE_URL", "https://api.experientiallabs.ai/v1"),
        api_key=os.environ["EXPLABS_API_KEY"],
        temperature=0,
    )
    manager = SkillManager(
        sources=[source],
        registry=registry,
        retriever=LexicalSkillRetriever(),
        reranker=ScoreSkillReranker(),
        discovery_candidate_pool_size=7,
        validator=DefaultSkillValidator(),
        config=SkillManagerConfig(
            allow_agent_skill_creation=True,
            require_human_approval=True,
        ),
        feedback_manager=feedback_manager,
        mcp_runtime=mcp_runtime,
        refresh_engine=refresh_engine,
        observability_sink=OpenTelemetrySkillSink(tracer),
    )

    unique_name = f"live-pr-analysis-{uuid4().hex[:8]}"
    pending = await manager.register_skill(
        Skill(
            metadata=SkillMetadata(
                name=unique_name,
                version="1.0.0",
                description="Analyze a pull request using a live MCP result.",
            ),
            instructions=(
                "Report only facts present in the MCP pull-request result.",
                "Keep the response to one sentence.",
            ),
            capabilities=(SkillCapability(name=capability.name),),
            provenance=SkillProvenance(
                origin=SkillOrigin.AGENT,
                source="live-integration",
            ),
        )
    )

    async def run_skill(state: GraphState) -> GraphState:
        del state
        approved = await manager.approve_skill(
            pending.skill_id,
            metadata={"reviewer": "live-integration"},
        )
        selected = await manager.discover("live pull request analysis", top_k=1)
        bundle = await manager.build_bundle(selected)
        tool_result = await mcp_runtime.execute(capability.capability_id, {"number": 42})
        with tracer.start_as_current_span("llm.chat.completions"):
            response = await model.ainvoke(
                [
                    SystemMessage(content="\n".join(bundle.instructions)),
                    HumanMessage(
                        content=(
                            "Summarize this MCP result in one sentence and mention the "
                            f"pull-request number: {tool_result}"
                        )
                    ),
                ]
            )
        return {"response": str(response.content), "skill_id": approved.skill_id}

    try:
        with tracer.start_as_current_span("skill-manager.live.run"):
            await manager.refresh(mode=RefreshMode.FULL, trigger=TriggerSource.MANUAL)
            builder = StateGraph(GraphState)
            builder.add_node("run_skill", run_skill)
            builder.add_edge(START, "run_skill")
            builder.add_edge("run_skill", END)
            graph = xai_runtime.instrument(builder.compile())
            result = await graph.ainvoke({})

            feedback_events = await feedback_manager.query(
                FeedbackQuery(target_type="skill", target_id=result["skill_id"], limit=10)
            )
            assert result["response"].strip()
            assert feedback_events and feedback_events[0].provenance is not None
            assert not manager.observability_errors

            provider_manager = SkillManager(
                registry=registry,
                discovery_provider=ExactDiscoveryProvider(),
                observability_sink=OpenTelemetrySkillSink(tracer),
            )
            provider_matches = await provider_manager.discover(unique_name, top_k=1)
            assert provider_matches and provider_matches[0].skill_id == result["skill_id"]
            await provider_manager.close()

        print(f"skill={unique_name}")
        print(f"mcp_capability={capability.name}")
        print(f"feedback_provenance={feedback_events[0].provenance.execution_id}")
        print(f"llm_response={result['response']}")
        print("grafana_service=skill-manager-live")
    finally:
        await manager.close()
        await refresh_engine.close()
        await mcp_runtime.close()
        await source.close()
        await registry.close()
        await xai_runtime.close()
        provider.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
