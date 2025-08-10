"""
Unit tests for the ACL parser module.

Tests cover:
- Well-formed ACL file parsing
- ACL files with comments and blank lines
- Invalid ACL files (topic lines without user context)
- Error handling and validation
"""

import pytest
import tempfile
import os
from io import StringIO

from src.acl_visualizer.parser import (
    ACLParser, ACLRule, ACLParseError, 
    parse_acl_file, validate_acl_rules
)


class TestACLRule:
    """Test the ACLRule dataclass."""
    
    def test_valid_rule_creation(self):
        """Test creating valid ACL rules."""
        rule = ACLRule(client="device001", access="read", topic="sensors/temperature")
        assert rule.client == "device001"
        assert rule.access == "read"
        assert rule.topic == "sensors/temperature"
    
    def test_invalid_access_type(self):
        """Test that invalid access types raise ValueError."""
        with pytest.raises(ValueError, match="Invalid access type"):
            ACLRule(client="device001", access="invalid", topic="sensors/temperature")
    
    def test_valid_access_types(self):
        """Test all valid access types."""
        valid_access = ['read', 'write', 'readwrite']
        for access in valid_access:
            rule = ACLRule(client="test", access=access, topic="test/topic")
            assert rule.access == access


class TestACLParser:
    """Test the ACLParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.parser = ACLParser()
    
    def test_parse_well_formed_acl(self):
        """Test parsing a well-formed ACL file."""
        acl_content = """
# Sample ACL file
user device001
topic read sensors/temperature/+
topic write actuators/device001/+

user device002
topic read sensors/humidity/+
topic readwrite actuators/device002/+

user admin
topic readwrite #
"""
        
        parser = ACLParser()
        result = parser.parse_string(acl_content)
        
        assert len(result) == 3
        assert "device001" in result
        assert "device002" in result
        assert "admin" in result
        
        # Check device001 rules
        device001_rules = result["device001"]
        assert len(device001_rules) == 2
        assert device001_rules[0].access == "read"
        assert device001_rules[0].topic == "sensors/temperature/+"
        assert device001_rules[1].access == "write"
        assert device001_rules[1].topic == "actuators/device001/+"
        
        # Check admin rules
        admin_rules = result["admin"]
        assert len(admin_rules) == 1
        assert admin_rules[0].access == "readwrite"
        assert admin_rules[0].topic == "#"
    
    def test_parse_with_comments_and_blank_lines(self):
        """Test parsing ACL with comments and blank lines."""
        acl_content = """
# This is a comment
# Another comment

user testuser
# Comment between rules
topic read test/topic

# Final comment
"""
        
        parser = ACLParser()
        result = parser.parse_string(acl_content)
        
        assert len(result) == 1
        assert "testuser" in result
        assert len(result["testuser"]) == 1
        assert result["testuser"][0].topic == "test/topic"
    
    def test_default_access_type(self):
        """Test that topic without explicit access defaults to readwrite."""
        acl_content = """
user testuser
topic default/topic
"""
        
        parser = ACLParser()
        result = parser.parse_string(acl_content)
        
        rule = result["testuser"][0]
        assert rule.access == "readwrite"
        assert rule.topic == "default/topic"
    
    def test_topic_without_user_context(self):
        """Test that topic lines without user context raise error."""
        acl_content = """
topic read orphan/topic
user testuser
topic read valid/topic
"""
        
        parser = ACLParser()
        with pytest.raises(ACLParseError, match="Topic rule without user context"):
            parser.parse_string(acl_content)
    
    def test_invalid_syntax(self):
        """Test handling of invalid ACL syntax."""
        acl_content = """
user testuser
invalid line syntax
topic read valid/topic
"""
        
        parser = ACLParser()
        with pytest.raises(ACLParseError, match="Invalid ACL syntax"):
            parser.parse_string(acl_content)
    
    def test_empty_file(self):
        """Test parsing empty ACL file."""
        parser = ACLParser()
        result = parser.parse_string("")
        assert result == {}
    
    def test_comments_only_file(self):
        """Test parsing file with only comments."""
        acl_content = """
# Only comments
# Nothing else
"""
        
        parser = ACLParser()
        result = parser.parse_string(acl_content)
        assert result == {}
    
    def test_user_with_no_rules(self):
        """Test user declaration with no following rules."""
        acl_content = """
user testuser
user anotheruser
topic read test/topic
"""
        
        parser = ACLParser()
        result = parser.parse_string(acl_content)
        
        assert len(result) == 2
        assert "testuser" in result
        assert "anotheruser" in result
        assert len(result["testuser"]) == 0
        assert len(result["anotheruser"]) == 1
    
    def test_multiple_users_same_name(self):
        """Test handling multiple users with same name."""
        acl_content = """
