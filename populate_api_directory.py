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

# Constants for API directories
APIS_GURU_URL = "https://api.apis.guru/v2/list.json"
PUBLIC_APIS_URL = "https://api.publicapis.org/entries"

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
    try:
        response = requests.get(APIS_GURU_URL)
        response.raise_for_status()
        api_data = response.json()
        
        apis = []
        for provider, provider_apis in api_data.items():
            for version, details in provider_apis["versions"].items():
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
                    api_info = details.get("info", {})
                    
                    # Extract endpoints from paths
                    paths = details.get("swaggerUrl", None)
                    endpoints = {}
                    
                    # We'll need to fetch the full OpenAPI spec to get paths
                    if paths:
                        try:
                            spec_response = requests.get(details["swaggerUrl"])
                            if spec_response.status_code == 200:
                                try:
                                    spec = spec_response.json()
                                    # Extract up to 5 example endpoints
                                    count = 0
                                    for path, methods in spec.get("paths", {}).items():
                                        if count >= 5:
                                            break
                                        
                                        for method, operation in methods.items():
                                            if method.lower() in ["get", "post"] and count < 5:
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
                    
                    # Add a small delay to avoid overwhelming the APIs.guru service
                    time.sleep(0.1)
        
        logger.info(f"Found {len(apis)} OSINT-relevant APIs from APIs.guru")
        return apis
    
    except requests.RequestException as e:
        logger.error(f"Error fetching APIs from APIs.guru: {str(e)}")
        return []

def fetch_public_apis():
    """Fetch APIs from the Public APIs directory"""
    logger.info("Fetching APIs from Public APIs directory...")
    try:
        response = requests.get(PUBLIC_APIS_URL)
        response.raise_for_status()
        api_data = response.json()
        
        apis = []
        
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
    
    except requests.RequestException as e:
        logger.error(f"Error fetching APIs from Public APIs directory: {str(e)}")
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