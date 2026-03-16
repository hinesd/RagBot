# Agent Retrieval Logic Specification

This document describes how the Judge Agent resolves rulesets and retrieves content for answering player questions. It is derived from the core concepts defined in [`game_rule_lifecycle.md`](game_rule_lifecycle.md).

## Overview

The agent's retrieval process follows a deterministic, multi-step pattern:
1. **Resolve** the active ruleset based on query parameters
2. **Fetch** golden rules unconditionally (by filter, not semantic search)
3. **Search** rulebook, card, and version corrections via semantic search
4. **Merge and re-rank** results before passing to the answer generator

This ensures:
- Golden rules are always present in every ruling's context
- Version-specific content is correctly filtered
- Version corrections are applied where relevant

---

## Ruleset Resolution (per query)

The `resolve_ruleset` function determines exactly which content is active for a given query. It takes four optional parameters and returns a complete ruleset object.

### Function Signature

```javascript
function resolve_ruleset(
  game_id: string,
  format_id?: string | null,
  rulebook_version_id?: string | null,
  as_of_date?: Date | null
): {
  rulebook_version: string,
  card_versions: string[],
  golden_rules: Chunk[],
  temporary: TemporaryContent[]
}
```

### Resolution Logic

#### Case 1: Format Specified
When a format is explicitly provided (e.g., "Riftbound Standard — Spring 2025"):

```javascript
if (format_id specified):
  rulebook_version = format.rulebook_version_id
  card_pool        = cards where set_id IN format.card_pool
  card_versions    = most recent active version of each card in card_pool
```

**Behavior**: The format pins the rulebook to a specific version, but cards are resolved dynamically to their most recent active versions within the format's card pool.

---

#### Case 2: Specific Rulebook Version Specified
When a user explicitly requests a specific rulebook version (e.g., "How does this work in v1.2?"):

```javascript
elif rulebook_version_id specified:
  rulebook_version = specified version
  card_versions    = most recent active version of ALL cards in game
```

**Behavior**: The rulebook is pinned to the requested version, but all cards use their current active versions. This allows users to ask "what if" questions about past rulesets.

---

#### Case 3: Historical Date Specified
When an `as_of_date` is provided (e.g., "What was the ruling on this question last month?"):

```javascript
elif as_of_date specified:
  rulebook_version = rulebook version active on as_of_date
  card_versions    = card versions active on as_of_date
```

**Behavior**: Both rulebook and cards are resolved to their state at the specified historical date. This enables accurate historical ruling reconstruction.

---

#### Case 4: Default Mode (No Special Parameters)
When no version, format, or date is specified:

```javascript
else (default):
  rulebook_version = most recent active rulebook version
  card_versions    = most recent active version of ALL cards in game
```

**Behavior**: The agent uses the current live ruleset for all games. This is the default behavior for new queries.

---

## Retrieval Order on Every Ruling Query

The agent follows a strict three-step retrieval pattern to ensure consistency and correctness.

### STEP 1 — Fetch Golden Rules Unconditionally

Golden rules are **always** injected into the agent's context, regardless of the query content. They are fetched by metadata filter, not semantic search.

```javascript
// Collection: golden_rule_chunks
filter: {
  game_id: resolved.game_id,
  version_id: resolved.rulebook_version_id,
  is_golden_rule: true
}
→ injected into top of context on every query, no exceptions
```

**Why this matters**:
- A question about a specific card interaction will always be informed by universal principles like "Can't beats Can"
- No ruling can be formed without awareness of golden rules
- This prevents the agent from missing critical precedence rules due to semantic search limitations

---

### STEP 2 — Parallel Semantic Search Across Three Collections

Three separate vector searches run in parallel, each with version-specific filters:

```javascript
// Collection: rulebook_chunks
filter: {
  game_id: resolved.game_id,
  version_id: resolved.rulebook_version_id
}

// Collection: card_chunks
filter: {
  game_id: resolved.game_id,
  version_id: IN resolved.card_version_ids
}

// Collection: version_correction_chunks
filter: {
  game_id: resolved.game_id,
  targets_version_id: IN resolved.all_version_ids
}
```

**Key behaviors**:
- **Rulebook chunks**: Only content from the resolved rulebook version is returned
- **Card chunks**: Only active card versions within the resolved set are returned
- **Version correction chunks**: Corrections targeting any resolved version (rulebook or cards) are included

---

### STEP 3 — Merge and Re-rank Results

All semantic results are merged and re-ranked using a cross-encoder before being passed to the answer generator.

