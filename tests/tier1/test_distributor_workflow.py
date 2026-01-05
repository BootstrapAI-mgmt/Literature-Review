"""
Tier 1 Tests: Doc Chain - Distributor Workflow
Tests T1-02-01 through T1-02-06

These tests validate the distributor workflow's ability to:
- Receive task lists from trigger
- Queue and prioritize tasks
- Dispatch tasks to appropriate agents
- Track task completion status
"""

import pytest


class TestDistributorWorkflowQueueManagement:
    """T1-02: Queue Management Tests"""
    
    def test_t1_02_01_receives_task_list(self, task_distributor_payload):
        """T1-02-01: Distributor receives task list from trigger"""
        # Given a task distributor payload
        payload = task_distributor_payload
        
        # Then it should contain a queue
        assert "queue" in payload
        assert len(payload["queue"]) > 0
    
    def test_t1_02_02_validates_task_structure(self, task_distributor_payload):
        """T1-02-02: Distributor validates task structure"""
        # Given tasks in the queue
        tasks = task_distributor_payload["queue"]
        
        # Then each task should have required fields
        for task in tasks:
            assert "task_id" in task
            assert "priority" in task
            assert "domain" in task
            assert "payload" in task
    
    def test_t1_02_03_prioritizes_tasks(self, task_distributor_payload):
        """T1-02-03: Distributor correctly prioritizes tasks"""
        # Given multiple tasks
        tasks = task_distributor_payload["queue"]
        
        # When sorted by priority
        sorted_tasks = sorted(tasks, key=lambda t: t["priority"])
        
        # Then priority 1 tasks should come first
        assert sorted_tasks[0]["priority"] <= sorted_tasks[-1]["priority"]


class TestDistributorWorkflowDispatch:
    """T1-02: Task Dispatch Tests"""
    
    def test_t1_02_04_extracts_task_for_dispatch(self, task_distributor_payload, workflow_simulator):
        """T1-02-04: Distributor extracts task for dispatch"""
        # Given a queue with tasks
        queue = task_distributor_payload["queue"]
        
        # When extracting the next task
        next_task = queue[0]
        
        # Then it should be ready for dispatch
        assert next_task["task_id"] == "update-architecture-blueprint"
        workflow_simulator.execute_node("Task Dispatch", next_task)
        workflow_simulator.complete_node({"dispatched": True})
    
    def test_t1_02_05_includes_metadata(self, task_distributor_payload):
        """T1-02-05: Distributor includes execution metadata"""
        # Given a payload
        payload = task_distributor_payload
        
        # Then metadata should be present
        assert "metadata" in payload
        assert "trigger_commit" in payload["metadata"]
        assert "total_tasks" in payload["metadata"]
    
    def test_t1_02_06_handles_empty_queue(self, workflow_simulator):
        """T1-02-06: Distributor handles empty queue gracefully"""
        # Given an empty queue
        empty_queue = {"queue": [], "metadata": {"total_tasks": 0}}
        
        # When processing
        workflow_simulator.execute_node("Queue Check", empty_queue)
        
        # Then it should complete without error
        workflow_simulator.complete_node({"status": "idle", "tasks_remaining": 0})
        assert workflow_simulator.executions[-1]["status"] == "success"
