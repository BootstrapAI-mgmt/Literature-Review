# ENHANCE-P5-4: Add Multi-Select Pillar Support to Interactive Prompts

**Category:** Interactive Prompts Enhancement  
**Priority:** 🟢 LOW  
**Effort:** 2 hours  
**Created:** November 17, 2025  
**Source:** PR #46 Review - Deferred Items Section #4

---

## Problem Statement

Current pillar selection only supports choosing one pillar or ALL. Users cannot select a custom subset of pillars (e.g., "just pillars 1, 3, and 5").

**Current Behavior:**
- Radio buttons: ALL, DEEP, individual pillars, NONE
- Terminal mode allows comma-separated: `"1,3,5"` → `[pillar1, pillar3, pillar5]`
- Dashboard only supports single selection or ALL

**Gap:** Dashboard lacks feature parity with terminal mode for pillar subset selection.

---

## Use Cases

### 1. Targeted Analysis
**Scenario:** User testing specific pillars  
**Current:** Must run ALL (wasteful) or one at a time (tedious)  
**Desired:** Select pillars 1, 3, 5 → run only those three

### 2. Incremental Testing
**Scenario:** Developer debugging new pillar logic  
**Current:** Test one pillar at a time, restart job each time  
**Desired:** Select multiple pillars to test together

### 3. Research Focus
**Scenario:** User only cares about methodology and results sections  
**Current:** Run all 10 pillars, ignore 8 of them  
**Desired:** Select just "Methodology" and "Results Analysis" pillars

### 4. Resource Optimization
**Scenario:** Limited API budget, want to analyze subset  
**Current:** All-or-nothing approach wastes resources  
**Desired:** Cherry-pick high-priority pillars

---

## Acceptance Criteria

- [ ] Checkbox UI for pillar selection (replaces radio buttons)
- [ ] Multi-select response parsing (array of pillar names)
- [ ] Orchestrator handles pillar subsets correctly
- [ ] "Select All" / "Clear All" convenience buttons
- [ ] Validation: at least one pillar selected (or NONE chosen)
- [ ] Backward compatibility: "ALL" option still works
- [ ] Terminal mode parity: supports same selections as comma-separated input

---

## UI Design

### Current UI (Radio Buttons)

```html
<div class="form-check">
    <input type="radio" name="pillar" value="ALL" checked>
    <label>ALL - Run all pillars</label>
</div>
<div class="form-check">
    <input type="radio" name="pillar" value="DEEP">
    <label>DEEP - Only deep review pillar</label>
</div>
<div class="form-check">
    <input type="radio" name="pillar" value="P1: Pillar 1">
    <label>1. Pillar 1</label>
</div>
<!-- ... more pillars ... -->
<div class="form-check">
    <input type="radio" name="pillar" value="NONE">
    <label>NONE - Skip pillar analysis</label>
</div>
```

### New UI (Checkboxes with Helpers)

```html
<div class="d-flex justify-content-between mb-3">
    <div>
        <button type="button" class="btn btn-sm btn-outline-primary" onclick="selectAllPillars()">
            <i class="bi bi-check-square"></i> Select All
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary" onclick="clearAllPillars()">
            <i class="bi bi-square"></i> Clear All
        </button>
    </div>
    <div>
        <span id="pillar-count" class="badge bg-info">0 selected</span>
    </div>
</div>

<hr>

<!-- Special options (mutually exclusive with individual pillars) -->
<div class="form-check">
    <input type="checkbox" class="form-check-input special-option" 
           id="pillar-all" value="ALL" onchange="handleSpecialOption('ALL')">
    <label class="form-check-label fw-bold" for="pillar-all">
        ALL - Run all pillars
    </label>
</div>
<div class="form-check">
    <input type="checkbox" class="form-check-input special-option" 
           id="pillar-deep" value="DEEP" onchange="handleSpecialOption('DEEP')">
    <label class="form-check-label fw-bold" for="pillar-deep">
        DEEP - Only deep review pillar
    </label>
</div>
<div class="form-check mb-2">
    <input type="checkbox" class="form-check-input special-option" 
           id="pillar-none" value="NONE" onchange="handleSpecialOption('NONE')">
    <label class="form-check-label fw-bold" for="pillar-none">
        NONE - Skip pillar analysis
    </label>
</div>

<hr>

<!-- Individual pillars -->
<div id="individual-pillars">
    <div class="form-check">
        <input type="checkbox" class="form-check-input pillar-checkbox" 
               id="pillar-1" value="P1: Pillar 1" onchange="updatePillarCount()">
        <label class="form-check-label" for="pillar-1">
            1. Pillar 1
        </label>
    </div>
    <div class="form-check">
        <input type="checkbox" class="form-check-input pillar-checkbox" 
               id="pillar-2" value="P2: Pillar 2" onchange="updatePillarCount()">
        <label class="form-check-label" for="pillar-2">
            2. Pillar 2
        </label>
    </div>
    <!-- ... more pillars ... -->
</div>
```

