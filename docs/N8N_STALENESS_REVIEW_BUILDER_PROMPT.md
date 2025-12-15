# N8N AI Builder Prompt: Staleness Review Workflow

> **Instructions:** This is the 5th workflow in the Documentation Chain system. It adds proactive staleness detection to complement the existing event-driven workflows.

---

## 🏗️ Architecture Context

This workflow integrates with the existing chain:

```
Existing Chain:
  GitHub Webhook → Trigger → Distributor → Agent → Callback

New Addition:
  Schedule/Manual → Staleness Review → (findings) → Distributor
                                    → (issues) → GitHub Issues
```

---

## Pre-Setup Checklist

Before building this workflow:

1. [ ] Workflows 1-4 are already built and working
2. [ ] GitHub API credential configured (Header Auth with PAT)
3. [ ] Gemini API credential configured
4. [ ] `documentation_matrix.json` updated with `staleness_config` section

---

# WORKFLOW 5: Doc Chain - Staleness Review

**Create a new workflow named "Doc Chain - Staleness Review", then use this prompt:**

```
Build a workflow that periodically reviews documentation domains for staleness by comparing docs against recent repository changes.

CONTEXT: This is workflow 5 of 5 in a documentation auto-update system. It runs on a schedule (weekly), identifies which documentation domains haven't been updated recently, analyzes repository changes since their last activity, uses AI to assess whether docs are stale, and routes findings to either the existing Distributor (for auto-updates) or creates GitHub issues (for manual review).

BUILD THESE NODES:

1. SCHEDULE TRIGGER node named "Weekly Review"
   - Trigger Interval: Weeks
   - Interval: 1
   - Trigger at Hour: 2 (2 AM)
   - Trigger on Weekdays: Sunday

2. WEBHOOK node named "Manual Trigger"
   - Path: /staleness-review
   - Method: POST
   - Respond: Immediately
   - Purpose: Allow manual triggering for testing or on-demand reviews

3. MERGE node named "Start Review"
   - Mode: Merge By Position
   - Inputs: Connect both triggers (Weekly Review and Manual Trigger)

4. HTTP REQUEST node named "Fetch Matrix"
   - Method: GET
   - URL: https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/docs/documentation_matrix.json
   - Response Format: JSON

5. CODE node named "Get Domains To Review"
   - JavaScript:
   const matrix = $input.first().json;
   const config = matrix.staleness_config || { default_review_interval_days: 7 };
   const now = new Date();
   const dayOfWeek = now.toLocaleDateString('en-US', { weekday: 'lowercase' });
   
   const domains = [];
   for (const [domain, info] of Object.entries(matrix.owner_domains || {})) {
     // Handle both old format (array) and new format (object with config)
     const domainConfig = Array.isArray(info) 
       ? { documents: info, review_interval_days: config.default_review_interval_days }
       : info;
     
     // If staggering is enabled, only include domains scheduled for today
     // Otherwise include all domains (for weekly batch review)
     const staggerDay = domainConfig.stagger_day;
     if (config.schedule?.stagger_domains && staggerDay && staggerDay !== dayOfWeek) {
       continue;
     }
     
     domains.push({
       domain,
       documents: domainConfig.documents || [],
       review_interval_days: domainConfig.review_interval_days || config.default_review_interval_days || 7,
       priority: domainConfig.priority || 'medium',
       staleness_indicators: []
     });
   }
   
   // Add staleness_indicators from document entries
   for (const doc of matrix.documents || []) {
     const domainEntry = domains.find(d => d.domain === doc.owner);
     if (domainEntry && doc.staleness_indicators) {
       domainEntry.staleness_indicators.push(...doc.staleness_indicators);
     }
   }
   
   // Deduplicate indicators
   domains.forEach(d => {
     d.staleness_indicators = [...new Set(d.staleness_indicators)];
   });
   
   return domains.map(d => ({ json: d }));

6. SPLIT IN BATCHES node named "Process Each Domain"
   - Batch Size: 1
   - Purpose: Process domains one at a time to manage API rate limits

7. HTTP REQUEST node named "Get Last Activity"
   - Method: GET
   - URL: https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/commits
   - Query Parameters:
     - path: ={{ $json.documents[0] || 'docs/' }}
     - per_page: 1
   - Authentication: Predefined Credential Type
   - Credential Type: Header Auth
   - Credential: GitHub API Token
   - Headers:
     - Accept: application/vnd.github.v3+json

8. CODE node named "Calculate Inactivity"
   - JavaScript:
   const domain = $('Process Each Domain').first().json;
   const commits = $input.first().json;
   
   // Get last commit date (handle empty response)
   const lastCommit = Array.isArray(commits) && commits.length > 0 ? commits[0] : null;
   const lastActivity = lastCommit?.commit?.author?.date 
     ? new Date(lastCommit.commit.author.date)
     : new Date('2000-01-01');
   
   const now = new Date();
   const daysInactive = Math.floor((now - lastActivity) / (1000 * 60 * 60 * 24));
   
   const needsReview = daysInactive >= domain.review_interval_days;
   
   return {
     ...domain,
     last_activity: lastActivity.toISOString(),
     last_commit_sha: lastCommit?.sha || null,
     days_inactive: daysInactive,
     needs_review: needsReview
   };

9. IF node named "Needs Review?"
   - Condition: Use boolean expression
   - Expression: {{ $json.needs_review === true }}
   - Operator: equals
   - Compare to: true
   - On false: Connect to "Log Healthy" node

10. HTTP REQUEST node named "Fetch Recent Changes"
    - Method: GET
    - URL: https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/commits
    - Query Parameters:
      - since: ={{ $json.last_activity }}
      - per_page: 100
    - Authentication: Header Auth (GitHub API Token)
    - Headers:
      - Accept: application/vnd.github.v3+json

11. CODE node named "Filter Relevant Changes"
    - JavaScript:
    const domain = $('Calculate Inactivity').first().json;
    const commits = $input.first().json;
    
    // Patterns to ignore (test, CI, style changes, and automated n8n commits)
    const ignorePatterns = [
      /^\[n8n\]/i,    // ALL automated n8n commits
      /^test(\(|:)/i,
      /^ci(\(|:)/i,
      /^chore(\(|:)/i,
      /^style(\(|:)/i,
      /^docs(\(|:)/i  // We're checking FOR doc staleness, not FROM doc changes
    ];
    
    // Filter and extract relevant commits
    const relevantChanges = [];
    const relevantScripts = domain.staleness_indicators || [];
    
    for (const commit of (Array.isArray(commits) ? commits : [])) {
      const message = commit.commit?.message || '';
      const firstLine = message.split('\n')[0];
      
      // Skip ignored patterns
      if (ignorePatterns.some(p => p.test(firstLine))) {
        continue;
      }
      
      // Check if commit likely touches relevant files
      const isRelevant = relevantScripts.length === 0 || 
        relevantScripts.some(script => 
          message.toLowerCase().includes(script.replace('.py', '').toLowerCase())
        );
      
      if (isRelevant || relevantScripts.length === 0) {
        relevantChanges.push({
          sha: commit.sha?.slice(0, 7),
          message: firstLine,
          author: commit.commit?.author?.name,
          date: commit.commit?.author?.date
        });
      }
    }
    
    return {
      ...domain,
      total_commits_analyzed: commits.length || 0,
      relevant_changes: relevantChanges.slice(0, 20), // Limit to 20 for context
      has_relevant_changes: relevantChanges.length > 0
    };

12. IF node named "Has Relevant Changes?"
    - Condition: {{ $json.has_relevant_changes === true }}
    - On false: Connect to "Log No Changes" (can reuse Log Healthy)

13. CODE node named "Fetch Doc Contents"
    - JavaScript:
    // For each document, we'll fetch content in the next HTTP node
    // This prepares the list of docs to fetch
    const domain = $input.first().json;
    
    return domain.documents.slice(0, 3).map(doc => ({  // Limit to 3 docs
      json: {
        ...domain,
        current_doc: doc
      }
    }));

14. HTTP REQUEST node named "Get Document Content"
    - Method: GET
    - URL: https://raw.githubusercontent.com/BootstrapAI-mgmt/Literature-Review/main/{{ $json.current_doc }}
    - Response Format: Text (not JSON)

15. CODE node named "Aggregate Doc Contents"
    - JavaScript:
    // Collect all document contents
    const items = $items('Get Document Content');
    const domain = $('Filter Relevant Changes').first().json;
    
    const docContents = items.map((item, i) => {
      const docPath = $items('Fetch Doc Contents')[i]?.json?.current_doc || `doc-${i}`;
      const content = item.json.data || item.json || '';
      // Truncate to first 2000 chars to fit in context
      const truncated = typeof content === 'string' 
        ? content.slice(0, 2000) 
        : JSON.stringify(content).slice(0, 2000);
      return `### ${docPath}\n\n${truncated}\n\n---`;
    }).join('\n\n');
    
    return {
      ...domain,
      document_contents: docContents
    };

