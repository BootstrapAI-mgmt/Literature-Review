"""
Centralized API Manager for all AI-related calls.
"""

import os
import sys
import json
import time
import hashlib
from typing import Optional, Any
from google import genai
from google.genai import types
from dotenv import load_dotenv
import logging
from sentence_transformers import SentenceTransformer

# Import global rate limiter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from global_rate_limiter import global_limiter, ErrorAction

load_dotenv()

# --- Logging ---
logger = logging.getLogger(__name__)

def safe_print(message):
    """Print message safely handling Unicode on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        print(str(message).encode(sys.stdout.encoding or 'utf-8', 'replace').decode(sys.stdout.encoding or 'utf-8'))

class APIManager:
    """Manages API calls with rate limiting, caching, and retry logic"""

    def __init__(self, cache_dir='api_cache'):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.last_call_time = 0
        self.calls_this_minute = 0
        self.minute_start = time.time()

        try:
            self.client = genai.Client()
            thinking_config = types.ThinkingConfig(thinking_budget=0)

            self.json_generation_config = types.GenerateContentConfig(
                temperature=0.2, 
                top_p=1.0, 
                top_k=1, 
                max_output_tokens=16384,
                response_mime_type="application/json",
                thinking_config=thinking_config
            )
            self.text_generation_config = types.GenerateContentConfig(
                temperature=0.2, 
                top_p=1.0, 
                top_k=1, 
                max_output_tokens=16384,
                thinking_config=thinking_config
            )
            logger.info("[SUCCESS] Gemini Client initialized.")
        except Exception as e:
            logger.critical(f"[ERROR] Critical Error initializing Gemini Client: {e}")
            raise

        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("[SUCCESS] Sentence Transformer initialized.")
        except Exception as e:
            logger.warning(f"[WARNING] Could not initialize Sentence Transformer: {e}")
            self.embedder = None

    def rate_limit(self):
        """Implement rate limiting using global limiter"""
        global_limiter.wait_for_quota()

    def get_cache_filepath(self, prompt_hash: str) -> str:
        return os.path.join(self.cache_dir, f"{prompt_hash}.json")

    def cached_api_call(self, prompt: str, use_cache: bool = True, is_json: bool = True) -> Optional[Any]:
        """Make API call with caching, validation, and retry logic"""
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        cache_filepath = self.get_cache_filepath(prompt_hash)

        if use_cache and os.path.exists(cache_filepath):
            try:
                with open(cache_filepath, 'r', encoding='utf-8') as f:
                    logger.debug(f"Cache hit for hash: {prompt_hash}")
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not read cache file {cache_filepath}: {e}")

        # Validate request before making API call
        is_valid, reason = global_limiter.validate_request(prompt, {'response_mime_type': 'application/json' if is_json else None})
        if not is_valid:
            logger.error(f"Request validation failed: {reason}")
            global_limiter.record_request(success=False)
            return None
        
        # Check if we should abort due to error patterns
        if global_limiter.should_abort_pipeline():
            logger.critical("Pipeline abort recommended due to error patterns")
            return None

        logger.debug(f"Cache miss for hash: {prompt_hash}. Calling API...")
        self.rate_limit()

        response_text = ""
        retry_attempts = 3
        retry_delay = 5
        for attempt in range(retry_attempts):
            try:
                current_config_object = self.json_generation_config if is_json else self.text_generation_config
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=current_config_object
                )
                response_text = response.text
                result = json.loads(response_text) if is_json else response_text
                
                try:
                    with open(cache_filepath, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2)
                except IOError as e:
                    logger.error(f"Could not write to cache file {cache_filepath}: {e}")

                # Record successful request
                global_limiter.record_request(success=True)
                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {e}. Response: '{response_text[:200]}...'")
                
                # Try to repair common JSON malformations (Gemini occasionally returns double quotes)
                if attempt == 0 and is_json:  # Only try repair on first attempt for JSON responses
                    try:
                        logger.info("Attempting JSON repair...")
                        repaired = response_text.replace('""', '"')  # Fix: ""key" -> "key"
                        result = json.loads(repaired)
                        logger.info("✅ Successfully repaired malformed JSON")
                        # Cache the repaired result
                        try:
                            with open(cache_filepath, 'w', encoding='utf-8') as f:
                                json.dump(result, f, indent=2)
                        except IOError as cache_error:
                            logger.error(f"Could not write repaired result to cache: {cache_error}")
                        global_limiter.record_request(success=True)
                        return result
                    except json.JSONDecodeError:
                        logger.warning("JSON repair failed, will retry API call")
                
                # Categorize error
                category = global_limiter.categorize_error(e, response_text)
                action = global_limiter.get_action_for_error(category)
                global_limiter.record_request(success=False, error=e, response_text=response_text)
                
                if action == ErrorAction.SKIP_DOCUMENT:
                    logger.error(f"Skipping request due to {category.name}")
                    return None
                elif attempt < retry_attempts - 1: 
                    time.sleep(retry_delay)
            except Exception as e:
                # Categorize error
                category = global_limiter.categorize_error(e, str(e))
                action = global_limiter.get_action_for_error(category)
                global_limiter.record_request(success=False, error=e, response_text=str(e))
                logger.error(f"API error on attempt {attempt + 1}: {type(e).__name__} - {e}")
            
            if action == ErrorAction.ABORT_PIPELINE:
                logger.critical(f"Aborting due to {category.name}")
                return None
            elif action == ErrorAction.SKIP_DOCUMENT:
                logger.error(f"Skipping request due to {category.name}")
                return None
            elif "429" in str(e): 
                time.sleep(retry_delay * (attempt + 2))
            elif attempt < retry_attempts - 1: 
                # Use delay from action's value tuple
                _, delay = action.value
                time.sleep(delay if delay > 0 else retry_delay)
        
        logger.error(f"API call failed after {retry_attempts} attempts.")
        return None
