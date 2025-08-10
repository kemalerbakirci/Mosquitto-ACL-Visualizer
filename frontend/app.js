/**
 * Mosquitto ACL Visualizer Frontend Application
 * 
 * This JavaScript application handles the frontend logic for:
 * - File upload and ACL parsing
 * - Data visualization (tables, graphs, security analysis)
 * - ACL editing and generation
 * - User interface interactions
 */

class ACLVisualizer {
    constructor() {
        this.currentData = null;
        this.currentSessionId = null;
    this.networkGraph = null;
        
        this.init();
    }
    
    init() {
    this.setupEventListeners();
        this.setupFileUpload();
    }
    
    setupEventListeners() {
    // no-op: minimal viewer currently needs no extra listeners
    }
    
    setupFileUpload() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        
        // Click to upload
        uploadArea.addEventListener('click', (e) => {
            // Avoid duplicate firing when clicking actual input overlay
            if (e.target !== fileInput) {
                fileInput.focus();
                fileInput.click();
            }
        });
        
        // File selection
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.uploadFile(file);
            }
        });
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const file = e.dataTransfer.files[0];
            if (file) {
                this.uploadFile(file);
            }
        });
    }
    
    async uploadFile(file) {
        if (!file.name.toLowerCase().endsWith('.acl')) {
            this.showToast('Please select a .acl file', 'error');
            return;
        }
        const formData = new FormData();
        formData.append('file', file);
        const statusDiv = document.getElementById('uploadStatus');
        statusDiv.innerHTML = '⏳ Uploading...';
        try {
            const response = await fetch('/upload', { method: 'POST', body: formData });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Upload failed');
            this.currentSessionId = result.session_id;
            statusDiv.innerHTML = '✅ File uploaded. Building visualization...';
            const vizResp = await fetch(`/visualize?session_id=${encodeURIComponent(this.currentSessionId)}`);
            const vizData = await vizResp.json();
            if (!vizResp.ok) throw new Error(vizData.error || 'Visualization failed');
            this.currentData = vizData;
            this.showToast('ACL parsed successfully', 'success');
            this.renderGraphView();
        } catch (e) {
            statusDiv.innerHTML = '❌ Error: ' + e.message;
            statusDiv.className = 'upload-status error';
            this.showToast(e.message, 'error');
        }
    }

    showNodeDetails(node, relationships) {
    }

    renderGraphView() {
        if (!this.currentData) return;
        
        const svg = d3.select('#networkGraph');
        svg.selectAll('*').remove();
        
        const container = document.querySelector('.graph-wrapper') || document.querySelector('.graph-section');
        const containerWidth = container ? container.clientWidth : 1000;
        const containerHeight = container ? container.clientHeight : 600;
        
        // Set proper margins for the graph
        const margin = { top: 60, bottom: 60, left: 120, right: 120 };
        const width = containerWidth - margin.left - margin.right;
        const height = containerHeight - margin.top - margin.bottom;
        
        svg.attr('width', containerWidth).attr('height', containerHeight);
        
        const data = this.filteredRelationships();
        const clients = data.nodes.filter(n => n.type === 'client').sort((a,b) => a.label.localeCompare(b.label));
        const topics = data.nodes.filter(n => n.type === 'topic').sort((a,b) => a.label.localeCompare(b.label));
        
        if (!clients.length && !topics.length) return;

        // Create main group with proper margins
        const root = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
        
        // Calculate positioning
        const clientSpacing = Math.min(60, Math.max(40, height / Math.max(clients.length, 1)));
        const topicSpacing = Math.min(60, Math.max(40, height / Math.max(topics.length, 1)));
        
        const clientStartY = (height - (clients.length - 1) * clientSpacing) / 2;
        const topicStartY = (height - (topics.length - 1) * topicSpacing) / 2;
        
        const clientX = 0;
        const topicX = width;
        
        // Position maps
        const cPos = new Map();
        const tPos = new Map();
        
        clients.forEach((c, i) => {
            cPos.set(c.id, { x: clientX, y: clientStartY + i * clientSpacing });
        });
        
        topics.forEach((t, i) => {
            tPos.set(t.id, { x: topicX, y: topicStartY + i * topicSpacing });
        });

        // Create enhanced tooltip for hover
        let tooltip = d3.select('.graph-tooltip');
        if (tooltip.empty()) {
            tooltip = d3.select('body').append('div')
                .attr('class', 'graph-tooltip')
                .style('position', 'absolute')
                .style('background', 'rgba(0, 0, 0, 0.9)')
                .style('color', 'white')
                .style('padding', '10px 14px')
                .style('border-radius', '6px')
                .style('font-size', '13px')
                .style('font-weight', '500')
                .style('pointer-events', 'none')
                .style('opacity', 0)
                .style('z-index', 1000)
                .style('max-width', '300px')
                .style('word-wrap', 'break-word')
                .style('box-shadow', '0 4px 12px rgba(0, 0, 0, 0.3)');
        }

        // Draw edges
        const edges = root.append('g').attr('class', 'edges')
            .selectAll('line')
            .data(data.edges)
            .enter()
            .append('line')
            .attr('x1', d => cPos.get(d.source)?.x || 0)
            .attr('y1', d => cPos.get(d.source)?.y || 0)
            .attr('x2', d => tPos.get(d.target)?.x || 0)
            .attr('y2', d => tPos.get(d.target)?.y || 0)
            .attr('stroke', d => ({
                read: '#10b981',
                write: '#f59e0b', 
                readwrite: '#2563eb'
            }[d.access] || '#94a3b8'))
            .attr('stroke-width', 2)
            .attr('opacity', 0.6)
            .style('cursor', 'pointer')
            .on('mouseenter', function(event, d) {
                d3.select(this).attr('opacity', 0.9).attr('stroke-width', 3);
                const sourceNode = data.nodes.find(n => n.id === d.source);
                const targetNode = data.nodes.find(n => n.id === d.target);
                tooltip.style('opacity', 1)
                    .html(`
                        <div style="font-weight: bold; margin-bottom: 6px;">Connection Details</div>
                        <div><strong>From:</strong> ${sourceNode?.label || 'Unknown'}</div>
                        <div><strong>To:</strong> ${targetNode?.label || 'Unknown'}</div>
                        <div><strong>Access:</strong> <span style="color: ${({
                            read: '#10b981',
                            write: '#f59e0b', 
                            readwrite: '#2563eb'
                        }[d.access] || '#94a3b8')}">${d.access}</span></div>
                    `)
                    .style('left', (event.pageX + 15) + 'px')
                    .style('top', (event.pageY - 10) + 'px');
            })
            .on('mouseleave', function() {
                d3.select(this).attr('opacity', 0.6).attr('stroke-width', 2);
                tooltip.style('opacity', 0);
            });

        const truncate = (s, maxLen = 15) => {
            if (!s) return '';
            return s.length > maxLen ? s.slice(0, maxLen - 1) + '…' : s;
        };

        // Draw client nodes
        const clientGroups = root.append('g').attr('class', 'clients')
            .selectAll('g.client')
            .data(clients)
            .enter()
            .append('g')
            .attr('class', 'client')
            .attr('transform', d => `translate(${cPos.get(d.id).x}, ${cPos.get(d.id).y})`)
            .style('cursor', 'pointer')
            .on('click', (event, d) => this.showNodeDetails(d, data))
            .on('mouseenter', (event, d) => {
                d3.select(event.currentTarget).select('circle').transition().duration(200).attr('r', 18);
                
                // Get client details from current data
                const clientData = this.currentData?.clients?.find(c => c.name === d.label);
                const topicCount = clientData?.topics?.length || 0;
                const accessTypes = clientData?.topics?.map(t => t.access) || [];
                const uniqueAccess = [...new Set(accessTypes)];
                
                tooltip.style('opacity', 1)
                    .html(`
                        <div style="font-weight: bold; margin-bottom: 6px; color: #3b82f6;">Client Details</div>
                        <div><strong>Name:</strong> ${d.label}</div>
                        <div><strong>Topics:</strong> ${topicCount}</div>
                        <div><strong>Permissions:</strong> ${uniqueAccess.join(', ') || 'None'}</div>
                        ${topicCount > 0 ? `<div style="margin-top: 6px; font-size: 11px; color: #ccc;">Click to see all topic permissions</div>` : ''}
                    `)
                    .style('left', (event.pageX + 15) + 'px')
                    .style('top', (event.pageY - 10) + 'px');
            })
            .on('mouseleave', function() {
                d3.select(this).select('circle').transition().duration(200).attr('r', 15);
                tooltip.style('opacity', 0);
            });
        
        clientGroups.append('circle')
            .attr('r', 15)
            .attr('fill', '#2563eb')
            .attr('stroke', '#fff')
            .attr('stroke-width', 3)
            .attr('filter', 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))');
        
        // Client labels with background for readability
        clientGroups.append('text')
            .text(d => truncate(d.label, 12))
            .attr('x', -25)
            .attr('y', 5)
            .attr('text-anchor', 'end')
            .attr('font-size', '12px')
            .attr('font-weight', '600')
            .attr('fill', 'white')
            .attr('stroke', 'white')
            .attr('stroke-width', '3')
            .attr('paint-order', 'stroke');
        
        clientGroups.append('text')
            .text(d => truncate(d.label, 12))
            .attr('x', -25)
            .attr('y', 5)
            .attr('text-anchor', 'end')
            .attr('font-size', '12px')
            .attr('font-weight', '600')
            .attr('fill', '#1e293b');

        // Draw topic nodes
        const topicGroups = root.append('g').attr('class', 'topics')
            .selectAll('g.topic')
            .data(topics)
            .enter()
            .append('g')
            .attr('class', 'topic')
            .attr('transform', d => `translate(${tPos.get(d.id).x}, ${tPos.get(d.id).y})`)
            .style('cursor', 'pointer')
            .on('click', (event, d) => this.showNodeDetails(d, data))
            .on('mouseenter', (event, d) => {
                d3.select(event.currentTarget).select('circle').transition().duration(200).attr('r', 15);
                
                // Get topic details from current data
                const topicData = this.currentData?.topics?.find(t => t.topic === d.label);
                const clientCount = topicData?.client_count || 0;
                const clients = topicData?.all_clients || [];
                const accessTypes = clients.map(c => c.access);
                const uniqueAccess = [...new Set(accessTypes)];
                
                tooltip.style('opacity', 1)
                    .html(`
                        <div style="font-weight: bold; margin-bottom: 6px; color: #d97706;">Topic Details</div>
                        <div><strong>Topic:</strong> ${d.label}</div>
                        <div><strong>Clients:</strong> ${clientCount}</div>
                        <div><strong>Access Types:</strong> ${uniqueAccess.join(', ') || 'None'}</div>
                        ${clientCount > 0 ? `<div style="margin-top: 6px; font-size: 11px; color: #ccc;">Click to see all client permissions</div>` : ''}
                    `)
                    .style('left', (event.pageX + 15) + 'px')
                    .style('top', (event.pageY - 10) + 'px');
            })
            .on('mouseleave', function() {
                d3.select(this).select('circle').transition().duration(200).attr('r', 12);
                tooltip.style('opacity', 0);
            });
        
        topicGroups.append('circle')
            .attr('r', 12)
            .attr('fill', '#d97706')
            .attr('stroke', '#fff')
            .attr('stroke-width', 3)
            .attr('filter', 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))');
        
        // Topic labels with background for readability
        topicGroups.append('text')
            .text(d => truncate(d.label, 15))
            .attr('x', 20)
            .attr('y', 5)
            .attr('text-anchor', 'start')
            .attr('font-size', '11px')
            .attr('font-weight', '600')
            .attr('fill', 'white')
            .attr('stroke', 'white')
            .attr('stroke-width', '3')
            .attr('paint-order', 'stroke');
        
        topicGroups.append('text')
            .text(d => truncate(d.label, 15))
            .attr('x', 20)
            .attr('y', 5)
            .attr('text-anchor', 'start')
            .attr('font-size', '11px')
            .attr('font-weight', '600')
            .attr('fill', '#1e293b');

        // Add section labels
        root.append('text')
            .attr('x', clientX)
            .attr('y', -25)
            .attr('text-anchor', 'middle')
            .attr('font-size', '14px')
            .attr('font-weight', '700')
            .attr('fill', '#2563eb')
            .text('CLIENTS');
        
        root.append('text')
            .attr('x', topicX)
            .attr('y', -25)
            .attr('text-anchor', 'middle')
            .attr('font-size', '14px')
            .attr('font-weight', '700')
            .attr('fill', '#d97706')
            .text('TOPICS');

        // Update legend
        const legend = document.getElementById('graphLegend');
        if (legend) {
            legend.style.opacity = data.edges.length > 0 ? 1 : 0.4;
        }
        
        this.networkGraph = { svg, tooltip };
        
    }

    showNodeDetails(node, relationships) {
        const panel = document.getElementById('graphDetails');
        const body = document.getElementById('detailsBody');
        const title = document.getElementById('detailsTitle');
        document.getElementById('closeDetails').onclick = () => panel.style.display='none';

        if (!panel) return;
        panel.style.display='flex';
        title.textContent = node.label;

        if (node.type === 'client') {
            const topics = this.currentData.clients.find(c=> c.name===node.label)?.topics || [];
            body.innerHTML = `<div class="details-heading">Client</div><p><strong>${node.label}</strong></p>`+
                `<div class="details-heading">Rules (${topics.length})</div>`+
                `<ul>${topics.map(t=> `<li><code>${t.topic}</code> <span class="access-badge ${t.access}">${t.access}</span></li>`).join('')}</ul>`;
        } else {
            // topic node
            const topicInfo = this.currentData.topics.find(t=> t.topic===node.label);
            if (topicInfo) {
                body.innerHTML = `<div class="details-heading">Topic</div><p><code>${topicInfo.topic}</code></p>`+
                    `<p><strong>${topicInfo.client_count}</strong> client(s)</p>`+
                    `<div class="details-heading">Access</div>`+
                    `<ul>${topicInfo.all_clients.map(c=> `<li>${c.client} <span class="access-badge ${c.access}">${c.access}</span></li>`).join('')}</ul>`;
            } else {
                body.innerHTML = '<p>No details.</p>';
            }
        }
    }
    
    applyFilters() { /* filters removed in minimal version */ }
    updateFilterBadge() {}

    filteredRelationships() {
        if (!this.currentData || !this.currentData.relationships) {
            return { nodes: [], edges: [] };
        }
        
        const accessVal = document.getElementById('accessFilter')?.value || '';
        const clientQ = document.getElementById('clientFilter')?.value.trim().toLowerCase() || '';
        const topicQ = document.getElementById('topicFilter')?.value.trim().toLowerCase() || '';
        
        const base = this.currentData.relationships;
        if (!accessVal && !clientQ && !topicQ) return base;
        
        const nodes = [];
        const nodeMap = new Map();
        const edges = [];
        
        base.edges.forEach(e => {
            const edgeAccess = e.access;
            const sourceNode = base.nodes.find(n => n.id === e.source);
            const targetNode = base.nodes.find(n => n.id === e.target);
            
            if (!sourceNode || !targetNode) return;
            
            const edgeClient = sourceNode.type === 'client' ? sourceNode.label.toLowerCase() : targetNode.label.toLowerCase();
            const edgeTopic = sourceNode.type === 'topic' ? sourceNode.label.toLowerCase() : targetNode.label.toLowerCase();
            
            if (clientQ && !edgeClient.includes(clientQ)) return;
            if (topicQ && !edgeTopic.includes(topicQ)) return;
            if (accessVal && accessVal !== edgeAccess) return;
            
            // Add nodes if not already added
            [sourceNode, targetNode].forEach(n => {
                if (!nodeMap.has(n.id)) {
                    nodeMap.set(n.id, { ...n });
                    nodes.push(nodeMap.get(n.id));
                }
            });
            
            edges.push({ ...e });
        });
        
        return { nodes, edges };
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
}

