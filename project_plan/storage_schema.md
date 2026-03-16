# Storage Schema Specification

This document describes the database tables and vector collections required to implement the RuleBook lifecycle model. It is derived from the core concepts defined in [`game_rule_lifecycle.md`](game_rule_lifecycle.md).

## Overview

The storage architecture supports:
- **Immutable versioning**: All published versions are preserved, never deleted
- **Temporal queries**: Historical rulings can be reconstructed by querying as-of specific dates
- **Multi-collection retrieval**: Golden rules, rulebook content, card content, and version corrections live in separate vector collections for optimized query patterns

## Database Tables

### `games`
Stores game metadata. Each game is isolated from others via `game_id`.

| Column | Type | Description |
|--------|------|-------------|
| `game_id` | string (PK) | Unique identifier for the game |
| `title` | string | Human-readable game name |
| `created_at` | timestamp | When the game was registered in the system |

---

### `documents`
Stores stable document identities. A document represents either a rulebook or a card, and maintains its identity across all versions.

| Column | Type | Description |
|--------|------|-------------|
| `document_id` | string (PK) | Stable identifier (e.g., "riftbound-core-rules", "shadowblade") |
| `document_type` | enum | "rulebook" \| "card" |
| `game_id` | string (FK → games.game_id) | Parent game |
| `title` | string | Display title (for rulebooks) |
| `card_name` | string | Display name (for cards) |
| `set_id` | string | Organizational label (cards only; no lifecycle impact) |

---

### `document_versions`
Stores all versions of documents. This is the core versioning table where lifecycle transitions occur.

| Column | Type | Description |
|--------|------|-------------|
| `version_id` | string (PK) | Unique identifier for this version |
| `document_id` | string (FK → documents.document_id) | Parent document |
| `version_label` | string | Human-readable label (e.g., "1.2", "Spiritforged Edition") |
| `content` | text | Full document text in Markdown |
| `effective_date` | timestamp | When this version became active |
| `status` | enum | "draft" \| "active" \| "superseded" |
| `superseded_by` | string (FK → version_id, nullable) | ID of the version that replaced this one |
| `metadata` | JSONB | Version-specific metadata (see below) |

**Metadata Structure:**

For **rulebooks**:
```json
{
  "sections": ["Section Title 1", "Section Title 2"],
  "rule_numbers": {"735.1.c": "Timing — Deflect"},
  "golden_rule_numbers": ["053", "053.1", "054"]
}
```

For **cards**:
```json
{
  "card_type": "Creature — Rogue",
  "cost": 3,
  "keywords": ["Deathtouch"],
  "stats": "2/1"
}
```

---

### `version_corrections`
Stores corrections and clarifications tied to specific document versions. Entries have no independent status—they are queryable only when their targeted version is active.

| Column | Type | Description |
|--------|------|-------------|
| `correction_id` | string (PK) | Unique identifier for this entry |
| `game_id` | string (FK → games.game_id) | Parent game |
| `subtype` | enum | "errata" \| "clarification" \| "faq" |
| `title` | string | Human-readable title |
| `content` | text | Full correction/clarification text in Markdown |
| `targets_document_id` | string (FK → documents.document_id) | Document being corrected |
| `targets_version_id` | string (FK → document_versions.version_id) | Specific version being corrected (required) |
| `targets_section` | string (nullable) | Optional: specific section or rule number within the version |
| `priority` | integer | Higher values win when multiple entries target the same section |
| `source_document` | string | Source of this correction (e.g., "Spiritforged FAQ") |
| `effective_date` | timestamp | When this version correction became effective |

---

### `version_correction_sources`
Stores the original source documents for version corrections (e.g., uploaded FAQs, errata PDFs). Preserves raw content for re-parsing if needed.

| Column | Type | Description |
|--------|------|-------------|
| `source_id` | string (PK) | Unique identifier for this source |
| `game_id` | string (FK → games.game_id) | Parent game |
| `title` | string | Source document title (e.g., "Spiritforged FAQ") |
| `original_content` | text | Raw uploaded content, preserved for re-parsing |
| `uploaded_at` | timestamp | When the source was uploaded |

---

### `formats`
Stores named snapshots that pin specific rulebook versions to card pools. Formats define reproducible rulesets for tournaments, legacy formats, or events.

| Column | Type | Description |
|--------|------|-------------|
| `format_id` | string (PK) | Unique identifier for this format |
| `game_id` | string (FK → games.game_id) | Parent game |
| `title` | string | Human-readable format name (e.g., "Riftbound Standard — Spring 2025") |
| `rulebook_version_id` | string (FK → document_versions.version_id) | Pinned rulebook version |
| `card_pool` | array of strings | Array of set_ids whose cards are legal in this format |
| `effective_date` | timestamp | When this format became active |
| `status` | enum | "draft" \| "active" \| "retired" |

---

### `ruling_snapshots`
Stores immutable records of every ruling delivered by the agent. Each snapshot captures exactly what content was active when the ruling was made, enabling historical reconstruction.

