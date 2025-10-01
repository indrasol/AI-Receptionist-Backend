"""
OpenAI Service for content processing and chunk generation
"""

import logging
import openai
from typing import List, Dict, Any, Optional
from app.config.settings import CSA_OPENAIIND

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for OpenAI API interactions"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=CSA_OPENAIIND)
    
    async def process_scraped_content_to_chunks(
        self, 
        scraped_content: Dict[str, Any], 
        organization_id: str,
        source_type: str = "website"
    ) -> List[Dict[str, Any]]:
        """
        Process scraped content and convert it to structured chunks using OpenAI
        """
        try:
            # Check if scraped_content is None or empty
            if not scraped_content:
                logger.warning("Scraped content is None or empty")
                return []
            
            logger.info(f"Processing scraped content from {scraped_content.get('url', 'unknown')}")
            
            # Extract content details
            url = scraped_content.get("url", "")
            title = scraped_content.get("title", "")
            content = scraped_content.get("content", "")
            headings = scraped_content.get("headings", [])
            
            if not content:
                logger.warning(f"No content found for {url}")
                return []
            
            # Create the prompt for OpenAI
            prompt = self._create_chunk_processing_prompt(url, title, content, headings)
            
            # Call OpenAI API
            response = await self._call_openai_api(prompt)
            
            # Parse the response into chunks
            chunks = self._parse_openai_response(response, url, organization_id, source_type)
            
            logger.info(f"Generated {len(chunks)} chunks from {url}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing scraped content: {str(e)}")
            raise e
    
    def _create_chunk_processing_prompt(self, url: str, title: str, content: str, headings: List[str]) -> str:
        """Create the prompt for OpenAI to process content into chunks"""
        
        prompt = f"""
You are an expert content analyst. I need you to analyze the following website content and create ONE comprehensive chunk that contains all the important information.

Website URL: {url}
Website Title: {title}
Headings Found: {', '.join(headings[:10])}  # Limit to first 10 headings

Content to analyze:
{content[:8000]}  # Limit content to avoid token limits

Please analyze this content and create ONE comprehensive chunk that includes ALL the important information from this website. This chunk should:

1. Be comprehensive and complete - include all relevant information
2. Be well-organized and structured
3. Be useful for answering any user questions about this website
4. Be self-contained with all necessary details

For the single chunk, provide:
- name: A descriptive title for the entire website (max 200 characters)
- description: What this comprehensive chunk covers (max 500 characters)
- content: The complete, cleaned, and comprehensive text content (max 100,000 characters)
- bullets: Up to 15 key bullet points covering all important aspects
- sample_questions: Up to 15 likely questions users would ask about this website

IMPORTANT: Create only ONE chunk that contains ALL the information from the website. Do not split into multiple chunks.

Format your response as a JSON object with this exact structure:
{{
  "name": "Complete Website Overview",
  "description": "Comprehensive information about all aspects of this website",
  "content": "Complete comprehensive content covering all aspects of the website including services, contact information, company details, locations, partnerships, and all other relevant information...",
  "bullets": [
    "Bullet point 1 covering key aspect",
    "Bullet point 2 covering another important aspect",
    "Bullet point 3 covering services",
    "Bullet point 4 covering contact information",
    "Bullet point 5 covering company details",
    "... up to 15 bullet points covering all important aspects"
  ],
  "sample_questions": [
    "Question 1 about services",
    "Question 2 about contact information",
    "Question 3 about company details",
    "Question 4 about locations",
    "Question 5 about partnerships",
    "... up to 15 questions covering all topics"
  ]
}}

Make sure the single chunk is comprehensive, useful, and contains all actionable information from the website. Include all important details in one complete chunk.

IMPORTANT: You must respond with ONLY a valid JSON object. Do not include any text before or after the JSON. RESPOND WITH ONLY THE JSON OBJECT - NO ADDITIONAL TEXT.
"""
        return prompt
    
    async def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API with the prompt"""
        try:
            # Use response_format to ensure JSON output
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using the more cost-effective model
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content analyst specializing in breaking down website content into structured, useful chunks for AI assistant training. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.3,  # Lower temperature for more consistent results
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            # Safely extract the content
            content = response.choices[0].message.content
            
            # Convert response to dict to avoid Pydantic issues
            if content is None:
                logger.error("OpenAI returned None content")
                raise ValueError("OpenAI API returned empty content")
            
            return str(content)
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            raise e
    
    def _parse_openai_response(
        self, 
        response: str, 
        url: str, 
        organization_id: str, 
        source_type: str
    ) -> List[Dict[str, Any]]:
        """Parse OpenAI response into chunk format"""
        try:
            import json
            
            logger.info(f"Raw OpenAI response: {response[:200]}...")
            
            # Parse the JSON response
            parsed_response = json.loads(response)
            
            # Handle different response formats
            if isinstance(parsed_response, dict):
                # If it's a dict, look for common keys
                if 'chunks' in parsed_response:
                    chunks_data = parsed_response['chunks']
                elif 'data' in parsed_response:
                    chunks_data = parsed_response['data']
                else:
                    # Assume the dict itself contains the chunk data
                    chunks_data = [parsed_response]
            elif isinstance(parsed_response, list):
                # If it's already a list, use it directly
                chunks_data = parsed_response
            else:
                logger.error(f"Unexpected response format: {type(parsed_response)}")
                return []
            
            # Convert to our chunk format
            chunks = []
            for chunk_data in chunks_data:
                if isinstance(chunk_data, dict):
                    chunk = {
                        "organization_id": organization_id,
                        "source_type": source_type,
                        "source_id": url,
                        "name": chunk_data.get("name", ""),
                        "description": chunk_data.get("description", ""),
                        "content": chunk_data.get("content", ""),
                        "bullets": chunk_data.get("bullets", []),
                        "sample_questions": chunk_data.get("sample_questions", []),
                        "is_attached_to_assistant": False
                    }
                    chunks.append(chunk)
            
            logger.info(f"Successfully parsed {len(chunks)} chunks from OpenAI response")
            return chunks
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {str(e)}")
            logger.error(f"Response content: {response[:500]}...")
            raise e
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {str(e)}")
            logger.error(f"Response type: {type(response)}, content: {str(response)[:200]}...")
            raise e
    
    async def generate_chunks_from_scraped_data(
        self,
        scraped_data: Dict[str, Any],
        organization_id: str
    ) -> List[Dict[str, Any]]:
        """
        Main method to generate chunks from scraped data
        Creates only ONE chunk per URL with comprehensive content
        """
        try:
            from app.config.settings import MAX_TOTAL_CHUNKS_CHARACTERS, MAX_CHUNK_CHARACTERS, MAX_CHUNKS_PER_URL
            
            scraped_content_list = scraped_data.get("scraped_content", [])
            all_chunks = []
            total_characters = 0
            
            for content in scraped_content_list:
                if content and content.get("status_code") == 200:  # Only process successful scrapes
                    # Check if we've reached the total character limit
                    if total_characters >= MAX_TOTAL_CHUNKS_CHARACTERS:
                        logger.warning(f"Reached total character limit of {MAX_TOTAL_CHUNKS_CHARACTERS:,} characters")
                        break
                    
                    # Generate only ONE chunk per URL
                    try:
                        chunks = await self.process_scraped_content_to_chunks(
                            content, 
                            organization_id, 
                            "website"
                        )
                    except Exception as e:
                        logger.error(f"Failed to process content for {content.get('url', 'unknown')}: {str(e)}")
                        continue
                    
                    # Ensure only one chunk per URL and validate character limits
                    if chunks:
                        chunk = chunks[0]  # Take only the first chunk
                        
                        # Check individual chunk character limit
                        chunk_content_length = len(chunk.get("content", ""))
                        if chunk_content_length > MAX_CHUNK_CHARACTERS:
                            logger.warning(f"Chunk content exceeds limit of {MAX_CHUNK_CHARACTERS:,} characters. Truncating.")
                            chunk["content"] = chunk["content"][:MAX_CHUNK_CHARACTERS] + "..."
                            chunk_content_length = MAX_CHUNK_CHARACTERS
                        
                        # Check total character limit
                        if total_characters + chunk_content_length <= MAX_TOTAL_CHUNKS_CHARACTERS:
                            all_chunks.append(chunk)
                            total_characters += chunk_content_length
                        else:
                            logger.warning(f"Cannot add chunk - would exceed total character limit of {MAX_TOTAL_CHUNKS_CHARACTERS:,}")
                            break
            
            logger.info(f"Generated {len(all_chunks)} chunks (1 per URL) with {total_characters:,} total characters from {len(scraped_content_list)} scraped pages")
            return all_chunks
            
        except Exception as e:
            logger.error(f"Error generating chunks from scraped data: {str(e)}")
            raise e
