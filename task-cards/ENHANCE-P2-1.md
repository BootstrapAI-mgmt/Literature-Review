# ENHANCE-P2-1: Cross-Batch Duplicate Detection

**Status:** NOT IMPLEMENTED  
**Priority:** 🟢 Low  
**Effort Estimate:** 3 hours  
**Category:** Phase 2 - Input Handling  
**Created:** November 17, 2025  
**Related PR:** #36 (Input Handling & PDF Upload)

---

## 📋 Overview

Add duplicate detection across multiple upload batches to prevent users from accidentally uploading the same PDF multiple times in different sessions.

**Use Case:**
- User uploads `paper1.pdf` on Monday
- On Wednesday, forgets and uploads `paper1.pdf` again
- System should detect: "This paper already exists in your database"

**Current Limitation:**
- Deduplication only works within a single upload batch
- Same PDF uploaded in different batches creates duplicate entries
- No warning to user about existing papers

---

## 🎯 Acceptance Criteria

### Must Have
- [ ] Check existing database for duplicates before inserting new papers
- [ ] User warning UI: "3 of 5 papers already exist. Skip or re-upload?"
- [ ] Option to skip duplicates or force re-upload (overwrite)

### Should Have
- [ ] Duplicate detection methods:
  - PDF hash (MD5/SHA256 of file content)
  - Title exact match
  - Title fuzzy match (>90% similarity)
- [ ] Show which existing papers match (job ID, upload date)

### Nice to Have
- [ ] Bulk action: "Skip all duplicates" or "Overwrite all"
- [ ] Duplicate preview: side-by-side comparison of metadata
- [ ] Statistics: "You have 50 papers, 12 are duplicates"

---

## 🛠️ Technical Implementation

### 1. Backend: Duplicate Detection Logic

**New Function:** `check_for_duplicates()`

```python
import hashlib
from difflib import SequenceMatcher

def compute_pdf_hash(file_path):
    """Compute SHA256 hash of PDF file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def check_for_duplicates(new_papers, existing_database):
    """
    Check if new papers already exist in database
    
    Returns:
        dict: {
            'duplicates': [list of duplicate papers],
            'new': [list of truly new papers],
            'matches': {new_paper_id: existing_paper_id}
        }
    """
    duplicates = []
    new = []
    matches = {}
    
    # Build lookup structures for existing papers
    existing_hashes = {p['hash']: p for p in existing_database if 'hash' in p}
    existing_titles = {p['title'].lower(): p for p in existing_database}
    
    for paper in new_papers:
        # Method 1: Hash match (most reliable)
        paper_hash = compute_pdf_hash(paper['file_path'])
        paper['hash'] = paper_hash
        
        if paper_hash in existing_hashes:
            duplicates.append(paper)
            matches[paper['id']] = existing_hashes[paper_hash]['id']
            continue
        
        # Method 2: Exact title match
        if paper['title'].lower() in existing_titles:
            duplicates.append(paper)
            matches[paper['id']] = existing_titles[paper['title'].lower()]['id']
            continue
        
        # Method 3: Fuzzy title match (optional)
        for existing_title, existing_paper in existing_titles.items():
            similarity = SequenceMatcher(None, paper['title'].lower(), existing_title).ratio()
            if similarity > 0.95:  # 95% similarity threshold
                duplicates.append(paper)
                matches[paper['id']] = existing_paper['id']
                break
        else:
            # No match found, this is new
            new.append(paper)
    
    return {
        'duplicates': duplicates,
        'new': new,
        'matches': matches
    }
```

### 2. Backend: Upload Endpoint Enhancement

**Modified Route:** `POST /api/upload`