```javascript
// Merge all semantic results
all_candidates = golden_rules + rulebook_results + card_results + version_correction_results

// Re-rank with cross-encoder
scores = cross_encoder.score(all_candidates, query)

// Select top N
top_n = scores.topN()

// Pass to answer_generator alongside golden rules
answer_generator.generate(
  query=query,
  context=top_n + golden_rules
)
```

**Why re-ranking matters**:
- Different collections may return overlapping or conflicting content
- The cross-encoder ensures the most relevant chunks are prioritized
- Golden rules remain at the top of the context (not subject to re-ranking)

---

## Precedence in Conflict Resolution

When retrieved content contains conflicts, the `conflict_resolver` applies this order:

| Priority | Source | Behavior |
|----------|--------|----------|
| 1 | **Golden rules** | Always present; universal principles applied to every ruling |
| 2 | **Version corrections** | Corrects the base version; higher priority integer wins when multiple entries target the same section |
| 3 | **Rulebook** | Base rules for the resolved version |
| 4 | **Cards** | Card-specific rules within the rulebook context |

**Important**: Golden rules take precedence when there is a conflict—but they are not about overriding. They are universal principles that inform every ruling. The agent always reasons with them present.

---

## Version Defaulting Logic

### Default Mode (No Version Context)

```javascript
// If no version context provided, always default to most recent active:
rulebook_version = get_active_version(game_id, document_type="rulebook")
card_versions    = get_all_active_versions(game_id, document_type="card")
```

### Format Specified

```javascript
// If format specified:
rulebook_version = format.rulebook_version_id
card_versions    = get_active_versions_for_sets(game_id, format.card_pool)
```

### Historical Date Specified

```javascript
// If as_of_date specified:
rulebook_version = get_version_active_on_date(game_id, "rulebook", as_of_date)
card_versions    = get_versions_active_on_date(game_id, "card", as_of_date)
```

---

## Query Parameter Examples

### Example 1: Default Live Ruling
```javascript
resolve_ruleset(
  game_id="riftbound"
)
// → Current live ruleset for all cards
```

### Example 2: Format-Based Ruling
```javascript
resolve_ruleset(
  game_id="riftbound",
  format_id="riftbound-standard-spring-2025"
)
// → Rulebook v1.2 + active versions of cards in the standard pool
```

### Example 3: Historical Reconstruction
```javascript
resolve_ruleset(
  game_id="riftbound",
  as_of_date="2024-12-01"
)
// → Rulebook and card versions that were active on Dec 1, 2024
```

### Example 4: Specific Version Analysis
```javascript
resolve_ruleset(
  game_id="riftbound",
  rulebook_version_id="riftbound-core-rules-v1.2"
)
// → Rulebook v1.2 + current active versions of all cards
```

---

## Edge Cases and Behaviors

### Version Corrections Under a Format

When a format is active, version corrections are resolved against the format's pinned rulebook version:

```javascript
Version corrections retrieved = entries where:
  targets_version_id = format's rulebook_version_id
  OR targets_version_id IN (active versions of cards in format's card_pool)
```

**Important**: A format may include version corrections (errata, FAQs) that have since been superseded in the live ruleset—because the format is pinned to an older rulebook version where those version corrections were still active. This is correct and intentional: a format defines a specific ruleset at a point in time, including its corrections.

### Multiple Rulebooks Per Game

If a game has multiple rulebook documents (e.g., "Core Rules" and "Tournament Rules"), each rulebook is treated as its own document with its own version history. The format system can pin to a specific rulebook version for each context. No special handling is required—the existing model supports this naturally.

---

## Agent Context Structure

The final context passed to the answer generator has this structure:

```javascript
{
  // Golden rules (always at top, never re-ranked)
  golden_rules: [
    { rule_number: "054", text: "Can't beats Can..." },
    { rule_number: "053", text: "Cards refer to themselves..." }
  ],

  // Re-ranked semantic results
  context_chunks: [
    { source: "rulebook", chunk_id: "...", text: "..." },
    { source: "version_correction", chunk_id: "...", text: "...", priority: 10 },
    { source: "card", chunk_id: "...", text: "..." }
  ],

  // Ruleset metadata for citation
  ruleset_info: {
    game_id: "riftbound",
    rulebook_version: "riftbound-core-rules-v1.2",
    card_versions: ["shadowblade-v1", "falling-star-v2"],
    format_id: null,
    as_of_date: null
  }
}
```

---

End of Agent Retrieval Logic Specification — v1.0
