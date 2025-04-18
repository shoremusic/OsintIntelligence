import os
import requests
import json
import logging
from app import db
from models import APIConfiguration, APIResult
import time
from datetime import datetime
from openai_service import analyze_image

# Configure logging
logger = logging.getLogger(__name__)

# RapidAPI credentials - securely loaded from environment variables
# as recommended in the RapidAPI documentation
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")
# Base domain for all RapidAPI services
RAPIDAPI_HOST = "rapidapi.com"

# RapidAPI rate limiting constants
RAPIDAPI_RATE_LIMIT_HEADER = "X-RateLimit-Limit"
RAPIDAPI_RATE_REMAINING_HEADER = "X-RateLimit-Remaining"

def query_apis(case_id, llm_analysis, available_apis):
    """
    Query selected APIs based on LLM analysis
    
    Args:
        case_id (int): ID of the OSINT case
        llm_analysis (dict): LLM analysis of input data with API recommendations
        available_apis (list): List of available API configurations
        
    Returns:
        list: List of API results
    """
    results = []
    
    try:
        # Get API category recommendations from LLM analysis
        recommended_categories = llm_analysis.get('recommended_api_categories', [])
        query_parameters = llm_analysis.get('query_parameters', {})
        
        logger.debug(f"Recommended API categories: {recommended_categories}")
        logger.debug(f"Available APIs: {[api.api_name for api in available_apis]}")
        
        for api in available_apis:
            # Check if this API should be used based on LLM recommendations
            api_category_match = False
            
            # Process the API's endpoints to check for category matches
            if api.endpoints:
                try:
                    endpoints = json.loads(api.endpoints)
                    for endpoint_name, endpoint_config in endpoints.items():
                        # Get the endpoint's categorization (defaulting to empty strings)
                        data_type = endpoint_config.get('data_type', '')
                        entity_type = endpoint_config.get('entity_type', '')
                        attribute_type = endpoint_config.get('attribute_type', '')
                        
                        # If the endpoint doesn't have categorization, try to use 'type' field for backward compatibility
                        if not data_type and 'type' in endpoint_config:
                            # Try to infer data_type, entity_type from 'type'
                            endpoint_type = endpoint_config.get('type', '').lower()
                            
                            if 'email' in endpoint_type:
                                data_type = 'TEXT'
                                entity_type = 'PERSON'
                                attribute_type = 'EMAIL'
                            elif 'phone' in endpoint_type:
                                data_type = 'TEXT'
                                entity_type = 'PERSON'
                                attribute_type = 'PHONE'
                            elif 'social' in endpoint_type:
                                data_type = 'TEXT'
                                entity_type = 'PERSON'
                                attribute_type = 'USERNAME'
                            elif 'location' in endpoint_type or 'geo' in endpoint_type:
                                data_type = 'LOCATION'
                                entity_type = 'ADDRESS'
                                attribute_type = 'COORDINATES'
                            elif 'image' in endpoint_type:
                                data_type = 'IMAGE'
                                entity_type = 'PERSON'
                                attribute_type = 'FACE'
                            
                        # Skip endpoints without proper categorization
                        if not data_type or not entity_type or not attribute_type:
                            continue
                        
                        # Try to match with recommended categories
                        for category in recommended_categories:
                            rec_data_type = category.get('data_type', '')
                            rec_entity_type = category.get('entity_type', '')
                            rec_attribute_type = category.get('attribute_type', '')
                            
                            # Check if this endpoint matches the recommended category
                            # We'll consider it a match if the data_type and at least one other field matches
                            if (data_type and rec_data_type and data_type.upper() == rec_data_type.upper() and 
                                ((entity_type and rec_entity_type and entity_type.upper() == rec_entity_type.upper()) or
                                 (attribute_type and rec_attribute_type and attribute_type.upper() == rec_attribute_type.upper()))):
                                api_category_match = True
                                break
                                
                        if api_category_match:
                            break
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Error parsing endpoints for API {api.api_name}: {e}")
            
            if not api_category_match:
                logger.debug(f"Skipping API {api.api_name} - does not match any recommended category")
                continue
            
            # Get API configuration
            endpoints = json.loads(api.endpoints) if api.endpoints else {}
            
            # Get API key from environment variables
            api_key = os.environ.get(api.api_key_env) if api.api_key_env else None
            
            # Query each relevant endpoint
            for endpoint_name, endpoint_config in endpoints.items():
                try:
                    # Get the endpoint's categorization (defaulting to empty strings)
                    data_type = endpoint_config.get('data_type', '')
                    entity_type = endpoint_config.get('entity_type', '')
                    attribute_type = endpoint_config.get('attribute_type', '')
                    
                    # If the endpoint doesn't have categorization, try to use 'type' field for backward compatibility
                    if not data_type and 'type' in endpoint_config:
                        # Try to infer data_type, entity_type from 'type'
                        endpoint_type = endpoint_config.get('type', '').lower()
                        
                        if 'email' in endpoint_type:
                            data_type = 'TEXT'
                            entity_type = 'PERSON'
                            attribute_type = 'EMAIL'
                        elif 'phone' in endpoint_type:
                            data_type = 'TEXT'
                            entity_type = 'PERSON'
                            attribute_type = 'PHONE'
                        elif 'social' in endpoint_type:
                            data_type = 'TEXT'
                            entity_type = 'PERSON'
                            attribute_type = 'USERNAME'
                        elif 'location' in endpoint_type or 'geo' in endpoint_type:
                            data_type = 'LOCATION'
                            entity_type = 'ADDRESS'
                            attribute_type = 'COORDINATES'
                        elif 'image' in endpoint_type:
                            data_type = 'IMAGE'
                            entity_type = 'PERSON'
                            attribute_type = 'FACE'
                    
                    # Skip endpoints without proper categorization
                    if not data_type or not entity_type or not attribute_type:
                        logger.debug(f"Skipping endpoint {endpoint_name} - missing categorization")
                        continue
                    
                    # Create a category key for matching with query parameters
                    category_key = f"{data_type}/{entity_type}/{attribute_type}"
                    
                    # Check if we have parameters for this category
                    params_to_use = []
                    if category_key in query_parameters and query_parameters[category_key]:
                        params_to_use = query_parameters[category_key]
                    
                    # If no direct category match, check for backward compatibility with old query parameter format
                    if not params_to_use:
                        # For backward compatibility, check the old endpoint 'type' field
                        endpoint_type = endpoint_config.get('type', '').lower()
                        for param_type, param_values in query_parameters.items():
                            # Handle both new format (TEXT/PERSON/EMAIL) and old format (email)
                            if '/' not in param_type and param_type.lower() in endpoint_type and param_values:
                                params_to_use.extend(param_values)
                    
                    if not params_to_use:
                        logger.debug(f"Skipping endpoint {endpoint_name} - no matching parameters for {category_key}")
                        continue
                    
                    # Prepare request URL and headers
                    url = f"{api.api_url.rstrip('/')}/{endpoint_config.get('path', '').lstrip('/')}"
                    headers = {
                        'Content-Type': 'application/json'
                    }
                    
                    # Add API key to headers or params as specified
                    params = {}
                    if api_key:
                        if endpoint_config.get('auth_type') == 'header':
                            headers[endpoint_config.get('auth_header', 'x-api-key')] = api_key
                        else:
                            params[endpoint_config.get('auth_param', 'apiKey')] = api_key
                    
                    # Add query parameters
                    for param in params_to_use:
                        if param and param.strip():
                            param_name = endpoint_config.get('param_name', 'query')
                            params[param_name] = param
                    
                    # Skip if no parameters to send
                    if not params:
                        logger.debug(f"Skipping endpoint {endpoint_name} - no parameters to send")
                        continue
                    
                    # Make the API request
                    logger.debug(f"Querying API: {api.api_name}, Endpoint: {endpoint_name}, URL: {url}, Params: {params}")
                    
                    method = endpoint_config.get('method', 'GET').upper()
                    if method == 'GET':
                        response = requests.get(url, headers=headers, params=params, timeout=10)
                    elif method == 'POST':
                        response = requests.post(url, headers=headers, json=params, timeout=10)
                    else:
                        logger.error(f"Unsupported HTTP method: {method}")
                        continue
                    
                    # Process the response
                    if response.status_code == 200:
                        result_data = response.json()
                        
                        # Create API result record
                        api_result = APIResult(
                            case_id=case_id,
                            api_config_id=api.id,
                            endpoint=endpoint_name,
                            query_params=json.dumps(params),
                            result=json.dumps(result_data),
                            status='success',
                            created_at=datetime.now()
                        )
                        db.session.add(api_result)
                        db.session.commit()
                        
                        # Add to results list
                        result_dict = api_result.to_dict()
                        result_dict['api_name'] = api.api_name
                        result_dict['category'] = category_key  # Add category information
                        results.append(result_dict)
                        
                    else:
                        error_msg = f"API error: {response.status_code} - {response.text}"
                        logger.error(error_msg)
                        
                        # Create API result record for error
                        api_result = APIResult(
                            case_id=case_id,
                            api_config_id=api.id,
                            endpoint=endpoint_name,
                            query_params=json.dumps(params),
                            status='error',
                            error_message=error_msg,
                            created_at=datetime.now()
                        )
                        db.session.add(api_result)
                        db.session.commit()
                        
                        # Add to results list
                        result_dict = api_result.to_dict()
                        result_dict['api_name'] = api.api_name
                        result_dict['category'] = category_key  # Add category information
                        results.append(result_dict)
                    
                    # Rate limiting - pause between API calls
                    time.sleep(1)
                        
                except Exception as e:
                    error_msg = f"Error querying API endpoint {endpoint_name}: {str(e)}"
                    logger.error(error_msg)
                    
                    # Create API result record for error
                    api_result = APIResult(
                        case_id=case_id,
                        api_config_id=api.id,
                        endpoint=endpoint_name,
                        query_params=json.dumps(params) if 'params' in locals() else "{}",
                        status='error',
                        error_message=error_msg,
                        created_at=datetime.now()
                    )
                    db.session.add(api_result)
                    db.session.commit()
                    
                    # Add to results list
                    result_dict = api_result.to_dict()
                    result_dict['api_name'] = api.api_name
                    result_dict['category'] = category_key if 'category_key' in locals() else "UNKNOWN"  # Add category information
                    results.append(result_dict)
        
        logger.debug(f"Completed API queries. Results count: {len(results)}")
        return results
    
    except Exception as e:
        logger.error(f"Error in API query process: {str(e)}")
        return results

