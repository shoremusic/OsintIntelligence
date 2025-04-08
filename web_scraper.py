import trafilatura
import logging

logger = logging.getLogger(__name__)

def get_website_text_content(url: str) -> str:
    """
    This function takes a url and returns the main text content of the website.
    The text content is extracted using trafilatura and easier to understand.
    The results is not directly readable, better to be summarized by LLM before consume
    by the user.
    
    Args:
        url (str): URL of the website to scrape
        
    Returns:
        str: Extracted text content from the website
    """
    try:
        logger.debug(f"Scraping website: {url}")
        
        # Send a request to the website
        downloaded = trafilatura.fetch_url(url)
        
        if not downloaded:
            logger.error(f"Failed to download content from {url}")
            return f"Failed to download content from {url}"
        
        # Extract text content
        text = trafilatura.extract(downloaded)
        
        if not text:
            logger.error(f"Failed to extract text content from {url}")
            return f"Failed to extract text content from {url}"
        
        logger.debug(f"Successfully scraped content from {url}")
        return text
    
    except Exception as e:
        error_msg = f"Error scraping website {url}: {str(e)}"
        logger.error(error_msg)
        return error_msg
