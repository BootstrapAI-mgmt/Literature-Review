# State Reconciliation - n8n Builder Prompt (Minimal)

**Workflow 6:** Verify documentation status matches repository state. 17 nodes total.

## Node List (Build Exactly)

| # | Type | Name |
|---|------|------|
| 1 | Schedule Trigger | Daily Reconciliation |
| 2 | Webhook | Manual Trigger |
| 3 | Merge | Start (Mode: Append, Include Unpaired: ✅) |
| 4 | Code | Workflow Configuration |
| 5 | HTTP Request | Fetch Matrix |
| 6 | HTTP Request | List Task Cards |
| 7 | Code | Filter and Group Cards |
| 8 | Split In Batches | Process Each Directory |
| 9 | HTTP Request | Fetch Directory Contents |
| 10 | Code | Extract Status from Cards |
| 11 | Code | Aggregate All Directories |
| 12 | HTTP Request | Fetch Current Indexes |
| 13 | Code | Find Mismatches |
| 14 | If | Has Mismatches? |
| 15 | AI Agent | Generate Corrections |
| 16 | Code | Log In Sync |
| 17 | HTTP Request | Send to Distributor |

## Key Connections

```
1,2 → 3 → 4 → 5 → 6 → 7 → 8 ⟲ 9 → 10 (loop)
                              ↓
                         11 → 12 → 13 → 14
                                         ├─ true → 15 → 17
                                         └─ false → 16
```

## Node 4 Config (Workflow Configuration)
```javascript
return {
  mismatch_threshold_percent: 5,
  status_complete_keywords: ['complete', 'done', '✅'],
  target_indexes: ['task-cards/README.md']
};
```

## Node 15 (AI Agent)
- Model: Gemini 2.5 Flash
- Output Parser: JSON Output Parser (attached)
- System: "Generate correction tasks for doc mismatches. Output JSON: {update_list_id, source, tasks[]}"

## URLs
- List Task Cards: `api.github.com/.../git/trees/main?recursive=1`
- Fetch Contents: `api.github.com/.../contents/{{ $json.replace(/\/$/, '') }}` (strip trailing slash!)
- Distributor: `gitlitreview.app.n8n.cloud/webhook/task-distributor`

## Headers (all GitHub requests)
- Authorization: `Bearer YOUR_PAT`
- Accept: `application/vnd.github.v3+json`
