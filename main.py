import os
import logging
from app import app
from openai_service import ai_provider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Check for required API keys
    openai_key = os.environ.get("OPENAI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    
    if not openai_key and not openrouter_key:
        logger.warning("*" * 80)
        logger.warning("WARNING: Neither OpenAI nor OpenRouter API keys are configured.")
        logger.warning("The application will have limited functionality.")
        logger.warning("Set OPENAI_API_KEY or OPENROUTER_API_KEY environment variables.")
        logger.warning("*" * 80)
    
    # Start the application
    app.run(host="0.0.0.0", port=5000, debug=True)
