# Rules

The `application_rules` condition schema and evaluator — the mechanical
pieces. `app/services/rule_engine_service.py` is the business-logic layer
that loads rules, builds the evaluation context, and orchestrates the
Critical → Required → Preference walk; nothing outside that service
imports this package.

- `schema.py` — `RuleCondition` (field/op/value, field allowlist enforced
  at validation time), `RuleDecision`
- `evaluator.py` — `matches(condition, context) -> bool`, one function per
  supported `op`, never `eval()`

## Rule

A condition can only reference a field in `ALLOWED_CONDITION_FIELDS`.
Reject anything else at write time (when a rule is created/updated via the
API), not at evaluation time — a malformed rule should never reach a job
the engine tries to evaluate it against.
