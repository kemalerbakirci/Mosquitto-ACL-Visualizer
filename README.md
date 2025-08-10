# Mosquitto ACL Visualizer

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Status](https://img.shields.io/badge/status-alpha-yellow)
![Tests](https://img.shields.io/badge/tests-pytest-informational)
![Code Style](https://img.shields.io/badge/code%20style-black-000000)
![Last Commit](https://img.shields.io/github/last-commit/yourusername/mosquitto-acl-visualizer)
![Issues](https://img.shields.io/github/issues/yourusername/mosquitto-acl-visualizer)
![Stars](https://img.shields.io/github/stars/yourusername/mosquitto-acl-visualizer?style=social)

A comprehensive tool for parsing, visualizing Mosquitto MQTT broker Access Control Lists (ACLs). T
## 🚀 Key Features

- **Interactive Visualization**: Visualize client-topic relationships through graphs and tables
- **Web Interface**: User-friendly web interface for file upload and visualization

## 📚 Documentation Map

| Topic | File |
|-------|------|
| Quick usage | `docs/usage.md` |
| API reference | `docs/api.md` |
| Architecture | `docs/architecture.md` |
| Comprehensive learning guide | `docs/comprehensive-guide.md` |
| ACL fundamentals tutorial | `docs/learning-acl.md` |

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask Backend  │    │   ACL Files     │
│   (HTML/JS/CSS) │◄──►│   (Python)       │◄──►│   (Mosquitto)   │
│                 │    │                  │    │                 │
│ • File Upload   │    │ • Parser         │    │ • Read/Write    │
│ • Visualization │    │ • Generator      │    │ • Validation    │
│ • ACL Editor    │    │ • Visualizer     │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📦 Installation

### Prerequisites
- Python 3.11+
- pip or Poetry

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kemalerbakirci/mosquitto-acl-visualizer.git
   cd mosquitto-acl-visualizer
   ```

2. **Install dependencies**:
   ```bash
   # Using pip
   pip install -r requirements.txt
   
   # Or using Poetry
   poetry install
   ```

3. **Run the application**:
   ```bash
   python -m src.acl_visualizer.webapp
   ```

4. **Open your browser** to `http://localhost:5000`

## 🎯 Usage

### Quick Start

1. **Upload an ACL file**: Use the web interface to upload your Mosquitto ACL file
2. **Visualize**: View the parsed ACL rules in a table and graph format
3. **Edit**: Modify ACL rules through the web interface
4. **Export**: Generate and download a new ACL file

### Example ACL Input

```
# Sample Mosquitto ACL file
user device001
topic read sensors/temperature/+
topic write actuators/device001/+

user device002
topic read sensors/humidity/+
topic readwrite actuators/device002/+

user admin
topic readwrite #
```

### Example Output

The tool generates visualizations showing:
- Client permissions matrix
- Topic hierarchy graph
- Overlapping permissions analysis
- Security recommendations

## 🔒 Security Implications

Misconfigured ACLs can lead to:

- **Unauthorized data access**: Clients reading sensitive topics
- **Topic pollution**: Clients writing to unauthorized topics
- **Privilege escalation**: Overly broad permissions
- **Data leakage**: Wildcard permissions exposing unintended data

This tool helps identify these issues by:
- Highlighting overlapping permissions
- Showing wildcard expansion
- Analyzing permission inheritance
- Suggesting least-privilege configurations

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/acl_visualizer

# Run specific test file
pytest tests/test_parser.py
```

## 🛠️ Development

### Project Structure

```
mosquitto-acl-visualizer/
├── src/acl_visualizer/          # Main Python package
│   ├── parser.py                # ACL file parsing
│   ├── generator.py             # ACL file generation
│   ├── visualizer.py            # Data visualization logic
│   └── webapp.py                # Flask web application
├── frontend/                    # Web interface
│   ├── index.html              # Main HTML page
│   ├── app.js                  # JavaScript logic
│   └── styles.css              # Styling
├── tests/                      # Test suite
├── docs/                       # Documentation
└── examples/                   # Sample ACL files
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Submit a pull request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write comprehensive tests for new features
- Document public APIs

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.


## 🙏 Acknowledgments

- [Eclipse Mosquitto](https://mosquitto.org/) for the MQTT broker
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [NetworkX](https://networkx.org/) for graph algorithms
