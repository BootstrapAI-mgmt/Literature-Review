# ENHANCE-P5-6: Document Interactive Prompts Feature

**Category:** Documentation  
**Priority:** 🟡 MEDIUM  
**Effort:** 2 hours  
**Created:** November 17, 2025  
**Source:** PR #46 Review - Documentation Section

---

## Problem Statement

Phase 5 Interactive Prompts feature (PR #46) has no user-facing documentation. Users don't know:
- How to use interactive prompts
- What prompt types are available
- What happens when timeout expires
- How dashboard mode compares to terminal mode

**Missing Documentation:**
- ❌ `docs/INTERACTIVE_PROMPTS_GUIDE.md` (comprehensive user guide)
- ❌ No update to `DASHBOARD_GUIDE.md` mentioning prompt feature
- ❌ No screenshots of prompt modal in documentation
- ❌ No comparison table between terminal and dashboard workflows

---

## Impact

**Without Documentation:**
- Users unaware of feature capabilities
- No guidance on timeout behavior
- Confusion about when prompts appear
- Support burden (answering same questions repeatedly)

**With Documentation:**
- Self-service user onboarding
- Clear expectations for timeout behavior
- Increased feature adoption
- Reduced support requests

---

## Acceptance Criteria

- [ ] Create `docs/INTERACTIVE_PROMPTS_GUIDE.md` (comprehensive guide)
- [ ] Update `docs/DASHBOARD_GUIDE.md` with interactive prompts section
- [ ] Add screenshots to documentation (minimum 2 screenshots)
- [ ] Update `README.md` to link to new guide
- [ ] Review by another team member for clarity
- [ ] Include troubleshooting section
- [ ] Document all prompt types (pillar_selection, run_mode, continue)

---

## Documentation Structure

### 1. INTERACTIVE_PROMPTS_GUIDE.md (New File)

**File:** `docs/INTERACTIVE_PROMPTS_GUIDE.md`

```markdown
# Interactive Prompts Guide

**Last Updated:** November 17, 2025  
**Feature Version:** Phase 5 (PR #46)  
**Prerequisites:** Web Dashboard deployed and running

---

## Overview

Interactive Prompts enable full feature parity between terminal and web dashboard modes. Users can control job execution through modal dialogs instead of terminal input.

**Key Benefits:**
- No terminal access required
- Visual interface for complex choices
- Concurrent job support (multiple jobs, each with own prompts)
- Timeout protection (auto-cancel idle jobs)
- Audit trail (prompt history in job metadata - if ENHANCE-P5-3 implemented)

---

## Available Prompt Types

### 1. Pillar Selection

**When It Appears:**
- Job started without pre-configured pillar selection
- Orchestrator needs to know which pillars to analyze

**Options:**
- **ALL** - Run all available pillars
- **DEEP** - Only deep review pillar
- **Individual Pillars** - Select specific pillar(s)
- **NONE** - Skip pillar analysis

**Timeout:** 5 minutes (300 seconds)

**Screenshot:** *(Pillar Selection Modal)*

**Example:**
```
┌─────────────────────────────────────┐
│ Select Which Pillars to Analyze    │
├─────────────────────────────────────┤
│ ○ ALL - Run all pillars             │
│ ○ DEEP - Only deep review pillar    │
│ ○ P1: Research Question              │
│ ○ P2: Methodology                    │
│ ...                                  │
│ ○ NONE - Skip pillar analysis       │
├─────────────────────────────────────┤
│ [Submit] [Cancel Job]                │
│ Timeout: 4:52 remaining              │
└─────────────────────────────────────┘
```

---

### 2. Run Mode Selection

**When It Appears:**
- Job started without `run_mode` in configuration
- Orchestrator needs to know: single pass or iterative deep loop?

**Options:**
- **ONCE** - Single analysis pass (quick)
- **DEEP_LOOP** - Iterative deep review until convergence (thorough)

**Timeout:** 2 minutes (120 seconds, if ENHANCE-P5-5 implemented)

**Use Cases:**
- **ONCE:** Quick gap analysis, initial assessment
- **DEEP_LOOP:** Research deep-dive, comprehensive coverage

---

### 3. Continue Prompt

**When It Appears:**
- During deep loop workflow
- After each iteration completes

**Options:**
- **Yes** - Continue deep review loop (default)
- **No** - Stop and finalize results

**Timeout:** 1 minute (60 seconds, if ENHANCE-P5-5 implemented)

**Example Workflow:**
```
Iteration 1: Gap analysis complete → Found 12 gaps
↓
"Continue deep review loop? Yes/No"
↓ [User selects Yes]
Iteration 2: Deep review → Gap analysis → Found 5 gaps
↓
"Continue deep review loop? Yes/No"
↓ [User selects No]
Job complete - results available
```

---

## Timeout Behavior

### What Happens on Timeout?

| Event | Result |
|-------|--------|
| User responds before timeout | Job continues with selected option |
| Timeout expires (no response) | **Job auto-cancelled** |
| User clicks "Cancel Job" | Same as timeout (job cancelled) |

### Timeout Durations

| Prompt Type | Default Timeout | Configurable? |
|-------------|----------------|---------------|
| Pillar Selection | 5 minutes (300s) | Yes (ENHANCE-P5-5) |
| Run Mode | 5 minutes (300s) | Yes (ENHANCE-P5-5) |
| Continue | 5 minutes (300s) | Yes (ENHANCE-P5-5) |

**Visual Countdown:**
- Displayed in modal: "Timeout: 4:32 remaining"
- Updates every second
- Final 30 seconds: countdown turns red (warning)

---

## Dashboard vs Terminal Mode

| Feature | Terminal Mode | Dashboard Mode |
|---------|--------------|----------------|
| **Pillar Selection** | `input()` prompt | Modal dialog with radio buttons |
| **Timeout** | None (blocks forever) | 5 minutes (auto-cancel) |
| **Concurrent Jobs** | N/A (single process) | ✅ Yes (per-job prompts) |
| **Visual Feedback** | Text only | Bootstrap modal with countdown timer |
| **Accessibility** | Terminal emulator required | Web browser (mobile-friendly) |
| **Prompt History** | None | ✅ Saved to job metadata (if ENHANCE-P5-3) |
| **Multi-Select Pillars** | Comma-separated: "1,3,5" | ✅ Checkboxes (if ENHANCE-P5-4) |

---

## How to Use

### Starting a Job with Prompts

**Step 1:** Navigate to Dashboard
```
http://localhost:5001
```

**Step 2:** Click "New Job" Button

**Step 3:** Configure Job (Optional)
- If you skip pillar selection → prompt will appear
- If you skip run mode → prompt will appear (if ENHANCE-P5-2)

**Step 4:** Click "Start Job"

**Step 5:** Respond to Prompts
- Prompt modal appears automatically
- Make selection
- Click "Submit" (or wait for timeout)

**Step 6:** Monitor Progress
- Job executes with your selections
- View real-time progress updates
- Download results when complete

---

### Example: Starting Job Without Configuration

```
1. Click "New Job"
2. Leave all fields empty → Click "Start Job"
3. Prompt appears: "Select which pillars to analyze"
4. Choose "ALL" → Click "Submit"
5. (If ENHANCE-P5-2 implemented) Prompt: "Select analysis mode"
6. Choose "ONCE" → Click "Submit"
7. Job runs → Monitor progress → Download results
```

---

## Concurrent Jobs

**Scenario:** Two jobs running simultaneously, both need pillar selection

**Behavior:**
- Each job has independent prompts
- Job ID displayed in prompt modal title: "Job abc123 - Select Pillars"
- Responding to Job A's prompt doesn't affect Job B
- Each job has own timeout countdown

**Visual Example:**
```
Job abc123: "Select pillars" (4:30 remaining)
Job def456: "Select pillars" (4:58 remaining)
```

---

## Troubleshooting

### Prompt Doesn't Appear

**Possible Causes:**
1. Job configured with all required parameters (no prompts needed)
2. WebSocket connection failed (check browser console)
3. Prompt timeout already expired before you opened dashboard

**Solutions:**
- Check job configuration (if all set, no prompts appear - this is normal)
- Refresh dashboard page (re-establishes WebSocket)
- Check job status (if "cancelled" → timeout expired)

---

### Prompt Timeout Too Short/Long

**Solution:** Configure timeout in `pipeline_config.json` (if ENHANCE-P5-5 implemented):

```json
{
  "prompts": {
    "timeouts": {
      "pillar_selection": 600,  // 10 minutes
      "run_mode": 120,
      "continue": 60
    }
  }
}
```

---

### Job Cancelled After Timeout

**Explanation:** Intentional behavior - prevents idle jobs from blocking resources

**Prevention:**
- Respond to prompts within timeout window
- Increase timeout in config (if needed)
- Pre-configure job parameters (skip prompts entirely)

---

### Modal Doesn't Close After Submit

**Possible Causes:**
1. Network error (response not reaching server)
2. Invalid response (validation failed)

**Solutions:**
- Check browser console for errors
- Verify network connectivity
- Try again - if persists, refresh page

---

## Best Practices

### 1. Pre-Configure for Automation
If running automated workflows, set all parameters in config to avoid prompts:

```json
{
  "pillar_selection": "ALL",
  "run_mode": "ONCE"
}
```

### 2. Use Appropriate Run Mode
- **Development/Testing:** ONCE (faster)
- **Production/Research:** DEEP_LOOP (comprehensive)

### 3. Monitor Concurrent Jobs
- Keep track of which job each prompt belongs to (check modal title)
- Respond to prompts promptly to avoid timeouts

### 4. Review Prompt History
(If ENHANCE-P5-3 implemented)
- Check job details modal to see what you selected
- Use "Replay Job" to re-run with same choices

---

## Advanced: Programmatic Prompt Response

For automated testing or CI/CD:

```python
import requests

# Simulate prompt response
response = requests.post(
    f"http://localhost:5001/api/prompts/{prompt_id}/response",
    json={"response": "ALL"}
)
```

---

## Related Documentation

- [Dashboard Guide](DASHBOARD_GUIDE.md) - General dashboard usage
- [Orchestrator Guide](ORCHESTRATOR_V2_GUIDE.md) - Pipeline configuration
- [Manual Testing Guide](MANUAL_TESTING_GUIDE.md) - Testing interactive workflows

---

## Future Enhancements

(Pending implementation - see task cards)

- **ENHANCE-P5-2:** Additional prompt types (run_mode, continue)
- **ENHANCE-P5-3:** Prompt history and replay
- **ENHANCE-P5-4:** Multi-select pillar checkboxes
- **ENHANCE-P5-5:** Configurable timeouts per prompt type

---

## FAQ

**Q: Can I skip prompts entirely?**  
A: Yes - pre-configure all parameters in `pipeline_config.json` or job creation form.

**Q: What happens if I close the browser during a prompt?**  
A: Timeout continues counting. If you return before timeout, prompt still available. After timeout, job cancelled.

**Q: Can I change my response after submitting?**  
A: No - responses are final. Cancel job and restart if needed.

**Q: Do prompts work on mobile devices?**  
A: Yes - responsive Bootstrap modals work on all screen sizes.

**Q: How do I know which job is prompting me?**  
A: Job ID displayed in modal title bar (e.g., "Job abc123 - Select Pillars").
```

---

### 2. Update DASHBOARD_GUIDE.md

**File:** `docs/DASHBOARD_GUIDE.md`

**Add new section after "Starting a Job":**

```markdown
## Interactive Job Control

The dashboard supports interactive prompts for job configuration, providing full feature parity with terminal mode.

### When Prompts Appear

Prompts appear when jobs are started without complete configuration:

- **Pillar Selection:** If no pillars specified in config
- **Run Mode:** If run mode not configured (requires ENHANCE-P5-2)
- **Continue Deep Loop:** During iterative deep review (requires ENHANCE-P5-2)

### Using Interactive Prompts

![Pillar Selection Modal](../screenshots/pillar_selection_prompt.png)

**Steps:**
1. Start a job without full configuration
2. Prompt modal appears automatically
3. Make your selection
4. Click "Submit" (or prompt times out after 5 minutes)
5. Job continues with your choices

### Timeout Behavior

- **Default:** 5 minutes per prompt
- **Visual Countdown:** Displayed in modal
- **On Timeout:** Job automatically cancelled
- **Configurable:** Yes (see `pipeline_config.json` - requires ENHANCE-P5-5)

### Concurrent Jobs

Multiple jobs can have active prompts simultaneously:
- Each job's prompt has unique ID
- Job ID displayed in modal title
- Independent timeout counters

**Example:**
```
Job abc123: Waiting for pillar selection (3:45 remaining)
Job def456: Waiting for run mode (4:30 remaining)
```

For detailed information, see the [Interactive Prompts Guide](INTERACTIVE_PROMPTS_GUIDE.md).
```

---

### 3. Update README.md

**File:** `README.md`

**Add to Documentation section:**

```markdown
## Documentation

### User Guides
- [User Manual](docs/USER_MANUAL.md) - Complete usage guide
- [Dashboard Guide](docs/DASHBOARD_GUIDE.md) - Web interface guide
- [Interactive Prompts Guide](docs/INTERACTIVE_PROMPTS_GUIDE.md) - ⭐ **NEW:** Prompts and timeout behavior
- [Manual Testing Guide](docs/MANUAL_TESTING_GUIDE.md) - Testing workflows

### Technical Guides
- [Orchestrator V2 Guide](docs/ORCHESTRATOR_V2_GUIDE.md) - Pipeline orchestration
- [Evidence Triangulation Guide](docs/EVIDENCE_TRIANGULATION_GUIDE.md) - Source diversity analysis
...
```

---

### 4. Screenshots to Capture

**Screenshot 1: Pillar Selection Modal**
- Save as: `docs/screenshots/pillar_selection_prompt.png`
- Shows: Modal with radio buttons, timeout countdown, Submit/Cancel buttons

**Screenshot 2: Timeout Warning**
- Save as: `docs/screenshots/prompt_timeout_warning.png`
- Shows: Modal with red countdown (< 30 seconds), warning state

**Screenshot 3: Job Details with Prompt History** (if ENHANCE-P5-3)
- Save as: `docs/screenshots/prompt_history.png`
- Shows: Job details modal with "User Decisions" section

**Screenshot 4: Concurrent Prompts**
- Save as: `docs/screenshots/concurrent_prompts.png`
- Shows: Multiple jobs with active prompts in job list

---

## Implementation Checklist

### Phase 1: Create Interactive Prompts Guide (1 hour)

- [ ] Create `docs/INTERACTIVE_PROMPTS_GUIDE.md`
- [ ] Write sections:
  - [ ] Overview
  - [ ] Available Prompt Types
  - [ ] Timeout Behavior
  - [ ] Dashboard vs Terminal Mode comparison
  - [ ] How to Use (step-by-step)
  - [ ] Concurrent Jobs
  - [ ] Troubleshooting
  - [ ] Best Practices
  - [ ] FAQ
- [ ] Add code examples and configuration snippets

### Phase 2: Update Existing Documentation (30 minutes)

- [ ] Update `DASHBOARD_GUIDE.md` with Interactive Prompts section
- [ ] Update `README.md` with link to new guide
- [ ] Cross-link related documentation

### Phase 3: Screenshots (20 minutes)

- [ ] Start dashboard locally
- [ ] Capture pillar selection modal screenshot
- [ ] Capture timeout warning screenshot
- [ ] (Optional) Capture concurrent prompts screenshot
- [ ] Save to `docs/screenshots/` directory
- [ ] Reference in documentation

### Phase 4: Review & Polish (10 minutes)

- [ ] Spell check and grammar review
- [ ] Verify all links work
- [ ] Test code examples
- [ ] Peer review by another team member
- [ ] Incorporate feedback

---

## Testing Plan

### Documentation Validation

1. **Completeness Check:**
   - All prompt types documented
   - Timeout behavior explained
   - Screenshots present and relevant

2. **Accuracy Check:**
   - Code examples work as written
   - Configuration snippets valid JSON
   - Screenshots match current UI

3. **Usability Check:**
   - New user can follow guide without external help
   - Troubleshooting section addresses common issues
   - FAQ covers likely questions

### User Testing

1. Give documentation to new user
2. Ask them to start job with prompts
3. Observe: Do they succeed without asking questions?
4. Collect feedback, update documentation

---

## Style Guide

### Voice & Tone
- **Audience:** Technical users (developers, researchers)
- **Voice:** Clear, professional, concise
- **Tone:** Helpful, instructive (not condescending)

### Formatting
- Use **bold** for important concepts
- Use `code blocks` for config snippets, URLs, commands
- Use tables for comparisons
- Use screenshots for visual features
- Use bullet points for lists

### Examples
✅ **Good:** "Prompt modal appears automatically when job starts"  
❌ **Bad:** "The system will trigger the prompt rendering subsystem upon job initialization"

✅ **Good:** "Timeout: 5 minutes (300 seconds)"  
❌ **Bad:** "The temporal constraint for prompt response is five minutes"

---

## Documentation Maintenance

### When to Update

- ✅ New prompt type added (ENHANCE-P5-2)
- ✅ Timeout configuration implemented (ENHANCE-P5-5)
- ✅ Multi-select pillars added (ENHANCE-P5-4)
- ✅ Prompt history feature released (ENHANCE-P5-3)
- ✅ UI changes affecting screenshots
- ✅ Bug fixes affecting documented behavior

### Review Schedule

- **After each PR:** Update affected sections
- **Quarterly:** Full documentation review
- **Major release:** Comprehensive update and screenshot refresh

---

## Dependencies

**Requires:**
- ✅ Phase 5 implementation (PR #46)
- ✅ Dashboard deployed and accessible
- ✅ Browser for screenshots

**Enhances:**
- ENHANCE-P5-2 (run_mode/continue prompts) - document new types
- ENHANCE-P5-3 (Prompt History) - document history feature
- ENHANCE-P5-4 (Multi-Select) - document checkbox UI
- ENHANCE-P5-5 (Configurable Timeout) - document config options

---

## Success Metrics

- [ ] Interactive Prompts Guide created and published
- [ ] DASHBOARD_GUIDE.md updated with prompts section
- [ ] README.md links to new guide
- [ ] Minimum 2 screenshots added
- [ ] Peer review completed with approval
- [ ] Zero ambiguities or unclear sections reported
- [ ] New users can use prompts without support requests

---

## Estimated Breakdown

- **Write INTERACTIVE_PROMPTS_GUIDE.md:** 1 hour
- **Update existing docs:** 30 minutes
- **Capture screenshots:** 20 minutes
- **Review & polish:** 10 minutes
- **Total:** 2 hours
