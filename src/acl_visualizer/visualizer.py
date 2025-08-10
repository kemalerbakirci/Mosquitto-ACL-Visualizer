"""
Mosquitto ACL Visualizer Module

This module generates visualization data structures from parsed ACL rules.
Creates graph-like structures showing client-topic relationships and overlaps.
"""

from typing import Dict, List, Set, Any, Tuple
from collections import defaultdict, Counter
import json
from .parser import ACLRule


class ACLVisualizer:
    """Creates visualization data from ACL rules."""
    
    def __init__(self, client_rules: Dict[str, List[ACLRule]]):
        """
        Initialize visualizer with parsed ACL rules.
        
        Args:
            client_rules: Dictionary mapping client names to ACLRule lists
        """
        self.client_rules = client_rules
        self._topic_hierarchy = None
        self._client_topic_matrix = None
    
    def generate_visualization_data(self) -> Dict[str, Any]:
        """
        Generate comprehensive visualization data structure.
        
        Returns:
            JSON-serializable dictionary with visualization data
        """
        return {
            'clients': self.get_client_summary(),
            'topics': self.get_topic_summary(),
            'relationships': self.get_client_topic_relationships(),
            'overlaps': self.get_topic_overlaps(),
            'hierarchy': self.get_topic_hierarchy(),
            'matrix': self.get_client_topic_matrix(),
            'security_analysis': self.get_security_analysis(),
            'statistics': self.get_statistics()
        }
    
    def get_client_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary information for all clients.
        
        Returns:
            List of client summary dictionaries
        """
        clients = []
        
        for client, rules in self.client_rules.items():
            read_topics = sum(1 for r in rules if 'read' in r.access)
            write_topics = sum(1 for r in rules if 'write' in r.access)
            
            # Categorize topics
            wildcard_topics = sum(1 for r in rules if '+' in r.topic or '#' in r.topic)
            exact_topics = len(rules) - wildcard_topics
            
            clients.append({
                'name': client,
                'total_rules': len(rules),
                'read_permissions': read_topics,
                'write_permissions': write_topics,
                'wildcard_topics': wildcard_topics,
                'exact_topics': exact_topics,
                'topics': [{'topic': r.topic, 'access': r.access} for r in rules]
            })
        
        return sorted(clients, key=lambda x: x['name'])
    
    def get_topic_summary(self) -> List[Dict[str, Any]]:
        """
        Get summary information for all topics.
        
        Returns:
            List of topic summary dictionaries
        """
        topic_clients = defaultdict(list)
        
        # Group clients by topic
        for client, rules in self.client_rules.items():
            for rule in rules:
                topic_clients[rule.topic].append({
                    'client': client,
                    'access': rule.access
                })
        
        topics = []
        for topic, clients in topic_clients.items():
            read_clients = [c['client'] for c in clients if 'read' in c['access']]
            write_clients = [c['client'] for c in clients if 'write' in c['access']]
            
            topics.append({
                'topic': topic,
                'client_count': len(set(c['client'] for c in clients)),
                'is_wildcard': '+' in topic or '#' in topic,
                'read_clients': read_clients,
                'write_clients': write_clients,
                'all_clients': clients
            })
        
        return sorted(topics, key=lambda x: x['topic'])
    
    def get_client_topic_relationships(self) -> Dict[str, Any]:
        """
        Generate graph data showing client-topic relationships.
        
        Returns:
            Graph data structure with nodes and edges
        """
        nodes = []
        edges = []
        
        # Add client nodes
        for client in self.client_rules.keys():
            nodes.append({
                'id': f'client_{client}',
                'label': client,
                'type': 'client',
                'size': len(self.client_rules[client])
            })
        
        # Add topic nodes and edges
        topic_set = set()
        for client, rules in self.client_rules.items():
            for rule in rules:
                topic_id = f'topic_{rule.topic}'
                
                # Add topic node if not already added
                if rule.topic not in topic_set:
                    topic_set.add(rule.topic)
                    nodes.append({
                        'id': topic_id,
                        'label': rule.topic,
                        'type': 'topic',
                        'is_wildcard': '+' in rule.topic or '#' in rule.topic
                    })
                
                # Add edge between client and topic
                edges.append({
                    'source': f'client_{client}',
                    'target': topic_id,
                    'access': rule.access,
                    'label': rule.access
                })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    def get_topic_overlaps(self) -> List[Dict[str, Any]]:
        """
        Find topics that multiple clients have access to.
        
        Returns:
            List of topic overlap information
        """
        topic_clients = defaultdict(set)
        
        # Group clients by topic
        for client, rules in self.client_rules.items():
            for rule in rules:
                topic_clients[rule.topic].add(client)
        
        # Find overlapping topics
        overlaps = []
        for topic, clients in topic_clients.items():
            if len(clients) > 1:
                overlaps.append({
                    'topic': topic,
                    'clients': list(clients),
                    'client_count': len(clients),
                    'is_wildcard': '+' in topic or '#' in topic
                })
        
        return sorted(overlaps, key=lambda x: x['client_count'], reverse=True)
    
    def get_topic_hierarchy(self) -> Dict[str, Any]:
        """
        Build hierarchical representation of topics.
        
        Returns:
            Hierarchical topic structure
        """
        if self._topic_hierarchy is None:
            self._topic_hierarchy = self._build_topic_hierarchy()
        
        return self._topic_hierarchy
    
    def _build_topic_hierarchy(self) -> Dict[str, Any]:
        """Build the topic hierarchy tree."""
        hierarchy = {}
        
        # Get all unique topics
        all_topics = set()
        for rules in self.client_rules.values():
            for rule in rules:
                if not ('+' in rule.topic or '#' in rule.topic):  # Skip wildcards for hierarchy
                    all_topics.add(rule.topic)
        
        # Build hierarchy
        for topic in all_topics:
            parts = topic.split('/')
            current = hierarchy
            
            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]
        
        return hierarchy
    
    def get_client_topic_matrix(self) -> Dict[str, Any]:
        """
        Generate a matrix showing client-topic access patterns.
        
        Returns:
            Matrix data with clients as rows and topics as columns
        """
        if self._client_topic_matrix is None:
            self._client_topic_matrix = self._build_client_topic_matrix()
        
        return self._client_topic_matrix
    
    def _build_client_topic_matrix(self) -> Dict[str, Any]:
        """Build the client-topic access matrix."""
        # Get all unique topics and clients
        all_topics = set()
        for rules in self.client_rules.values():
            for rule in rules:
                all_topics.add(rule.topic)
        
        all_topics = sorted(list(all_topics))
        all_clients = sorted(list(self.client_rules.keys()))
        
        # Build matrix
        matrix = []
        for client in all_clients:
            row = []
            client_rules = {rule.topic: rule.access for rule in self.client_rules[client]}
            
            for topic in all_topics:
                access = client_rules.get(topic, 'none')
                row.append(access)
            
            matrix.append(row)
        
        return {
            'clients': all_clients,
            'topics': all_topics,
            'matrix': matrix
        }
    
    def get_security_analysis(self) -> Dict[str, Any]:
        """
        Analyze potential security issues in ACL configuration.
        
        Returns:
            Security analysis results
        """
        issues = []
        warnings = []
        recommendations = []
        
        for client, rules in self.client_rules.items():
            # Check for overly permissive rules
            for rule in rules:
                if rule.topic == '#' and rule.access in ['write', 'readwrite']:
                    issues.append({
                        'level': 'high',
                        'client': client,
                        'issue': 'Write access to all topics (#)',
                        'description': f"Client '{client}' has {rule.access} access to all topics"
                    })
                
                if '+' in rule.topic and rule.access in ['write', 'readwrite']:
                    warnings.append({
                        'level': 'medium',
                        'client': client,
                        'issue': 'Write access to wildcard topics',
                        'description': f"Client '{client}' has {rule.access} access to '{rule.topic}'"
                    })
        
        # Check for topic conflicts
        write_topics = defaultdict(list)
        for client, rules in self.client_rules.items():
            for rule in rules:
                if rule.access in ['write', 'readwrite']:
                    write_topics[rule.topic].append(client)
        
        for topic, clients in write_topics.items():
            if len(clients) > 1:
                warnings.append({
                    'level': 'medium',
                    'topic': topic,
                    'issue': 'Multiple writers to same topic',
                    'description': f"Multiple clients can write to '{topic}': {', '.join(clients)}"
                })
        
        # Generate recommendations
        if any(issue['level'] == 'high' for issue in issues):
            recommendations.append("Review and restrict overly permissive wildcard permissions")
        
        if len(warnings) > 0:
            recommendations.append("Consider implementing least-privilege access controls")
        
        total_rules = sum(len(rules) for rules in self.client_rules.values())
        if total_rules > 100:
            recommendations.append("Large ACL files can be difficult to maintain - consider grouping similar clients")
        
        return {
            'issues': issues,
            'warnings': warnings,
            'recommendations': recommendations,
            'security_score': self._calculate_security_score(issues, warnings)
        }
    
    def _calculate_security_score(self, issues: List[Dict], warnings: List[Dict]) -> int:
        """Calculate a security score (0-100, higher is better)."""
        score = 100
        score -= len(issues) * 20  # High-impact issues
        score -= len(warnings) * 5  # Medium-impact warnings
        return max(0, score)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Generate general statistics about the ACL configuration.
        
        Returns:
            Statistics dictionary
        """
        total_clients = len(self.client_rules)
        total_rules = sum(len(rules) for rules in self.client_rules.values())
        
        # Count access types
        access_counts = Counter()
        topic_counts = Counter()
        
        for rules in self.client_rules.values():
            for rule in rules:
                access_counts[rule.access] += 1
                if '+' in rule.topic or '#' in rule.topic:
                    topic_counts['wildcard'] += 1
                else:
                    topic_counts['exact'] += 1
        
        # Find most common topics
        all_topics = []
        for rules in self.client_rules.values():
            all_topics.extend(rule.topic for rule in rules)
        
        common_topics = Counter(all_topics).most_common(5)
        
        return {
            'total_clients': total_clients,
            'total_rules': total_rules,
            'avg_rules_per_client': round(total_rules / total_clients, 2) if total_clients > 0 else 0,
            'access_distribution': dict(access_counts),
            'topic_distribution': dict(topic_counts),
            'most_common_topics': [{'topic': topic, 'count': count} for topic, count in common_topics]
        }