```python
@app.route('/api/upload', methods=['POST'])
def upload_papers():
    """Upload PDFs with duplicate detection"""
    files = request.files.getlist('files')
    
    # Extract metadata from PDFs
    new_papers = []
    for file in files:
        file_path = save_temp_file(file)
        metadata = extract_pdf_metadata(file_path)
        metadata['file_path'] = file_path
        new_papers.append(metadata)
    
    # Load existing database
    existing_database = load_review_log()
    
    # Check for duplicates
    duplicate_check = check_for_duplicates(new_papers, existing_database)
    
    if duplicate_check['duplicates']:
        # Return duplicate warning to user
        return jsonify({
            'status': 'duplicates_found',
            'duplicates': duplicate_check['duplicates'],
            'new': duplicate_check['new'],
            'matches': duplicate_check['matches'],
            'message': f"{len(duplicate_check['duplicates'])} of {len(new_papers)} papers already exist"
        }), 200
    else:
        # No duplicates, proceed with upload
        save_papers_to_database(duplicate_check['new'])
        return jsonify({
            'status': 'success',
            'uploaded': len(duplicate_check['new'])
        }), 200

@app.route('/api/upload/confirm', methods=['POST'])
def confirm_upload():
    """Confirm upload after duplicate warning"""
    data = request.json
    action = data['action']  # 'skip_duplicates' or 'overwrite_all'
    papers = data['papers']
    
    if action == 'skip_duplicates':
        # Only upload new papers
        new_papers = [p for p in papers if not p.get('is_duplicate')]
        save_papers_to_database(new_papers)
        return jsonify({'status': 'success', 'uploaded': len(new_papers)})
    
    elif action == 'overwrite_all':
        # Upload all papers, overwriting duplicates
        save_papers_to_database(papers, overwrite=True)
        return jsonify({'status': 'success', 'uploaded': len(papers)})
    
    else:
        return jsonify({'error': 'Invalid action'}), 400
```

### 3. Frontend: Duplicate Warning Modal

**Location:** `webdashboard/templates/index.html`

```html
<!-- Duplicate Warning Modal -->
<div class="modal" id="duplicateWarningModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-warning text-dark">
                <h5 class="modal-title">⚠️ Duplicate Papers Detected</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <p class="alert alert-warning">
                    <strong><span id="duplicate-count">0</span> of <span id="total-count">0</span> papers already exist</strong> in your database.
                </p>
                
                <h6>Duplicates Found:</h6>
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Paper Title</th>
                            <th>Match Type</th>
                            <th>Existing Upload Date</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="duplicate-list">
                        <!-- Populated dynamically -->
                    </tbody>
                </table>
                
                <h6 class="mt-3">New Papers (<span id="new-count">0</span>):</h6>
                <ul id="new-papers-list">
                    <!-- Populated dynamically -->
                </ul>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" data-bs-dismiss="modal">Cancel Upload</button>
                <button class="btn btn-primary" onclick="handleDuplicates('skip_duplicates')">
                    Skip Duplicates (Upload <span id="new-count-btn">0</span> New)
                </button>
                <button class="btn btn-danger" onclick="handleDuplicates('overwrite_all')">
                    Overwrite All
                </button>
            </div>
        </div>
    </div>
</div>
```

**JavaScript:**
```javascript
async function uploadPapers(files) {
    const formData = new FormData();
    for (let file of files) {
        formData.append('files', file);
    }
    
    const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    
    if (data.status === 'duplicates_found') {
        // Show duplicate warning modal
        showDuplicateWarning(data);
    } else if (data.status === 'success') {
        // Upload successful
        showSuccess(`Uploaded ${data.uploaded} papers`);
        refreshPaperList();
    }
}

function showDuplicateWarning(data) {
    document.getElementById('duplicate-count').textContent = data.duplicates.length;
    document.getElementById('total-count').textContent = data.duplicates.length + data.new.length;
    document.getElementById('new-count').textContent = data.new.length;
    document.getElementById('new-count-btn').textContent = data.new.length;
    
    // Populate duplicate list
    const tbody = document.getElementById('duplicate-list');
    tbody.innerHTML = '';
    for (let dup of data.duplicates) {
        const existingId = data.matches[dup.id];
        const row = `
            <tr>
                <td>${dup.title}</td>
                <td><span class="badge bg-warning">Hash Match</span></td>
                <td>${getUploadDate(existingId)}</td>
                <td>
                    <input type="checkbox" checked> Skip
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    }
    
    // Populate new papers list
    const newList = document.getElementById('new-papers-list');
    newList.innerHTML = '';
    for (let paper of data.new) {
        newList.innerHTML += `<li>${paper.title}</li>`;
    }
    
    // Store data for confirmation
    window.uploadData = data;
    
    // Show modal
    new bootstrap.Modal(document.getElementById('duplicateWarningModal')).show();
}