16. AI AGENT node named "Staleness Assessment" (use Gemini)
    - Model: gemini-1.5-pro (or gemini-1.5-flash for cost savings)
    - Temperature: 0.3
    - System prompt:
      You are a Documentation Staleness Reviewer. Analyze whether documentation has become stale by comparing current docs against recent repository changes.
      
      Look for:
      1. Missing features: New functionality not yet documented
      2. Outdated references: Code references that no longer match
      3. Changed behavior: Defaults, parameters, or behaviors that changed
      4. Deprecated patterns: Old approaches still documented but replaced
      5. Missing cross-references: New docs that should be linked
      
      Staleness scoring:
      - 0.0-0.2: Healthy
      - 0.2-0.4: Minor drift
      - 0.4-0.6: Moderate staleness
      - 0.6-0.8: Significant staleness
      - 0.8-1.0: Critical staleness
      
      Output ONLY valid JSON:
      {"domain":"@example","staleness_score":0.5,"confidence":0.8,"needs_update":true,"summary":"Brief summary","findings":[{"document":"path","issue_type":"missing_feature","severity":"medium","description":"What is wrong","suggested_update":"How to fix"}],"recommended_action":"auto_update|manual_review|create_issue|healthy","update_tasks":[{"task_id":"stale-001","document":"path","owner":"@domain","update_type":"UPDATE_FEATURE","description":"Task description","depends_on":[],"priority":1}]}
    
    - User message:
      Review domain {{ $json.domain }} for staleness.
      
      Days inactive: {{ $json.days_inactive }}
      Documents: {{ $json.documents.join(', ') }}
      
      Recent changes ({{ $json.relevant_changes.length }} commits):
      {{ $json.relevant_changes.map(c => c.sha + ': ' + c.message).join('\n') }}
      
      Document contents:
      {{ $json.document_contents }}

