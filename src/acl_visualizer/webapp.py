"""
Flask Web Application for Mosquitto ACL Visualizer

This module provides a web interface for uploading, parsing, visualizing,
and generating Mosquitto ACL files.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from flask import Flask, request, jsonify, send_file, render_template_string, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest

from .parser import ACLParser, ACLParseError, ACLRule
from .generator import ACLGenerator, ACLGenerateError, validate_generation_input
from .visualizer import ACLVisualizer, create_visualization_data


# Store parsed ACL data in session (in production, use proper session management)
acl_data_store = {}


def create_app(config=None):
    """
    Application factory function.
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Configured Flask application
    """
    # Flask app configuration
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
    
    if config:
        app.config.update(config)

    @app.route('/')
    def index():
        """Serve the main application page."""
        # Get the project root directory (where pyproject.toml is located)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(current_dir, '../..')
        frontend_dir = os.path.join(project_root, 'frontend')
        frontend_dir = os.path.abspath(frontend_dir)
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/static/<path:filename>')
    def static_files(filename):
        """Serve static files from frontend directory."""
        # Get the project root directory (where pyproject.toml is located)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(current_dir, '../..')
        frontend_dir = os.path.join(project_root, 'frontend')
        frontend_dir = os.path.abspath(frontend_dir)
        return send_from_directory(frontend_dir, filename)

    @app.route('/styles.css')
    def styles():
        """Serve the CSS file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(current_dir, '../..')
        frontend_dir = os.path.join(project_root, 'frontend')
        frontend_dir = os.path.abspath(frontend_dir)
        return send_from_directory(frontend_dir, 'styles.css')

    @app.route('/app.js')
    def app_js():
        """Serve the JavaScript file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.join(current_dir, '../..')
        frontend_dir = os.path.join(project_root, 'frontend')
        frontend_dir = os.path.abspath(frontend_dir)
        return send_from_directory(frontend_dir, 'app.js')

    @app.route('/upload', methods=['POST'])
    def upload_acl_file():
        """
        Upload and parse an ACL file.
        
        Returns:
            JSON response with parsed ACL data or error
        """
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not file.filename.endswith('.acl'):
                return jsonify({'error': 'Invalid file type. Please upload a .acl file'}), 400
            
            # Save uploaded file temporarily
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Parse the ACL file
            parser = ACLParser()
            client_rules = parser.parse_file(filepath)
            
            # Store parsed data (use session ID in production)
            session_id = filename  # Simple approach for demo
            acl_data_store[session_id] = client_rules
            
            # Clean up temporary file
            os.remove(filepath)
            
            # Return summary information
            total_clients = len(client_rules)
            total_rules = sum(len(rules) for rules in client_rules.values())
            
            return jsonify({
                'message': 'File uploaded and parsed successfully',
                'session_id': session_id,
                'summary': {
                    'total_clients': total_clients,
                    'total_rules': total_rules,
                    'clients': list(client_rules.keys())
                }
            })
            
        except ACLParseError as e:
            return jsonify({'error': f'ACL parsing error: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'error': f'Server error: {str(e)}'}), 500

    @app.route('/visualize')
    def visualize():
        """
        Generate visualization data for uploaded ACL file.
        
        Returns:
            JSON response with visualization data
        """
        try:
            session_id = request.args.get('session_id')
            if not session_id or session_id not in acl_data_store:
                return jsonify({'error': 'No ACL data found. Please upload a file first.'}), 400
            
            client_rules = acl_data_store[session_id]
            visualizer = ACLVisualizer(client_rules)
            visualization_data = visualizer.generate_visualization_data()
            
            return jsonify(visualization_data)
            
        except Exception as e:
            return jsonify({'error': f'Visualization error: {str(e)}'}), 500

    @app.route('/generate', methods=['POST'])
    def generate_acl():
        """
        Generate a new ACL file from provided rules.
        
        Expected JSON format:
        {
            "client_rules": {
                "client1": [
                    {"client": "client1", "access": "read", "topic": "topic1"},
                    ...
                ]
            },
            "options": {
                "sort_clients": true,
                "include_comments": true,
                "access_filter": ["read", "write"]  // optional
            }
        }
        
        Returns:
            Generated ACL file as download
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            client_rules_data = data.get('client_rules', {})
            options = data.get('options', {})
            
            # Convert dict data to ACLRule objects
            client_rules = {}
            for client, rules_data in client_rules_data.items():
                rules = []
                for rule_data in rules_data:
                    rule = ACLRule(
                        client=rule_data['client'],
                        access=rule_data['access'],
                        topic=rule_data['topic']
                    )
                    rules.append(rule)
                client_rules[client] = rules
            
            # Validate input
            validation_errors = validate_generation_input(client_rules)
            if validation_errors:
                return jsonify({
                    'error': 'Validation failed',
                    'details': validation_errors
                }), 400
            
            # Create generator with options
            generator = ACLGenerator(
                sort_clients=options.get('sort_clients', True),
                include_comments=options.get('include_comments', True)
            )
            
            # Generate ACL content
            access_filter = options.get('access_filter')
            if access_filter:
                access_filter = set(access_filter)
            
            acl_content = generator.generate_string(client_rules, access_filter)
            
            # Save to temporary file for download
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'generated_acl_{timestamp}.acl'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(acl_content)
            
            return send_file(
                filepath,
                as_attachment=True,
                download_name=filename,
                mimetype='text/plain'
            )
            
        except ValueError as e:
            return jsonify({'error': f'Invalid data: {str(e)}'}), 400
        except ACLGenerateError as e:
            return jsonify({'error': f'Generation error: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'error': f'Server error: {str(e)}'}), 500

    @app.route('/api/clients', methods=['GET'])
    def get_clients():
        """
        Get list of clients and their summary information.
        
        Returns:
            JSON response with client data
        """
        try:
            session_id = request.args.get('session_id')
            if not session_id or session_id not in acl_data_store:
                return jsonify({'error': 'No ACL data found'}), 400
            
            client_rules = acl_data_store[session_id]
            visualizer = ACLVisualizer(client_rules)
            clients = visualizer.get_client_summary()
            
            return jsonify({'clients': clients})
            
        except Exception as e:
            return jsonify({'error': f'Server error: {str(e)}'}), 500

    @app.route('/api/topics', methods=['GET'])
    def get_topics():
        """
        Get list of topics and their summary information.
        
        Returns:
            JSON response with topic data
        """
        try:
            session_id = request.args.get('session_id')
            if not session_id or session_id not in acl_data_store:
                return jsonify({'error': 'No ACL data found'}), 400
            
            client_rules = acl_data_store[session_id]
            visualizer = ACLVisualizer(client_rules)
            topics = visualizer.get_topic_summary()
            
            return jsonify({'topics': topics})
            
        except Exception as e:
            return jsonify({'error': f'Server error: {str(e)}'}), 500

    @app.route('/api/security-analysis', methods=['GET'])
    def get_security_analysis():
        """
        Get security analysis of ACL configuration.
        
        Returns:
            JSON response with security analysis
        """
        try:
            session_id = request.args.get('session_id')
            if not session_id or session_id not in acl_data_store:
                return jsonify({'error': 'No ACL data found'}), 400
            
            client_rules = acl_data_store[session_id]
            visualizer = ACLVisualizer(client_rules)
            analysis = visualizer.get_security_analysis()
            
            return jsonify(analysis)
            
        except Exception as e:
            return jsonify({'error': f'Server error: {str(e)}'}), 500

    @app.route('/api/export/<format>')
    def export_data(format):
        """
        Export ACL data in various formats.
        
        Args:
            format: Export format ('json', 'csv', 'acl')
            
        Returns:
            Exported file as download
        """
        try:
            session_id = request.args.get('session_id')
            if not session_id or session_id not in acl_data_store:
                return jsonify({'error': 'No ACL data found'}), 400
            
            client_rules = acl_data_store[session_id]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format == 'json':
                # Export as JSON
                data = {}
                for client, rules in client_rules.items():
                    data[client] = [
                        {'client': r.client, 'access': r.access, 'topic': r.topic}
                        for r in rules
                    ]
                
                filename = f'acl_export_{timestamp}.json'
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                return send_file(
                    filepath,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/json'
                )
                
            elif format == 'acl':
                # Export as ACL file
                generator = ACLGenerator(sort_clients=True, include_comments=True)
                acl_content = generator.generate_string(client_rules)
                
                filename = f'exported_{timestamp}.acl'
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(acl_content)
                
                return send_file(
                    filepath,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='text/plain'
                )
                
            else:
                return jsonify({'error': f'Unsupported export format: {format}'}), 400
                
        except Exception as e:
            return jsonify({'error': f'Export error: {str(e)}'}), 500

    # Error handlers
    @app.errorhandler(413)
    def file_too_large(e):
        """Handle file too large error."""
        return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

    @app.errorhandler(404)
    def not_found(e):
        """Handle not found errors."""
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(e):
        """Handle internal server errors."""
        return jsonify({'error': 'Internal server error'}), 500

    # Enable CORS for development
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    return app


def main():
    """Main entry point for the application."""
    import os
    port = int(os.environ.get('PORT', 5000))
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
