import json
import os
import logging
import requests
import base64
from typing import Dict, List, Any, Optional, Mapping, Union
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Import OpenAI conditionally to handle cases where the library isn't installed
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available. Install with 'pip install openai'")
    # Create dummy class to prevent errors
    class OpenAI:
        def __init__(self, **kwargs):
            pass

# Initialize clients
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# OpenRouter - use OPENAI_API_KEY if OPENROUTER_API_KEY is not set (for backward compatibility)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", OPENAI_API_KEY)
OPENROUTER_API_URL = os.environ.get("OPENROUTER_API_URL", "https://openrouter.ai/api/v1")

# Default model settings
DEFAULT_MODEL = "gpt-4o"  # OpenAI's latest model
DEFAULT_PROVIDER = "openrouter"  # Default provider (openai or openrouter)

# Class to handle AI provider selection and API calls
class AIProvider:
    def __init__(self):
        self.provider = os.environ.get("DEFAULT_AI_PROVIDER", DEFAULT_PROVIDER)
        self.model = os.environ.get("DEFAULT_AI_MODEL", DEFAULT_MODEL)
        self.available_models = {}
        
        # Initialize OpenAI client if API key is available
        if OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            self.openai_client = None
            
        # Cache the model list if OpenRouter is available
        if OPENROUTER_API_KEY:
            self.refresh_model_list()
        
    def refresh_model_list(self):
        """Get list of available models from OpenRouter"""
        if not OPENROUTER_API_KEY:
            self.available_models = {}
            return
            
        try:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{OPENROUTER_API_URL}/models",
                headers=headers
            )
            
            if response.status_code == 200:
                models_data = response.json().get("data", [])
                # Format model data for easier selection
                self.available_models = {
                    model.get("id"): {
                        "name": model.get("name"),
                        "description": model.get("description"),
                        "context_length": model.get("context_length"),
                        "pricing": model.get("pricing", {})
                    } for model in models_data
                }
                logger.debug(f"Retrieved {len(self.available_models)} models from OpenRouter")
            else:
                logger.error(f"Failed to get models from OpenRouter: {response.status_code} - {response.text}")
                self.available_models = {}
        except Exception as e:
            logger.error(f"Error fetching models from OpenRouter: {str(e)}")
            self.available_models = {}
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get list of available models"""
        # Add OpenAI models if API key is available
        models: Dict[str, Dict[str, Any]] = {}
        
        if OPENAI_API_KEY:
            models.update({
                "openai:gpt-4o": {"name": "GPT-4o", "description": "OpenAI's latest model", "provider": "openai"},
                "openai:gpt-4-turbo": {"name": "GPT-4 Turbo", "description": "OpenAI's GPT-4 Turbo model", "provider": "openai"},
                "openai:gpt-3.5-turbo": {"name": "GPT-3.5 Turbo", "description": "OpenAI's GPT-3.5 Turbo model", "provider": "openai"},
            })
        
        # Add OpenRouter models
        for model_id, model_info in self.available_models.items():
            models[f"openrouter:{model_id}"] = {
                "name": model_info.get("name", model_id),
                "description": model_info.get("description", ""),
                "provider": "openrouter",
                "context_length": model_info.get("context_length"),
                "pricing": model_info.get("pricing", {})
            }
            
        return models
    
    def set_model(self, model_id):
        """Set the model to use for AI requests"""
        if ":" in model_id:
            provider, model = model_id.split(":", 1)
            self.provider = provider
            self.model = model
        else:
            # Assume OpenAI if no provider specified
            self.provider = "openai"
            self.model = model_id
    
    def chat_completion(self, messages, response_format=None, max_tokens=None):
        """
        Send a chat completion request to the selected AI provider
        
        Args:
            messages (list): List of message objects (role, content)
            response_format (dict, optional): Format specification for the response
            max_tokens (int, optional): Maximum tokens in the response
            
        Returns:
            dict: Response from the AI provider
        """
        if self.provider == "openai":
            return self._openai_chat_completion(messages, response_format, max_tokens)
        elif self.provider == "openrouter":
            return self._openrouter_chat_completion(messages, response_format, max_tokens)
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    def _openai_chat_completion(self, messages, response_format=None, max_tokens=None):
        """Send a chat completion request to OpenAI"""
        if not self.openai_client:
            raise ValueError("OpenAI API key not provided")
            
        kwargs = {
            "model": self.model,
            "messages": messages
        }
        
        if response_format:
            kwargs["response_format"] = response_format
            
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
            
        try:
            response = self.openai_client.chat.completions.create(**kwargs)
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "provider": "openai"
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def _openrouter_chat_completion(self, messages, response_format=None, max_tokens=None):
        """Send a chat completion request to OpenRouter"""
        if not OPENROUTER_API_KEY:
            raise ValueError("OpenRouter API key not provided")
            
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://osint.intelligence.platform", # Identifying the application
            "X-Title": "OSINT Intelligence Platform" # Identifying the application
        }
        
        payload = {
            "model": self.model,
            "messages": messages
        }
        
        if response_format:
            # OpenRouter may handle response format differently than OpenAI
            payload["response_format"] = response_format
            
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        try:
            response = requests.post(
                f"{OPENROUTER_API_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                response_data = response.json()
                return {
                    "content": response_data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    "model": response_data.get("model", self.model),
                    "provider": "openrouter"
                }
            else:
                error_msg = f"OpenRouter API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
        except Exception as e:
            logger.error(f"OpenRouter API error: {str(e)}")
            raise

# Create global AI provider instance
ai_provider = AIProvider()

def process_input_with_llm(input_data):
    """
    Process input data with LLM to determine which APIs to query
    
    Args:
        input_data (dict): Dictionary containing user input data
        
    Returns:
        dict: Dictionary containing API selection and query parameters
    """
    try:
        # Create a prompt for the LLM
        prompt = f"""
        You are an OSINT specialist analyzing input data to determine the most effective APIs to query.
        
        Here is the input data:
        Name: {input_data.get('name', 'Not provided')}
        Phone Number: {input_data.get('phone', 'Not provided')}
        Email: {input_data.get('email', 'Not provided')}
        Social Media Handles: {input_data.get('social_media', 'Not provided')}
        Last Known Location: {input_data.get('location', 'Not provided')}
        Vehicle Information: {input_data.get('vehicle', 'Not provided')}
        Additional Information: {input_data.get('additional_info', 'Not provided')}
        Primary Image Provided: {'Yes' if input_data.get('has_image') else 'No'}
        Secondary Image Provided: {'Yes' if input_data.get('has_secondary_image') else 'No'}
        
        Our system uses a three-level categorization structure for OSINT APIs:
        1. Data Type: TEXT, IMAGE, VIDEO, LOCATION, NETWORK
        2. Entity Type: PERSON, ORGANIZATION, DOMAIN, DEVICE, ADDRESS, etc.
        3. Attribute Type: NAME, EMAIL, PHONE, IP, URL, FACE, LICENSE_PLATE, USERNAME, etc.
        
        For example:
        - Email verification APIs are categorized as: TEXT/PERSON/EMAIL
        - Phone validation APIs are categorized as: TEXT/PERSON/PHONE
        - IP geolocation APIs are categorized as: NETWORK/DEVICE/IP and LOCATION/ADDRESS/COORDINATES
        - Social media profile search APIs are categorized as: TEXT/PERSON/USERNAME or TEXT/PERSON/SOCIAL
        - Facial recognition APIs are categorized as: IMAGE/PERSON/FACE
        - License plate recognition APIs are categorized as: IMAGE/DEVICE/LICENSE_PLATE
        
        Based on the input data, determine which categories of APIs would be most useful to query.
        Only recommend categories that have relevant input data. For example, don't recommend IMAGE APIs if no image is provided.
        
        Return your analysis in the following JSON format:
        {
            "recommended_api_categories": [
                {
                    "data_type": "TEXT or IMAGE or VIDEO or LOCATION or NETWORK",
                    "entity_type": "PERSON or ORGANIZATION or DOMAIN or DEVICE or ADDRESS",
                    "attribute_type": "NAME or EMAIL or PHONE or IP or URL or FACE, etc."
                }
            ],
            "query_parameters": {
                "TEXT/PERSON/EMAIL": ["list of parameters for email APIs"],
                "TEXT/PERSON/PHONE": ["list of parameters for phone APIs"],
                "TEXT/PERSON/USERNAME": ["list of parameters for social media APIs"],
                "LOCATION/ADDRESS/COORDINATES": ["list of parameters for location APIs"],
                "IMAGE/DEVICE/LICENSE_PLATE": ["list of parameters for vehicle APIs"],
                "IMAGE/PERSON/FACE": ["list of parameters for image APIs"]
            },
            "reasoning": "Explanation of your recommendations, including why certain categories were included or excluded"
        }
        """
        
        # Call AI provider
        response = ai_provider.chat_completion(
            messages=[
                {"role": "system", "content": "You are an OSINT specialist analyzing data to determine API query strategies."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        result = json.loads(response["content"])
        logger.debug(f"LLM API selection result: {result}")
        logger.debug(f"Used model: {response.get('model')}, Provider: {response.get('provider')}")
        return result
    
    except Exception as e:
        logger.error(f"Error processing input with LLM: {str(e)}")
        # Return a default response in case of error that uses our new categorization structure
        default_categories = []
        
        if input_data.get('email'):
            default_categories.append({
                "data_type": "TEXT",
                "entity_type": "PERSON",
                "attribute_type": "EMAIL"
            })
        
        if input_data.get('phone'):
            default_categories.append({
                "data_type": "TEXT",
                "entity_type": "PERSON",
                "attribute_type": "PHONE"
            })
        
        if input_data.get('social_media'):
            default_categories.append({
                "data_type": "TEXT",
                "entity_type": "PERSON",
                "attribute_type": "USERNAME"
            })
        
        if input_data.get('location'):
            default_categories.append({
                "data_type": "LOCATION",
                "entity_type": "ADDRESS",
                "attribute_type": "COORDINATES"
            })
        
        if input_data.get('vehicle'):
            default_categories.append({
                "data_type": "TEXT",
                "entity_type": "DEVICE",
                "attribute_type": "VEHICLE"
            })
        
        if input_data.get('has_image'):
            default_categories.append({
                "data_type": "IMAGE",
                "entity_type": "PERSON",
                "attribute_type": "FACE"
            })
        
        # Prepare query parameters
        query_params = {}
        for category in default_categories:
            category_key = f"{category['data_type']}/{category['entity_type']}/{category['attribute_type']}"
            if category['attribute_type'] == 'EMAIL':
                query_params[category_key] = [input_data.get('email')]
            elif category['attribute_type'] == 'PHONE':
                query_params[category_key] = [input_data.get('phone')]
            elif category['attribute_type'] == 'USERNAME':
                query_params[category_key] = [input_data.get('social_media')]
            elif category['attribute_type'] == 'COORDINATES':
                query_params[category_key] = [input_data.get('location')]
            elif category['attribute_type'] == 'VEHICLE':
                query_params[category_key] = [input_data.get('vehicle')]
            elif category['attribute_type'] == 'FACE':
                query_params[category_key] = ["image_search"]
        
        return {
            "recommended_api_categories": default_categories,
            "query_parameters": query_params,
            "reasoning": "Default selection due to error in LLM processing. Selected categories based on available input data."
        }

def analyze_data_with_llm(api_results, input_data):
    """
    Analyze the gathered API data with LLM
    
    Args:
        api_results (list): List of API results
        input_data (dict): Dictionary containing user input data
        
    Returns:
        dict: Dictionary containing analysis of the data
    """
    try:
        # Format API results for the prompt
        api_results_text = json.dumps(api_results, indent=2)
        
        # Create a prompt for the LLM
        prompt = f"""
        You are an OSINT analyst reviewing data collected from various intelligence sources.
        
        INITIAL DATA:
        Name: {input_data.get('name', 'Not provided')}
        Phone Number: {input_data.get('phone', 'Not provided')}
        Email: {input_data.get('email', 'Not provided')}
        Social Media Handles: {input_data.get('social_media', 'Not provided')}
        Last Known Location: {input_data.get('location', 'Not provided')}
        Vehicle Information: {input_data.get('vehicle', 'Not provided')}
        Primary Image Provided: {'Yes' if input_data.get('has_image') else 'No'}
        Secondary Image Provided: {'Yes' if input_data.get('has_secondary_image') else 'No'}
        
        API RESULTS:
        {api_results_text}
        
        Analyze this data and identify:
        1. Key findings and connections
        2. Potential leads for further investigation
        3. Reliability assessment of the gathered information
        4. Geographical information that can be mapped
        5. Timeline of activities if applicable
        6. Data points that can be visualized
        
        Return your analysis in the following JSON format:
        {
            "key_findings": ["list of important discoveries"],
            "connections": ["identified relationships between data points"],
            "further_investigation": ["areas that need more research"],
            "reliability_assessment": {
                "high_confidence": ["list of highly reliable data points"],
                "medium_confidence": ["list of somewhat reliable data points"],
                "low_confidence": ["list of questionable data points"]
            },
            "geographical_data": [
                {"location": "place name", "coordinates": [lat, long], "source": "where this was found"}
            ],
            "timeline_data": [
                {"date": "YYYY-MM-DD", "event": "description", "source": "where this was found"}
            ],
            "visualization_data": {
                "network_connections": ["data points that can be shown in a network graph"],
                "frequency_analysis": ["data that can be shown in frequency charts"]
            },
            "summary": "Overall assessment of the gathered intelligence"
        }
        """
        
        # Call AI provider
        response = ai_provider.chat_completion(
            messages=[
                {"role": "system", "content": "You are an OSINT analyst reviewing intelligence data."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        result = json.loads(response["content"])
        logger.debug(f"LLM data analysis result: {json.dumps(result, indent=2)}")
        logger.debug(f"Used model: {response.get('model')}, Provider: {response.get('provider')}")
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing data with LLM: {str(e)}")
        # Return a default analysis in case of error
        return {
            "key_findings": ["Unable to perform analysis due to an error"],
            "connections": [],
            "further_investigation": ["Review all data manually"],
            "reliability_assessment": {
                "high_confidence": [],
                "medium_confidence": [],
                "low_confidence": ["All data should be manually verified"]
            },
            "geographical_data": [],
            "timeline_data": [],
            "visualization_data": {
                "network_connections": [],
                "frequency_analysis": []
            },
            "summary": "Analysis failed due to an error. Please review the raw data."
        }

def generate_report_with_llm(data_analysis, api_results, input_data):
    """
    Generate a comprehensive report from the analyzed data
    
    Args:
        data_analysis (dict): Analysis of the data by LLM
        api_results (list): List of API results
        input_data (dict): Dictionary containing user input data
        
    Returns:
        dict: Dictionary containing the report
    """
    try:
        # Format data for the prompt
        data_analysis_text = json.dumps(data_analysis, indent=2)
        
        # Create a prompt for the LLM
        subject_info = f"""
        You are an OSINT specialist creating a comprehensive intelligence report.
        
        SUBJECT INFORMATION:
        Name: {input_data.get('name', 'Subject')}
        Primary Image Provided: {'Yes' if input_data.get('has_image') else 'No'}
        Secondary Image Provided: {'Yes' if input_data.get('has_secondary_image') else 'No'}
        
        ANALYZED DATA:
        {data_analysis_text}
        """
        
        # Use a regular string (not an f-string) for the JSON template part
        json_format = """
        Create a professional intelligence report with the following sections:
        1. Executive Summary
        2. Subject Profile
        3. Key Findings
        4. Digital Footprint Analysis
        5. Geographical Analysis
        6. Timeline of Activities
        7. Network Connections
        8. Intelligence Gaps and Uncertainties
        9. Recommendations for Further Investigation
        10. Methodology
        
        Return your report in the following JSON format:
        {
            "title": "Intelligence Report on [Subject Name]",
            "date": "Current date",
            "sections": [
                {
                    "title": "Executive Summary",
                    "content": "Summary text",
                    "visualization_type": null
                },
                {
                    "title": "Subject Profile",
                    "content": "Profile text",
                    "visualization_type": null
                },
                {
                    "title": "Key Findings",
                    "content": "Findings text",
                    "visualization_type": "bullet_list"
                },
                {
                    "title": "Digital Footprint Analysis",
                    "content": "Analysis text",
                    "visualization_type": "pie_chart",
                    "visualization_data": {"categories": [], "values": []}
                },
                {
                    "title": "Geographical Analysis",
                    "content": "Geo analysis text",
                    "visualization_type": "map",
                    "visualization_data": {"locations": []}
                },
                {
                    "title": "Timeline of Activities",
                    "content": "Timeline text",
                    "visualization_type": "timeline",
                    "visualization_data": {"events": []}
                },
                {
                    "title": "Network Connections",
                    "content": "Network text",
                    "visualization_type": "network_graph",
                    "visualization_data": {"nodes": [], "edges": []}
                },
                {
                    "title": "Intelligence Gaps and Uncertainties",
                    "content": "Gaps text",
                    "visualization_type": "bullet_list"
                },
                {
                    "title": "Recommendations",
                    "content": "Recommendations text",
                    "visualization_type": "bullet_list"
                },
                {
                    "title": "Methodology",
                    "content": "Methodology text",
                    "visualization_type": null
                }
            ]
        }
        """
        
        # Combine the parts
        prompt = subject_info + json_format
        
        # Call AI provider
        response = ai_provider.chat_completion(
            messages=[
                {"role": "system", "content": "You are an OSINT specialist creating a professional intelligence report."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        result = json.loads(response["content"])
        logger.debug(f"LLM report generation result: {json.dumps(result, indent=2)}")
        logger.debug(f"Used model: {response.get('model')}, Provider: {response.get('provider')}")
        return result
    
    except Exception as e:
        logger.error(f"Error generating report with LLM: {str(e)}")
        # Return a default report in case of error
        return {
            "title": f"Intelligence Report on {input_data.get('name', 'Subject')}",
            "date": "Current date",
            "sections": [
                {
                    "title": "Executive Summary",
                    "content": "Unable to generate a complete report due to an error. Please review the raw data.",
                    "visualization_type": None
                },
                {
                    "title": "Methodology",
                    "content": "This report was generated using OSINT techniques and automated API queries.",
                    "visualization_type": None
                }
            ]
        }

def analyze_image(base64_image, image_type="primary"):
    """
    Analyze an image using vision capabilities
    
    Args:
        base64_image (str): Base64-encoded image
        image_type (str): Type of image ('primary' or 'secondary')
        
    Returns:
        str: Analysis of the image
    """
    try:
        # Ensure we're using OpenAI for image analysis since it supports multimodal
        original_provider = ai_provider.provider
        original_model = ai_provider.model
        
        # Temporarily switch to OpenAI if we're not already using it
        if ai_provider.provider != "openai":
            ai_provider.set_model("openai:gpt-4o")
            
        # Customize prompt based on image type
        if image_type == "primary":
            prompt_text = "Analyze this primary image for OSINT purposes. Identify visible details that could be useful for intelligence gathering such as location indicators, identifiable objects, text, landmarks, etc."
        else:
            prompt_text = "Analyze this secondary image for OSINT purposes. Look for additional context, comparative elements, or supplementary information. Identify details that might complement or contrast with the primary image."
            
        response = ai_provider.chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        # Restore original provider and model
        if ai_provider.provider != original_provider or ai_provider.model != original_model:
            ai_provider.provider = original_provider
            ai_provider.model = original_model
            
        return response["content"]
    
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        return "Image analysis failed: " + str(e)