def create_visualization_data(client_rules: Dict[str, List[ACLRule]]) -> Dict[str, Any]:
    """
    Convenience function to create visualization data.
    
    Args:
        client_rules: Dictionary mapping client names to ACLRule lists
        
    Returns:
        Complete visualization data structure
    """
    visualizer = ACLVisualizer(client_rules)
    return visualizer.generate_visualization_data()


def export_visualization_json(client_rules: Dict[str, List[ACLRule]], 
                            output_path: str) -> None:
    """
    Export visualization data to JSON file.
    
    Args:
        client_rules: Dictionary mapping client names to ACLRule lists
        output_path: Path to output JSON file
    """
    data = create_visualization_data(client_rules)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    from .parser import parse_acl_file
    
    if len(sys.argv) != 3:
        print("Usage: python visualizer.py <acl_file> <output_json>")
        sys.exit(1)
    
    acl_file = sys.argv[1]
    output_json = sys.argv[2]
    
    try:
        # Parse ACL file
        print(f"Parsing {acl_file}...")
        rules = parse_acl_file(acl_file)
        
        # Generate visualization data
        print("Generating visualization data...")
        data = create_visualization_data(rules)
        
        # Export to JSON
        print(f"Exporting to {output_json}...")
        export_visualization_json(rules, output_json)
        
        print("✅ Visualization data generated successfully!")
        
        # Show summary
        stats = data['statistics']
        print(f"   Clients: {stats['total_clients']}")
        print(f"   Rules: {stats['total_rules']}")
        print(f"   Security Score: {data['security_analysis']['security_score']}/100")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)