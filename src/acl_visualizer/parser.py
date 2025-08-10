"""
Mosquitto ACL Parser Module

This module provides functionality to parse Mosquitto ACL files into structured Python objects.
Each ACL rule includes client CN, access level, and topic string.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, TextIO
import re
from pathlib import Path


@dataclass
class ACLRule:
    """Represents a single ACL rule for a client."""
    client: str
    access: str  # 'read', 'write', 'readwrite'
    topic: str
    
    def __post_init__(self):
        """Validate access type."""
        valid_access = {'read', 'write', 'readwrite'}
        if self.access not in valid_access:
            raise ValueError(f"Invalid access type: {self.access}. Must be one of {valid_access}")


class ACLParseError(Exception):
    """Raised when ACL file parsing fails."""
    pass


class ACLParser:
    """Parser for Mosquitto ACL files."""
    
    # Regex patterns for parsing ACL lines
    USER_PATTERN = re.compile(r'^user\s+(.+)$')
    TOPIC_PATTERN = re.compile(r'^topic\s+(?:(read|write|readwrite)\s+)?(.+)$')
    COMMENT_PATTERN = re.compile(r'^\s*#.*$')
    EMPTY_PATTERN = re.compile(r'^\s*$')
    
    def __init__(self):
        self.current_client: Optional[str] = None
        self.line_number: int = 0
        
    def parse_file(self, file_path: str) -> Dict[str, List[ACLRule]]:
        """
        Parse an ACL file and return structured data.
        
        Args:
            file_path: Path to the ACL file
            
        Returns:
            Dictionary mapping client names to lists of ACLRule objects
            
        Raises:
            ACLParseError: If the file cannot be parsed
            FileNotFoundError: If the file doesn't exist
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return self.parse_stream(f)
        except FileNotFoundError:
            raise ACLParseError(f"ACL file not found: {file_path}")
        except UnicodeDecodeError as e:
            raise ACLParseError(f"Unable to decode file {file_path}: {e}")
    
    def parse_string(self, acl_content: str) -> Dict[str, List[ACLRule]]:
        """
        Parse ACL content from a string.
        
        Args:
            acl_content: ACL file content as string
            
        Returns:
            Dictionary mapping client names to lists of ACLRule objects
        """
        from io import StringIO
        return self.parse_stream(StringIO(acl_content))
    
    def parse_stream(self, stream: TextIO) -> Dict[str, List[ACLRule]]:
        """
        Parse ACL content from a text stream.
        
        Args:
            stream: Text stream containing ACL content
            
        Returns:
            Dictionary mapping client names to lists of ACLRule objects
            
        Raises:
            ACLParseError: If parsing fails
        """
        client_rules: Dict[str, List[ACLRule]] = {}
        self.current_client = None
        self.line_number = 0
        
        for line in stream:
            self.line_number += 1
            line = line.strip()
            
            # Skip empty lines and comments
            if self._is_empty_or_comment(line):
                continue
                
            # Parse user lines
            user_match = self.USER_PATTERN.match(line)
            if user_match:
                self.current_client = user_match.group(1).strip()
                if self.current_client not in client_rules:
                    client_rules[self.current_client] = []
                continue
            
            # Parse topic lines
            topic_match = self.TOPIC_PATTERN.match(line)
            if topic_match:
                if self.current_client is None:
                    raise ACLParseError(
                        f"Line {self.line_number}: Topic rule without user context: {line}"
                    )
                
                access = topic_match.group(1) or 'readwrite'  # Default to readwrite
                topic = topic_match.group(2).strip()
                
                try:
                    rule = ACLRule(
                        client=self.current_client,
                        access=access,
                        topic=topic
                    )
                    client_rules[self.current_client].append(rule)
                except ValueError as e:
                    raise ACLParseError(f"Line {self.line_number}: {e}")
                continue
            
            # If we get here, the line is invalid
            raise ACLParseError(f"Line {self.line_number}: Invalid ACL syntax: {line}")
        
        return client_rules
    
    def _is_empty_or_comment(self, line: str) -> bool:
        """Check if a line is empty or a comment."""
        return bool(self.EMPTY_PATTERN.match(line) or self.COMMENT_PATTERN.match(line))


def parse_acl_file(file_path: str) -> Dict[str, List[ACLRule]]:
    """
    Convenience function to parse an ACL file.
    
    Args:
        file_path: Path to the ACL file
        
    Returns:
        Dictionary mapping client names to lists of ACLRule objects
    """
    parser = ACLParser()
    return parser.parse_file(file_path)


def validate_acl_rules(client_rules: Dict[str, List[ACLRule]]) -> List[str]:
    """
    Validate ACL rules and return a list of warnings.
    
    Args:
        client_rules: Parsed ACL rules
        
    Returns:
        List of validation warnings
    """
    warnings = []
    
    for client, rules in client_rules.items():
        if not rules:
            warnings.append(f"Client '{client}' has no ACL rules")
            continue
            
        # Check for overly permissive wildcards
        for rule in rules:
            if rule.topic == '#' and rule.access in ['write', 'readwrite']:
                warnings.append(
                    f"Client '{client}' has write access to all topics (#) - security risk"
                )
            
            # Check for potential topic conflicts
            if '+' in rule.topic and rule.access in ['write', 'readwrite']:
                warnings.append(
                    f"Client '{client}' has write access to wildcard topic '{rule.topic}'"
                )
    
    return warnings


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python parser.py <acl_file>")
        sys.exit(1)

    try:
        rules = parse_acl_file(sys.argv[1])
        print(f"Successfully parsed {len(rules)} clients:")

        for client, client_rules in rules.items():
            print(f"\n{client}:")
            for rule in client_rules:
                print(f"  {rule.access}: {rule.topic}")

        # Show validation warnings
        warnings = validate_acl_rules(rules)
        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  ⚠️  {warning}")

    except ACLParseError as e:
        print(f"Error parsing ACL file: {e}", file=sys.stderr)
        sys.exit(1)
