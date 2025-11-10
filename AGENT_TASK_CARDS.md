# Agent Task Cards - Literature Review System

**Date Created:** 2025-11-10  
**Status:** Ready for Assignment  
**Total Cards:** 4

---

## 🎫 TASK CARD #1: Fix DRA Prompting for Judge Alignment

**Priority:** 🔴 CRITICAL  
**Estimated Effort:** 2-3 hours  
**Risk Level:** MEDIUM  
**Dependencies:** None  
**Blocks:** All gap-filling functionality

### Problem Statement

The Deep Requirements Analyzer (DRA) has a 100% rejection rate (1038/1038 claims rejected). Root cause: DRA does not receive the canonical sub-requirement definition text from `pillar_definitions_enhanced.json` that the Judge uses for validation, resulting in evidence that doesn't align with validation criteria.

### Acceptance Criteria

**Success Metrics:**
- [ ] DRA approval rate >60% on first re-submission
- [ ] DRA can identify when no better evidence exists (returns empty list)
- [ ] Evidence chunks directly quote requirement-satisfying text
- [ ] No degradation in Judge approval rate for original claims

**Technical Requirements:**
- [ ] DRA loads `pillar_definitions_enhanced.json`
- [ ] DRA prompt includes full sub-requirement definition as "THE LAW" section
- [ ] DRA prompt includes Judge's rejection reason
- [ ] DRA prompt instructs AI to address specific rejection points

### Implementation Guide

**File to Modify:** `DeepRequirementsAnalyzer.py`

**Step 1: Add Definitions Loading (New Function)**
```python
# Add after imports, around line 30
DEFINITIONS_FILE = 'pillar_definitions_enhanced.json'

def load_pillar_definitions(filepath: str) -> Dict:
    """Load pillar definitions for DRA analysis."""
    if not os.path.exists(filepath):
        logger.error(f"Pillar definitions file not found: {filepath}")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading pillar definitions: {e}")
        return {}

def find_sub_requirement_definition(definitions: Dict, pillar_key: str, 
                                     sub_req_key: str) -> Optional[str]:
    """Extract the full definition text for a sub-requirement."""
    for pillar_name, pillar_data in definitions.items():
        if pillar_name == pillar_key or pillar_name.startswith(pillar_key):
            for req_key, sub_req_list in pillar_data.get('requirements', {}).items():
                for sub_req_text in sub_req_list:
                    if sub_req_text == sub_req_key or sub_req_text.startswith(sub_req_key):
                        return sub_req_text
    return None
```

