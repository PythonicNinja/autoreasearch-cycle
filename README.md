# autoreasearch-cycle

# PRD: Generic Autonomic Optimization Engine (Windowed Autoresearch Pattern)

## 1. Summary

We want to build a **generic optimization engine** that implements the “autoresearch” pattern in a domain‑agnostic way. The core abstraction:

- There is a **Policy** describing how a system behaves.
- An AI **Optimizer** is allowed to propose changes to the Policy within strict constraints.
- The system evaluates each Policy in a fixed **Evaluation Window**.
- The system measures a primary **Objective Metric** (plus optional constraints).
- The engine logs **Runs** and uses their history to drive further optimization.

This PRD specifies a generic engine and contracts (interfaces, schemas, lifecycle) that are independent of any specific domain (UI, pricing, infra, etc.). Domain‑specific behavior is implemented via plugins/adapters on top of this core.

## 2. Goals & Non‑Goals

### 2.1 Goals

- Define a **generic pattern** for iterative, agent‑driven optimization:
  - Single logical Policy object to modify per optimization scope.
  - Fixed Evaluation Windows (time/traffic/sample‑based).
  - Single primary Objective Metric with optional constraint metrics.
- Provide an engine that:
  - Can be applied to multiple domains without changing core logic.
  - Supports pluggable **Domain Adapters**.
  - Supports pluggable **Optimizers** (LLMs, heuristics, scripts).
- Provide a simple, uniform **logging and introspection model**:
  - Policies, Experiments, Runs, Metrics.

### 2.2 Non‑Goals (v1)

- No domain‑specific business logic in the core (no UI, pricing, infra rules).
- No full analytics/BI product (only minimal inspection APIs or basic views).
- No attempt at universal statistical testing (domains can add their own).

## 3. Core Concepts (Domain‑Agnostic)

1. **Policy**  
   A structured configuration object that controls some aspect of a system’s behavior.  
   Examples (not baked into the engine): UI layout config, pricing rules, infra config, agent routing strategy.

   Requirements:
   - Serializable (JSON/YAML/text).
   - Validated against a **Policy Schema**.
   - Versioned and immutable once created.

2. **Policy Schema**  
   A machine‑readable contract specifying:
   - Fields, types, allowed ranges/enums.
   - Invariants and constraints (validation rules).
   The schema is provided by the Domain Adapter and enforced by the engine.

3. **Experiment**  
   An optimization attempt within a domain/scope. It defines:
   - A **baseline policy**.
   - How **Evaluation Windows** are configured.
   - The primary **Objective Metric** and optional constraint metrics.
   Experiments can span multiple policy candidates over time.

4. **Evaluation Window**  
   A fixed evaluation budget for one Policy deployment. Can be defined by:
   - Time (e.g., 1 hour, 24 hours).
   - Count of events/samples (e.g., 10,000 requests).
   - Custom stop condition exposed by the Domain Adapter.

5. **Run**  
   A single deployment of a specific Policy within a specific Evaluation Window. It records:
   - Policy ID.
   - Window configuration.
   - Measured metrics.
   - Context / metadata.

6. **Objective Metric & Constraints**  
   - **Primary metric**: scalar value to maximize/minimize (e.g., success rate, throughput, profit proxy).
   - **Constraint metrics**: used as guardrails (e.g., error rate, latency, safety score).

7. **Optimizer**  
   A component that proposes new candidate Policies, given:
   - Policy Schema.
   - Baseline policy.
   - History of Runs and metrics.
   - Optimization goal (maximize/minimize primary metric).

   Optimizers can be:
   - LLM‑based agents (e.g., Claude).
   - Algorithmic optimizers (Bayesian, evolutionary, heuristic).
   - Human‑in‑the‑loop assisted tools.

8. **Domain Adapter**  
   A plugin that connects the generic engine to a specific domain. It knows how to:
   - Apply a Policy to the actual system.
   - Monitor when an Evaluation Window is complete.
   - Aggregate metrics and return them to the engine.

## 4. Generic User Stories

### 4.1 Product / Owner

- I can define a **domain scope** with:
  - A Policy Schema.
  - An objective metric definition.
  - Constraints and safety rules.