17. CODE node named "Parse Assessment"
    - JavaScript:
    const domain = $('Aggregate Doc Contents').first().json;
    const response = $input.first().json;
    const text = response.text || response.output || JSON.stringify(response);
    
    // Extract JSON from response
    let assessment;
    try {
      const jsonMatch = text.match(/```json\n?([\s\S]*?)\n?```/) || text.match(/\{[\s\S]*\}/);
      assessment = JSON.parse(jsonMatch ? (jsonMatch[1] || jsonMatch[0]) : text);
    } catch (e) {
      assessment = {
        staleness_score: 0.5,
        confidence: 0.3,
        needs_update: false,
        summary: "Could not parse AI response",
        findings: [],
        recommended_action: "manual_review",
        update_tasks: []
      };
    }
    
    // Normalize and validate
    const score = Math.max(0, Math.min(1, assessment.staleness_score || 0));
    const now = new Date();
    
    return {
      assessment_id: `sa-${now.toISOString().slice(0,10)}-${domain.domain.replace('@','')}`,
      timestamp: now.toISOString(),
      domain: domain.domain,
      documents: domain.documents,
      days_inactive: domain.days_inactive,
      staleness_score: score,
      confidence: Math.max(0, Math.min(1, assessment.confidence || 0.5)),
      needs_update: assessment.needs_update || score >= 0.5,
      summary: assessment.summary || 'Assessment complete',
      findings: assessment.findings || [],
      recommended_action: assessment.recommended_action || 
        (score >= 0.7 ? 'auto_update' : score >= 0.5 ? 'manual_review' : score >= 0.3 ? 'create_issue' : 'healthy'),
      update_tasks: (assessment.update_tasks || []).map((t, i) => ({
        ...t,
        task_id: t.task_id || `stale-${i+1}`,
        owner: t.owner || domain.domain,
        source: 'staleness_review'
      }))
    };

18. SWITCH node named "Route By Score"
    - Mode: Rules
    - Rules:
      - Rule 1 (Auto Update): {{ $json.staleness_score >= 0.7 && $json.update_tasks.length > 0 }}
      - Rule 2 (Manual Review): {{ $json.staleness_score >= 0.5 }}
      - Rule 3 (Create Issue): {{ $json.staleness_score >= 0.3 }}
      - Fallback (Healthy): All other cases

19. HTTP REQUEST node named "Send to Distributor" (connect from Rule 1)
    - Method: POST
    - URL: https://gitlitreview.app.n8n.cloud/webhook/task-distributor
    - Content Type: JSON
    - Body (JSON):
    {
      "update_list_id": "ul-stale-{{ $json.assessment_id }}",
      "source": "staleness_review",
      "trigger": {
        "type": "staleness_review",
        "domain": "{{ $json.domain }}",
        "staleness_score": {{ $json.staleness_score }},
        "assessment_id": "{{ $json.assessment_id }}"
      },
      "tasks": {{ JSON.stringify($json.update_tasks) }}
    }

