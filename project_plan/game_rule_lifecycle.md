# TCG Rules Lifecycle Overview

This document defines the **Rules Lifecycle** — a versioned tracking model for rulebooks and cards across any TCG. By maintaining a complete history of rule evolution, we enable an agentic RAG-based system that simplifies card lookups, rule lookups, and performs authoritative rulings on any tracked game version.

## Why This Matters

The Game Rules Lifecycle ensures every ruling is traceable to the exact ruleset in effect at the time it was made. Judges, players, and the system can confidently know which rules applied during any moment — enabling transparent, auditable decisions that stand up to scrutiny.

## Table of Contents

- [1. Versioned Game Mechanics](#1-versioned-game-mechanics)
- [2. Golden Rules](#2-golden-rules)
- [3. Formats](#3-formats)
- [4. Ruling Snapshots](#4-ruling-snapshots)

### See Also:

- [`storage_schema.md`](storage_schema.md) — Database tables and vector collections
- [`agent_retrieval_logic.md`](agent_retrieval_logic.md) — How the agent resolves rulesets and retrieves content
## 1. Versioning Game Mechanics

This system handles gameplay mechanics that evolve over time through versioning. Mechanics are defined in two places: the rulebook and individual cards, each with its own independent versioning lifecycle.

| Document | Rulebook | Card |
|----------|----------|------|
| **Scope** | The entire game's rules | A card's independent rule |
| **Size** | Large, hierarchical document | Small, dense record |
| **Versioning** | v1.0 → v1.2 → v2.0 | v1.0 → v2.0 |
| **Lifecycle independence** | Yes | Yes |
| **New version behavior** | Fully replaces previous | Fully replaces previous |
| **Version Corrections** | Errata, FAQs, clarifications | Errata, FAQs, clarifications |
| **Golden rules** | Core rules only (rulebook) - govern conflicts with card abilities | N/A |

### Versioning Structure

Both rulebooks and cards are versioned documents with identical lifecycle behavior. Each document belongs to a specific game and maintains its identity within that game, while versions evolve independently per document.

```
Game
 ├── game_id
 ├── game_name
 │
 └── DOCUMENT (belongs to a specific game, maintains identity within that game)
     │
     ├── document_id       e.g. "riftbound-core-rules", "shadowblade"
     ├── document_type     "rulebook" | "card"
     │
     └── VERSIONS  (one-to-many, independent per document)
           │
           ├── version_id          unique per version
           ├── version_label       human-readable, e.g. "1.2", "Spiritforged Edition"
           ├── content             full document text (Markdown)
           ├── is_standard         marks this version as the standard/current version (True/False)
           ├── effective_date      when this version became effective
           │
           └─── ASSOCIATED CORRECTIONS  (tied to this version, no independent status)
                 ├── errata
                 ├── faqs
                 └── clarifications

```

### Version Rules

- **Immutability**: Individual versions are immutable once created — they cannot be modified after publication, except for the `is_standard` field
- **Version Changes**: If changes need to be made to a version before the next version is ready for publishing, that will be tracked as a `correction`

- **Historical preservation**: All versions remain available for historical ruling reconstruction
- **Independent lifecycles**: Rulebook and card version lifecycles are fully independent of each other, but both must specify the same `game_id`
- **Standard version tracking**: Each game has exactly one `standard_version` per document type — this is the most recent version marked with `is_standard: true`. When a new version is published, `is_standard` is set to `false` on the previous standard version and `true` on the new version.

### Version Corrections

Version corrections (errata, FAQs, clarifications) are tied to a specific version of a document and have no independent lifecycle. They exist entirely within the context of the version they target.

### Correction Subtypes

| Subtype | Purpose |
|---------|---------|
| errata | Corrects specific text in the targeted version |
| clarification | Interpretive guidance without changing text |
| faq | Q&A format explaining design intent |

> Subtype affects citation formatting only. No effect on retrieval, precedence, or lifecycle logic.


## 2. Golden Rules

Golden rules are fundamental, overriding principles that dictate how to resolve conflicts between game components. They exist specifically to ensure game functionality when **card abilities contradict core rules**, offering a clear, consistent hierarchy for resolving disputes and enabling complex, situational interactions.

**Example Golden Rules**

- **001.** Card text supersedes rulebook text. Whenever a card's rule fundamentally contradicts the rulebook, the card's indication is what is true.
- **002.** "Can't overrides Can"

### How Golden Rules Are Designated and Used

Golden rules must be specified intentionally and stored in the version's metadata as `golden_rules`. The admin reviews extracted rule numbers and marks specific ones as golden rules during upload or review. This approach is intentionally explicit — the system does not attempt to infer which rules are golden. Different games will have different golden rules, and some games may have none at all.

**How the Agent Uses Golden Rules:**
For games that designate golden rules, they are injected into the agent's context on every ruling unconditionally. They are not retrieved via semantic search; they are fetched directly by the `is_golden_rule: true` metadata tag and placed at the top of the context before any other content.

This ensures:
- The agent always reasons with universal principles present when golden rules exist
- No ruling is formed without awareness of applicable golden rules

**Golden Rules Are Version-Specific:**
Golden rule designations belong to a specific rulebook version. When a new rulebook version is published, the admin re-designates golden rules for the new version. The agent always uses the golden rule designations from the version specified for a given ruling.

If no golden rules are designated for a rulebook version, the agent skips the golden rule injection step. Golden rules are optional — the system does not require them to function.

## 3. Formats

A **Format** is a named snapshot that pins specific versions of documents (rulebooks and cards) together to define a complete, reproducible ruleset for a particular play environment — such as a tournament format, legacy format, or limited-time event format.

#### Format Structure

```
Format
 ├── format_id              unique identifier, e.g. "standard-2024", "legacy"
 ├── format_name            human-readable name
 ├── version_pins           list of pinned versions by version_id
 │   ├── rulebook_version   version_id of the rulebook
 │   └── card_versions      list of version_ids for cards
 └── created_at             timestamp of format creation

```

#### Format Flexibility

A format can reference any rulebook version (existing or newly created) and any card version. This allows users to create custom formats with unique combinations of rules and cards. When creating a new rulebook version, it becomes available for pinning immediately — there is no draft/publish workflow that affects format compatibility.

#### Format Independence from Versioning

Formats are **separate entities** from the versioning model. They do not:
- Modify version properties (like `is_standard`, `effective_date`, or content)
- Introduce new status fields or document types
- Affect how documents are stored or indexed

A format is simply a label that simplifies card lookups, rule lookups, and performs authoritative rulings on formats specified versions. 


## 4. Ruling Snapshots

Every ruling delivered by the agent is recorded as an immutable snapshot to ensure that a complete record of exactly what was used when a ruling was made. This is important to ensure rulings are fully auditable and trackable. 

### Snapshot Structure

A ruling snapshot captures:
- **Ruling content**: The query, ruling text, and confidence level
- **Ruleset context**: Format ID, rulebook version ID and label, golden rules snapshot, card versions referenced, and version correction IDs

> Snapshots are never modified. If the same question is asked after a new version is published, a new snapshot is created under the new ruleset. The old snapshot is unchanged and remains fully queryable.

---

End of Game Rules Lifecycle Specification — v5.0