async function handleDuplicates(action) {
    const response = await fetch('/api/upload/confirm', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            action: action,
            papers: action === 'skip_duplicates' 
                ? window.uploadData.new 
                : [...window.uploadData.new, ...window.uploadData.duplicates]
        })
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
        showSuccess(`Uploaded ${data.uploaded} papers`);
        refreshPaperList();
        bootstrap.Modal.getInstance(document.getElementById('duplicateWarningModal')).hide();
    }
}
```

---

## 🧪 Testing Strategy

### Unit Tests

**File:** `tests/unit/test_duplicate_detection.py`

```python
def test_hash_based_duplicate_detection():
    """Test PDF hash duplicate detection"""
    # Create two identical PDFs
    pdf1 = create_test_pdf("Test Paper", "content")
    pdf2 = create_test_pdf("Test Paper", "content")  # Same content
    
    hash1 = compute_pdf_hash(pdf1)
    hash2 = compute_pdf_hash(pdf2)
    
    assert hash1 == hash2

def test_title_exact_match():
    """Test exact title matching"""
    new_papers = [{'title': 'Machine Learning Survey', 'id': 'new1'}]
    existing = [{'title': 'Machine Learning Survey', 'id': 'existing1'}]
    
    result = check_for_duplicates(new_papers, existing)
    
    assert len(result['duplicates']) == 1
    assert len(result['new']) == 0
    assert result['matches']['new1'] == 'existing1'

def test_fuzzy_title_match():
    """Test fuzzy title matching (95% threshold)"""
    new_papers = [{'title': 'A Survey of Machine Learning', 'id': 'new1'}]
    existing = [{'title': 'Survey of Machine Learning', 'id': 'existing1'}]
    
    result = check_for_duplicates(new_papers, existing)
    
    assert len(result['duplicates']) == 1  # Should match

def test_no_duplicates():
    """Test when no duplicates exist"""
    new_papers = [{'title': 'New Paper', 'id': 'new1'}]
    existing = [{'title': 'Existing Paper', 'id': 'existing1'}]
    
    result = check_for_duplicates(new_papers, existing)
    
    assert len(result['duplicates']) == 0
    assert len(result['new']) == 1

def test_mixed_duplicates_and_new():
    """Test batch with both duplicates and new papers"""
    new_papers = [
        {'title': 'Duplicate Paper', 'id': 'new1'},
        {'title': 'New Paper', 'id': 'new2'},
        {'title': 'Another Duplicate', 'id': 'new3'}
    ]
    existing = [
        {'title': 'Duplicate Paper', 'id': 'existing1'},
        {'title': 'Another Duplicate', 'id': 'existing2'}
    ]
    
    result = check_for_duplicates(new_papers, existing)
    
    assert len(result['duplicates']) == 2
    assert len(result['new']) == 1
    assert result['new'][0]['title'] == 'New Paper'
```

### Integration Tests

**File:** `tests/integration/test_upload_with_duplicates.py`

```python
def test_upload_with_duplicates(client):
    """Test upload endpoint with duplicate papers"""
    # Pre-populate database
    create_existing_paper(title="Existing Paper 1")
    
    # Upload batch with duplicate
    files = [
        create_test_pdf("Existing Paper 1"),  # Duplicate
        create_test_pdf("New Paper 1")  # New
    ]
    
    response = client.post('/api/upload', data={'files': files})
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'duplicates_found'
    assert len(data['duplicates']) == 1
    assert len(data['new']) == 1