20. HTTP REQUEST node named "Create Review Issue" (connect from Rules 2 and 3)
    - Method: POST
    - URL: https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/issues
    - Authentication: Header Auth (GitHub API Token)
    - Headers:
      - Accept: application/vnd.github.v3+json
    - Body (JSON):
    {
      "title": "📚 Staleness Review: {{ $json.domain }} (score: {{ ($json.staleness_score * 100).toFixed(0) }}%)",
      "body": "## Automated Staleness Review\n\n**Domain:** {{ $json.domain }}\n**Staleness Score:** {{ ($json.staleness_score * 100).toFixed(0) }}%\n**Confidence:** {{ ($json.confidence * 100).toFixed(0) }}%\n**Days Inactive:** {{ $json.days_inactive }}\n\n### Summary\n\n{{ $json.summary }}\n\n### Documents Reviewed\n\n{{ $json.documents.map(d => '- ' + d).join('\\n') }}\n\n### Findings\n\n{{ $json.findings.length > 0 ? $json.findings.map(f => '- **' + f.document + '** (' + f.severity + '): ' + f.description).join('\\n') : 'No specific issues identified.' }}\n\n### Recommended Actions\n\n{{ $json.findings.length > 0 ? $json.findings.map(f => '- [ ] ' + f.suggested_update).join('\\n') : '- [ ] Manual review recommended' }}\n\n---\n*Assessment ID: {{ $json.assessment_id }}*\n*This issue was automatically created by the staleness review workflow.*",
      "labels": ["documentation", "staleness-review", "automated"]
    }

21. CODE node named "Log Healthy" (connect from Needs Review? false, Has Relevant Changes? false, and Route By Score fallback)
    - JavaScript:
    const input = $input.first().json;
    console.log(`Domain ${input.domain || 'unknown'} is healthy (score: ${input.staleness_score || 'N/A'})`);
    return {
      domain: input.domain,
      status: 'healthy',
      staleness_score: input.staleness_score || 0,
      action: 'none',
      timestamp: new Date().toISOString()
    };

22. MERGE node named "Collect Results"
    - Mode: Append
    - Connect all terminal nodes: Send to Distributor, Create Review Issue, Log Healthy
    - This collects all results for the digest

23. CODE node named "Generate Digest"
    - JavaScript:
    const results = $items('Collect Results');
    const now = new Date();
    
    // Calculate week number
    const startOfYear = new Date(now.getFullYear(), 0, 1);
    const weekNum = Math.ceil(((now - startOfYear) / 86400000 + startOfYear.getDay() + 1) / 7);
    const weekId = `${now.getFullYear()}-W${weekNum.toString().padStart(2, '0')}`;
    
    const domainResults = results.filter(r => r.json.domain);
    
    const digest = {
      digest_id: `digest-${weekId}`,
      week: weekId,
      generated_at: now.toISOString(),
      summary: {
        domains_reviewed: domainResults.length,
        domains_healthy: domainResults.filter(r => (r.json.staleness_score || 0) < 0.3).length,
        domains_need_attention: domainResults.filter(r => (r.json.staleness_score || 0) >= 0.5).length,
        avg_staleness: domainResults.length > 0 
          ? (domainResults.reduce((sum, r) => sum + (r.json.staleness_score || 0), 0) / domainResults.length).toFixed(2)
          : 0
      },
      domain_statuses: domainResults.map(r => ({
        domain: r.json.domain,
        staleness_score: r.json.staleness_score || 0,
        status: r.json.status || (r.json.staleness_score >= 0.5 ? 'needs_attention' : 'healthy'),
        action: r.json.action || r.json.recommended_action || 'none'
      }))
    };
    
    return digest;

24. IF node named "Has Findings?"
    - Condition: {{ $json.summary.domains_need_attention > 0 }}
    - On true: Create digest issue
    - On false: End (silent success)

