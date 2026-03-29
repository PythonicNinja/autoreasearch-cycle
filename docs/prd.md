# PRD: Generic Autonomic Optimization Engine (Windowed Autoresearch Pattern)

Archived note: this document captures the earlier broad-engine direction. The current repo scope is much smaller and centered on `examples/blogui/`.

## 1. Summary

We want to build a generic optimization engine that implements the autoresearch pattern in a domain-agnostic way. The core abstraction:

- There is a Policy describing how a system behaves.
- An AI Optimizer is allowed to propose changes to the Policy within strict constraints.
- The system evaluates each Policy in a fixed Evaluation Window.
- The system measures a primary Objective Metric plus optional constraints.
- The engine logs Runs and uses their history to drive further optimization.

This PRD specifies a generic engine and contracts that are independent of any specific domain. Domain-specific behavior is implemented via plugins and adapters on top of this core.

## 2. Goals and Non-Goals

### 2.1 Goals

- Define a generic pattern for iterative, agent-driven optimization:
  - single logical Policy object to modify per optimization scope
  - fixed Evaluation Windows, including time, traffic, or sample based windows
  - single primary Objective Metric with optional constraint metrics
- Provide an engine that:
  - can be applied to multiple domains without changing core logic
  - supports pluggable Domain Adapters
  - supports pluggable Optimizers such as LLMs, heuristics, or scripts
- Provide a simple, uniform logging and introspection model for Policies, Experiments, Runs, and Metrics

### 2.2 Non-Goals (v1)

- No domain-specific business logic in the core
- No full analytics or BI product
- No universal statistical testing framework

## 3. Core Concepts

1. **Policy**
   A structured configuration object that controls some aspect of a system's behavior.

   Requirements:
   - serializable
   - validated against a Policy Schema
   - versioned and immutable once created

2. **Policy Schema**
   A machine-readable contract specifying:
   - fields, types, allowed ranges, and enums
   - invariants and constraints

3. **Experiment**
   An optimization attempt within a domain or scope. It defines:
   - a baseline policy
   - how Evaluation Windows are configured
   - the primary Objective Metric and optional constraint metrics

4. **Evaluation Window**
   A fixed evaluation budget for one Policy deployment. It can be defined by:
   - time
   - count of events or samples
   - a custom stop condition exposed by the Domain Adapter

5. **Run**
   A single deployment of a specific Policy within a specific Evaluation Window.

6. **Objective Metric and Constraints**
   - primary metric: scalar value to maximize or minimize
   - constraint metrics: guardrails such as error rate, latency, or safety score

7. **Optimizer**
   A component that proposes candidate Policies using:
   - Policy Schema
   - baseline policy
   - run history and metrics
   - optimization goal

8. **Domain Adapter**
   A plugin that connects the generic engine to a specific domain. It knows how to:
   - apply a Policy
   - determine when a window completes
   - aggregate and submit metrics

## 4. Generic User Stories

### 4.1 Product / Owner

- I can define a domain scope with a Policy Schema, objective metric, and constraints.
- I can start and stop Experiments without knowing domain internals.
- I can inspect tried Policies, run results, and the current baseline.

### 4.2 Developer / Domain Owner

- I can implement a Domain Adapter for my system.
- I can keep domain logic outside the engine.
- I can roll back to previous Policy versions.

### 4.3 Optimizer Integrator

- I can plug in different Optimizers without changing domain code.
- I can constrain what an Optimizer can change via the Policy Schema.
- I can inspect proposal history and resulting metrics.

## 5. Functional Requirements

### 5.1 Policy Management

- The engine must support Policy create, read, and list operations.
- Policies are immutable after creation.
- Policies must be validated against a versioned Policy Schema.

### 5.2 Experiments and Runs

- Experiments include:
  - `experiment_id`
  - `domain_id`
  - `baseline_policy_id`
  - `status`
  - evaluation window configuration
  - objective metric definition
  - optional constraints
- Runs include:
  - `run_id`
  - `experiment_id`
  - `policy_id`
  - `window_config`
  - `start_time`
  - `end_time`
  - `status`
  - primary metric result
  - constraint metrics
  - domain metadata

### 5.3 Evaluation Windows

- v1 must support:
  - time-based windows
  - sample-based windows
- The engine must provide Domain Adapters with window configuration.
- The engine must guard against never-ending windows and duplicate metric submissions.

### 5.4 Optimizer API

**Input to Optimizer**

- domain ID and Policy Schema
- baseline Policy
- recent Run history
- objective definition and direction
- optional constraints

**Output from Optimizer**

- candidate Policy content
- optional metadata or rationale

The engine must validate optimizer outputs using schema validation and optional domain validation hooks.

### 5.5 Domain Adapter API

Adapters are responsible for:

- providing Policy Schema and metric definitions
- applying Policies for each Run
- detecting window completion
- gathering metrics
- submitting metrics back to the engine

### 5.6 Logging and Introspection

The engine must log Runs in a tabular, domain-agnostic format and provide APIs to:

- list experiments and runs by domain or status
- retrieve history for a domain or experiment
- export logs for offline analysis

## 6. Non-Functional Requirements

- Domain isolation
- Safety through schema and domain validation
- Extensibility for new adapters and optimizers
- Auditability of policy changes, proposals, and run results

## 7. High-Level Architecture

### 7.1 Components

1. **Core Engine**
   - manages Policies, Experiments, and Runs
   - implements the optimization loop

2. **Domain Adapter Registry**
   - tracks registered domains
   - provides schema, metrics, and validation hooks

3. **Optimizer Registry**
   - tracks available optimizer implementations

4. **Storage**
   - versioned Policy store
   - Experiment and Run store
   - optional external metrics integration later

5. **Control Plane API / Minimal UI**
   - APIs for defining domains, creating Experiments, managing baselines, and inspecting Runs

### 7.2 Generic Experiment Flow

1. A user creates an Experiment for a domain.
2. The engine invokes an Optimizer with schema, baseline, and recent history.
3. The engine validates and stores the candidate Policy.
4. The engine starts a Run and passes the Policy plus window config to the Domain Adapter.
5. The Domain Adapter applies the Policy and returns aggregated metrics on completion.
6. The engine closes the Run and persists metrics.
7. A human or strategy decides whether to continue, stop, or promote a new baseline.

## 8. Risks and Open Questions

- metric quality and drift
- conflicting objectives
- safety and compliance
- unsafe optimizer behavior

## 9. Milestones

1. **M1: Core Engine MVP**
   - Policy, Experiment, and Run models
   - Policy Schema support and validation
   - Evaluation Window abstraction
   - logging and inspection APIs

2. **M2: Reference Domain Adapter**
   - synthetic or sandbox domain
   - end-to-end run from proposal to metrics

3. **M3: Reference Optimizer**
   - random or rule-based optimizer
   - optional LLM-based optimizer later

4. **M4: Extensibility and Hardening**
   - adapter documentation
   - rollback and safety checks
   - stable external APIs
