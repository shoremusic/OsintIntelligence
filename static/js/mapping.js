/**
 * OSINT Application Mapping JavaScript
 * Handles mapping and geolocation visualization using Leaflet.js
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize map if on the report page and map container exists
    const mapContainer = document.getElementById('location-map');
    if (mapContainer) {
        initializeMap(mapContainer);
    }
});

/**
 * Initialize the map and add markers
 * @param {HTMLElement} container - The map container element
 */
function initializeMap(container) {
    // Get map data from container attributes
    const mapData = JSON.parse(container.getAttribute('data-locations') || '[]');
    
    if (!mapData || !mapData.length) {
        container.innerHTML = '<div class="alert alert-info">No location data available</div>';
        return;
    }
    
    // Initialize map
    const map = L.map(container.id).setView([0, 0], 2);
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Create bounds for auto-zooming
    const bounds = L.latLngBounds();
    
    // Add markers for each location
    mapData.forEach(location => {
        if (!location.coordinates || location.coordinates.length !== 2) return;
        
        const [lat, lng] = location.coordinates;
        
        // Add marker
        const marker = L.marker([lat, lng]).addTo(map);
        
        // Add popup with location information
        let popupContent = `<strong>${location.location}</strong>`;
        if (location.description) {
            popupContent += `<br>${location.description}`;
        }
        if (location.source) {
            popupContent += `<br><small>Source: ${location.source}</small>`;
        }
        
        marker.bindPopup(popupContent);
        
        // Extend bounds to include this marker
        bounds.extend([lat, lng]);
    });
    
    // Fit map to bounds if we have markers
    if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50] });
    }
    
    // Add connection lines between points if requested
    if (mapData.length > 1 && container.getAttribute('data-show-paths') === 'true') {
        const pathPoints = mapData.map(location => location.coordinates);
        L.polyline(pathPoints, { color: 'red', weight: 2, opacity: 0.5, dashArray: '5, 10' }).addTo(map);
    }
    
    // Add heat map if requested and we have enough points
    if (mapData.length >= 3 && container.getAttribute('data-show-heat') === 'true') {
        const heatPoints = mapData.map(location => {
            const [lat, lng] = location.coordinates;
            return [lat, lng, location.intensity || 1];
        });
        
        L.heatLayer(heatPoints, {
            radius: 25,
            blur: 15,
            maxZoom: 17
        }).addTo(map);
    }
    
    // Force a resize after initialization to fix rendering issues
    setTimeout(() => {
        map.invalidateSize();
    }, 100);
}

/**
 * Create a new map with the specified locations
 * @param {string} containerId - ID of the container element
 * @param {Array} locations - Array of location objects with coordinates
 * @param {Object} options - Map options
 */
function createMap(containerId, locations, options = {}) {
    const container = document.getElementById(containerId);
    if (!container || !locations || !locations.length) return;
    
    // Set data attributes for the map
    container.setAttribute('data-locations', JSON.stringify(locations));
    
    if (options.showPaths) {
        container.setAttribute('data-show-paths', 'true');
    }
    
    if (options.showHeat) {
        container.setAttribute('data-show-heat', 'true');
    }
    
    // Initialize the map
    initializeMap(container);
}