- I can start and stop Experiments without knowing domain internals.
- I can inspect:
  - Which Policies were tried.
  - How each Policy performed (metrics per Run).
  - Which Policy is currently the baseline.

### 4.2 Developer / Domain Owner

- I can implement a **Domain Adapter** for my system that:
  - Translates a generic Policy into concrete configuration/runtime behavior.
  - Emits metrics for completed Evaluation Windows.
- I can keep my domain logic outside the engine and update it independently.
- I can easily roll back to any previous Policy version.

### 4.3 Optimizer Integrator

- I can plug in different Optimizers (LLM, algorithmic) without changing domain code.
- I can tightly **constrain** what an Optimizer can change via the Policy Schema.
- I can see the full history of Optimization proposals and resulting metrics.

## 5. Functional Requirements

### 5.1 Policy Management

- The engine must support CRUD operations for Policies:
  - Create Policy from content + schema.
  - Read Policy by ID.
  - List Policies by domain/scope.
- Policies are:
  - Immutable after creation (new Policy = new version).
  - Validated against a Policy Schema before acceptance.
- Policy Schema:
  - Is defined per domain/scope by the Domain Adapter.
  - Is versioned and may evolve over time.
  - Is referenced from Policies via `schema_version`.

### 5.2 Experiments & Runs

- Experiments:
  - Have: `experiment_id`, `domain_id`, `baseline_policy_id`, `status`, `created_at`, etc.
  - Include configuration of:
    - Evaluation Window type (time‑based, count‑based, custom).
    - Objective Metric definition (name, direction: maximize/minimize).
    - Constraint metrics definitions (names, thresholds if any).
- Runs:
  - Have: `run_id`, `experiment_id`, `policy_id`, `window_config`, `start_time`, `end_time`, `status`.
  - Store:
    - Primary metric result (scalar).
    - Constraint metrics (scalars).
    - Domain metadata (opaque JSON).
- The engine must support:
  - Scheduling Runs (for candidate Policies).
  - Tracking their lifecycle (scheduled → running → completed/failed).
  - Logging results in a uniform structure.

### 5.3 Evaluation Windows

- The engine must support at least:
  - **Time‑based windows**:
    - Start at `t0`, end at `t0 + duration`.
  - **Sample‑based windows**:
    - End after N samples/events reported by Domain Adapter.
- The engine must provide Domain Adapters with:
  - Window configuration (for instrumenting metrics in the domain).
  - A way to signal window completion and submit aggregated metrics.
- The engine must guard against:
  - Windows that never complete (timeouts).
  - Duplicate metric submissions.

### 5.4 Optimizer API

- The engine must provide a generic Optimizer interface:

  **Input to Optimizer:**
  - Domain ID and Policy Schema.
  - Baseline Policy.
  - A slice of recent Runs (configurable).
  - Objective Metric definition and direction.
  - Optional constraints (thresholds).

  **Output from Optimizer:**
  - Candidate Policy content (must validate against schema).
  - Optional metadata/rationale (free‑form text or JSON).

- The engine must validate all Optimizer outputs:
  - Schema validation.
  - Domain‑specific validation (via Domain Adapter hook).
- The engine must handle:
  - Approving or rejecting candidate Policies.
  - Logging Optimizer proposals and decisions.

### 5.5 Domain Adapter API

- The engine must expose a contract Domain Adapters implement:

  **Adapter responsibilities:**
  - Provide:
    - Policy Schema (for validation and editing).
    - Objective & constraint metrics definitions (names, units).
  - For each Run:
    - `apply_policy(policy, window_config)` – deploy behavior.
    - `observe_window(run_id)` or callback mechanism to:
      - detect when the window completes,
      - gather metrics,
      - submit metrics back to the engine.

- Adapters are responsible for:
  - Safely applying Policies to their systems (e.g., canarying, rollbacks).
  - Ensuring metric correctness for each window.

### 5.6 Logging and Introspection

- The engine must log Runs in a **tabular, domain‑agnostic format**, e.g.:

  - `run_id`, `experiment_id`, `domain_id`, `policy_id`,  
    `primary_metric_value`, `primary_metric_name`,  
    `constraints_json`, `window_start`, `window_end`,  
    `optimizer_id`, `meta_json`.