// Initialize the application
const aclVisualizer = new ACLVisualizer();

// Global functions for button handlers
window.aclVisualizer = aclVisualizer;

// ...existing code...
const offsetX = (width - margin.left - margin.right) / 2;
const offsetY = (height - margin.top - margin.bottom) / 2;
const root = svg.append('g').attr('transform', `translate(${margin.left + offsetX},${margin.top + offsetY})`);

// Add hover effect to display full labels
const truncate = (s, m = 20) => {
    if (!s) return '';
    return s.length > m ? s.slice(0, m - 1) + '\u2026' : s;
};

const showFullLabel = (element, label) => {
    const tooltip = d3.select('body').append('div')
        .attr('class', 'tooltip')
        .style('position', 'absolute')
        .style('background', '#fff')
        .style('border', '1px solid #ccc')
        .style('padding', '5px')
        .style('border-radius', '4px')
        .style('box-shadow', '0 2px 4px rgba(0, 0, 0, 0.2)')
        .style('pointer-events', 'none')
        .text(label);

    element.on('mouseenter', function (event) {
        tooltip.style('left', `${event.pageX + 10}px`).style('top', `${event.pageY + 10}px`).style('display', 'block');
    }).on('mouseleave', function () {
        tooltip.style('display', 'none');
        tooltip.remove();
    });
};

// Apply hover effect to nodes
clients.forEach(client => {
    const node = root.append('circle')
        .attr('r', 15)
        .attr('fill', '#2563eb')
        .attr('stroke', '#fff')
        .attr('stroke-width', 2);
    showFullLabel(node, client.label);
});

// Apply hover effect to topics
topics.forEach(topic => {
    const node = root.append('circle')
        .attr('r', 12)
        .attr('fill', '#d97706')
        .attr('stroke', '#fff')
        .attr('stroke-width', 2);
    showFullLabel(node, topic.label);
});