| Column | Type | Description |
|--------|------|-------------|
| `snapshot_id` | string (PK) | Unique identifier for this ruling |
| `game_id` | string (FK → games.game_id) | Parent game |
| `query` | text | The original user question |
| `ruling_text` | text | The agent's generated ruling |
| `confidence` | enum | "low" \| "medium" \| "high" |
| `format_id` | string (nullable, FK → formats.format_id) | Format used for this ruling |
| `rulebook_version_id` | string (FK → document_versions.version_id) | Rulebook version active at time of ruling |
| `rulebook_version_label` | string | Human-readable rulebook version label |
| `golden_rules_snapshot` | text | Golden rules that were injected into this ruling's context |
| `card_versions_referenced` | JSONB | Array of card versions referenced in the ruling |
| `version_correction_ids` | array of strings | IDs of version corrections included in this ruling |
| `source` | enum | "discord" \| "ui" \| "api" |
| `discord_thread_id` | string (nullable) | Discord thread ID if source is discord |
| `requested_by` | string | User ID who requested the ruling |
| `delivered_at` | timestamp | When the ruling was delivered |

---

### `audit_log`
Stores every version transition and publish action for compliance and debugging.

| Column | Type | Description |
|--------|------|-------------|
| `audit_id` | string (PK) | Unique identifier for this audit entry |
| `action_type` | enum | "publish" \| "supersede" \| "retire" \| "update_metadata" |
| `entity_type` | enum | "document_version" \| "format" \| "golden_rule" |
| `entity_id` | string | ID of the entity affected |
| `previous_state` | JSONB | State before the action (if applicable) |
| `new_state` | JSONB | State after the action (if applicable) |
| `performed_by` | string | User or system that performed the action |
| `performed_at` | timestamp | When the action occurred |

---

### `discord_config`
Maps Discord servers to games, channels, and formats for automated ruling delivery.

| Column | Type | Description |
|--------|------|-------------|
| `config_id` | string (PK) | Unique identifier for this config |
| `discord_server_id` | string | Discord server ID |
| `game_id` | string (FK → games.game_id) | Game associated with this server |
| `rules_channel_id` | string | Discord channel ID for rule-related discussions |
| `formats` | JSONB | Array of format objects with channel mappings |

---

## Vector Collections

The system uses four separate vector collections to optimize retrieval patterns. Each chunk stores its `version_id`, enabling temporal filtering without deletion.

### Collection: `golden_rule_chunks`

**Source**: Rulebook chunks tagged with `is_golden_rule = true`

**Query-time filter**:
```
game_id + version_id = resolved_rulebook_version_id
AND is_golden_rule = true
```

**Chunk metadata example**:
```json
{
  "game_id": "riftbound",
  "version_id": "riftbound-core-rules-v1.2",
  "document_type": "rulebook",
  "is_golden_rule": true,
  "rule_number": "054",
  "section": "Can't beats Can",
  "breadcrumb": "Core Rules v1.2 > Golden Rules > 054"
}
```

---

### Collection: `rulebook_chunks`

**Source**: All rulebook chunks excluding golden rules

**Query-time filter**:
```
game_id + version_id = resolved_rulebook_version_id
```

---

### Collection: `card_chunks`

**Source**: Active card versions only

**Query-time filter**:
```
game_id + version_id IN (resolved_card_version_ids)
```

---

### Collection: `version_correction_chunks`

**Source**: All version correction entries

**Query-time filter**:
```
game_id + targets_version_id IN (resolved_rulebook_version_id + resolved_card_version_ids)
→ collection: version_correction_chunks
```

---

## Why Old Chunks Are Not Deleted

Every chunk stores its `version_id`. When a version is superseded:
1. The version transitions to "superseded" status in the database
2. Its chunks remain in the vector index but are excluded by the version filter
3. They are available for historical reconstruction when querying with an `as_of_date`

This approach:
- **Simplifies operations**: No need for re-indexing or chunk deletion jobs
- **Preserves history**: All versions remain queryable for temporal analysis
- **Maintains consistency**: The version filter is the single source of truth for what content is active

---

## Re-indexing Triggers

| Event | Action |
|-------|--------|
| New rulebook version published | Index all chunks; tag chunks for `golden_rule_numbers` with `is_golden_rule = true` |
| New card version published | Index card chunks with new `version_id` |
| New version correction created | Index correction chunks with `targets_version_id` |
| Version superseded | No action — version filter handles exclusion automatically |
| Golden rule numbers updated on draft | Re-tag affected chunks before version goes active |

---

## Infrastructure Requirements

### "Never Delete" Policy Enforcement

To support historical ruling reconstruction, the following must be enforced at the infrastructure level:

- **No cascade deletes** on `document_versions`, `version_correction_chunks`, or `ruling_snapshots` tables
- **No purge jobs** that remove superseded versions
- **Archival strategy**: Consider cold storage for very old data if retention requirements demand it, but never delete

### Indexing Strategy

- Use a vector database that supports:
  - Hybrid search (vector + metadata filtering)
  - Batch indexing operations
  - Version-aware chunking (each chunk must store its `version_id`)

---

End of Storage Schema Specification — v1.0
