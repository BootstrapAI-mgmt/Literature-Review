# Fresh Analysis Trigger Feature

## Overview
The Fresh Analysis Trigger feature automatically detects directory state and recommends the appropriate analysis mode (baseline vs continuation), matching CLI behavior when selecting empty or existing output directories.

## Feature Status
✅ **COMPLETE** - Production Ready

## Test Coverage
- **Unit Tests**: 13/13 passing
- **Integration Tests**: 7/7 passing
- **Total**: 20/20 passing ✅

## Usage

### For Users

1. **Navigate to Dashboard**: Open http://localhost:8000
2. **Select Output Directory Mode**: Choose "Custom Path" or "Select Existing Directory"
3. **Enter/Select Path**: Type or select your desired output directory
4. **Automatic Analysis**: Dashboard automatically analyzes the directory and shows:
   - 📁 **New Directory** → Recommends baseline mode
   - 📂 **Empty Directory** → Recommends baseline mode
   - 📄 **Contains CSV Files** → Recommends baseline mode
   - ✅ **Has Previous Results** → Recommends continuation mode
5. **Take Action**: 
   - Click "✅ Use Recommended Mode" to accept suggestion
   - Click "🔀 Choose Different Mode" to manually override

### API Usage

```bash
# Analyze directory state
curl -X POST http://localhost:8000/api/upload/analyze-directory \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key" \
  -d '{"directory_path": "/path/to/your/directory"}'

# Response
{
  "directory": "/path/to/your/directory",
  "state": {
    "state": "empty",
    "recommended_mode": "baseline",
    "file_count": 0,
    "has_gap_report": false,
    "csv_files": [],
    "last_modified": null
  },
  "recommendation": {
    "mode": "baseline",
    "reason": "Directory is empty. Will run fresh baseline analysis."
  }
}
```

## Directory States

| State | Description | Recommendation | Trigger Fresh Analysis |
|-------|-------------|----------------|----------------------|
| `not_exist` | Directory doesn't exist | Baseline | ✅ Yes |
| `empty` | Directory exists but empty | Baseline | ✅ Yes |
| `has_csv` | Has CSV files, no analysis report | Baseline | ✅ Yes |
| `has_results` | Has gap_analysis_report.json | Continuation | ❌ No |

## CLI Parity

| Scenario | CLI Behavior | Dashboard Behavior | Parity |
|----------|-------------|-------------------|--------|
| Empty folder | Fresh baseline | Fresh baseline | ✅ Match |
| Folder with CSVs | Fresh baseline | Fresh baseline | ✅ Match |
| Non-existent folder | Fresh baseline | Fresh baseline | ✅ Match |
| Folder with results | N/A | Continuation offered | ✅ Better |

## Implementation Details

### Backend Functions

**`detect_directory_state(output_dir: Path) -> Dict`**
- Analyzes directory structure and content
- Returns state information and recommendation
- Located in: `webdashboard/app.py` (lines 583-671)

**`get_recommendation_reason(state: Dict) -> str`**
- Generates human-readable recommendation text
- Located in: `webdashboard/app.py` (lines 674-685)

### API Endpoint

**`POST /api/upload/analyze-directory`**
- Request: `{"directory_path": "/path"}`
- Response: `{"directory": "...", "state": {...}, "recommendation": {...}}`
- Authentication: Requires `X-API-KEY` header
- Located in: `webdashboard/app.py` (lines 1067-1133)

### Frontend Components

**Directory State Indicator**
- HTML: `webdashboard/templates/index.html` (lines 1055-1078)
- JavaScript: `webdashboard/templates/index.html` (lines 3599-3701)
- Functions: `analyzeOutputDirectory()`, `displayDirectoryState()`

### Job Metadata

Jobs now include:
- `fresh_analysis`: Boolean flag indicating if this is a fresh baseline analysis
- `directory_state`: Full directory state information

## Security

- ✅ API key authentication required
- ✅ System directory protection (blocks `/etc`, `/bin`, etc.)
- ✅ Path traversal prevention
- ✅ Input validation on all paths

## Files Modified

1. `webdashboard/app.py` - Backend implementation
2. `webdashboard/templates/index.html` - Frontend UI
3. `tests/unit/test_fresh_analysis_trigger.py` - Unit tests (new)
4. `tests/integration/test_fresh_analysis_api.py` - Integration tests (new)

## Development

### Running Tests

```bash
# Unit tests only
pytest tests/unit/test_fresh_analysis_trigger.py -v

# Integration tests only
pytest tests/integration/test_fresh_analysis_api.py -v

# All fresh analysis tests
pytest tests/unit/test_fresh_analysis_trigger.py tests/integration/test_fresh_analysis_api.py -v
```

### Test Coverage

All tests use real filesystem operations (tempfile) for accurate validation.

## Future Enhancements

Potential improvements (not in scope for this implementation):
- Remember user's last choice (localStorage)
- Show preview of files in directory
- Estimate analysis time based on directory contents
- Batch directory analysis for multiple paths

## References

- **Task Card**: PARITY-W1-3
- **Dependency**: PARITY-W1-1 (Output Directory Selector)
- **Priority**: 🔴 CRITICAL
- **Effort**: 6-8 hours (actual: ~6 hours)

## Changelog

### v1.0.0 (2025-11-22)
- Initial implementation
- Backend directory state detection
- API endpoint for directory analysis
- Frontend UI with visual indicators
- Comprehensive test coverage (20 tests)
- Full CLI parity achieved