---

## Implementation Plan

### 1. Update UI Component

**File:** `webdashboard/templates/index.html`

```javascript
function renderPillarSelectionPrompt(promptData) {
    const pillars = promptData.pillars || [];
    
    let html = `
        <div class="pillar-selection-container">
            <!-- Helper buttons -->
            <div class="d-flex justify-content-between mb-3">
                <div>
                    <button type="button" class="btn btn-sm btn-outline-primary" 
                            onclick="selectAllPillars()">
                        <i class="bi bi-check-square"></i> Select All
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" 
                            onclick="clearAllPillars()">
                        <i class="bi bi-square"></i> Clear All
                    </button>
                </div>
                <div>
                    <span id="pillar-count" class="badge bg-info">0 selected</span>
                </div>
            </div>
            
            <hr>
            
            <!-- Special options -->
            <div class="form-check">
                <input type="checkbox" class="form-check-input special-option" 
                       id="pillar-all" value="ALL" onchange="handleSpecialOption('ALL')">
                <label class="form-check-label fw-bold" for="pillar-all">
                    ALL - Run all pillars
                </label>
            </div>
            <div class="form-check">
                <input type="checkbox" class="form-check-input special-option" 
                       id="pillar-deep" value="DEEP" onchange="handleSpecialOption('DEEP')">
                <label class="form-check-label fw-bold" for="pillar-deep">
                    DEEP - Only deep review pillar
                </label>
            </div>
            <div class="form-check mb-2">
                <input type="checkbox" class="form-check-input special-option" 
                       id="pillar-none" value="NONE" onchange="handleSpecialOption('NONE')">
                <label class="form-check-label fw-bold" for="pillar-none">
                    NONE - Skip pillar analysis
                </label>
            </div>
            
            <hr>
            
            <!-- Individual pillars -->
            <div id="individual-pillars">
    `;
    
    pillars.forEach((pillar, index) => {
        html += `
            <div class="form-check">
                <input type="checkbox" class="form-check-input pillar-checkbox" 
                       id="pillar-${index}" value="${pillar}" 
                       onchange="updatePillarCount()">
                <label class="form-check-label" for="pillar-${index}">
                    ${index + 1}. ${pillar}
                </label>
            </div>
        `;
    });
    
    html += `
            </div>
        </div>
    `;
    
    return html;
}

function selectAllPillars() {
    // Uncheck special options
    $('.special-option').prop('checked', false);
    
    // Check all individual pillars
    $('.pillar-checkbox').prop('checked', true);
    updatePillarCount();
}

function clearAllPillars() {
    // Uncheck everything
    $('.special-option, .pillar-checkbox').prop('checked', false);
    updatePillarCount();
}

function handleSpecialOption(option) {
    const checkbox = $(`#pillar-${option.toLowerCase()}`);
    
    if (checkbox.is(':checked')) {
        // Uncheck all other options (special and individual)
        $('.special-option, .pillar-checkbox').not(checkbox).prop('checked', false);
    }
    
    updatePillarCount();
}

function updatePillarCount() {
    // Count selected individual pillars
    const selectedPillars = $('.pillar-checkbox:checked').length;
    
    // Check if special option selected
    const specialSelected = $('.special-option:checked').val();
    
    if (specialSelected) {
        $('#pillar-count').text(specialSelected).removeClass('bg-info').addClass('bg-primary');
    } else if (selectedPillars > 0) {
        $('#pillar-count').text(`${selectedPillars} selected`)
                          .removeClass('bg-primary').addClass('bg-info');
    } else {
        $('#pillar-count').text('0 selected').removeClass('bg-primary').addClass('bg-secondary');
    }
}

