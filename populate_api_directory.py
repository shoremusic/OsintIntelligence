"""
Script to populate the database with API configurations from public API directories
- APIs.guru (https://github.com/APIs-guru/openapi-directory)
- Public APIs GitHub Repo (https://github.com/public-apis/public-apis)
"""

import json
import logging
import os
import time
import requests
from app import app, db
from models import APIConfiguration

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants for API directories - with fallback URLs
APIS_GURU_URLS = [
    "https://api.apis.guru/v2/list.json",
    "https://raw.githubusercontent.com/APIs-guru/openapi-directory/gh-pages/v2/list.json"
]
PUBLIC_APIS_URLS = [
    "https://api.publicapis.org/entries",
    "https://raw.githubusercontent.com/public-apis/public-apis/master/entries",
    "https://raw.githubusercontent.com/public-apis/public-apis/master/entries.json"
]

# For resilience, also include a small set of pre-defined OSINT APIs
PREDEFINED_APIS = [
    {
        "api_name": "IPinfo",
        "api_url": "https://ipinfo.io",
        "api_key_env": "IPINFO_API_KEY",
        "description": "IPinfo provides accurate IP address data that helps understand and reach targeted audiences. The service offers IP to geolocation, ASN, carrier information, and more.\n\nOSINT Categories: Location, Network, Digital Footprint",
        "endpoints": json.dumps({
            "ip_lookup": {
                "path": "/{ip}",
                "method": "GET",
                "params": {
                    "token": "{api_key}"
                },
                "description": "Get details for a specific IP address"
            },
            "bulk_lookup": {
                "path": "/batch",
                "method": "POST",
                "params": {
                    "token": "{api_key}"
                },
                "description": "Look up information for multiple IP addresses"
            }
        }),
        "format": json.dumps({
            "example": {
                "ip": "8.8.8.8",
                "hostname": "dns.google",
                "city": "Mountain View",
                "region": "California",
                "country": "US",
                "loc": "37.4056,-122.0775",
                "org": "AS15169 Google LLC",
                "postal": "94043",
                "timezone": "America/Los_Angeles"
            },
            "osint_categories": ["location", "network", "digital_footprint"],
            "source": "predefined"
        })
    },
    {
        "api_name": "EmailRep",
        "api_url": "https://emailrep.io",
        "api_key_env": "EMAILREP_API_KEY",
        "description": "EmailRep is a system of crawlers, scanners, and enrichment services that collects reputation data on email addresses. It helps determine if an email is suspicious, malicious, or legitimate.\n\nOSINT Categories: Contact, Security, Digital Footprint",
        "endpoints": json.dumps({
            "email_lookup": {
                "path": "/query/{email}",
                "method": "GET",
                "headers": {
                    "Key": "{api_key}"
                },
                "description": "Lookup reputation information for an email address"
            }
        }),
        "format": json.dumps({
            "example": {
                "email": "bill@microsoft.com",
                "reputation": "high",
                "suspicious": False,
                "references": 79,
                "details": {
                    "blacklisted": False,
                    "malicious_activity": False,
                    "malicious_activity_recent": False,
                    "credentials_leaked": True,
                    "credentials_leaked_recent": False,
                    "data_breach": True,
                    "first_seen": "04/28/2008",
                    "last_seen": "07/26/2020",
                    "domain_exists": True,
                    "domain_reputation": "high",
                    "domain_age": "1975-04-04",
                    "new_domain": False
                }
            },
            "osint_categories": ["contact", "security", "digital_footprint"],
            "source": "predefined"
        })
    },
    {
        "api_name": "Geocoding",
        "api_url": "https://maps.googleapis.com/maps/api",
        "api_key_env": "GOOGLE_MAPS_API_KEY",
        "description": "Google Maps Geocoding API provides geocoding and reverse geocoding of addresses. Find location coordinates from addresses or addresses from coordinates for OSINT investigations.\n\nOSINT Categories: Location",
        "endpoints": json.dumps({
            "geocode": {
                "path": "/geocode/json",
                "method": "GET",
                "params": {
                    "address": "{address}",
                    "key": "{api_key}"
                },
                "description": "Convert an address to geographic coordinates"
            },
            "reverse_geocode": {
                "path": "/geocode/json",
                "method": "GET",
                "params": {
                    "latlng": "{latitude},{longitude}",
                    "key": "{api_key}"
                },
                "description": "Convert geographic coordinates to an address"
            }
        }),
        "format": json.dumps({
            "example": {
                "results": [
                    {
                        "formatted_address": "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA",
                        "geometry": {
                            "location": {
                                "lat": 37.4224764,
                                "lng": -122.0842499
                            }
                        }
                    }
                ]
            },
            "osint_categories": ["location"],
            "source": "predefined"
        })
    }
]