25. HTTP REQUEST node named "Create Digest Issue"
    - Method: POST
    - URL: https://api.github.com/repos/BootstrapAI-mgmt/Literature-Review/issues
    - Authentication: Header Auth (GitHub API Token)
    - Body (JSON):
    {
      "title": "📊 Weekly Staleness Digest: {{ $json.week }}",
      "body": "## Documentation Staleness Weekly Digest\n\n**Week:** {{ $json.week }}\n**Generated:** {{ $json.generated_at }}\n\n### Summary\n\n| Metric | Value |\n|--------|-------|\n| Domains Reviewed | {{ $json.summary.domains_reviewed }} |\n| Healthy | {{ $json.summary.domains_healthy }} |\n| Need Attention | {{ $json.summary.domains_need_attention }} |\n| Avg Staleness | {{ ($json.summary.avg_staleness * 100).toFixed(0) }}% |\n\n### Domain Status\n\n| Domain | Score | Status | Action |\n|--------|-------|--------|--------|\n{{ $json.domain_statuses.map(d => '| ' + d.domain + ' | ' + (d.staleness_score * 100).toFixed(0) + '% | ' + d.status + ' | ' + d.action + ' |').join('\\n') }}\n\n---\n*Digest ID: {{ $json.digest_id }}*",
      "labels": ["documentation", "staleness-digest", "automated"]
    }

CONNECT NODES:
1,2 → 3 (Start Review)
3 → 4 (Fetch Matrix)
4 → 5 (Get Domains)
5 → 6 (Split in Batches)
6 → 7 (Get Last Activity)
7 → 8 (Calculate Inactivity)
8 → 9 (Needs Review?)
9 true → 10 (Fetch Recent Changes)
9 false → 21 (Log Healthy)
10 → 11 (Filter Relevant Changes)
11 → 12 (Has Relevant Changes?)
12 true → 13 (Fetch Doc Contents)
12 false → 21 (Log Healthy)
13 → 14 (Get Document Content)
14 → 15 (Aggregate Doc Contents)
15 → 16 (AI Staleness Assessment)
16 → 17 (Parse Assessment)
17 → 18 (Route By Score)
18 Rule1 → 19 (Send to Distributor)
18 Rule2,3 → 20 (Create Review Issue)
18 Fallback → 21 (Log Healthy)
19, 20, 21 → 22 (Collect Results)
22 → 23 (Generate Digest)
23 → 24 (Has Findings?)
24 true → 25 (Create Digest Issue)
24 false → End

LOOP: After 22 (Collect Results), check if more domains in batch. 
The Split In Batches node automatically loops back for remaining items.
```

---

## Post-Build Verification

After building the workflow:

1. [ ] Activate the workflow
2. [ ] Test with manual trigger using POST to `/webhook/staleness-review`:
   ```bash
   curl -X POST https://gitlitreview.app.n8n.cloud/webhook/staleness-review \
     -H "Content-Type: application/json" \
     -d '{"test": true}'
   ```
3. [ ] Verify Matrix is fetched correctly
4. [ ] Verify domains are identified
5. [ ] Check GitHub API calls succeed (activity, commits)
6. [ ] Verify AI assessment produces valid JSON
7. [ ] Test routing: manually adjust staleness_score in Parse Assessment to test each branch
8. [ ] Verify issues are created in GitHub
9. [ ] Verify digest is generated

---

## 🔧 Troubleshooting

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| No domains to review | Stagger schedule mismatch | Disable stagger or adjust day |
| GitHub 404 errors | Document path wrong | Check paths in matrix |
| AI returns invalid JSON | Prompt too complex | Simplify, use flash model |
| Distributor not receiving | Wrong webhook URL | Verify Distributor is active |
| All domains "healthy" | Threshold too high | Lower review_interval_days |

### Debug Mode

Add a temporary Code node to log state at any point:
```javascript
console.log('DEBUG:', JSON.stringify($input.first().json, null, 2));
return $input.first().json;
```

### Reset for Fresh Run

To re-run staleness review for all domains (bypass inactivity check):
```javascript
// In Calculate Inactivity, temporarily add:
return {
  ...domain,
  needs_review: true,  // Force review
  days_inactive: 999
};
```

---

## 📊 Metrics & Monitoring

Track these in your observability system:

```javascript
// Add at end of workflow
const metrics = {
  workflow: 'staleness_review',
  timestamp: new Date().toISOString(),
  domains_reviewed: $json.summary.domains_reviewed,
  domains_healthy: $json.summary.domains_healthy,
  domains_need_attention: $json.summary.domains_need_attention,
  avg_staleness: $json.summary.avg_staleness,
  execution_time_ms: Date.now() - $workflow.startTime
};
// Log or send to metrics endpoint
```

---

*Prompt Version: 1.0*
*For use with: Doc Chain - Staleness Review workflow*
*Compatible with: n8n Cloud and self-hosted*