function getSelectedPillars() {
    // Check for special options first
    const specialOption = $('.special-option:checked').val();
    if (specialOption) {
        return specialOption;  // Return "ALL", "DEEP", or "NONE"
    }
    
    // Otherwise, return array of selected individual pillars
    const selected = [];
    $('.pillar-checkbox:checked').each(function() {
        selected.push($(this).val());
    });
    
    // Validation
    if (selected.length === 0) {
        alert('Please select at least one pillar or choose a special option');
        return null;
    }
    
    return selected;  // Returns array like ["P1: Pillar 1", "P3: Pillar 3"]
}
```

---

### 2. Update Response Handling

**File:** `webdashboard/templates/index.html`

```javascript
function submitPromptResponse(promptId) {
    const promptType = currentPrompt.type;
    let response;
    
    if (promptType === 'pillar_selection') {
        response = getSelectedPillars();
        if (response === null) {
            return;  // Validation failed
        }
    } else {
        // Other prompt types (run_mode, continue, etc.)
        response = $('input[name="' + promptType + '"]:checked').val();
    }
    
    // Send to server
    fetch(`/api/prompts/${promptId}/response`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({response: response})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            $('#prompt-modal').modal('hide');
        }
    });
}
```

---

### 3. Update Backend to Handle Arrays

**File:** `webdashboard/prompt_handler.py`

```python
async def request_user_input(
    self,
    job_id: str,
    prompt_type: str,
    prompt_data: dict,
    timeout_seconds: int = 300
) -> Union[str, List[str]]:  # Can return string OR list
    """
    Request user input via prompt
    
    Returns:
        str: For single-value prompts (run_mode, continue, etc.)
        List[str]: For multi-select prompts (pillar_selection with subset)
    """
    # ... existing code ...
    
    result = await future
    
    # Return type depends on response structure
    if isinstance(result, list):
        return result  # Multi-select pillar subset
    else:
        return result  # Single value (ALL, DEEP, NONE, run_mode, etc.)
```

**File:** `pipeline_orchestrator.py`

```python
async def handle_pillar_selection(config):
    """Handle pillar selection from user prompt"""
    if config.prompt_callback:
        pillar_response = await config.prompt_callback(
            prompt_type="pillar_selection",
            prompt_data={"message": "Select which pillars to analyze", "pillars": [...]}
        )
        
        # Handle different response types
        if isinstance(pillar_response, str):
            # Special options: "ALL", "DEEP", "NONE"
            if pillar_response == "ALL":
                return load_all_pillars()
            elif pillar_response == "DEEP":
                return [get_deep_review_pillar()]
            elif pillar_response == "NONE":
                return []
            else:
                # Single pillar selected (backward compatibility)
                return [load_pillar(pillar_response)]
        
        elif isinstance(pillar_response, list):
            # Multi-select: ["P1: Pillar 1", "P3: Pillar 3", "P5: Pillar 5"]
            return [load_pillar(p) for p in pillar_response]
        
        else:
            raise ValueError(f"Invalid pillar_response type: {type(pillar_response)}")
    
    # Fallback to config
    return config.selected_pillars or load_all_pillars()
```

---

### 4. Update Tests

**File:** `tests/integration/test_interactive_prompts.py`

```python
@pytest.mark.asyncio
async def test_multi_select_pillars():
    """Test multi-select pillar selection"""
    handler = PromptHandler()
    
    # Request pillar selection
    future = handler.request_user_input(
        job_id="test_job",
        prompt_type="pillar_selection",
        prompt_data={"message": "Select pillars", "pillars": ["Pillar 1", "Pillar 2", "Pillar 3"]},
        timeout_seconds=300
    )
    
    # Simulate user selecting multiple pillars
    prompt_id = list(handler.pending_prompts.keys())[0]
    await handler.submit_response(prompt_id, ["P1: Pillar 1", "P3: Pillar 3"])
    
    result = await future
    
    # Verify multi-select response
    assert isinstance(result, list)
    assert len(result) == 2
    assert "P1: Pillar 1" in result
    assert "P3: Pillar 3" in result

@pytest.mark.asyncio
async def test_special_option_all():
    """Test ALL special option still works"""
    handler = PromptHandler()
    
    future = handler.request_user_input(
        job_id="test_job",
        prompt_type="pillar_selection",
        prompt_data={"message": "Select pillars"},
        timeout_seconds=300
    )
    
    prompt_id = list(handler.pending_prompts.keys())[0]
    await handler.submit_response(prompt_id, "ALL")
    
    result = await future
    
    # Verify ALL option returns string (not list)
    assert isinstance(result, str)
    assert result == "ALL"

@pytest.mark.asyncio
async def test_validation_no_pillars_selected():
    """Test validation when no pillars selected"""
    # UI validation should prevent this, but test backend handling
    handler = PromptHandler()
    
    future = handler.request_user_input(
        job_id="test_job",
        prompt_type="pillar_selection",
        prompt_data={"message": "Select pillars"},
        timeout_seconds=300
    )
    
    prompt_id = list(handler.pending_prompts.keys())[0]
    
    # Try to submit empty list
    with pytest.raises(ValueError, match="At least one pillar must be selected"):
        await handler.submit_response(prompt_id, [])