**Step 2: Modify build_dra_prompt() Function (Lines 155-203)**
```python
def build_dra_prompt(claims_for_document: List[Dict], full_paper_text: str,
                     pillar_definitions: Dict) -> str:
    """
    Builds the prompt for the Deep Requirements Analyzer AI.
    This prompt includes *all* rejected claims for a single document.
    """

    rejection_list_str = ""
    for i, claim in enumerate(claims_for_document, 1):
        # NEW: Get the canonical definition
        pillar_key = claim.get('pillar', 'N/A')
        sub_req_key = claim.get('sub_requirement', 'N/A')
        definition_text = find_sub_requirement_definition(
            pillar_definitions, pillar_key, sub_req_key
        )
        
        rejection_list_str += f"""
--- REJECTED CLAIM #{i} ---
Pillar: {pillar_key}
Sub-Requirement Key: {sub_req_key}
FULL REQUIREMENT DEFINITION ("THE LAW"):
"{definition_text if definition_text else 'NOT FOUND - Cannot satisfy this claim!'}"

Judge's Rejection Reason: "{claim.get('judge_notes', 'N/A')}"
Original Evidence Provided: "{claim.get('evidence_chunk', 'N/A')}"
(Internal Claim ID: {claim.get('claim_id')})
"""

    return f"""
You are an expert "Deep Requirements Analyzer." Your task is to re-evaluate a list of claims that were rejected by an impartial Judge. You will find *better* evidence for *all* of them from the full text of the single paper provided.

--- CRITICAL INSTRUCTIONS ---
1. The "FULL REQUIREMENT DEFINITION" shown for each rejected claim is the EXACT text that the Judge will validate against.
2. Your evidence MUST DIRECTLY and EXPLICITLY satisfy that FULL definition, NOT just the sub-requirement key.
3. The Judge rejected the original attempt for specific reasons. Your new evidence must ADDRESS those reasons.
4. Quote text EXACTLY from the paper. The Judge will verify your quotes.
5. If you cannot find text that CLEARLY satisfies the FULL definition, DO NOT submit a claim for that requirement.

--- LIST OF REJECTED CLAIMS ---
{rejection_list_str}
--- END OF LIST ---

--- YOUR TASK ---
1.  **Understand "THE LAW":** For each rejected claim, carefully read the FULL REQUIREMENT DEFINITION.
2.  **Understand the Rejection:** Read why the Judge rejected the original evidence.
3.  **Scan the FULL TEXT:** Read the entire document provided below.
4.  **Find Direct Evidence:** For each rejected claim, locate text that:
    - DIRECTLY addresses the FULL REQUIREMENT DEFINITION
    - Overcomes the Judge's specific rejection reason
    - Is EXPLICIT, not implied or tangential
5.  **Be Selective:** Only submit claims where you have HIGH confidence (>0.9) that the new evidence will satisfy the Judge.

--- Output Format ---
Return ONLY a JSON object with a single key, "new_claims_to_rejudge", which is a list.
For *each* rejected claim you were able to find *new, better* evidence for, return a new claim object in the list.

Example:
{{
  "new_claims_to_rejudge": [
    {{
      "original_claim_id": "(String) The 'Internal Claim ID' of the rejected claim.",
      "claim_summary": "(String) A 1-sentence argument for why this evidence NOW satisfies the FULL definition AND addresses the rejection.",
      "evidence_chunk": "(String) EXACT quote from paper. Can be multiple paragraphs if needed for completeness.",
      "reviewer_confidence": 0.95
    }}
  ]
}}

If no new, high-quality evidence is found for *any* of the rejected claims, return an empty list:
{{
  "new_claims_to_rejudge": []
}}

--- FULL PAPER TEXT ---
{full_paper_text}
--- END FULL PAPER TEXT ---
"""
```

**Step 3: Update run_analysis() Function (Lines 207-320)**
```python
def run_analysis(
        rejected_claims: List[Dict],
        api_manager: Any,
        papers_folder_path: str
) -> List[Dict]:
    """
    Main entry point for the DRA.
    Takes a list of rejected claims, **groups them by document**,
    re-scans each source file *once*, and returns a list of new,
    improved claims for re-judgment.
    """

    if not papers_folder_path:
        logger.error("DRA: Cannot run analysis, papers folder path is not set.")
        return []

    # NEW: Load pillar definitions
    pillar_definitions = load_pillar_definitions(DEFINITIONS_FILE)
    if not pillar_definitions:
        logger.error("DRA: Cannot proceed without pillar definitions.")
        return []

    text_extractor = TextExtractor()
    new_claims_for_rejudgment = []

    # Group claims by filename
    claims_by_file = defaultdict(list)
    for claim in rejected_claims:
        filename = claim.get('filename') or claim.get('_filename', 'N/A')
        if filename:
            claims_by_file[filename].append(claim)

    logger.info(f"DRA: Received {len(rejected_claims)} rejected claims, grouped into {len(claims_by_file)} documents for analysis.")
    safe_print(f"DRA: Analyzing {len(rejected_claims)} rejected claims across {len(claims_by_file)} documents.")

    # Loop through each DOCUMENT
    for i, (filename, claims_for_doc) in enumerate(claims_by_file.items(), 1):
        safe_print(f"  DRA: Analyzing Document {i}/{len(claims_by_file)}: {filename[:30]}... ({len(claims_for_doc)} rejected claims)")

        if not filename:
            logger.warning("DRA: Skipping claim group, missing filename.")
            continue

        # Find and read the full paper text
        filepath = find_paper_filepath(filename, papers_folder_path)
        if not filepath:
            logger.error(f"DRA: Could not find source file {filename}. Skipping all {len(claims_for_doc)} claims for this doc.")
            continue

        full_text, _, _ = text_extractor.robust_text_extraction(filepath)
        if not full_text:
            logger.error(f"DRA: Could not extract text from {filename}. Skipping all {len(claims_for_doc)} claims.")
            continue

        # Build the new prompt (with ALL claims for this doc + definitions)
        prompt = build_dra_prompt(claims_for_doc, full_text, pillar_definitions)  # MODIFIED

        # ... rest of function unchanged ...
```