def get_all_apis():
    """
    Get all API configurations
    
    Returns:
        list: List of API configurations
    """
    try:
        apis = APIConfiguration.query.all()
        return apis
    except Exception as e:
        logger.error(f"Error getting APIs: {str(e)}")
        return []

def add_api_config(api_name, api_url, api_key_env, description, endpoints, format_details):
    """
    Add a new API configuration
    
    Args:
        api_name (str): Name of the API
        api_url (str): Base URL of the API
        api_key_env (str): Environment variable name for the API key
        description (str): Description of the API
        endpoints (str): JSON string of endpoint configurations
        format_details (str): JSON string of format details
        
    Returns:
        APIConfiguration: Newly created API configuration
    """
    try:
        # Validate endpoints JSON
        if endpoints:
            json.loads(endpoints)
        
        # Validate format JSON
        if format_details:
            json.loads(format_details)
        
        # Create new API configuration
        api_config = APIConfiguration(
            api_name=api_name,
            api_url=api_url,
            api_key_env=api_key_env,
            description=description,
            endpoints=endpoints,
            format=format_details,
            created_at=datetime.now()
        )
        
        db.session.add(api_config)
        db.session.commit()
        
        return api_config
    
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in endpoints or format field")
    
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error adding API configuration: {str(e)}")

