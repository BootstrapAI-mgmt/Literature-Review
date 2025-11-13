"""
Centralized API Manager for all AI-related calls.
"""

import os
import sys
import json
import time
import hashlib
from typing import Optional, Any
import google.generativeai as genai
from dotenv import load_dotenv
import logging
from sentence_transformers import SentenceTransformer

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
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables.")
            genai.configure(api_key=api_key)

            self.client = genai.GenerativeModel('gemini-1.5-flash')
            self.json_generation_config = genai.types.GenerationConfig(
                temperature=0.2, top_p=1.0, top_k=1, max_output_tokens=16384,
                response_mime_type="application/json"
            )
            self.text_generation_config = genai.types.GenerationConfig(
                temperature=0.2, top_p=1.0, top_k=1, max_output_tokens=16384
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
        """Implement rate limiting"""
        current_time = time.time()
        if current_time - self.minute_start >= 60:
            self.calls_this_minute = 0
            self.minute_start = current_time

        # Assuming some config for API calls per minute
        api_calls_per_minute = 60 
        if self.calls_this_minute >= api_calls_per_minute:
            sleep_time = 60.1 - (current_time - self.minute_start)
            if sleep_time > 0:
                logger.info(f"Rate limit reached. Sleeping for {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
            self.calls_this_minute = 0
            self.minute_start = time.time()
        self.calls_this_minute += 1

    def get_cache_filepath(self, prompt_hash: str) -> str:
        return os.path.join(self.cache_dir, f"{prompt_hash}.json")

    def cached_api_call(self, prompt: str, use_cache: bool = True, is_json: bool = True) -> Optional[Any]:
        """Make API call with caching and retry logic"""
        prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        cache_filepath = self.get_cache_filepath(prompt_hash)

        if use_cache and os.path.exists(cache_filepath):
            try:
                with open(cache_filepath, 'r', encoding='utf-8') as f:
                    logger.debug(f"Cache hit for hash: {prompt_hash}")
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not read cache file {cache_filepath}: {e}")

        logger.debug(f"Cache miss for hash: {prompt_hash}. Calling API...")
        self.rate_limit()

        response_text = ""
        retry_attempts = 3
        retry_delay = 5
        for attempt in range(retry_attempts):
            try:
                current_config_object = self.json_generation_config if is_json else self.text_generation_config
                response = self.client.generate_content(
                    contents=prompt,
                    generation_config=current_config_object
                )
                response_text = response.text
                result = json.loads(response_text) if is_json else response_text
                
                try:
                    with open(cache_filepath, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2)
                except IOError as e:
                    logger.error(f"Could not write to cache file {cache_filepath}: {e}")

                return result
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on attempt {attempt + 1}: {e}. Response: '{response_text[:200]}...'")
                if attempt < retry_attempts - 1: time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"API error on attempt {attempt + 1}: {type(e).__name__} - {e}")
                if "429" in str(e): time.sleep(retry_delay * (attempt + 2))
                elif attempt < retry_attempts - 1: time.sleep(retry_delay)
        
        logger.error(f"API call failed after {retry_attempts} attempts.")
        return None