### Testing Strategy

**Test 1: Basic Functionality**
```bash
# Create a test case with 1-2 rejected claims
# Run DRA manually
python -c "
import DeepRequirementsAnalyzer as dra
from Judge import APIManager

api_manager = APIManager()
papers_folder = dra.find_papers_folder()

# Mock rejected claim
test_claims = [{
    'claim_id': 'test123',
    'filename': 'test_paper.pdf',
    'pillar': 'Pillar 1: Biological Stimulus-Response',
    'sub_requirement': 'Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes',
    'evidence_chunk': 'weak evidence here',
    'judge_notes': 'Rejected. Evidence is too general and does not show conclusive model.',
    'status': 'rejected'
}]

results = dra.run_analysis(test_claims, api_manager, papers_folder)
print(f'DRA returned {len(results)} new claims')
"
```

**Test 2: Measure Approval Rate**
```bash
# After implementing, run full Judge pipeline
python Judge.py

# Check logs for:
# - "DRA: No new high-confidence evidence found" messages (should be <40% of cases)
# - "VERDICT (Appeal): APPROVED" count (should be >60% of DRA submissions)
# - "VERDICT (Appeal): REJECTED" count (should be <40%)
```

**Test 3: Validate Definition Inclusion**
```python
# Check that definitions are being included in prompts
import DeepRequirementsAnalyzer as dra

definitions = dra.load_pillar_definitions('pillar_definitions_enhanced.json')
assert len(definitions) > 0, "Definitions not loaded!"

# Test definition lookup
test_def = dra.find_sub_requirement_definition(
    definitions,
    'Pillar 1: Biological Stimulus-Response',
    'Sub-1.1.1: Conclusive model of how raw sensory data is transduced into neural spikes'
)
assert test_def is not None, "Definition lookup failed!"
print(f"Found definition: {test_def[:100]}...")
```

### Rollback Plan

If approval rate does not improve or degrades:
1. Revert changes to `DeepRequirementsAnalyzer.py`
2. Restore original `build_dra_prompt()` function
3. Document specific failure modes in logs
4. Consider alternative approaches (e.g., few-shot examples)

### Files to Modify

- [x] `DeepRequirementsAnalyzer.py`
  - Add definition loading functions
  - Modify `build_dra_prompt()`
  - Modify `run_analysis()` to pass definitions

### Success Indicators

- ✅ DRA approval rate >60%
- ✅ Judge logs show "VERDICT (Appeal): APPROVED" for majority of DRA claims
- ✅ No increase in API errors or timeouts
- ✅ DRA correctly returns empty list when no evidence found

---

## 🎫 TASK CARD #2: Refactor Judge to Use Version History

**Priority:** 🔴 CRITICAL  
**Estimated Effort:** 4-6 hours  
**Risk Level:** HIGH  
**Dependencies:** None  
**Blocks:** Data consistency, sync script reliability

### Problem Statement

Judge.py currently reads from and writes to both `deep_coverage_database.json` and `neuromorphic-research_database.csv`, violating the single source of truth architecture. This causes:
- Data inconsistency between databases
- Sync script unable to reconcile conflicting changes
- Version history not being updated with Judge verdicts
- Potential data corruption/loss

### Acceptance Criteria

**Success Metrics:**
- [ ] Judge NEVER writes to `deep_coverage_database.json`
- [ ] Judge NEVER writes to `neuromorphic-research_database.csv`
- [ ] All claim updates appear in `review_version_history.json` with timestamps
- [ ] Sync script successfully propagates changes to CSV
- [ ] No data loss during Judge→Sync→CSV flow
- [ ] All existing functionality preserved

**Technical Requirements:**
- [ ] New version history I/O functions created
- [ ] Judge loads claims ONLY from version history
- [ ] Judge updates claims ONLY in version history
- [ ] Version history tracks all status changes
- [ ] Backward compatibility with existing data

### Implementation Guide

**Files to Modify:**
1. `Judge.py` - Major refactor
2. `review_version_history.json` - Data format validation
3. `sync_history_to_db.py` - May need minor updates

**Step 1: Create Version History I/O Functions (Add to Judge.py after line 300)**