def get_api_config(api_id):
    """
    Get an API configuration by ID
    
    Args:
        api_id (int): ID of the API configuration
        
    Returns:
        APIConfiguration: API configuration
    """
    try:
        api_config = APIConfiguration.query.get(api_id)
        if not api_config:
            raise ValueError(f"API configuration with ID {api_id} not found")
        
        return api_config
    
    except Exception as e:
        raise Exception(f"Error getting API configuration: {str(e)}")

def update_api_config(api_id, api_name, api_url, api_key_env, description, endpoints, format_details):
    """
    Update an API configuration
    
    Args:
        api_id (int): ID of the API configuration
        api_name (str): Name of the API
        api_url (str): Base URL of the API
        api_key_env (str): Environment variable name for the API key
        description (str): Description of the API
        endpoints (str): JSON string of endpoint configurations
        format_details (str): JSON string of format details
        
    Returns:
        APIConfiguration: Updated API configuration
    """
    try:
        # Get API configuration
        api_config = get_api_config(api_id)
        
        # Validate endpoints JSON
        if endpoints:
            json.loads(endpoints)
        
        # Validate format JSON
        if format_details:
            json.loads(format_details)
        
        # Update API configuration
        if api_name:
            api_config.api_name = api_name
        if api_url:
            api_config.api_url = api_url
        if api_key_env:
            api_config.api_key_env = api_key_env
        if description:
            api_config.description = description
        if endpoints:
            api_config.endpoints = endpoints
        if format_details:
            api_config.format = format_details
        
        api_config.updated_at = datetime.now()
        
        db.session.commit()
        
        return api_config
    
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in endpoints or format field")
    
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error updating API configuration: {str(e)}")