# OSINT categories and relevant keywords
OSINT_CATEGORIES = {
    "personal_info": ["person", "people", "personal", "individual", "identity", "background", "check"],
    "contact": ["email", "phone", "contact", "sms", "verification", "validate"],
    "social_media": ["social", "network", "profile", "twitter", "facebook", "instagram", "linkedin", "social media"],
    "location": ["location", "geo", "address", "map", "place", "tracking", "ip", "geolocation"],
    "digital_footprint": ["search", "lookup", "find", "discover", "data", "breach", "leaks"],
    "network": ["network", "domain", "dns", "ip", "whois", "ssl", "certificate", "host"],
    "security": ["security", "threat", "vulnerability", "abuse", "malware", "phishing", "intelligence"],
    "business": ["company", "business", "corporate", "organization", "employer"],
    "financial": ["finance", "bank", "money", "payment", "crypto", "bitcoin", "transaction"],
    "government": ["government", "public", "record", "license", "official", "authority"],
    "general": ["osint", "intelligence", "information", "data"]
}

def fetch_apis_guru():
    """Fetch APIs from the APIs.guru directory"""
    logger.info("Fetching APIs from APIs.guru...")
    
    # Try all available URLs until one works
    api_data = None
    for url in APIS_GURU_URLS:
        try:
            logger.info(f"Trying to fetch APIs from {url}...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            api_data = response.json()
            logger.info(f"Successfully fetched APIs from {url}")
            break
        except requests.RequestException as e:
            logger.warning(f"Error fetching APIs from {url}: {str(e)}")
    
    # If all URLs failed, return empty list
    if api_data is None:
        logger.warning("All APIs.guru URLs failed. Using predefined APIs only.")
        return []
    
    # Process the API data
    apis = []
    try:
        # Limit to 20 APIs to prevent timeouts in web requests
        api_count = 0
        max_apis = 20
        
        for provider, provider_apis in api_data.items():
            if api_count >= max_apis:
                break
                
            for version, details in provider_apis["versions"].items():
                if api_count >= max_apis:
                    break
                    
                # Filter for OSINT-relevant APIs
                categories = details.get("info", {}).get("x-apisguru-categories", [])
                title = details.get("info", {}).get("title", "").lower()
                description = details.get("info", {}).get("description", "").lower()
                
                # Determine API OSINT categories
                api_osint_categories = []
                for category, keywords in OSINT_CATEGORIES.items():
                    for keyword in keywords:
                        if (keyword in title or keyword in description or 
                            any(keyword in cat.lower() for cat in categories)):
                            api_osint_categories.append(category)
                            break
                
                # API is relevant if it falls into at least one OSINT category
                is_relevant = len(api_osint_categories) > 0
                
                if is_relevant:
                    api_count += 1
                    api_info = details.get("info", {})
                    
                    # Extract endpoints from paths
                    paths = details.get("swaggerUrl", None)
                    endpoints = {}
                    
                    # We'll need to fetch the full OpenAPI spec to get paths
                    if paths:
                        try:
                            spec_response = requests.get(details["swaggerUrl"], timeout=5)
                            if spec_response.status_code == 200:
                                try:
                                    spec = spec_response.json()
                                    # Extract up to 3 example endpoints
                                    count = 0
                                    for path, methods in spec.get("paths", {}).items():
                                        if count >= 3:
                                            break
                                        
                                        for method, operation in methods.items():
                                            if method.lower() in ["get", "post"] and count < 3:
                                                endpoint_name = operation.get("operationId", f"{method}_{path}")
                                                endpoint_name = endpoint_name.replace(" ", "_").lower()
                                                
                                                endpoint_config = {
                                                    "path": path,
                                                    "method": method.upper(),
                                                    "params": {},
                                                    "description": operation.get("summary", "No description available")
                                                }
                                                
                                                # Add parameters
                                                for param in operation.get("parameters", []):
                                                    if param.get("in") == "query":
                                                        param_name = param.get("name")
                                                        if param_name:
                                                            if "api_key" in param_name.lower() or "apikey" in param_name.lower():
                                                                endpoint_config["params"][param_name] = "{api_key}"
                                                            else:
                                                                endpoint_config["params"][param_name] = f"{{{param_name}}}"
                                                
                                                endpoints[endpoint_name] = endpoint_config
                                                count += 1
                                except json.JSONDecodeError:
                                    logger.warning(f"Could not parse OpenAPI spec for {provider}")
                        except requests.RequestException as e:
                            logger.warning(f"Error fetching OpenAPI spec for {provider}: {str(e)}")
                    
                    # Format description to include OSINT categories
                    original_description = api_info.get("description", "No description available")
                    osint_categories_str = ", ".join([cat.replace("_", " ").title() for cat in api_osint_categories])
                    enhanced_description = f"{original_description}\n\nOSINT Categories: {osint_categories_str}"
                    
                    api = {
                        "api_name": f"APIsguru - {api_info.get('title', provider)}",
                        "api_url": api_info.get("x-origin", [{}])[0].get("url", ""),
                        "api_key_env": f"{provider.upper().replace('.', '_').replace('-', '_')}_API_KEY",
                        "description": enhanced_description,
                        "endpoints": json.dumps(endpoints) if endpoints else json.dumps({}),
                        "format": json.dumps({
                            "example": {},
                            "osint_categories": api_osint_categories,
                            "source": "apis_guru"
                        })
                    }
                    
                    apis.append(api)
                    logger.info(f"Processed API: {api['api_name']}")
        
        logger.info(f"Found {len(apis)} OSINT-relevant APIs from APIs.guru")
        return apis
    
    except Exception as e:
        logger.error(f"Error processing APIs from APIs.guru: {str(e)}")
        return []

def fetch_public_apis():
    """Fetch APIs from the Public APIs directory"""
    logger.info("Fetching APIs from Public APIs directory...")
    
    # Try all available URLs until one works
    api_data = None
    for url in PUBLIC_APIS_URLS:
        try:
            logger.info(f"Trying to fetch APIs from {url}...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            api_data = response.json()
            logger.info(f"Successfully fetched APIs from {url}")
            break
        except requests.RequestException as e:
            logger.warning(f"Error fetching APIs from {url}: {str(e)}")
    
    # If all URLs failed, return empty list
    if api_data is None:
        logger.warning("All Public APIs URLs failed. Using predefined APIs only.")
        return []
    
    # Process the API data
    apis = []
    try:
        # Map Public API categories to our OSINT categories
        category_mapping = {
            "Security": ["security", "digital_footprint"],
            "Data": ["digital_footprint", "general"],
            "Email": ["contact"],
            "Phone": ["contact"],
            "Science & Math": ["general"],
            "Social": ["social_media"],
            "Open Data": ["general", "digital_footprint"],
            "Geocoding": ["location"],
            "Government": ["government"],
            "Anti-Malware": ["security"],
            "Tracking": ["location", "digital_footprint"],
            "Authentication": ["security"],
            "Development": ["network", "general"]
        }
        
        for entry in api_data.get("entries", []):
            category = entry.get("Category")
            api_name = entry.get('API', '')
            description = entry.get('Description', '')
            
            # Determine if this API is OSINT-relevant
            api_osint_categories = []
            
            # Check if the API's category is in our mapping
            if category in category_mapping:
                api_osint_categories.extend(category_mapping[category])
            
            # Also check if the API name or description contains any of our OSINT keywords
            api_text = (api_name + " " + description).lower()
            for osint_category, keywords in OSINT_CATEGORIES.items():
                for keyword in keywords:
                    if keyword in api_text and osint_category not in api_osint_categories:
                        api_osint_categories.append(osint_category)
                        break
            
            # Only process if it has at least one OSINT category
            if api_osint_categories:
                # Determine API key parameter name based on Auth field
                auth = entry.get("Auth", "")
                api_key_param = "api_key"
                if auth == "apiKey":
                    api_key_param = "api_key"
                elif auth == "X-API-Key":
                    api_key_param = "X-API-Key"
                
                # Create a standard endpoint configuration
                endpoint_name = "default_endpoint"
                endpoint = {
                    "path": "/",
                    "method": "GET",
                    "params": {},
                    "description": entry.get("Description", "No description available")
                }
                
                # If auth is required, add API key parameter
                if auth and auth != "":
                    if auth in ["apiKey", "X-API-Key"]:
                        endpoint["params"][api_key_param] = "{api_key}"
                    # Add header for auth if specified
                    if auth.startswith("X-"):
                        endpoint["headers"] = {auth: "{api_key}"}
                
                endpoints = {endpoint_name: endpoint}
                
                # Format description to include OSINT categories
                original_description = entry.get("Description", "No description available")
                osint_categories_str = ", ".join([cat.replace("_", " ").title() for cat in api_osint_categories])
                enhanced_description = f"{original_description}\n\nOSINT Categories: {osint_categories_str}"
                
                api = {
                    "api_name": f"PublicAPI - {entry.get('API')}",
                    "api_url": entry.get("Link", "").rstrip("/"),
                    "api_key_env": f"{entry.get('API', '').upper().replace(' ', '_').replace('-', '_')}_API_KEY",
                    "description": enhanced_description,
                    "endpoints": json.dumps(endpoints),
                    "format": json.dumps({
                        "example": {},
                        "osint_categories": api_osint_categories,
                        "source": "public_apis",
                        "category": category
                    })
                }
                
                apis.append(api)
                logger.info(f"Processed API: {api['api_name']}")
        
        logger.info(f"Found {len(apis)} OSINT-relevant APIs from Public APIs directory")
        return apis
    
    except Exception as e:
        logger.error(f"Error processing APIs from Public APIs directory: {str(e)}")
        return []

def add_api_config_if_not_exists(api_data):
    """Add API configuration if it doesn't already exist"""
    existing = APIConfiguration.query.filter_by(api_name=api_data["api_name"]).first()
    if existing:
        logger.info(f"API '{api_data['api_name']}' already exists.")
        return existing
    
    try:
        new_api = APIConfiguration(
            api_name=api_data["api_name"],
            api_url=api_data["api_url"],
            api_key_env=api_data["api_key_env"],
            description=api_data["description"],
            endpoints=api_data["endpoints"],
            format=api_data["format"]
        )
        
        db.session.add(new_api)
        db.session.commit()
        logger.info(f"Added API: {api_data['api_name']}")
        return new_api
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding API {api_data['api_name']}: {str(e)}")
        return None

def main():
    """Main function to populate APIs from both directories"""
    logger.info("Starting API directory population...")
    
    with app.app_context():
        # Add predefined APIs first
        logger.info(f"Adding {len(PREDEFINED_APIS)} predefined OSINT APIs to database")
        for api_data in PREDEFINED_APIS:
            add_api_config_if_not_exists(api_data)
        
        # Fetch and add APIs from APIs.guru
        apis_guru_apis = fetch_apis_guru()
        logger.info(f"Adding {len(apis_guru_apis)} APIs from APIs.guru to database")
        for api_data in apis_guru_apis:
            add_api_config_if_not_exists(api_data)
        
        # Fetch and add APIs from Public APIs
        public_apis = fetch_public_apis()
        logger.info(f"Adding {len(public_apis)} APIs from Public APIs to database")
        for api_data in public_apis:
            add_api_config_if_not_exists(api_data)
            
    logger.info("Completed API directory population")

if __name__ == "__main__":
    main()