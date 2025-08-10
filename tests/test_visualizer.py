"""
Unit tests for the ACL visualizer module.

Tests cover:
- Single client with multiple topics
- Multiple clients with shared topic prefixes
- Empty ACL list returns empty graph
- Visualization data structure generation
"""

import pytest
import json
import tempfile
import os

from src.acl_visualizer.parser import ACLRule
from src.acl_visualizer.visualizer import (
    ACLVisualizer, create_visualization_data, export_visualization_json
)


class TestACLVisualizer:
    """Test the ACLVisualizer class."""
    
    def test_single_client_multiple_topics(self):
        """Test visualization with single client having multiple topics."""
        client_rules = {
            "device001": [
                ACLRule(client="device001", access="read", topic="sensors/temperature"),
                ACLRule(client="device001", access="write", topic="actuators/fan"),
                ACLRule(client="device001", access="readwrite", topic="devices/device001/status")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        data = visualizer.generate_visualization_data()
        
        # Check client summary
        clients = data['clients']
        assert len(clients) == 1
        client = clients[0]
        assert client['name'] == "device001"
        assert client['total_rules'] == 3
        assert client['read_permissions'] == 2  # read + readwrite
        assert client['write_permissions'] == 2  # write + readwrite
        
        # Check topics
        topics = data['topics']
        assert len(topics) == 3
        topic_names = [t['topic'] for t in topics]
        assert "sensors/temperature" in topic_names
        assert "actuators/fan" in topic_names
        assert "devices/device001/status" in topic_names
    
    def test_multiple_clients_shared_topics(self):
        """Test visualization with multiple clients accessing same exact topics."""
        client_rules = {
            "sensor1": [
                ACLRule(client="sensor1", access="write", topic="sensors/data"),
                ACLRule(client="sensor1", access="read", topic="config/sensor1")
            ],
            "sensor2": [
                ACLRule(client="sensor2", access="write", topic="sensors/data"),  # Same topic as sensor1
                ACLRule(client="sensor2", access="read", topic="config/sensor2")
            ],
            "collector": [
                ACLRule(client="collector", access="read", topic="sensors/data")  # Same topic
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        data = visualizer.generate_visualization_data()
        
        # Check overlaps - multiple clients have access to same topic
        overlaps = data['overlaps']
        
        # Find the sensors/data topic in overlaps (shared by all three clients)
        shared_topic_overlap = None
        for overlap in overlaps:
            if overlap['topic'] == "sensors/data":
                shared_topic_overlap = overlap
                break
        
        assert shared_topic_overlap is not None
        assert shared_topic_overlap['client_count'] == 3
        assert "sensor1" in shared_topic_overlap['clients']
        assert "sensor2" in shared_topic_overlap['clients']
        assert "collector" in shared_topic_overlap['clients']
        assert shared_topic_overlap['is_wildcard'] is False
    
    def test_empty_acl_list(self):
        """Test that empty ACL list returns appropriate empty structures."""
        client_rules = {}
        
        visualizer = ACLVisualizer(client_rules)
        data = visualizer.generate_visualization_data()
        
        assert data['clients'] == []
        assert data['topics'] == []
        assert data['overlaps'] == []
        assert data['relationships']['nodes'] == []
        assert data['relationships']['edges'] == []
        
        stats = data['statistics']
        assert stats['total_clients'] == 0
        assert stats['total_rules'] == 0
        assert stats['avg_rules_per_client'] == 0
    
    def test_client_summary_generation(self):
        """Test detailed client summary generation."""
        client_rules = {
            "device1": [
                ACLRule(client="device1", access="read", topic="sensors/+"),
                ACLRule(client="device1", access="write", topic="devices/device1/cmd"),
                ACLRule(client="device1", access="readwrite", topic="devices/device1/status")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        clients = visualizer.get_client_summary()
        
        assert len(clients) == 1
        client = clients[0]
        
        assert client['name'] == "device1"
        assert client['total_rules'] == 3
        assert client['read_permissions'] == 2  # read + readwrite
        assert client['write_permissions'] == 2  # write + readwrite
        assert client['wildcard_topics'] == 1  # sensors/+
        assert client['exact_topics'] == 2
        
        # Check topics details
        topics = client['topics']
        assert len(topics) == 3
        topic_accesses = {t['topic']: t['access'] for t in topics}
        assert topic_accesses['sensors/+'] == 'read'
        assert topic_accesses['devices/device1/cmd'] == 'write'
        assert topic_accesses['devices/device1/status'] == 'readwrite'
    
    def test_topic_summary_generation(self):
        """Test topic summary generation."""
        client_rules = {
            "client1": [
                ACLRule(client="client1", access="read", topic="shared/topic"),
                ACLRule(client="client1", access="write", topic="client1/private")
            ],
            "client2": [
                ACLRule(client="client2", access="write", topic="shared/topic"),
                ACLRule(client="client2", access="read", topic="client2/private")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        topics = visualizer.get_topic_summary()
        
        # Find shared topic
        shared_topic = next(t for t in topics if t['topic'] == 'shared/topic')
        assert shared_topic['client_count'] == 2
        assert shared_topic['is_wildcard'] is False
        assert set(shared_topic['read_clients']) == {'client1'}
        assert set(shared_topic['write_clients']) == {'client2'}
        
        # Check private topics
        private_topics = [t for t in topics if 'private' in t['topic']]
        assert len(private_topics) == 2
        for topic in private_topics:
            assert topic['client_count'] == 1
    
    def test_relationship_graph_generation(self):
        """Test client-topic relationship graph generation."""
        client_rules = {
            "client1": [
                ACLRule(client="client1", access="read", topic="topic1"),
                ACLRule(client="client1", access="write", topic="topic2")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        relationships = visualizer.get_client_topic_relationships()
        
        nodes = relationships['nodes']
        edges = relationships['edges']
        
        # Check nodes
        client_nodes = [n for n in nodes if n['type'] == 'client']
        topic_nodes = [n for n in nodes if n['type'] == 'topic']
        
        assert len(client_nodes) == 1
        assert len(topic_nodes) == 2
        
        client_node = client_nodes[0]
        assert client_node['id'] == 'client_client1'
        assert client_node['label'] == 'client1'
        assert client_node['size'] == 2  # number of rules
        
        # Check edges
        assert len(edges) == 2
        for edge in edges:
            assert edge['source'] == 'client_client1'
            assert edge['target'].startswith('topic_')
    
    def test_topic_overlaps_detection(self):
        """Test detection of topic overlaps between clients."""
        client_rules = {
            "client1": [
                ACLRule(client="client1", access="read", topic="shared"),
                ACLRule(client="client1", access="read", topic="private1")
            ],
            "client2": [
                ACLRule(client="client2", access="write", topic="shared"),
                ACLRule(client="client2", access="read", topic="private2")
            ],
            "client3": [
                ACLRule(client="client3", access="readwrite", topic="shared")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        overlaps = visualizer.get_topic_overlaps()
        
        # Should find one overlap for "shared" topic
        assert len(overlaps) == 1
        overlap = overlaps[0]
        
        assert overlap['topic'] == 'shared'
        assert overlap['client_count'] == 3
        assert set(overlap['clients']) == {'client1', 'client2', 'client3'}
        assert overlap['is_wildcard'] is False
    
    def test_topic_hierarchy_building(self):
        """Test topic hierarchy tree building."""
        client_rules = {
            "client1": [
                ACLRule(client="client1", access="read", topic="sensors/temperature/room1"),
                ACLRule(client="client1", access="read", topic="sensors/temperature/room2"),
                ACLRule(client="client1", access="read", topic="sensors/humidity/room1"),
                ACLRule(client="client1", access="read", topic="actuators/fan/room1")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        hierarchy = visualizer.get_topic_hierarchy()
        
        # Check structure
        assert 'sensors' in hierarchy
        assert 'actuators' in hierarchy
        
        sensors = hierarchy['sensors']
        assert 'temperature' in sensors
        assert 'humidity' in sensors
        
        temperature = sensors['temperature']
        assert 'room1' in temperature
        assert 'room2' in temperature
    
    def test_client_topic_matrix(self):
        """Test client-topic access matrix generation."""
        client_rules = {
            "client1": [
                ACLRule(client="client1", access="read", topic="topic1"),
                ACLRule(client="client1", access="write", topic="topic2")
            ],
            "client2": [
                ACLRule(client="client2", access="readwrite", topic="topic1")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        matrix_data = visualizer.get_client_topic_matrix()
        
        clients = matrix_data['clients']
        topics = matrix_data['topics']
        matrix = matrix_data['matrix']
        
        assert clients == ['client1', 'client2']
        assert set(topics) == {'topic1', 'topic2'}
        
        # Check matrix values
        topic1_idx = topics.index('topic1')
        topic2_idx = topics.index('topic2')
        
        # client1 row
        assert matrix[0][topic1_idx] == 'read'
        assert matrix[0][topic2_idx] == 'write'
        
        # client2 row
        assert matrix[1][topic1_idx] == 'readwrite'
        assert matrix[1][topic2_idx] == 'none'
    
    def test_security_analysis(self):
        """Test security analysis functionality."""
        client_rules = {
            "dangerous": [
                ACLRule(client="dangerous", access="write", topic="#"),
                ACLRule(client="dangerous", access="readwrite", topic="sensors/+/control")
            ],
            "safe": [
                ACLRule(client="safe", access="read", topic="sensors/temperature"),
                ACLRule(client="safe", access="write", topic="actuators/safe/control")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        analysis = visualizer.get_security_analysis()
        
        # Check for high-priority issues (write to all topics)
        issues = analysis['issues']
        assert len(issues) > 0
        
        high_issues = [i for i in issues if i['level'] == 'high']
        assert len(high_issues) > 0
        assert any('write access to all topics' in issue['description'] for issue in high_issues)
        
        # Check for warnings (wildcard write access)
        warnings = analysis['warnings']
        wildcard_warnings = [w for w in warnings if 'wildcard topics' in w['description'] or 'sensors/+/control' in w['description']]
        assert len(wildcard_warnings) > 0
        
        # Security score should be reduced due to issues
        assert analysis['security_score'] < 100
    
    def test_statistics_generation(self):
        """Test statistics generation."""
        client_rules = {
            "client1": [
                ACLRule(client="client1", access="read", topic="sensors/+"),
                ACLRule(client="client1", access="write", topic="specific/topic")
            ],
            "client2": [
                ACLRule(client="client2", access="readwrite", topic="another/topic")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        stats = visualizer.get_statistics()
        
        assert stats['total_clients'] == 2
        assert stats['total_rules'] == 3
        assert stats['avg_rules_per_client'] == 1.5
        
        access_dist = stats['access_distribution']
        assert access_dist['read'] == 1
        assert access_dist['write'] == 1
        assert access_dist['readwrite'] == 1
        
        topic_dist = stats['topic_distribution']
        assert topic_dist['wildcard'] == 1  # sensors/+
        assert topic_dist['exact'] == 2


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_create_visualization_data(self):
        """Test the convenience function for creating visualization data."""
        client_rules = {
            "testclient": [
                ACLRule(client="testclient", access="read", topic="test/topic")
            ]
        }
        
        data = create_visualization_data(client_rules)
        
        # Should have all expected keys
        expected_keys = ['clients', 'topics', 'relationships', 'overlaps', 
                        'hierarchy', 'matrix', 'security_analysis', 'statistics']
        
        for key in expected_keys:
            assert key in data
        
        assert len(data['clients']) == 1
        assert data['clients'][0]['name'] == 'testclient'
    
    def test_export_visualization_json(self):
        """Test JSON export functionality."""
        client_rules = {
            "testclient": [
                ACLRule(client="testclient", access="read", topic="test/topic")
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            export_visualization_json(client_rules, temp_path)
            
            # Verify file was created and contains valid JSON
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert 'clients' in data
            assert 'statistics' in data
            assert len(data['clients']) == 1
            
        finally:
            os.unlink(temp_path)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_clients_with_no_rules(self):
        """Test handling of clients with empty rule lists."""
        client_rules = {
            "empty_client": []
        }
        
        visualizer = ACLVisualizer(client_rules)
        data = visualizer.generate_visualization_data()
        
        # Should handle empty clients gracefully
        clients = data['clients']
        assert len(clients) == 1
        client = clients[0]
        assert client['name'] == "empty_client"
        assert client['total_rules'] == 0
    
    def test_unicode_topic_names(self):
        """Test handling of Unicode characters in topic names."""
        client_rules = {
            "unicode_client": [
                ACLRule(client="unicode_client", access="read", topic="센서/온도/데이터"),
                ACLRule(client="unicode_client", access="write", topic="アクチュエータ/ファン/制御")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        data = visualizer.generate_visualization_data()
        
        # Should handle Unicode topics correctly
        topics = data['topics']
        topic_names = [t['topic'] for t in topics]
        assert "센서/온도/데이터" in topic_names
        assert "アクチュエータ/ファン/制御" in topic_names
    
    def test_very_large_topic_hierarchy(self):
        """Test handling of deep topic hierarchies."""
        client_rules = {
            "deep_client": [
                ACLRule(client="deep_client", access="read", 
                       topic="level1/level2/level3/level4/level5/deep_topic")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        hierarchy = visualizer.get_topic_hierarchy()
        
        # Should build deep hierarchy correctly
        current = hierarchy
        levels = ["level1", "level2", "level3", "level4", "level5", "deep_topic"]
        
        for level in levels:
            assert level in current
            current = current[level]
    
    def test_wildcard_topic_handling(self):
        """Test proper handling of wildcard topics in hierarchy."""
        client_rules = {
            "wildcard_client": [
                ACLRule(client="wildcard_client", access="read", topic="sensors/+/data"),
                ACLRule(client="wildcard_client", access="read", topic="devices/#")
            ]
        }
        
        visualizer = ACLVisualizer(client_rules)
        
        # Wildcards should not appear in hierarchy (only exact topics)
        hierarchy = visualizer.get_topic_hierarchy()
        assert hierarchy == {}  # No exact topics to build hierarchy from
        
        # But should appear in topic summary
        topics = visualizer.get_topic_summary()
        wildcard_topics = [t for t in topics if t['is_wildcard']]
        assert len(wildcard_topics) == 2


if __name__ == "__main__":
    pytest.main([__file__])