def delete_api_config(api_id):
    """
    Delete an API configuration
    
    Args:
        api_id (int): ID of the API configuration
        
    Returns:
        bool: True if successful
    """
    try:
        # Get API configuration
        api_config = get_api_config(api_id)
        
        # Delete API configuration
        db.session.delete(api_config)
        db.session.commit()
        
        return True
    
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Error deleting API configuration: {str(e)}")

def add_rapidapi_config(api_config, case_id):
    """
    Add a RapidAPI configuration on the fly
    
    Args:
        api_config (dict): Dictionary containing RapidAPI configuration
        case_id (int): ID of the OSINT case
        
    Returns:
        APIConfiguration: Newly created API configuration object
    """
    try:
        # Create a standardized endpoint configuration
        endpoints = {
            api_config['endpoint']: {
                'path': api_config['endpoint'],
                'method': api_config['method'],
                'auth_type': 'header',
                'auth_header': 'x-rapidapi-key',
                'param_name': api_config['param_name'],
                'type': api_config.get('type', 'unknown')
            }
        }
        
        # Create API configuration
        api_name = f"RapidAPI - {api_config['name']}"
        api_url = f"https://{api_config['host']}"
        
        api_config_obj = APIConfiguration(
            api_name=api_name,
            api_url=api_url,
            api_key_env="RAPIDAPI_KEY",
            description=f"RapidAPI integration for {api_config['name']} (automatically added)",
            endpoints=json.dumps(endpoints),
            format=json.dumps({"format": "json"}),
            created_at=datetime.now()
        )
        
        db.session.add(api_config_obj)
        db.session.commit()
        
        logger.info(f"Created new RapidAPI configuration: {api_name}")
        return api_config_obj
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding RapidAPI configuration: {str(e)}")
        # Create a placeholder API config that won't interfere with other operations
        placeholder = APIConfiguration(
            api_name=f"RapidAPI - {api_config.get('name', 'Unknown')}-{case_id}",
            api_url="https://rapidapi.com",
            api_key_env="RAPIDAPI_KEY",
            description="Error creating configuration - placeholder",
            endpoints="{}",
            format="{}",
            created_at=datetime.now()
        )
        db.session.add(placeholder)
        db.session.commit()
        return placeholder

