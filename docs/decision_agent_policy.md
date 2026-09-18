# Scribbly Decision Agent — V1 Decision Policy

## 1. Purpose

The Decision Agent is the final AI decision layer in the Scribbly Talent Acquisition Agent pipeline.

It receives the outputs of the Application Analyzer and Risk Assessment Agent and recommends one of three outcomes:

- `approve`
- `reject`
- `escalate`

The Decision Agent does **not** replace the human administrator. Its recommendation supports the Scribbly Review Center workflow.

## 2. Inputs

### Application Analyzer

- `overall_score`
- `summary`

### Risk Assessment Agent

- `risk_score`
- `risk_level`
- `toxicity_detected`
- `spam_detected`
- `suspicious_links`
- `ai_generated_detected`
- `explanation`

Writing quality and moderation risk are separate dimensions and must be considered separately.

# 3. APPROVE

Recommend `approve` when:

- No policy risk is detected, and
- `overall_score` is above **65**.

A writer with no detected moderation risk and an overall score above 65 demonstrates sufficient writing potential for the Scribbly writer program.

AI-generated content does not prevent approval because AI-assisted or AI-generated writing is allowed by Scribbly policy.

# 4. REJECT

Recommend `reject` under these conditions.

## Case 1 — Very Poor Writing Quality

- `overall_score < 20`

This applies even when no significant moderation risk is detected.

## Case 2 — Multiple Significant Policy Violations

Reject when:

- The writing score is strong, but
- Multiple significant policy violations or high-risk signals are detected.

Writing quality does not override serious or repeated policy violations.

## Case 3 — Moderate/Low Writing Quality + Extreme Risk

Reject when:

- `overall_score` is between **21 and 50**, and
- At least one detected policy violation represents an **extreme level of risk**.

# 5. ESCALATE

Recommend `escalate` when:

- `overall_score` is between **25 and 100**, and
- A policy violation or risk is detected,
- But the violation is minor, ambiguous, or insufficiently severe for automatic rejection.

The purpose of escalation is to allow a human administrator to inspect the original submission and the AI assessments before making the final decision.

# 6. Important Decision Principles

## Writing Quality vs. Risk

A high writing score does not mean that content is safe.

A low writing score does not automatically mean that content violates Scribbly policy.

The Decision Agent must consider both dimensions.

## AI-Generated Content

AI-generated writing is allowed on Scribbly.

Therefore:

- `ai_generated_detected = true` must not automatically cause rejection.
- AI detection is not itself a policy violation.
- Decisions must be based on writing quality and actual moderation risks.

## Human Review

`escalate` exists for cases where automatic decision-making is inappropriate.

The administrator should be able to inspect:

- writing quality,
- detected risks,
- risk severity,
- and the reason for escalation.

# 7. V1 Decision Philosophy

| Outcome | Meaning |
|---|---|
| `approve` | Applicant appears suitable for writer approval. |
| `reject` | Applicant does not meet the required quality/risk threshold. |
| `escalate` | Human administrator should review the case. |

The Decision Agent is a **recommendation agent**, not an autonomous authority.

# 8. Decision Contract

The Decision Agent should return structured data matching the `AgentDecision` model.

```json
{
    "recommendation": "approve | reject | escalate",
    "confidence": 0,
    "reasoning": "string"
}
```

### `recommendation`

Must be exactly one of:

- `approve`
- `reject`
- `escalate`

### `confidence`

An integer from `0` to `100`.

This represents the AI's confidence in its recommendation. It should not be interpreted as a probability that the applicant is objectively suitable.

### `reasoning`

A concise explanation of the factors that led to the recommendation.

The Decision Agent should explain its decision without exposing hidden chain-of-thought.

# 9. Future V2 Considerations

V1 intentionally keeps the decision model simple.

Future versions may introduce:

- explicit violation severity
- moderator action recommendations
- weighted risk categories
- more granular rejection criteria
- probationary approval
- historical applicant behavior
- writer trust scores

These should be introduced only after the V1 workflow has been tested and validated.