user testuser
topic read topic1

user testuser
topic write topic2
"""
        
        parser = ACLParser()
        result = parser.parse_string(acl_content)
        
        assert len(result) == 1
        assert len(result["testuser"]) == 2
        
        topics = [rule.topic for rule in result["testuser"]]
        assert "topic1" in topics
        assert "topic2" in topics


class TestFileOperations:
    """Test file-based operations."""
    
    def test_parse_file_success(self):
        """Test successful file parsing."""
        acl_content = """
user testuser
topic read test/topic
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.acl', delete=False) as f:
            f.write(acl_content)
            temp_path = f.name
        
        try:
            result = parse_acl_file(temp_path)
            assert len(result) == 1
            assert "testuser" in result
        finally:
            os.unlink(temp_path)
    
    def test_parse_nonexistent_file(self):
        """Test parsing non-existent file raises error."""
        with pytest.raises(ACLParseError, match="ACL file not found"):
            parse_acl_file("/nonexistent/file.acl")
    
    def test_parse_invalid_encoding(self):
        """Test handling of files with invalid encoding."""
        # Create a file with invalid UTF-8
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.acl', delete=False) as f:
            f.write(b'\xff\xfe\x00\x00')  # Invalid UTF-8 sequence
            temp_path = f.name
        
        try:
            with pytest.raises(ACLParseError, match="Unable to decode file"):
                parse_acl_file(temp_path)
        finally:
            os.unlink(temp_path)


class TestValidation:
    """Test ACL rule validation functions."""
    
    def test_validate_empty_rules(self):
        """Test validation of empty rule set."""
        warnings = validate_acl_rules({})
        assert len(warnings) == 0
    
    def test_validate_client_with_no_rules(self):
        """Test validation warns about clients with no rules."""
        client_rules = {"empty_client": []}
        warnings = validate_acl_rules(client_rules)
        
        assert len(warnings) == 1
        assert "has no ACL rules" in warnings[0]
    
    def test_validate_dangerous_wildcard_permissions(self):
        """Test validation of dangerous wildcard permissions."""
        client_rules = {
            "dangerous_client": [
                ACLRule(client="dangerous_client", access="write", topic="#"),
                ACLRule(client="dangerous_client", access="readwrite", topic="#")
            ]
        }
        
        warnings = validate_acl_rules(client_rules)
        
        assert len(warnings) == 2
        assert all("write access to all topics" in warning for warning in warnings)
    
    def test_validate_wildcard_write_permissions(self):
        """Test validation of wildcard write permissions."""
        client_rules = {
            "client1": [
                ACLRule(client="client1", access="write", topic="sensors/+/data"),
                ACLRule(client="client1", access="readwrite", topic="actuators/+/control")
            ]
        }
        
        warnings = validate_acl_rules(client_rules)
        
        assert len(warnings) == 2
        assert all("write access to wildcard topic" in warning for warning in warnings)
    
    def test_validate_safe_permissions(self):
        """Test validation of safe permissions generates no warnings."""
        client_rules = {
            "safe_client": [
                ACLRule(client="safe_client", access="read", topic="#"),
                ACLRule(client="safe_client", access="read", topic="sensors/+"),
                ACLRule(client="safe_client", access="write", topic="specific/topic"),
                ACLRule(client="safe_client", access="readwrite", topic="another/specific/topic")
            ]
        }
        
        warnings = validate_acl_rules(client_rules)
        assert len(warnings) == 0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_whitespace_handling(self):
        """Test proper handling of whitespace."""
        acl_content = """
   user   testuser   
   topic   read   test/topic   
"""
        
        parser = ACLParser()
        result = parser.parse_string(acl_content)
        
        assert "testuser" in result
        rule = result["testuser"][0]
        assert rule.access == "read"
        assert rule.topic == "test/topic"
    
    def test_line_number_tracking(self):
        """Test that line numbers are correctly tracked in errors."""
        acl_content = """
# Line 1: comment
user testuser
# Line 3: comment
topic read valid/topic
invalid syntax on line 6
"""
        
        parser = ACLParser()
        with pytest.raises(ACLParseError, match="Line 6.*Invalid ACL syntax"):
            parser.parse_string(acl_content)
    
    def test_unicode_support(self):
        """Test support for Unicode characters in topics and usernames."""
        acl_content = """
user tëst_üser
topic read tëst/tópic/ñame
topic write データ/センサー/温度
"""
        
        parser = ACLParser()
        result = parser.parse_string(acl_content)
        
        assert "tëst_üser" in result
        topics = [rule.topic for rule in result["tëst_üser"]]
        assert "tëst/tópic/ñame" in topics
        assert "データ/センサー/温度" in topics


if __name__ == "__main__":
    pytest.main([__file__])