```python
# --- VERSION HISTORY I/O FUNCTIONS ---
VERSION_HISTORY_FILE = 'review_version_history.json'

def load_version_history(filepath: str = VERSION_HISTORY_FILE) -> Dict:
    """Loads the review version history (source of truth)."""
    if not os.path.exists(filepath):
        logger.warning(f"Version history file not found: {filepath}. Starting fresh.")
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            history = json.load(f)
        logger.info(f"Loaded history for {len(history)} files from {filepath}")
        return history
    except Exception as e:
        logger.error(f"Failed to load version history from {filepath}: {e}")
        return {}

def save_version_history(filepath: str, history: Dict):
    """Saves updated review version history."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved version history to {filepath}")
    except Exception as e:
        logger.error(f"Error saving version history to {filepath}: {e}")
        safe_print(f"❌ CRITICAL: Failed to save version history: {e}")

def extract_pending_claims_from_history(history: Dict) -> List[Dict]:
    """Extracts all pending claims from version history."""
    claims = []
    for filename, versions in history.items():
        if not versions:
            continue
        latest = versions[-1].get('review', {})
        for claim in latest.get('Requirement(s)', []):
            if claim.get('status') == 'pending_judge_review':
                # Add metadata for tracking
                claim['_source_filename'] = filename
                claim['_source_type'] = 'version_history'
                claims.append(claim)
    logger.info(f"Extracted {len(claims)} pending claims from version history")
    return claims

def update_claims_in_history(history: Dict, updated_claims: List[Dict]) -> Dict:
    """Updates claim statuses in version history and creates new version entries."""
    # Create lookup by claim_id
    claims_by_id = {c['claim_id']: c for c in updated_claims}
    
    timestamp = datetime.now().isoformat()
    updated_files = []
    
    for filename, versions in history.items():
        if not versions:
            continue
        
        latest = versions[-1]
        requirements = latest.get('review', {}).get('Requirement(s)', [])
        
        # Track if any claims were updated for this file
        file_updated = False
        updated_claim_ids = []
        
        for claim in requirements:
            if claim['claim_id'] in claims_by_id:
                updated = claims_by_id[claim['claim_id']]
                claim['status'] = updated['status']
                claim['judge_notes'] = updated['judge_notes']
                claim['judge_timestamp'] = updated['judge_timestamp']
                file_updated = True
                updated_claim_ids.append(claim['claim_id'])
        
        # Add new version entry if file was updated
        if file_updated:
            new_version = {
                'timestamp': timestamp,
                'review': latest['review'],  # Copy of entire review with updated claims
                'changes': {
                    'status': 'judge_update',
                    'updated_claims': len(updated_claim_ids),
                    'claim_ids': updated_claim_ids
                }
            }
            versions.append(new_version)
            updated_files.append(filename)
    
    logger.info(f"Updated {len(updated_files)} files in version history")
    return history

def add_new_claims_to_history(history: Dict, new_claims: List[Dict]) -> Dict:
    """Adds new claims (from DRA) to version history."""
    timestamp = datetime.now().isoformat()
    claims_by_file = defaultdict(list)
    
    # Group claims by filename
    for claim in new_claims:
        filename = claim.get('_source_filename') or claim.get('filename')
        if filename:
            claims_by_file[filename].append(claim)
    
    for filename, claims in claims_by_file.items():
        if filename not in history:
            logger.warning(f"File {filename} not in history. Skipping new claims.")
            continue
        
        versions = history[filename]
        if not versions:
            continue
        
        latest = versions[-1]
        latest['review']['Requirement(s)'].extend(claims)
        
        # Add new version entry
        new_version = {
            'timestamp': timestamp,
            'review': latest['review'],
            'changes': {
                'status': 'dra_appeal',
                'new_claims': len(claims),
                'claim_ids': [c['claim_id'] for c in claims]
            }
        }
        versions.append(new_version)
    
    logger.info(f"Added {len(new_claims)} new claims to version history")
    return history
```

**Step 2: Refactor main() Function (Replace lines 430-653)**

