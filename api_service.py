import os
import requests
import json
import logging
from app import db
from models import APIConfiguration, APIResult
import time
from datetime import datetime

logger = logging.getLogger(__name__)

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
        # Map recommended API types to available APIs
        recommended_types = llm_analysis.get('recommended_api_types', [])
        query_parameters = llm_analysis.get('query_parameters', {})
        
        logger.debug(f"Recommended API types: {recommended_types}")
        logger.debug(f"Available APIs: {[api.api_name for api in available_apis]}")
        
        for api in available_apis:
            # Check if this API should be used based on LLM recommendations
            api_type_match = False
            api_name_lower = api.api_name.lower()
            
            # Map API to recommended types
            for api_type in recommended_types:
                if api_type.lower() in api_name_lower or api_type.lower() in api.description.lower():
                    api_type_match = True
                    break
            
            if not api_type_match:
                logger.debug(f"Skipping API {api.api_name} - not in recommended types")
                continue
            
            # Get API configuration
            endpoints = json.loads(api.endpoints) if api.endpoints else {}
            
            # Get API key from environment variables
            api_key = os.environ.get(api.api_key_env) if api.api_key_env else None
            
            # Query each relevant endpoint
            for endpoint_name, endpoint_config in endpoints.items():
                try:
                    # Determine if this endpoint should be queried based on parameters
                    endpoint_type = endpoint_config.get('type', '').lower()
                    params_to_use = []
                    
                    for param_type, param_values in query_parameters.items():
                        if param_type.lower() in endpoint_type and param_values:
                            params_to_use.extend(param_values)
                    
                    if not params_to_use:
                        logger.debug(f"Skipping endpoint {endpoint_name} - no matching parameters")
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
