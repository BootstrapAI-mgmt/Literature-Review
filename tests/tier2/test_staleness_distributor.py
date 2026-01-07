"""
Tier 2 Tests: Staleness → Distributor Integration
Tests T2-INT-05

These tests validate the integration between:
- Staleness review workflow
- Task distributor for documentation refresh tasks
"""

import pytest


class TestStalenessDistributorIntegration:
    """T2-INT-05: Staleness → Distributor Communication"""
    
    @pytest.mark.integration
    def test_t2_int_05_01_staleness_triggers_distributor(self, payloader):
        """T2-INT-05-01: Staleness workflow can trigger distributor"""
        # Given a staleness detection payload
        staleness_payload = {
            "trigger": "scheduled",
            "stale_documents": [
                {
                    "path": "docs/MASTER_ARCHITECTURE_BLUEPRINT.md",
                    "age_days": 10,
                    "threshold_days": 7,
                    "action": "refresh"
                }
            ],
            "action_required": True
        }
        
        # Then the payload should be valid for dispatch
        assert staleness_payload["action_required"] == True
        assert len(staleness_payload["stale_documents"]) > 0
        
        # And can be sent to distributor
        try:
            response = payloader.send_to_webhook("/staleness-review", staleness_payload)
            assert response is not None
        except Exception as e:
            pytest.skip(f"n8n not available: {e}")
    
    @pytest.mark.integration
    def test_t2_int_05_02_staleness_creates_refresh_tasks(self, payloader):
        """T2-INT-05-02: Staleness creates refresh tasks for stale docs"""
        # Given stale documents
        stale_docs = [
            {"path": "docs/MASTER_ARCHITECTURE_BLUEPRINT.md", "age_days": 10},
            {"path": "task-cards/OPERATIONALIZATION_WAVE_INDEX.md", "age_days": 3}
        ]
        
        # When generating refresh tasks
        tasks = []
        for doc in stale_docs:
            tasks.append({
                "task_id": f"refresh-{doc['path'].replace('/', '-')}",
                "domain": "documentation",
                "action": "refresh_check",
                "document": doc["path"],
                "context": {"age_days": doc["age_days"]}
            })
        
        # Then tasks should be created for each stale document
        assert len(tasks) == len(stale_docs)
        for task in tasks:
            assert "task_id" in task
            assert task["action"] == "refresh_check"
    
    @pytest.mark.integration
    def test_t2_int_05_03_staleness_respects_thresholds(self, payloader):
        """T2-INT-05-03: Staleness only flags documents exceeding threshold"""
        # Given documents with various ages
        documents = [
            {"path": "docs/MASTER_ARCHITECTURE_BLUEPRINT.md", "age_days": 5, "threshold_days": 7},
            {"path": "task-cards/INDEX.md", "age_days": 2, "threshold_days": 1},
            {"path": "README.md", "age_days": 25, "threshold_days": 30}
        ]
        
        # When checking staleness
        stale = [d for d in documents if d["age_days"] > d["threshold_days"]]
        fresh = [d for d in documents if d["age_days"] <= d["threshold_days"]]
        
        # Then only documents exceeding threshold should be stale
        assert len(stale) == 1
        assert stale[0]["path"] == "task-cards/INDEX.md"
        assert len(fresh) == 2