```

---

## Validation Logic

### Client-Side (JavaScript)

```javascript
function validatePillarSelection() {
    const specialOption = $('.special-option:checked').val();
    const individualPillars = $('.pillar-checkbox:checked').length;
    
    if (!specialOption && individualPillars === 0) {
        alert('Please select at least one pillar or choose a special option (ALL, DEEP, NONE)');
        return false;
    }
    
    return true;
}
```

### Server-Side (Python)

```python
async def submit_response(self, prompt_id: str, response: Union[str, List[str]]) -> bool:
    """Validate and submit prompt response"""
    
    prompt_info = self.pending_prompts[prompt_id]
    
    # Validation for pillar_selection
    if prompt_info['type'] == 'pillar_selection':
        if isinstance(response, list):
            if len(response) == 0:
                raise ValueError("At least one pillar must be selected")
            # Validate each pillar exists
            valid_pillars = prompt_info['data'].get('pillars', [])
            for pillar in response:
                if pillar not in [f"P{i+1}: {p}" for i, p in enumerate(valid_pillars)]:
                    raise ValueError(f"Invalid pillar: {pillar}")
        elif isinstance(response, str):
            if response not in ['ALL', 'DEEP', 'NONE']:
                raise ValueError(f"Invalid special option: {response}")
    
    # ... rest of validation ...
```

---

## Backward Compatibility

### Old Jobs with Single Pillar
```python
# Orchestrator handles both formats
if isinstance(pillar_response, str):
    # Old format: "P1: Pillar 1" or "ALL"
    pillars = handle_single_pillar(pillar_response)
elif isinstance(pillar_response, list):
    # New format: ["P1: Pillar 1", "P3: Pillar 3"]
    pillars = handle_multi_select(pillar_response)
```

### Terminal Mode Compatibility
```python
# Terminal mode already supports comma-separated
# "1,3,5" → ["P1: ...", "P3: ...", "P5: ..."]
# Dashboard now matches this behavior
```

---

## Testing Plan

### Unit Tests
1. Multi-select response parsing
2. Special option handling (ALL, DEEP, NONE)
3. Validation (empty selection, invalid pillars)
4. Backward compatibility (single pillar strings)

### Integration Tests
1. Full workflow: prompt → multi-select → orchestrator handles subset
2. UI: Select All button → all pillars checked
3. UI: Clear All button → no pillars checked
4. UI: Select special option → individual pillars disabled

### Manual Testing
1. Start job → pillar prompt appears
2. Click "Select All" → verify all checked, count updates
3. Click "Clear All" → verify none checked
4. Select pillars 1, 3, 5 → verify count shows "3 selected"
5. Select "ALL" → verify individual pillars unchecked
6. Submit with no selection → verify validation error

---

## UI/UX Considerations

### Visual Feedback
- **Badge color:** Info (blue) for individual pillars, Primary (darker blue) for special options
- **Count display:** Updates in real-time as user selects/deselects
- **Disabled state:** Individual pillars grayed out when special option selected

### Accessibility
- All checkboxes have proper labels
- Keyboard navigation works (Tab, Space to toggle)
- Screen reader announces count changes

### Mobile Responsiveness
- Buttons stack vertically on small screens
- Checkboxes have larger touch targets
- Scrollable pillar list if many pillars

---

## Estimated Breakdown

- **UI component updates:** 1 hour
  - Checkbox rendering: 20 min
  - Helper buttons: 15 min
  - Validation: 15 min
  - Styling: 10 min
- **Backend updates:** 30 minutes
  - Response parsing: 15 min
  - Orchestrator handling: 15 min
- **Testing:** 30 minutes
- **Total:** 2 hours

---

## Dependencies

**Requires:**
- ✅ `prompt_handler.py` (done in PR #46)
- ✅ Pillar selection prompt UI (done in PR #46)

**Synergy:**
- Works with ENHANCE-P5-3 (Prompt History) - records multi-select choices
- Complements ENHANCE-P5-2 (run_mode prompts) - similar UX pattern

---

## Success Metrics

- [ ] Users can select custom pillar subsets (e.g., 2, 4, 7)
- [ ] "Select All" / "Clear All" buttons work correctly
- [ ] Special options (ALL, DEEP, NONE) still functional
- [ ] Validation prevents empty selection
- [ ] Backward compatible with single pillar selection
- [ ] Feature parity with terminal mode achieved