```python
def main():
    start_time = time.time()
    logger.info("\n" + "=" * 80)
    logger.info("JUDGE PIPELINE v2.0 (Uses Version History as Source of Truth)")
    logger.info("=" * 80)

    logger.info("\n=== INITIALIZING COMPONENTS ===")
    safe_print("\n=== INITIALIZING COMPONENTS ===")
    try:
        api_manager = APIManager()
    except Exception as init_e:
        logger.critical(f"Failed to initialize core components: {init_e}")
        safe_print(f"❌ Failed to initialize core components: {init_e}")
        return

    papers_folder_path = dra.find_papers_folder()
    if not papers_folder_path:
        logger.error("Could not find PAPERS_FOLDER. DRA will fail.")
        safe_print("❌ Could not find PAPERS_FOLDER. DRA will be skipped.")

    logger.info("\n=== LOADING DATA ===")
    safe_print("\n=== LOADING DATA ===")

    # NEW: Load ONLY from version history
    version_history = load_version_history(VERSION_HISTORY_FILE)
    pillar_definitions = load_pillar_definitions(DEFINITIONS_FILE)

    if not pillar_definitions:
        logger.critical("Missing pillar definitions. Exiting.")
        safe_print("❌ Missing pillar definitions. Exiting.")
        return
    
    if not version_history:
        logger.info("No version history found. Nothing to judge.")
        safe_print("⚖️ No version history found. All work is done.")
        return

    # Extract pending claims
    claims_to_judge = extract_pending_claims_from_history(version_history)
    
    if not claims_to_judge:
        logger.info("No pending claims found in version history.")
        safe_print("⚖️ No pending claims found. All work is done.")
        return
    
    logger.info(f"Found {len(claims_to_judge)} total claims pending judgment.")
    safe_print(f"⚖️ Found {len(claims_to_judge)} total claims pending judgment. The court is in session.")

    # --- PHASE 1: Initial Judgment ---
    logger.info("\n--- PHASE 1: Initial Judgment ---")
    safe_print("\n--- PHASE 1: Initial Judgment ---")

    init_approved_count = 0
    init_rejected_count = 0
    claims_for_dra_appeal = []
    all_judged_claims = []  # Track all claims for updating history

    for i, claim in enumerate(claims_to_judge, 1):
        filename = claim.get('_source_filename', 'N/A')
        claim_id_short = f"{filename[:15]}... ({claim['claim_id'][:6]})"
        logger.info(f"\n--- Judging Claim {i}/{len(claims_to_judge)}: {claim_id_short} ---")
        safe_print(f"\n--- Judging Claim {i}/{len(claims_to_judge)}: {claim_id_short} ---")

        try:
            sub_req_key = claim.get('sub_requirement') or claim.get('sub_requirement_key', 'N/A')
            pillar_key = claim.get('pillar', 'N/A')
            definition_text = find_robust_sub_requirement_text(sub_req_key)

            if not definition_text:
                logger.error(f"  Could not find definition for claim. Rejecting.")
                safe_print(f"  ❌ Could not find definition for '{sub_req_key}'. Rejecting.")
                ruling = {"verdict": "rejected", "judge_notes": f"Rejected. Could not find sub-requirement definition for '{sub_req_key}' in pillar file."}
            else:
                prompt = build_judge_prompt(claim, definition_text)
                logger.info(f"  Submitting claim to Judge AI...")
                safe_print(f"  Submitting claim to Judge AI...")
                response = api_manager.cached_api_call(prompt, use_cache=False, is_json=True)
                ruling = validate_judge_response(response)

            if ruling:
                canonical_pillar = find_robust_pillar_key(pillar_key)
                canonical_sub_req = definition_text
                if canonical_pillar: claim['pillar'] = canonical_pillar
                if canonical_sub_req:
                    claim['sub_requirement'] = canonical_sub_req
                    claim.pop('sub_requirement_key', None)

                claim['status'] = ruling['verdict']
                claim['judge_notes'] = ruling['judge_notes']
                claim['judge_timestamp'] = datetime.now().isoformat()
                all_judged_claims.append(claim)

                if ruling['verdict'] == 'approved':
                    logger.info(f"  VERDICT: APPROVED")
                    safe_print(f"  ✅ VERDICT: APPROVED")
                    init_approved_count += 1
                else:
                    logger.info(f"  VERDICT: REJECTED (Pending DRA)")
                    safe_print(f"  ❌ VERDICT: REJECTED (Sending to DRA for appeal)")
                    init_rejected_count += 1
                    claims_for_dra_appeal.append(claim)
            else:
                logger.error(f"  Judge AI returned invalid response. Claim will be re-judged next run.")
                safe_print(f"  ⚠️ Judge AI returned invalid response. Skipping for next run.")
        except Exception as e:
            logger.critical(f"  CRITICAL UNHANDLED ERROR on claim {claim['claim_id']}: {e}")
            safe_print(f"  ❌ CRITICAL ERROR on claim. See log. Skipping.")

    # --- PHASE 2: DRA Appeal Process ---
    logger.info("\n--- PHASE 2: DRA Appeal Process ---")
    safe_print("\n--- PHASE 2: DRA Appeal Process ---")

    new_claims_for_rejudgment = []
    if not claims_for_dra_appeal:
        logger.info("No rejected claims to send to DRA.")
        safe_print("⚖️ No rejected claims to send to DRA. Skipping appeal process.")
    elif not papers_folder_path:
        logger.error("PAPERS_FOLDER not found. Skipping DRA appeal process.")
        safe_print("❌ PAPERS_FOLDER not found. Skipping DRA appeal process.")
    else:
        safe_print(f"⚖️ Sending {len(claims_for_dra_appeal)} rejected claims to Deep Requirements Analyzer for appeal...")
        new_claims_for_rejudgment = dra.run_analysis(
            claims_for_dra_appeal,
            api_manager,
            papers_folder_path
        )
        # Add source metadata
        for claim in new_claims_for_rejudgment:
            claim['_source_filename'] = claim.get('filename')
            claim['_source_type'] = 'dra_appeal'

    # --- PHASE 3: Final Judgment (on Appeals) ---
    logger.info("\n--- PHASE 3: Final Judgment (on Appeals) ---")
    safe_print("\n--- PHASE 3: Final Judgment (on Appeals) ---")

    dra_approved_count = 0
    dra_rejected_count = 0

    if not new_claims_for_rejudgment:
        logger.info("DRA did not re-submit any new claims.")
        safe_print("⚖️ DRA did not re-submit any new claims.")
    else:
        logger.info(f"DRA re-submitted {len(new_claims_for_rejudgment)} new claims. Starting final judgment...")
        safe_print(f"⚖️ DRA re-submitted {len(new_claims_for_rejudgment)} new claims. Starting final judgment...")

        for i, new_claim in enumerate(new_claims_for_rejudgment, 1):
            filename = new_claim.get('filename', 'N/A')
            claim_id_short = f"{filename[:15]}... ({new_claim['claim_id'][:6]})"
            logger.info(f"\n--- Re-Judging Claim {i}/{len(new_claims_for_rejudgment)}: {claim_id_short} ---")
            safe_print(f"\n--- Re-Judging Claim {i}/{len(new_claims_for_rejudgment)}: {claim_id_short} ---")

            try:
                sub_req_key = new_claim.get('sub_requirement', 'N/A')
                pillar_key = new_claim.get('pillar', 'N/A')
                definition_text = find_robust_sub_requirement_text(sub_req_key)

                if not definition_text:
                    logger.error(f"  Could not find definition for DRA claim. Rejecting.")
                    safe_print(f"  ❌ Could not find definition for '{sub_req_key}'. Rejecting.")
                    ruling = {"verdict": "rejected", "judge_notes": f"Rejected. (DRA Appeal) Could not find sub-requirement definition for '{sub_req_key}'."}
                else:
                    prompt = build_judge_prompt(new_claim, definition_text)
                    logger.info(f"  Submitting DRA claim to Judge AI...")
                    safe_print(f"  Submitting DRA claim to Judge AI...")
                    response = api_manager.cached_api_call(prompt, use_cache=False, is_json=True)
                    ruling = validate_judge_response(response)

                if ruling:
                    new_claim['status'] = ruling['verdict']
                    new_claim['judge_notes'] = ruling['judge_notes']
                    new_claim['judge_timestamp'] = datetime.now().isoformat()

                    if ruling['verdict'] == 'approved':
                        logger.info(f"  VERDICT (Appeal): APPROVED")
                        safe_print(f"  ✅ VERDICT (Appeal): APPROVED")
                        dra_approved_count += 1
                    else:
                        logger.info(f"  VERDICT (Appeal): REJECTED")
                        safe_print(f"  ❌ VERDICT (Appeal): REJECTED")
                        dra_rejected_count += 1

                    all_judged_claims.append(new_claim)
                else:
                    logger.error(f"  Judge AI returned invalid response for DRA claim. Claim is lost.")
                    safe_print(f"  ⚠️ Judge AI returned invalid response for DRA claim. Skipping.")

            except Exception as e:
                logger.critical(f"  CRITICAL UNHANDLED ERROR on DRA claim {new_claim['claim_id']}: {e}")
                safe_print(f"  ❌ CRITICAL ERROR on DRA claim. See log. Skipping.")

    # --- PHASE 4: Save All Results to Version History ---
    logger.info("\n--- PHASE 4: Saving Results to Version History ---")
    safe_print("\n--- PHASE 4: Saving Results to Version History ---")

    # Update existing claims
    version_history = update_claims_in_history(version_history, all_judged_claims)
    
    # Add new DRA claims
    if new_claims_for_rejudgment:
        version_history = add_new_claims_to_history(version_history, new_claims_for_rejudgment)

    # Save to version history ONLY
    save_version_history(VERSION_HISTORY_FILE, version_history)

    logger.info("\n" + "=" * 80)
    logger.info("JUDGMENT COMPLETE")
    safe_print("\n" + "=" * 80)
    safe_print("⚖️ Judgment Complete. The court is adjourned.")
    safe_print("--- Phase 1: Initial Judgment ---")
    safe_print(f"  Total Claims Judged: {init_approved_count + init_rejected_count}")
    safe_print(f"  ✅ Initial Approved: {init_approved_count}")
    safe_print(f"  ❌ Initial Rejected (Sent to DRA): {init_rejected_count}")
    safe_print("--- Phase 3: DRA Appeal Judgment ---")
    safe_print(f"  Total Claims Re-Submitted by DRA: {len(new_claims_for_rejudgment)}")
    safe_print(f"  ✅ DRA Appeal Approved: {dra_approved_count}")
    safe_print(f"  ❌ DRA Appeal Rejected: {dra_rejected_count}")
    safe_print("\n  📝 Version history updated:")
    safe_print(f"    - {VERSION_HISTORY_FILE}")
    safe_print("\n  ⚠️  Run sync_history_to_db.py to update CSV database.")

    end_time = time.time()
    logger.info(f"Total time taken: {end_time - start_time:.2f} seconds.")
    safe_print(f"Total time taken: {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    main()
```

