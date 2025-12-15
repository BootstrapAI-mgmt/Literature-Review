# Staleness Review - n8n Builder Prompt

Workflow 5: Weekly documentation staleness check using AI assessment.

## Nodes (22 total)

1. **SCHEDULE TRIGGER** "Weekly Review" - Weekly Sunday 2 AM

2. **WEBHOOK** "Manual Trigger" - Path: /staleness-review

3. **MERGE** "Start Review" - Merge By Position

4. **HTTP REQUEST** "Fetch Matrix" - GET https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/docs/documentation_matrix.json

5. **CODE** "Get Domains" - Extract domains needing review by interval

6. **SPLIT IN BATCHES** "Process Each" - Batch Size: 1

7. **HTTP REQUEST** "Get Last Activity" - GET GitHub commits API with path param

8. **CODE** "Calculate Inactivity" - Days since last commit vs review_interval_days

9. **IF** "Needs Review?" - days_inactive >= review_interval_days

10. **HTTP REQUEST** "Fetch Recent Changes" - GET commits since last_activity

11. **CODE** "Filter Changes" - Exclude test/ci/chore commits

12. **IF** "Has Changes?" - relevant_changes.length > 0

13. **CODE** "Prep Doc Fetch" - List docs to fetch (limit 3)

14. **HTTP REQUEST** "Get Doc Content" - GET raw.githubusercontent.com/.../{current_doc}

15. **CODE** "Aggregate Docs" - Combine contents (truncate 2000 chars each)

16. **AI AGENT** "Staleness Assessment" - Gemini 2.5 Flash
    - System: "Documentation Staleness Reviewer. Output JSON with staleness_score (0-1), findings[], recommended_action, update_tasks[]"
    - User: Domain info, changes, doc contents

17. **CODE** "Parse Assessment" - Extract JSON, normalize score 0-1

18. **SWITCH** "Route By Score"
    - ≥0.7 with tasks: Auto Update → Distributor
    - ≥0.5: Manual Review → Create Issue
    - ≥0.3: Create Issue
    - else: Log Healthy

19. **HTTP REQUEST** "Send to Distributor" - POST /webhook/task-distributor with tasks

20. **HTTP REQUEST** "Create Issue" - POST GitHub issues API with findings

21. **CODE** "Log Healthy" - Record healthy domains

22. **MERGE** "Collect Results" → **CODE** "Generate Digest"

## Key Expressions
- Filter: `ignorePatterns = [/^test/i, /^ci/i, /^chore/i]`
- Score thresholds: 0.7=auto, 0.5=manual, 0.3=issue
- Auth: Header Auth "GitHub API Token"