def test_skip_duplicates_action(client):
    """Test skip duplicates action"""
    papers = [
        {'title': 'New Paper', 'is_duplicate': False},
        {'title': 'Duplicate Paper', 'is_duplicate': True}
    ]
    
    response = client.post('/api/upload/confirm', json={
        'action': 'skip_duplicates',
        'papers': papers
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['uploaded'] == 1  # Only new paper uploaded

def test_overwrite_all_action(client):
    """Test overwrite all action"""
    papers = [
        {'title': 'New Paper', 'is_duplicate': False},
        {'title': 'Duplicate Paper', 'is_duplicate': True}
    ]
    
    response = client.post('/api/upload/confirm', json={
        'action': 'overwrite_all',
        'papers': papers
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['uploaded'] == 2  # Both papers uploaded
```

---

## 📚 Documentation Updates

### User Guide Addition

**File:** `docs/DASHBOARD_GUIDE.md`

**New Section:**
```markdown
## Duplicate Paper Detection

### Automatic Detection

When uploading PDFs, the dashboard automatically checks for duplicates using:

1. **PDF Hash**: Exact file content match (most reliable)
2. **Title Match**: Exact title match (case-insensitive)
3. **Fuzzy Match**: Similar titles (≥95% similarity)

### Handling Duplicates

If duplicates are detected, you'll see a warning modal:

**Options:**
- **Skip Duplicates**: Upload only new papers (recommended)
- **Overwrite All**: Replace existing papers with new uploads
- **Cancel**: Abort upload

**Example:**
```
⚠️ Duplicate Papers Detected
3 of 5 papers already exist

Duplicates:
- "Machine Learning Survey" (uploaded Nov 10, 2025)
- "Deep Learning Review" (uploaded Nov 12, 2025)

New Papers (2):
- "Transformer Models"
- "Attention Mechanisms"

Action: Skip Duplicates → Only upload 2 new papers
```

### Why Duplicates Matter

- **Avoid redundancy**: Don't waste storage/analysis time on same paper
- **Maintain data quality**: Prevent duplicate entries in gap analysis
- **Save costs**: Skip re-processing same papers

### Manual Cleanup

If duplicates slip through, use Smart Deduplication feature:
```bash
python scripts/deduplicate_papers.py --threshold 0.90
```
```

---

## 🚀 Deployment Notes

### Performance Considerations

**Hash Computation:**
- PDF hash: ~50ms per file (acceptable for <50 files)
- For large batches (>100 files), consider async processing

**Database Lookup:**
- Current implementation: O(n) scan of existing papers
- For >1000 papers, add hash index for O(1) lookup

### Storage Changes

**Updated Schema:** `review_log.json`
```json
{
  "papers": [
    {
      "id": "paper_123",
      "title": "Machine Learning Survey",
      "hash": "sha256:abc123...",  // NEW: PDF hash
      "upload_date": "2025-11-17T10:30:00",
      "metadata": {...}
    }
  ]
}
```

**Migration:**
- Existing papers without hash: compute on first load
- Hash computation is one-time per paper

---

## 🔗 Related Issues

- PR #36: Input Handling & PDF Upload (foundation)
- PR #47: Smart Deduplication (complementary within-batch dedup)
- Future: Automatic deduplication on upload (no user prompt)

---

## 📈 Success Metrics

**User Impact:**
- Prevent accidental re-uploads
- Save time (no re-processing duplicates)
- Cleaner database (no duplicate entries)

**Technical Metrics:**
- Hash computation: <50ms per PDF
- Duplicate check: <100ms for 100 existing papers
- False positive rate: <1% (fuzzy matching threshold tuning)

---

## ✅ Definition of Done

- [ ] Backend: `check_for_duplicates()` function implemented
- [ ] Backend: `compute_pdf_hash()` function implemented
- [ ] Backend: `/api/upload` endpoint enhanced with duplicate check
- [ ] Backend: `/api/upload/confirm` endpoint for user action
- [ ] Frontend: Duplicate warning modal UI
- [ ] Frontend: Skip/Overwrite action handlers
- [ ] Unit tests (≥90% coverage)
- [ ] Integration tests (upload with duplicates)
- [ ] Documentation updated (DASHBOARD_GUIDE.md)
- [ ] Manual testing with real PDFs
- [ ] Code review approved
- [ ] Merged to main branch