### Testing Strategy

**Test 1: Version History Read**
```bash
# Backup existing data
cp review_version_history.json review_version_history_backup.json

# Run Judge with new code
python Judge.py

# Verify version history was updated
python -c "
import json
with open('review_version_history.json') as f:
    history = json.load(f)
    for filename, versions in history.items():
        if len(versions) > 1:
            latest = versions[-1]
            print(f'{filename}: {latest[\"changes\"][\"status\"]}')
"
```

**Test 2: No Direct Database Writes**
```bash
# Check that Judge doesn't modify CSV/JSON
md5sum neuromorphic-research_database.csv > before.md5
md5sum deep_coverage_database.json >> before.md5

python Judge.py

md5sum neuromorphic-research_database.csv > after.md5
md5sum deep_coverage_database.json >> after.md5

diff before.md5 after.md5
# Should show NO differences
```

**Test 3: Sync Flow**
```bash
# Run complete flow
python Judge.py
python sync_history_to_db.py

# Verify CSV has Judge updates
python -c "
import pandas as pd
import json

df = pd.read_csv('neuromorphic-research_database.csv')
for _, row in df.iterrows():
    reqs = json.loads(row['Requirement(s)'])
    for claim in reqs:
        if claim.get('judge_timestamp'):
            print(f'{row[\"FILENAME\"]}: {claim[\"status\"]} - {claim.get(\"judge_notes\", \"\")[:50]}')
"
```

