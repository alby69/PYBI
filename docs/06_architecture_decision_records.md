# Architecture Decision Records

## ADR 001: Canonical Semantic Package

- **Status:** Accepted
- **Decision:** Semantic model persistence, model-view schemas, DAX translation,
  RLS, relationship detection, and synchronization live under `pybi.semantic`.
  The distinct persisted, editor, query-adapter, and runtime schemas remain
  separate because they have different shapes and serialization contracts.
- **Compatibility:** `pybi.core`, `pybi.model`, and `pybi.models` retain thin
  re-export modules where callers still use historical paths. New code imports
  from `pybi.semantic`.
- **Consequence:** There is one package owner for semantic behavior without
  forcing incompatible API, persisted, and runtime payloads into a single model.

## ADR 002: Deprecated Backend Package

- **Status:** Accepted
- **Decision:** `pybi` is the canonical implementation. `backend` contains only
  a deprecation-warning package entry point and the `backend.main` launch
  wrapper; former `backend.*` implementation imports are removed.
- **Consequence:** Internal imports and tests use `pybi.*`. External callers
  using `backend` subpackages must migrate.

## ADR 003: Synchronous Internal Events

- **Status:** Accepted
- **Decision:** A small in-process event bus in `pybi.core.events` communicates
  ETL completion to interested modules. ETL publishes output tables; the
  default dashboard binder registers or refreshes them.
- **Consequence:** ETL does not import dashboard code. Handlers run synchronously
  and their errors propagate to the publisher. This is not a durable or
  cross-process message queue.

## ADR 004: Configuration and Shared Filters

- **Status:** Accepted
- **Decision:** `pybi.config.Settings` centralizes existing environment-backed
  paths, JWT settings, and DuckDB resource limits. A production deployment must
  provide a strong JWT secret. `DATABASE_URL` and `REDIS_URL` are accepted but
  do not yet select active storage/cache backends.
- **Decision:** Dashboard `FilterContext` owns cross-filter state; report
  visuals consume it. SQL filter clause formatting is shared in
  `pybi.core.filtering` to avoid a semantic-to-dashboard import cycle.
- **Consequence:** Report query construction remains visual-specific, while
  filter state and SQL clause behavior are not duplicated.