- It must provide APIs to:
  - List experiments and Runs by domain and status.
  - Retrieve full history for a given domain or experiment.
  - Export logs (CSV/Parquet/JSON) for offline analysis.

## 6. Non‑Functional Requirements

- **Domain isolation**:  
  Experiments in different domains must not interfere with each other.

- **Safety**:
  - Policies must be validated via schemas and domain checks.
  - The engine must support explicit rollback to a previous baseline Policy.

- **Extensibility**:
  - Adding a new domain should require only:
    - registering a new Domain Adapter,
    - defining its Policy Schema and metrics.
  - Adding a new Optimizer should not require core changes.

- **Auditability**:
  - All Policy changes, Optimizer proposals, and Run results must be traceable.
  - It should be easy to answer: “Why is this Policy the current baseline?”

## 7. High‑Level Architecture

### 7.1 Components

1. **Core Engine**
   - Manages Policies, Experiments, Runs.
   - Implements the generic optimization loop.

2. **Domain Adapter Registry**
   - Catalog of registered domains/scopes.
   - For each domain:
     - Policy Schema provider.
     - Metrics and validation hooks.
     - Methods to apply Policies and collect metrics.

3. **Optimizer Registry**
   - Catalog of Optimizers (LLM‑based, algorithmic, manual).
   - Engine calls Optimizer with a well‑defined context to get candidate Policies.

4. **Storage**
   - Policy Store (versioned).
   - Experiment & Run Store (relational/tabular).
   - Optionally, external metrics/TSDB integration.

5. **Control Plane API / Minimal UI**
   - APIs for:
     - defining domains,
     - creating Experiments,
     - managing baseline Policies,
     - inspecting Runs and metrics.
   - Simple UI is optional but recommended for human operators.

### 7.2 Generic Experiment Flow

1. A user (or schedule) creates an Experiment for domain `D`:
   - Select baseline Policy.
   - Configure Evaluation Window.
   - Specify Objective and constraints.

2. Engine invokes an Optimizer for domain `D`:
   - Provides Policy Schema, baseline, and recent history.
   - Receives candidate Policy.

3. Engine validates and stores candidate Policy.

4. Engine schedules and starts a Run:
   - Passes Policy + window config to Domain Adapter.

5. Domain Adapter:
   - Applies Policy in the real system.
   - Tracks metrics according to window config.
   - On window completion, submits metrics to engine.

6. Engine:
   - Closes Run, logs metrics.
   - Updates Experiment status.
   - Optionally triggers another optimization step (next candidate) based on configured strategy.

7. Human or auto‑strategy:
   - May promote candidate Policy to new baseline.
   - May end the Experiment or continue.

## 8. Risks & Open Questions (Generic)

- **Metric quality and drift**:
  - The engine treats metrics as opaque scalars; domain owners must ensure they are meaningful and stable.

- **Conflicting objectives**:
  - The single primary metric pattern is a simplification; multi‑objective trade‑offs must be encoded into that metric or handled externally.

- **Safety & compliance**:
  - Domain owners must specify constraints; the engine can enforce them but cannot infer domain rules.

- **Optimizer behavior**:
  - LLM‑based Optimizers may propose invalid or unsafe policies; schema + domain validation is required, but additional guardrails may be needed over time.

## 9. Milestones (Generic)

1. **M1: Core Engine MVP**
   - Policy, Experiment, Run models.
   - Policy Schema support and validation.
   - Evaluation Window abstraction (time + count).
   - Basic logging & inspection APIs.

2. **M2: Reference Domain Adapter**
   - Implement a simple synthetic or sandbox domain (e.g., optimizing a mathematical function or simulation) to validate the pattern.
   - End‑to‑end run from Optimizer proposal to metric logging.

3. **M3: Reference Optimizer**
   - Implement at least:
     - Rule‑based / random baseline Optimizer.
     - Optional LLM‑based Optimizer via generic API.

4. **M4: Extensibility & Hardening**
   - Document how to add new domains.
   - Add safety checks, rollbacks, and audit trails.
   - Stabilize APIs for external adopters.