### Rollback Plan

1. Restore backup: `cp review_version_history_backup.json review_version_history.json`
2. Revert Judge.py to v1.7
3. Document failure mode
4. Consider hybrid approach (dual write to version history + databases temporarily)

### Files to Modify

- [x] `Judge.py` (v1.7 → v2.0)
  - Add version history I/O functions
  - Refactor main() to use version history
  - Remove direct CSV/JSON writes
- [ ] `sync_history_to_db.py` (verify compatibility)

### Success Indicators

- ✅ Judge updates version history with all verdicts
- ✅ No direct writes to CSV or deep_coverage_db
- ✅ Sync script successfully propagates changes
- ✅ All claim statuses correctly tracked
- ✅ No data loss

---

## 🎫 TASK CARD #3: Implement Large Document Chunking

**Priority:** 🟡 IMPORTANT  
**Estimated Effort:** 6-8 hours  
**Risk Level:** MEDIUM  
**Dependencies:** None  
**Blocks:** Processing papers >100 pages

### Problem Statement

Judge, DRA, and Deep Reviewer lack text chunking capabilities, causing failures on large documents that exceed API token limits. Journal Reviewer has robust chunking implementation that should be replicated.

### Acceptance Criteria

**Success Metrics:**
- [ ] Successfully process 200-page documents
- [ ] No API timeout errors on large papers
- [ ] Page numbers accurately tracked across chunks
- [ ] Claims from different chunks properly merged
- [ ] No degradation in processing quality