def query_rapidapi(case_id, llm_analysis, available_apis, input_data):
    """
    Query RapidAPI based on LLM analysis
    
    Args:
        case_id (int): ID of the OSINT case
        llm_analysis (dict): LLM analysis of input data with API recommendations
        available_apis (list): List of available API configurations
        input_data (dict): User input data
        
    Returns:
        list: List of API results
    """
    results = []
    
    if not RAPIDAPI_KEY:
        logger.warning("RapidAPI key not configured. Skipping RapidAPI queries.")
        return results
    
    try:
        # Get recommended categories and parameters from LLM analysis
        recommended_categories = llm_analysis.get('recommended_api_categories', [])
        query_parameters = llm_analysis.get('query_parameters', {})
        
        # For backward compatibility, extract simple types if new format isn't available
        recommended_types = []
        if not recommended_categories:
            recommended_types = llm_analysis.get('recommended_api_types', [])
        
        # Define RapidAPI mappings - these are common OSINT APIs on RapidAPI
        rapidapi_mappings = {
            'email': [
                {
                    'name': 'Email Verification API',
                    'host': 'email-checker.p.rapidapi.com',
                    'endpoint': '/verify/v1',
                    'method': 'GET',
                    'param_name': 'email'
                },
                {
                    'name': 'Hunter.io Email Finder',
                    'host': 'hunter-email-finder.p.rapidapi.com',
                    'endpoint': '/v2/email-finder',
                    'method': 'GET',
                    'param_name': 'domain'
                }
            ],
            'phone': [
                {
                    'name': 'NumVerify API',
                    'host': 'numverify.p.rapidapi.com',
                    'endpoint': '/validate',
                    'method': 'GET',
                    'param_name': 'number'
                },
                {
                    'name': 'Phone Validator',
                    'host': 'phone-validator-api.p.rapidapi.com',
                    'endpoint': '/validate',
                    'method': 'GET',
                    'param_name': 'phoneNumber'
                }
            ],
            'ipaddress': [
                {
                    'name': 'IP Geolocation API',
                    'host': 'ip-geo-location.p.rapidapi.com',
                    'endpoint': '/ip/check',
                    'method': 'GET',
                    'param_name': 'ip'
                }
            ],
            'domain': [
                {
                    'name': 'Website Categorization',
                    'host': 'website-categorization.p.rapidapi.com',
                    'endpoint': '/api',
                    'method': 'GET',
                    'param_name': 'url'
                },
                {
                    'name': 'Domain WHOIS API',
                    'host': 'domain-whois.p.rapidapi.com',
                    'endpoint': '/api/domain/lookup',
                    'method': 'GET',
                    'param_name': 'domain'
                }
            ],
            'social': [
                {
                    'name': 'Social Media Analysis',
                    'host': 'social-media-stats-and-network-api.p.rapidapi.com',
                    'endpoint': '/stats',
                    'method': 'GET', 
                    'param_name': 'username'
                }
            ],
            'name': [
                {
                    'name': 'Person Lookup API',
                    'host': 'person-lookup.p.rapidapi.com',
                    'endpoint': '/v1/search',
                    'method': 'GET',
                    'param_name': 'name'
                }
            ],
            'location': [
                {
                    'name': 'Geocoding API',
                    'host': 'geocoding-by-api-ninjas.p.rapidapi.com',
                    'endpoint': '/v1/geocoding',
                    'method': 'GET',
                    'param_name': 'city'
                }
            ]
        }
        
        # Create a mapping between new category format and old data types
        category_to_type_mapping = {
            'TEXT/PERSON/EMAIL': 'email',
            'TEXT/PERSON/PHONE': 'phone',
            'TEXT/PERSON/USERNAME': 'social',
            'TEXT/PERSON/NAME': 'name',
            'NETWORK/DEVICE/IP': 'ipaddress',
            'TEXT/ORGANIZATION/DOMAIN': 'domain',
            'LOCATION/ADDRESS/COORDINATES': 'location',
            'IMAGE/PERSON/FACE': 'image'
        }
        
        # Process image data if available
        image_data = None
        
        for data_type, data_value in input_data.items():
            if data_type == 'has_image' and data_value:
                # Get image data from database
                from models import DataPoint
                image_point = DataPoint.query.filter_by(case_id=case_id, data_type='image').first()
                if image_point:
                    image_data = image_point.value
                    
                    # Analyze image if available
                    if image_data:
                        image_analysis = analyze_image(image_data)
                        rapidapi_mappings['image'] = [
                            {
                                'name': 'Image Analysis API',
                                'host': 'image-to-text-api.p.rapidapi.com',
                                'endpoint': '/analyze',
                                'method': 'POST',
                                'content_type': 'multipart/form-data',
                                'param_name': 'image',
                                'data_type': 'IMAGE',
                                'entity_type': 'PERSON',
                                'attribute_type': 'FACE'
                            }
                        ]
        
        # Query RapidAPI for each data type
        for data_type, param_values in query_parameters.items():
            # Map new category format to old data types
            api_type = data_type
            if '/' in data_type and data_type in category_to_type_mapping:
                api_type = category_to_type_mapping[data_type]
            
            if api_type in rapidapi_mappings and param_values:
                for api_config in rapidapi_mappings[api_type]:
                    # Add category information for later reference
                    api_config['category'] = data_type
                    for param_value in param_values:
                        if param_value and param_value.strip():
                            try:
                                # Prepare request
                                url = f"https://{api_config['host']}{api_config['endpoint']}"
                                headers = {
                                    'x-rapidapi-key': RAPIDAPI_KEY,
                                    'x-rapidapi-host': api_config['host']
                                }
                                
                                params = {
                                    api_config['param_name']: param_value
                                }
                                
                                # Make request
                                logger.debug(f"Querying RapidAPI: {api_config['name']}, URL: {url}, Params: {params}")
                                
                                try:
                                    if api_config['method'] == 'GET':
                                        logger.debug(f"Making GET request to {url}")
                                        response = requests.get(url, headers=headers, params=params, timeout=15)
                                    elif api_config['method'] == 'POST':
                                        if api_config.get('content_type') == 'multipart/form-data':
                                            # Handle file uploads
                                            files = None
                                            if data_type == 'image' and image_data:
                                                import base64
                                                import io
                                                image_content = base64.b64decode(image_data)
                                                files = {
                                                    'image': ('image.jpg', io.BytesIO(image_content), 'image/jpeg')
                                                }
                                                logger.debug(f"Making POST request with file upload to {url}")
                                                response = requests.post(url, headers=headers, data=params, files=files, timeout=30)
                                            else:
                                                logger.debug(f"Making POST request with form data to {url}")
                                                response = requests.post(url, headers=headers, data=params, timeout=15)
                                        else:
                                            logger.debug(f"Making POST request with JSON data to {url}")
                                            response = requests.post(url, headers=headers, json=params, timeout=15)
                                    else:
                                        logger.error(f"Unsupported HTTP method: {api_config['method']}")
                                        continue
                                        
                                    # Log rate limiting information if provided by RapidAPI
                                    if RAPIDAPI_RATE_LIMIT_HEADER in response.headers:
                                        rate_limit = response.headers.get(RAPIDAPI_RATE_LIMIT_HEADER)
                                        rate_remaining = response.headers.get(RAPIDAPI_RATE_REMAINING_HEADER, 'unknown')
                                        logger.debug(f"RapidAPI rate limit: {rate_limit}, remaining: {rate_remaining}")
                                        
                                except requests.exceptions.RequestException as e:
                                    # Handle request exceptions properly as recommended in RapidAPI best practices
                                    logger.error(f"Request error to {url}: {str(e)}")
                                    error_msg = f"Request error: {str(e)}"
                                    
                                    # Create API entry for the error
                                    api_name = f"RapidAPI - {api_config['name']}"
                                    api_config_obj = APIConfiguration.query.filter_by(api_name=api_name).first()
                                    
                                    if not api_config_obj:
                                        # Create API config on the fly for this RapidAPI
                                        api_config_obj = add_rapidapi_config(api_config, case_id)
                                    
                                    # Create API result record for error
                                    api_result = APIResult(
                                        case_id=case_id,
                                        api_config_id=api_config_obj.id,
                                        endpoint=api_config['endpoint'],
                                        query_params=json.dumps(params),
                                        status='error',
                                        error_message=error_msg,
                                        created_at=datetime.now()
                                    )
                                    db.session.add(api_result)
                                    db.session.commit()
                                    
                                    # Add to results list and skip to next API
                                    result_dict = api_result.to_dict()
                                    result_dict['api_name'] = api_name
                                    result_dict['category'] = api_config.get('category', data_type)
                                    results.append(result_dict)
                                    continue
                                
                                # Create API configuration entry if it doesn't exist
                                api_name = f"RapidAPI - {api_config['name']}"
                                api_config_obj = APIConfiguration.query.filter_by(api_name=api_name).first()
                                
                                if not api_config_obj:
                                    endpoints = {
                                        api_config['endpoint']: {
                                            'path': api_config['endpoint'],
                                            'method': api_config['method'],
                                            'auth_type': 'header',
                                            'auth_header': 'x-rapidapi-key',
                                            'param_name': api_config['param_name'],
                                            'type': data_type
                                        }
                                    }
                                    
                                    api_config_obj = APIConfiguration(
                                        api_name=api_name,
                                        api_url=f"https://{api_config['host']}",
                                        api_key_env="RAPIDAPI_KEY",
                                        description=f"RapidAPI integration for {api_config['name']}",
                                        endpoints=json.dumps(endpoints),
                                        format=json.dumps({"format": "json"}),
                                        created_at=datetime.now()
                                    )
                                    
                                    db.session.add(api_config_obj)
                                    db.session.commit()
                                
                                # Process the response based on status code - implementing best practices from RapidAPI docs
                                if 200 <= response.status_code < 300:  # Success codes (200-299)
                                    try:
                                        result_data = response.json()
                                    except json.JSONDecodeError:
                                        result_data = {"raw_text": response.text}
                                    
                                    logger.debug(f"RapidAPI success response from {api_config['name']}")
                                    
                                    # Create API result record
                                    api_result = APIResult(
                                        case_id=case_id,
                                        api_config_id=api_config_obj.id,
                                        endpoint=api_config['endpoint'],
                                        query_params=json.dumps(params),
                                        result=json.dumps(result_data),
                                        status='success',
                                        created_at=datetime.now()
                                    )
                                    db.session.add(api_result)
                                    db.session.commit()
                                    
                                    # Add to results list
                                    result_dict = api_result.to_dict()
                                    result_dict['api_name'] = api_name
                                    result_dict['category'] = api_config.get('category', data_type)
                                    results.append(result_dict)
                                    
                                elif response.status_code == 401 or response.status_code == 403:
                                    # Authentication errors - need new API key
                                    error_msg = f"RapidAPI authentication error: {response.status_code} - API key may be invalid or expired"
                                    logger.error(error_msg)
                                    
                                elif response.status_code == 429:
                                    # Rate limit exceeded
                                    error_msg = f"RapidAPI rate limit exceeded for {api_config['name']}"
                                    logger.error(error_msg)
                                    
                                    # Wait longer before next request
                                    time.sleep(3)
                                    
                                elif 400 <= response.status_code < 500:
                                    # Other client errors
                                    error_msg = f"RapidAPI client error: {response.status_code} - {response.text}"
                                    logger.error(error_msg)
                                    
                                elif 500 <= response.status_code < 600:
                                    # Server errors
                                    error_msg = f"RapidAPI server error: {response.status_code} - {response.text}"
                                    logger.error(error_msg)
                                    
                                else:
                                    # Other errors
                                    error_msg = f"RapidAPI unexpected error: {response.status_code} - {response.text}"
                                    logger.error(error_msg)
                                    
                                    # Create API result record for error
                                    api_result = APIResult(
                                        case_id=case_id,
                                        api_config_id=api_config_obj.id,
                                        endpoint=api_config['endpoint'],
                                        query_params=json.dumps(params),
                                        status='error',
                                        error_message=error_msg,
                                        created_at=datetime.now()
                                    )
                                    db.session.add(api_result)
                                    db.session.commit()
                                    
                                    # Add to results list
                                    result_dict = api_result.to_dict()
                                    result_dict['api_name'] = api_name
                                    result_dict['category'] = api_config.get('category', data_type)
                                    results.append(result_dict)
                                
                                # Rate limiting - pause between API calls
                                time.sleep(1.5)
                                
                            except Exception as e:
                                error_msg = f"Error querying RapidAPI {api_config['name']}: {str(e)}"
                                logger.error(error_msg)
                                
                                # Try to get API configuration object
                                api_name = f"RapidAPI - {api_config['name']}"
                                api_config_obj = APIConfiguration.query.filter_by(api_name=api_name).first()
                                
                                if api_config_obj:
                                    # Create API result record for error
                                    api_result = APIResult(
                                        case_id=case_id,
                                        api_config_id=api_config_obj.id,
                                        endpoint=api_config['endpoint'],
                                        query_params=json.dumps(params) if 'params' in locals() else "{}",
                                        status='error',
                                        error_message=error_msg,
                                        created_at=datetime.now()
                                    )
                                    db.session.add(api_result)
                                    db.session.commit()
                                    
                                    # Add to results list
                                    result_dict = api_result.to_dict()
                                    result_dict['api_name'] = api_name
                                    result_dict['category'] = api_config.get('category', "UNKNOWN")
                                    results.append(result_dict)
        
        logger.debug(f"Completed RapidAPI queries. Results count: {len(results)}")
        return results
    
    except Exception as e:
        logger.error(f"Error in RapidAPI query process: {str(e)}")
        return results
