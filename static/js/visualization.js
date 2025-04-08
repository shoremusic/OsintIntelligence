/**
 * OSINT Application Visualization JavaScript
 * Handles data visualization using D3.js
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize visualizations if on the report page
    if (document.getElementById('report-container')) {
        initializeVisualizations();
    }
});

/**
 * Initialize all visualizations in the report
 */
function initializeVisualizations() {
    // Find all visualization containers
    document.querySelectorAll('.visualization-container').forEach(container => {
        const vizType = container.getAttribute('data-viz-type');
        const vizData = JSON.parse(container.getAttribute('data-viz-data') || '{}');
        const vizId = container.getAttribute('id');
        
        // Create visualization based on type
        switch (vizType) {
            case 'pie_chart':
                createPieChart(vizId, vizData);
                break;
            case 'bar_chart':
                createBarChart(vizId, vizData);
                break;
            case 'timeline':
                createTimeline(vizId, vizData);
                break;
            case 'network_graph':
                createNetworkGraph(vizId, vizData);
                break;
            case 'bullet_list':
                createBulletList(vizId, vizData);
                break;
            default:
                console.log(`Visualization type '${vizType}' not supported`);
        }
    });
}

/**
 * Create a pie chart visualization
 * @param {string} containerId - ID of the container element
 * @param {Object} data - Data for the visualization
 */
function createPieChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container || !data || !data.categories || !data.values) return;
    
    const width = container.clientWidth;
    const height = 300;
    const margin = 40;
    const radius = Math.min(width, height) / 2 - margin;
    
    // Create color scale
    const color = d3.scaleOrdinal()
        .domain(data.categories)
        .range(d3.schemeCategory10);
    
    // Create SVG
    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${width / 2}, ${height / 2})`);
    
    // Create pie chart
    const pie = d3.pie()
        .value(d => d.value);
    
    const pieData = data.categories.map((category, i) => ({
        name: category,
        value: data.values[i] || 0
    }));
    
    const arc = d3.arc()
        .innerRadius(0)
        .outerRadius(radius);
    
    const arcs = svg.selectAll('arc')
        .data(pie(pieData))
        .enter()
        .append('g')
        .attr('class', 'arc');
    
    arcs.append('path')
        .attr('d', arc)
        .attr('fill', d => color(d.data.name))
        .attr('stroke', 'white')
        .style('stroke-width', '2px');
    
    // Add labels
    arcs.append('text')
        .attr('transform', d => {
            const centroid = arc.centroid(d);
            const x = centroid[0];
            const y = centroid[1];
            const h = Math.sqrt(x * x + y * y);
            return `translate(${x / h * (radius * 0.8)}, ${y / h * (radius * 0.8)})`;
        })
        .attr('dy', '.35em')
        .attr('text-anchor', 'middle')
        .text(d => d.data.name);
    
    // Add legend
    const legend = svg.selectAll('.legend')
        .data(pieData)
        .enter()
        .append('g')
        .attr('class', 'legend')
        .attr('transform', (d, i) => `translate(${radius + 20}, ${i * 20 - height / 2 + 20})`);
    
    legend.append('rect')
        .attr('width', 15)
        .attr('height', 15)
        .attr('fill', d => color(d.name));
    
    legend.append('text')
        .attr('x', 20)
        .attr('y', 12.5)
        .attr('font-size', '12px')
        .text(d => `${d.name} (${d.value})`);
}

/**
 * Create a bar chart visualization
 * @param {string} containerId - ID of the container element
 * @param {Object} data - Data for the visualization
 */
function createBarChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container || !data || !data.categories || !data.values) return;
    
    const width = container.clientWidth;
    const height = 300;
    const margin = { top: 20, right: 30, bottom: 40, left: 50 };
    
    // Create SVG
    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // Create scales
    const x = d3.scaleBand()
        .domain(data.categories)
        .range([margin.left, width - margin.right])
        .padding(0.1);
    
    const y = d3.scaleLinear()
        .domain([0, d3.max(data.values) * 1.1]) // Add 10% headroom
        .nice()
        .range([height - margin.bottom, margin.top]);
    
    // Add bars
    svg.selectAll('rect')
        .data(data.values)
        .enter()
        .append('rect')
        .attr('x', (d, i) => x(data.categories[i]))
        .attr('y', d => y(d))
        .attr('width', x.bandwidth())
        .attr('height', d => y(0) - y(d))
        .attr('fill', 'steelblue');
    
    // Add axes
    svg.append('g')
        .attr('transform', `translate(0, ${height - margin.bottom})`)
        .call(d3.axisBottom(x))
        .selectAll('text')
        .attr('transform', 'rotate(-45)')
        .style('text-anchor', 'end');
    
    svg.append('g')
        .attr('transform', `translate(${margin.left}, 0)`)
        .call(d3.axisLeft(y));
    
    // Add labels
    svg.selectAll('.label')
        .data(data.values)
        .enter()
        .append('text')
        .attr('class', 'label')
        .attr('x', (d, i) => x(data.categories[i]) + x.bandwidth() / 2)
        .attr('y', d => y(d) - 5)
        .attr('text-anchor', 'middle')
        .text(d => d);
}

/**
 * Create a timeline visualization
 * @param {string} containerId - ID of the container element
 * @param {Object} data - Data for the visualization
 */
function createTimeline(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container || !data || !data.events || !data.events.length) return;
    
    // Sort events by date
    const events = data.events.sort((a, b) => new Date(a.date) - new Date(b.date));
    
    // Create timeline HTML
    let timelineHtml = '<div class="timeline">';
    
    events.forEach((event, index) => {
        const side = index % 2 === 0 ? 'left' : 'right';
        const date = new Date(event.date);
        const formattedDate = date.toLocaleDateString();
        
        timelineHtml += `
        <div class="timeline-item">
            <div class="timeline-badge ${side}">
                <i class="fas fa-circle"></i>
            </div>
            <div class="timeline-panel ${side}">
                <div class="timeline-heading">
                    <h5 class="timeline-title">${formattedDate}</h5>
                </div>
                <div class="timeline-body">
                    <p>${event.event}</p>
                    ${event.source ? `<small class="text-muted">Source: ${event.source}</small>` : ''}
                </div>
            </div>
        </div>
        `;
    });
    
    timelineHtml += '</div>';
    
    // Add timeline to container
    container.innerHTML = timelineHtml;
}

/**
 * Create a network graph visualization
 * @param {string} containerId - ID of the container element
 * @param {Object} data - Data for the visualization
 */
function createNetworkGraph(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container || !data || !data.nodes || !data.edges) return;
    
    const width = container.clientWidth;
    const height = 400;
    
    // Create SVG
    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // Create force simulation
    const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.edges).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(40));
    
    // Add edges
    const link = svg.append('g')
        .selectAll('line')
        .data(data.edges)
        .enter()
        .append('line')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', d => d.value || 1);
    
    // Add nodes
    const node = svg.append('g')
        .selectAll('g')
        .data(data.nodes)
        .enter()
        .append('g');
    
    // Add circles for nodes
    node.append('circle')
        .attr('r', d => d.value || 10)
        .attr('fill', d => d.color || '#69b3a2')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragging)
            .on('end', dragended));
    
    // Add labels for nodes
    node.append('text')
        .attr('dx', 15)
        .attr('dy', '.35em')
        .text(d => d.name)
        .style('font-size', '12px');
    
    // Add tooltip for nodes
    node.append('title')
        .text(d => d.tooltip || d.name);
    
    // Update positions on each tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        node
            .attr('transform', d => `translate(${d.x}, ${d.y})`);
    });
    
    // Drag functions
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragging(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

/**
 * Create a bullet list visualization
 * @param {string} containerId - ID of the container element
 * @param {Object} data - Data for the visualization
 */
function createBulletList(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container || !data || !data.items || !data.items.length) return;
    
    // Create bullet list HTML
    let listHtml = '<ul class="bullet-list">';
    
    data.items.forEach(item => {
        listHtml += `<li>${item}</li>`;
    });
    
    listHtml += '</ul>';
    
    // Add list to container
    container.innerHTML = listHtml;
}