**Technical Requirements:**
- [ ] Judge processes claims in batches (batch_size=10)
- [ ] DRA chunks text at 50,000 characters
- [ ] Deep Reviewer chunks text at 75,000 characters
- [ ] All modules track page ranges
- [ ] Chunk results properly aggregated

### Implementation Guide

This task should be split into **3 sub-tasks**, one for each module:

**Sub-Task 3A: Judge Batching**
**Sub-Task 3B: DRA Text Chunking**
**Sub-Task 3C: Deep Reviewer Chunking**

Each sub-task follows similar pattern:
1. Create chunking/batching function
2. Modify main processing loop
3. Add page number tracking
4. Test with large documents

**Detailed implementation examples provided in ARCHITECTURE_ANALYSIS.md Issue #3**

### Testing Strategy

```bash
# Test with progressively larger documents
python Judge.py  # Run on dataset with 50, 100, 150, 200 page papers
python Deep-Reviewer.py  # Same

# Monitor logs for:
# - No API timeout errors
# - Proper chunk boundaries
# - Accurate page numbers in results
```

### Files to Modify

- [ ] `Judge.py`
- [ ] `DeepRequirementsAnalyzer.py`
- [ ] `Deep-Reviewer.py`

---

## 🎫 TASK CARD #4: Design Decision - Deep Coverage Database

**Priority:** 🟢 MINOR  
**Estimated Effort:** 2-3 hours (discussion + implementation)  
**Risk Level:** LOW  
**Dependencies:** TASK CARD #2 (Version History Refactor)  
**Blocks:** None

### Problem Statement

The `deep_coverage_database.json` appears to duplicate functionality of the version history's claim tracking. With version history now as the source of truth, we need to decide if this separate database is still needed.

### Decision Points

**Option A: Merge into Version History (Recommended)**
- **Pros:**
  - Single source of truth maintained
  - Simpler data flow
  - Less duplication
  - Easier debugging
- **Cons:**
  - Version history file grows larger
  - Requires migration of existing deep_coverage_db data

**Option B: Keep Separate with Clear Purpose**
- **Pros:**
  - Deep Reviewer has dedicated workspace
  - Version history stays focused on Journal Reviewer output
  - No migration needed
- **Cons:**
  - Violates single source of truth
  - Requires sync mechanisms
  - More complex architecture

### Recommended Action

**IF Task Card #2 is completed:**
1. Analyze current `deep_coverage_database.json` content
2. Create migration script to move data to version history
3. Update Deep Reviewer to write to version history
4. Deprecate `deep_coverage_database.json`
5. Update documentation

**Implementation:** See ARCHITECTURE_ANALYSIS.md Issue #5

### Files to Potentially Modify

- [ ] `Deep-Reviewer.py`
- [ ] Create `migrate_deep_coverage.py` script
- [ ] Update ARCHITECTURE_ANALYSIS.md

---

## Summary

**Total Task Cards:** 4  
**Critical (🔴):** 2  
**Important (🟡):** 1  
**Minor (🟢):** 1  

**Recommended Execution Order:**
1. TASK CARD #1 (DRA Prompting) - Unblocks gap-filling workflow
2. TASK CARD #2 (Version History) - Foundation for data integrity
3. TASK CARD #3 (Chunking) - Scalability improvements
4. TASK CARD #4 (Design Decision) - Cleanup/optimization

**Estimated Total Effort:** 14-20 hours

---

**Document Status:** READY FOR ASSIGNMENT  
**Last Updated:** 2025-11-10  
**Maintained By:** Architecture Team
