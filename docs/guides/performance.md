# Measuring discovery and bundle performance

Run the synthetic 10,000-Skill benchmark from the project root:

```console
uv run python -m benchmarks.benchmark_10k
```

The benchmark exercises model construction, source loading and indexing,
exact and semantic discovery, dependency resolution, bundle construction,
concurrent queries, and Python-traced memory. It uses deterministic fake
embeddings; its semantic timings measure integration overhead, not relevance
or the performance of a production embedding service.

One measured run on Windows with the project's Python 3.12 environment
produced:

| Operation | Elapsed time |
|---|---:|
| Construct 10,000 Skill models | 0.656 s |
| YAML load, validation, and indexing | 46.263 s |
| Exact discovery index | 0.387 s |
| Exact top-10 query | 0.129 s |
| Synthetic semantic embedding index | 0.553 s |
| Synthetic semantic query | 0.840 s |
| Resolve a six-Skill dependency chain | 0.00050 s |
| Build a one-Skill capability bundle | 0.00043 s |
| 100 concurrent exact queries | 12.946 s |
| Peak Python-traced memory | 127,051,641 bytes (121.2 MiB) |

These are a single machine's observed measurements, not service-level
guarantees. Hardware, Python and dependency versions, catalog content, and
native allocations affect results; `tracemalloc` does not include every
native allocation. Use the benchmark as a reproducible local baseline and
measure your production workload separately.
