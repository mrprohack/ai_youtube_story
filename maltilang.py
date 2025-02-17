from groq import Groq
import time
import os
import logging
from pathlib import Path
from typing import Optional, Dict
from dotenv import load_dotenv
import json
import re
from language_config import SUPPORTED_LANGUAGES, get_language_config, get_script_template
import argparse
from colorama import init, Fore, Style
from elevenlabs import ElevenLabs

class StoryPlanner:
    """Handles story planning and generation using the Groq API for YouTube content."""
    
    def __init__(self, model: str = "llama-3.3-70b-versatile", language: str = "en", show_logs: bool = False, test_audio: bool = False):
        """Initialize the StoryPlanner with API configuration."""
        # Setup logging first
        try:
            log_directory = Path("logs")
            log_directory.mkdir(parents=True, exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            log_file = log_directory / f"story_planner_{timestamp}.log"
            
            # Configure logging based on show_logs parameter
            handlers = []
            if show_logs:
                handlers = [
                    logging.FileHandler(log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            else:
                # Only file handler when not showing logs
                handlers = [logging.FileHandler(log_file, encoding='utf-8')]
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=handlers
            )
            self.logger = logging.getLogger(__name__)
            if show_logs:
                self.logger.info(f"Logging initialized. Log file: {log_file}")
        except Exception as e:
            print(f"Warning: Failed to initialize logging: {str(e)}")
            self.logger = None
        
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
            
        self.client = Groq(api_key=self.api_key)
        self.model = model
        
        # Initialize Eleven Labs client and API keys
        self.elevenlabs_keys = self._load_elevenlabs_keys()
        self.current_key_index = 0
        
        # Test audio generation if requested
        if test_audio:
            self._test_audio_generation()
        else:
            self.tts_client = self._initialize_elevenlabs_client()
        
        # Add language configuration
        self.language = language
        self.lang_config = get_language_config(language)
        self.script_template = get_script_template(self.lang_config['script_style'])

    def _load_elevenlabs_keys(self) -> list:
        """Load ElevenLabs API keys from file."""
        try:
            keys = []
            with open('elevenlabs_apis', 'r') as f:
                for line in f:
                    # Extract only the API key part (after the colon)
                    if ':' in line:
                        key = line.strip().split(':')[1]
                        if key.startswith('sk_'):  # Validate key format
                            keys.append(key)
            
            if not keys:
                raise ValueError("No valid API keys found in elevenlabs_apis file")
            
            if self.logger:
                self.logger.info(f"Loaded {len(keys)} API keys successfully")
            else:
                print(f"Loaded {len(keys)} API keys successfully")
            return keys
            
        except Exception as e:
            error_msg = f"Error loading ElevenLabs API keys: {str(e)}"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(f"Error: {error_msg}")
            raise

    def _initialize_elevenlabs_client(self) -> ElevenLabs:
        """Initialize ElevenLabs client with current API key."""
        return ElevenLabs(api_key=self.elevenlabs_keys[self.current_key_index])

    def _rotate_elevenlabs_key(self):
        """Rotate to the next available API key."""
        self.current_key_index = (self.current_key_index + 1) % len(self.elevenlabs_keys)
        self.tts_client = self._initialize_elevenlabs_client()
        self.logger.info(f"Rotated to new API key (index: {self.current_key_index})")

    def _check_credit_balance(self, text: str) -> bool:
        """
        Check if there are enough credits to process the text.
        Returns True if sufficient credits available, False otherwise.
        """
        try:
            # Get user subscription info
            user_info = self.tts_client.user.get()
            
            if hasattr(user_info, 'subscription'):
                # Calculate remaining character quota
                remaining_chars = user_info.subscription.character_count
                # Estimate required characters (including some buffer)
                required_chars = len(text) * 1.1  # Add 10% buffer
                
                if self.logger:
                    self.logger.info(f"Credit check - Remaining: {remaining_chars}, Required: {required_chars}")
                else:
                    print(f"Credit check - Remaining: {remaining_chars}, Required: {required_chars}")
                
                return remaining_chars >= required_chars
            return True  # If can't get subscription info, assume ok
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to check credit balance: {str(e)}")
            else:
                print(f"Warning: Failed to check credit balance: {str(e)}")
            return True  # If check fails, assume ok to proceed
    
    def _estimate_total_credits_needed(self, text_files: list) -> int:
        """
        Estimate total credits needed for all text files.
        Returns estimated character count needed.
        """
        total_chars = 0
        try:
            for file_path in text_files:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_chars += len(content)
            
            # Add 10% buffer
            total_chars = int(total_chars * 1.1)
            
            if self.logger:
                self.logger.info(f"Estimated total characters needed: {total_chars}")
            else:
                print(f"Estimated total characters needed: {total_chars}")
                
            return total_chars
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error estimating credits: {str(e)}")
            else:
                print(f"Error estimating credits: {str(e)}")
            return 0

    def _handle_text_to_speech(self, text: str, max_retries: int = 3) -> bytes:
        """Handle text-to-speech conversion with API key rotation and credit check."""
        # Check credits before processing
        if not self._check_credit_balance(text):
            error_msg = "Insufficient credits to process text"
            if self.logger:
                self.logger.error(error_msg)
            else:
                print(f"Error: {error_msg}")
            raise ValueError(error_msg)
            
        tried_keys = set()  # Keep track of keys we've tried
        initial_key_index = self.current_key_index  # Remember where we started
        
        while True:
            current_key = self.elevenlabs_keys[self.current_key_index]
            
            if current_key in tried_keys:
                if len(tried_keys) >= len(self.elevenlabs_keys):
                    # If we've tried all keys, wait for 5 minutes and try again
                    self.logger.warning("All keys tried, waiting 5 minutes before retrying...")
                    time.sleep(10)  # Wait 5 minutes
                    tried_keys.clear()  # Clear tried keys to start fresh
                    continue
                
                # Move to next key if current one is already tried
                self._rotate_elevenlabs_key()
                continue
            
            try:
                tried_keys.add(current_key)
                self.logger.info(f"Trying key {self.current_key_index + 1}/{len(self.elevenlabs_keys)}")
                
                audio_stream = self.tts_client.text_to_speech.convert(
                    voice_id="JBFqnCBsd6RMkjVDRZzb",
                    output_format="mp3_44100_128",
                    text=text,
                    model_id="eleven_multilingual_v2"
                )
                
                audio_data = b''
                for chunk in audio_stream:
                    if chunk is not None:
                        audio_data += chunk
                return audio_data
                
            except Exception as e:
                error_str = str(e).lower()
                if 'quota_exceeded' in error_str or '401' in error_str or 'unauthorized' in error_str:
                    self.logger.warning(f"Quota exceeded or unauthorized for key {self.current_key_index + 1}, trying next key...")
                    self._rotate_elevenlabs_key()
                    
                    # If we've cycled through all keys once
                    if self.current_key_index == initial_key_index:
                        self.logger.warning("Cycled through all keys once, waiting 5 minutes before retrying...")
                        time.sleep(10)  # Wait 5 minutes
                        tried_keys.clear()  # Clear tried keys to start fresh
                    continue
                else:
                    self.logger.error(f"Error in text-to-speech conversion: {str(e)}")
                    raise

    def _create_project_structure(self, book_name: str) -> Dict[str, Path]:
        """Create project structure for the book content."""
        try:
            # Sanitize book name for directory creation
            safe_book_name = re.sub(r'[<>:"/\\|?*]', '', book_name)
            safe_book_name = safe_book_name.strip()
            
            paths = {
                'root': Path("youtube_content") / safe_book_name,
                'script': Path("youtube_content") / safe_book_name / "script",
                'voice_over': Path("youtube_content") / safe_book_name / "voice_over",
            }
            
            for path in paths.values():
                path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created directory: {path}")
                
            return paths
        except Exception as e:
            self.logger.error(f"Failed to create project structure: {str(e)}")
            raise

    def _clean_json_response(self, response: str) -> str:
        """Clean and fix common JSON formatting issues in API responses."""
        try:
            # Remove any non-JSON text before and after the JSON object
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > 0:
                response = response[json_start:json_end]
            
            # Fix common escape character issues
            response = response.replace('\\n', '\n')
            response = response.replace('\\"', '"')
            response = re.sub(r'\\([^"\\\/bfnrtu])', r'\1', response)
            
            return response
        except Exception as e:
            self.logger.error(f"Error cleaning JSON response: {str(e)}")
            return response

    def generate_book_script(self, book_name: str) -> dict:
        """Generate a comprehensive video script for the book."""
        prompt = f"""Create a detailed single video script for the book '{book_name}'.
        Format your response STRICTLY as a JSON object with the following structure:
        {{
            "title": "Video Title",
            "duration": "20-30 minutes",
            "target_audience": "string",
            "sections": [
                {{
                    "title": "Section Title",
                    "duration": "string",
                    "voice_over": "Detailed voice-over script",
                    "visual_notes": "Description of visuals/animations",
                    "background_music": "Music mood suggestion"
                }}
            ],
            "key_points": ["string"],
            "visual_style": "Overall visual style description",
            "thumbnail_text": "string"
        }}"""

        messages = [
            {"role": "system", "content": f"You are a professional YouTube scriptwriter specializing in {self.lang_config['name']} book summaries and analysis. Create a comprehensive, engaging script that covers the book's key ideas in a single video. Include clear voice-over instructions and visual suggestions."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._make_api_call(messages)
            if not response:
                raise ValueError("Empty response from API")
                
            cleaned_response = self._clean_json_response(response)
            return json.loads(cleaned_response)
        except Exception as e:
            self.logger.error(f"Error generating book script: {str(e)}")
            raise

    def save_script_content(self, paths: Dict[str, Path], book_name: str, script_data: dict) -> None:
        """Save the script content in different formats."""
        try:
            # Save full script in JSON format
            script_file = paths['script'] / "full_script.json"
            with open(script_file, "w", encoding="utf-8") as f:
                json.dump(script_data, f, indent=4, ensure_ascii=False)

            # Save individual voice-over scripts for each section
            voice_over_dir = paths['voice_over'] / "sections"
            voice_over_dir.mkdir(exist_ok=True)
            
            for i, section in enumerate(script_data['sections'], 1):
                # Create sanitized filename from section title
                section_filename = f"{i:02d}_{re.sub(r'[^\w\s-]', '', section['title']).strip().replace(' ', '_').lower()}.txt"
                section_file = voice_over_dir / section_filename
                
                with open(section_file, "w", encoding="utf-8") as f:
                    f.write(f"# {section['title']}\n")
                    f.write(f"Duration: {section['duration']}\n\n")
                    f.write(f"{section['voice_over']}\n")

            # Save main voice-over script
            voice_over_file = paths['voice_over'] / "voice_over_script.txt"
            with open(voice_over_file, "w", encoding="utf-8") as f:
                f.write(f"# {script_data['title']}\n")
                f.write(f"Target Duration: {script_data['duration']}\n\n")
                
                for i, section in enumerate(script_data['sections'], 1):
                    f.write(f"\n{'='*50}\n")
                    f.write(f"Section {i}: {section['title']}\n")
                    f.write(f"Duration: {section['duration']}\n")
                    f.write(f"{'='*50}\n\n")
                    f.write("VOICE OVER:\n")
                    f.write(f"{section['voice_over']}\n\n")

            # Save production script with visual notes
            production_file = paths['script'] / "production_script.txt"
            with open(production_file, "w", encoding="utf-8") as f:
                f.write(f"# {script_data['title']}\n")
                f.write(f"Target Duration: {script_data['duration']}\n")
                f.write(f"Target Audience: {script_data['target_audience']}\n")
                f.write(f"\nVisual Style: {script_data['visual_style']}\n")
                f.write("\nKey Points:\n")
                for point in script_data['key_points']:
                    f.write(f"- {point}\n")
                
                for i, section in enumerate(script_data['sections'], 1):
                    f.write(f"\n{'='*50}\n")
                    f.write(f"Section {i}: {section['title']}\n")
                    f.write(f"Duration: {section['duration']}\n")
                    f.write(f"{'='*50}\n\n")
                    f.write("VOICE OVER:\n")
                    f.write(f"{section['voice_over']}\n\n")
                    f.write("VISUAL NOTES:\n")
                    f.write(f"{section['visual_notes']}\n\n")
                    f.write("BACKGROUND MUSIC:\n")
                    f.write(f"{section['background_music']}\n\n")

            self.logger.info("Saved all script content successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving script content: {str(e)}")
            raise

    def how_many_titles(self, book_name: str) -> int:
        """Get the number of titles/chapters in the book."""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant"
            },
            {
                "role": "user",
                "content": f"How many titles/chapters are in the book {book_name}? Return a number only."
            }
        ]
        response = self._make_api_call(messages)
        try:
            return int(response.strip())
        except ValueError:
            self.logger.error(f"Invalid response for title count: {response}")
            return 5  # Default to 5 titles if unable to determine

    def generate_title_voice_over(self, book_name: str, title_number: int, paths: Dict[str, Path]) -> None:
        """Generate voice-over for a specific title/chapter."""
        try:
            # Create titles directory
            titles_dir = paths['voice_over'] / "titles"
            titles_dir.mkdir(exist_ok=True)
            
            # Get introduction content if this is the first title
            intro_content = ""
            if title_number == 1:
                intro_messages = [
                    {
                        "role": "system",
                        "content": "You are a YouTube content creator known for engaging book summaries. Create a hook that grabs attention and makes viewers want to learn more."
                    },
                    {
                        "role": "user",
                        "content": f"Create an engaging YouTube-style introduction for '{book_name}'. Start with a hook, then briefly explain what viewers will learn. Make it conversational and exciting, like you're telling a friend about an amazing book."
                    }
                ]
                intro_content = self._make_api_call(intro_messages)
            
            # Get title content
            is_final_title = title_number == self.how_many_titles(book_name)
            messages = [
                {
                    "role": "system",
                    "content": "You are a YouTube storyteller specializing in book summaries. Create engaging content that uses real examples and stories to illustrate the book's ideas. Make it conversational and relatable, like a friend sharing valuable insights."
                },
                {
                    "role": "user",
                    "content": f"Create an engaging YouTube-style script for {'the final title' if is_final_title else f'title {title_number}'} of '{book_name}'. Include real examples and stories that illustrate the main ideas. Make it conversational and easy to follow. {'Include a conclusion and call-to-action.' if is_final_title else ''}"
                }
            ]
            title_content = self._make_api_call(messages)
            
            # Clean up the content
            cleaned_intro = re.sub(r'\[.*?\]', '', intro_content)
            cleaned_intro = re.sub(r'\*\*.*?\*\*', '', cleaned_intro)
            cleaned_intro = cleaned_intro.strip()
            
            cleaned_content = re.sub(r'\[.*?\]', '', title_content)
            cleaned_content = re.sub(r'\*\*.*?\*\*', '', cleaned_content)
            cleaned_content = cleaned_content.strip()
            
            # Prepare the final script content
            final_content = []
            if title_number == 1:
                final_content.append("Hey everyone! " + cleaned_intro + "\n\n")
            else:
                final_content.append("Hey everyone, welcome back! ")
            
            # Add the title name explicitly at the start of content
            title_name = cleaned_content.split('.')[0]
            if is_final_title:
                final_content.append(f"In today's video, we're covering the final title of {book_name}\n\n")
            else:
                final_content.append(f"In today's video, we're diving into part {title_number} of {book_name}\n\n")
            final_content.append(cleaned_content)
            
            # Add end card for the last title
            if is_final_title:
                end_card = "\n\nThat's all for today's video! If you enjoyed this summary and found value in these insights, don't forget to like and subscribe for more book summaries like this one. Hit that notification bell to stay updated with our latest videos. Share this with someone who might benefit from these lessons. Thanks for watching, and I'll see you in the next video!"
                final_content.append(end_card)
            
            final_script = "\n".join(final_content)
            
            # Save title script
            title_number_padded = f"{title_number:02d}"
            script_path = titles_dir / f"title_{title_number_padded}_script.txt"
            voiceover_script_path = titles_dir / f"title_{title_number_padded}_script_voiceover.txt"
            
            # Save the full script with all content
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(f"Title {title_number} of {book_name}\n")
                f.write("=" * 80 + "\n\n")
                f.write(final_script)
            
            # Create clean voice-over version (remove visual instructions)
            clean_script = re.sub(r'\([^)]*\)', '', final_script)  # Remove anything in parentheses
            clean_script = re.sub(r'Host: *', '', clean_script)    # Remove "Host:" markers
            clean_script = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_script)  # Normalize multiple line breaks
            clean_script = clean_script.strip()
            
            # Save the clean voice-over script
            with open(voiceover_script_path, 'w', encoding='utf-8') as f:
                f.write(f"Title {title_number} of {book_name}\n")
                f.write("=" * 80 + "\n\n")
                f.write(clean_script)
            
            # Generate audio for this title
            audio_path = titles_dir / f"title_{title_number_padded}_audio.mp3"
            
            # Function to chunk text while preserving sentence boundaries
            def chunk_text(text, chunk_size=4000):
                sentences = re.split(r'(?<=[.!?])\s+', text)
                chunks = []
                current_chunk = []
                current_length = 0
                
                for sentence in sentences:
                    sentence_length = len(sentence)
                    if current_length + sentence_length > chunk_size and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = []
                        current_length = 0
                    
                    current_chunk.append(sentence)
                    current_length += sentence_length
                
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                
                return chunks
            
            # Process title audio
            text_chunks = chunk_text(clean_script)  # Use clean_script instead of final_script
            
            with open(audio_path, 'wb') as audio_file:
                for chunk_num, chunk in enumerate(text_chunks, 1):
                    self.logger.info(f"Processing chunk {chunk_num}/{len(text_chunks)} of title {title_number}...")
                    audio_data = self._handle_text_to_speech(chunk)
                    audio_file.write(audio_data)
                    
                    if chunk_num < len(text_chunks):
                        time.sleep(1)  # Prevent rate limiting
            
            self.logger.info(f"Generated voice-over for title {title_number}")
            return script_path, audio_path
            
        except Exception as e:
            self.logger.error(f"Error generating voice-over for title {title_number}: {str(e)}")
            raise

    def generate_voice_over(self, script_data: dict, paths: Dict[str, Path], show_logs: bool = False) -> None:
        """Generate voice-over audio files for each title and section."""
        try:
            # First, collect all text files that will need processing
            text_files = []
            
            # Add title scripts
            book_name = script_data['title']
            num_titles = self.how_many_titles(book_name)
            titles_dir = paths['voice_over'] / "titles"
            for title_num in range(1, num_titles + 1):
                title_number_padded = f"{title_num:02d}"
                script_path = titles_dir / f"title_{title_number_padded}_script_voiceover.txt"
                if script_path.exists():
                    text_files.append(script_path)
            
            # Add section scripts
            sections_dir = paths['voice_over'] / "sections"
            for i, section in enumerate(script_data['sections'], 1):
                section_number = f"{i:02d}"
                script_path = sections_dir / f"{section_number}_section_script.txt"
                if script_path.exists():
                    text_files.append(script_path)
            
            # Estimate total credits needed
            total_chars_needed = self._estimate_total_credits_needed(text_files)
            
            # Check if we have enough credits with any key
            sufficient_credits = False
            for key in self.elevenlabs_keys:
                self.tts_client = ElevenLabs(api_key=key)
                if self._check_credit_balance("x" * total_chars_needed):
                    sufficient_credits = True
                    break
            
            if not sufficient_credits:
                error_msg = f"Insufficient credits to process all files. Need approximately {total_chars_needed} characters."
                if self.logger:
                    self.logger.error(error_msg)
                else:
                    print(f"Error: {error_msg}")
                raise ValueError(error_msg)
            
            # Reset client to first key
            self.current_key_index = 0
            self.tts_client = self._initialize_elevenlabs_client()
            
            # Continue with existing voice-over generation code
            # First, get the number of titles
            book_name = script_data['title']
            num_titles = self.how_many_titles(book_name)
            
            # Generate voice-over for each title
            title_files = []
            for title_num in range(1, num_titles + 1):
                if not show_logs:
                    print(f"{Fore.YELLOW}🎙️ Generating voice-over for title {title_num}/{num_titles}...{Style.RESET_ALL}")
                script_path, audio_path = self.generate_title_voice_over(book_name, title_num, paths)
                title_files.append((script_path, audio_path))
            
            # Also generate section voice-overs as before
            sections_dir = paths['voice_over'] / "sections"
            sections_dir.mkdir(exist_ok=True)
            
            # Process each section
            for i, section in enumerate(script_data['sections'], 1):
                if not show_logs:
                    print(f"{Fore.YELLOW}🎙️ Generating voice-over for section {i}/{len(script_data['sections'])}...{Style.RESET_ALL}")
                
                section_number = f"{i:02d}"
                
                # Clean up the voice over content
                cleaned_voice_over = re.sub(r'\[.*?\]', '', section['voice_over'])  # Remove anything in square brackets
                cleaned_voice_over = re.sub(r'\*\*.*?\*\*', '', cleaned_voice_over)  # Remove anything in double asterisks
                cleaned_voice_over = re.sub(r'\n\s*\n', '\n\n', cleaned_voice_over)  # Normalize line breaks
                cleaned_voice_over = cleaned_voice_over.strip()
                
                # Create section script
                section_script = []
                section_script.append(f"Section {i}: {section['title']}\n")
                section_script.append("=" * 80 + "\n\n")
                section_script.append(f"{cleaned_voice_over}\n")
                
                # Save section script
                section_script_path = sections_dir / f"{section_number}_section_script.txt"
                with open(section_script_path, 'w', encoding='utf-8') as f:
                    f.write("".join(section_script))
                
                # Generate audio for this section
                section_audio_path = sections_dir / f"{section_number}_section_audio.mp3"
                
                # Process section audio
                section_text = f"Section {i}: {section['title']}. {cleaned_voice_over}"
                text_chunks = chunk_text(section_text)
                
                with open(section_audio_path, 'wb') as section_file:
                    for chunk_num, chunk in enumerate(text_chunks, 1):
                        self.logger.info(f"Processing chunk {chunk_num}/{len(text_chunks)} of section {i}...")
                        
                        audio_data = self._handle_text_to_speech(chunk)
                        section_file.write(audio_data)
                        
                        if chunk_num < len(text_chunks):
                            time.sleep(1)
            
            self.logger.info("Generated all voice-overs successfully")
            
        except Exception as e:
            self.logger.error(f"Error generating voice-over: {str(e)}")
            raise

    def _make_api_call(self, messages: list, retry_count: int = 3) -> Optional[str]:
        """Make API call with retry logic and rate limiting."""
        for attempt in range(retry_count):
            try:
                response = self.client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    temperature=0.7,
                    max_tokens=4000,
                    top_p=0.9,
                    stop=None
                )
                if not response.choices:
                    raise ValueError("Empty response from API")
                return response.choices[0].message.content
            except Exception as e:
                self.logger.error(f"API call failed (attempt {attempt + 1}/{retry_count}): {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

    def _test_audio_generation(self):
        """Test audio generation capability for all loaded keys."""
        print(f"\n{Fore.CYAN}🔍 Testing ElevenLabs API Keys for Audio Generation...{Style.RESET_ALL}\n")
        
        working_keys = []
        total_keys = len(self.elevenlabs_keys)
        
        for i, key in enumerate(self.elevenlabs_keys, 1):
            print(f"\r{Fore.CYAN}Testing key {i}/{total_keys}...{Style.RESET_ALL}", end='')
            
            try:
                client = ElevenLabs(api_key=key)
                # Try to generate a very short audio
                audio = client.text_to_speech.convert(
                    text="Test.",
                    voice_id="JBFqnCBsd6RMkjVDRZzb",
                    output_format="mp3_44100_128",
                    model_id="eleven_multilingual_v2"
                )
                working_keys.append(key)
                print(f"\r{Fore.GREEN}✓ Key {i}: Working{Style.RESET_ALL}")
            except Exception as e:
                print(f"\r{Fore.RED}✗ Key {i}: Failed - {str(e)}{Style.RESET_ALL}")
            
            print()  # New line after each key
        
        print("\n" + "=" * 80)
        print(f"{Fore.CYAN}Audio Generation Test Results:{Style.RESET_ALL}")
        print(f"Total Keys: {total_keys}")
        print(f"Working Keys: {Fore.GREEN}{len(working_keys)}{Style.RESET_ALL}")
        print(f"Failed Keys: {Fore.RED}{total_keys - len(working_keys)}{Style.RESET_ALL}")
        
        if working_keys:
            # Update the keys list to only include working keys
            self.elevenlabs_keys = working_keys
            self.tts_client = self._initialize_elevenlabs_client()
            print(f"\n{Fore.GREEN}Successfully initialized with {len(working_keys)} working keys{Style.RESET_ALL}")
        else:
            raise ValueError("No working keys found for audio generation")

def main():
    """Main execution function."""
    # Initialize colorama
    init()

    # Set up argument parser
    parser = argparse.ArgumentParser(description='YouTube Book Video Script Generator')
    parser.add_argument('--log', action='store_true', help='Show detailed logs instead of pretty output')
    parser.add_argument('--audio', action='store_true', help='Test audio generation capability for all keys')
    args = parser.parse_args()

    try:
        # Show available languages with colorful output
        print(f"\n{Fore.CYAN}📚 Available languages:{Style.RESET_ALL}")
        for code, lang in SUPPORTED_LANGUAGES.items():
            print(f"  {Fore.GREEN}🌐 {code}{Style.RESET_ALL}: {Fore.YELLOW}{lang['name']}{Style.RESET_ALL}")
            
        # Get language selection
        while True:
            language = input(f"\n{Fore.CYAN}🌍 Enter language code (default: en):{Style.RESET_ALL} ").strip().lower() or 'en'
            if language in SUPPORTED_LANGUAGES:
                break
            print(f"{Fore.RED}❌ Unsupported language code. Please choose from: {', '.join(SUPPORTED_LANGUAGES.keys())}{Style.RESET_ALL}")
        
        # Initialize planner with show_logs and test_audio parameters
        planner = StoryPlanner(language=language, show_logs=args.log, test_audio=args.audio)
        
        # If only testing audio, exit after initialization
        if args.audio:
            return
            
        while True:
            book_name = input(f"{Fore.CYAN}📖 Enter the name of the book for video creation:{Style.RESET_ALL} ").strip()
            if book_name:
                break
            print(f"{Fore.RED}❌ Book name cannot be empty. Please try again.{Style.RESET_ALL}")

        # Create project structure
        paths = planner._create_project_structure(book_name)
        if not args.log:
            print(f"{Fore.GREEN}✅ Project structure created successfully{Style.RESET_ALL}")
        
        # Generate content outline
        if not args.log:
            print(f"{Fore.YELLOW}⚡ Generating comprehensive video script...{Style.RESET_ALL}")
        planner.logger.info("Generating comprehensive video script...")
        script_data = planner.generate_book_script(book_name)
        
        # Save outline
        if not args.log:
            print(f"{Fore.YELLOW}📝 Saving script content...{Style.RESET_ALL}")
        planner.save_script_content(paths, book_name, script_data)
        
        # Generate voice-over
        if not args.log:
            print(f"{Fore.YELLOW}🎙️ Generating voice-over audio...{Style.RESET_ALL}")
        planner.generate_voice_over(script_data, paths, show_logs=args.log)
        
        success_msg = "Video script and voice-over generation completed successfully"
        planner.logger.info(success_msg)
        if not args.log:
            print(f"\n{Fore.GREEN}🎉 {success_msg}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}📂 Generated files:{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}1. Full Script (JSON):{Style.RESET_ALL} {paths['script']}/full_script.json")
            print(f"  {Fore.YELLOW}2. Voice-over Scripts:{Style.RESET_ALL} {paths['voice_over']}/sections/")
            print(f"  {Fore.YELLOW}3. Main Voice-over Script:{Style.RESET_ALL} {paths['voice_over']}/voice_over_script.txt")
            print(f"  {Fore.YELLOW}4. Production Script:{Style.RESET_ALL} {paths['script']}/production_script.txt")
            
            # Show title files
            num_titles = planner.how_many_titles(book_name)
            print(f"\n{Fore.CYAN}📂 Title Files (in {paths['voice_over']}/titles/):{Style.RESET_ALL}")
            for i in range(1, num_titles + 1):
                title_num = f"{i:02d}"
                print(f"  {Fore.YELLOW}Title {i}:{Style.RESET_ALL}")
                print(f"    - Script: title_{title_num}_script.txt")
                print(f"    - Audio:  title_{title_num}_audio.mp3")
            
            # Show section files
            print(f"\n{Fore.CYAN}📂 Section Files (in {paths['voice_over']}/sections/):{Style.RESET_ALL}")
            for i in range(1, len(script_data['sections']) + 1):
                section_num = f"{i:02d}"
                print(f"  {Fore.YELLOW}Section {i}:{Style.RESET_ALL}")
                print(f"    - Script: {section_num}_section_script.txt")
                print(f"    - Audio:  {section_num}_section_audio.mp3")
        
    except Exception as e:
        error_msg = f"Program failed: {str(e)}"
        if 'planner' in locals() and hasattr(planner, 'logger'):
            planner.logger.error(error_msg)
        if not args.log:
            print(f"{Fore.RED}❌ {error_msg}{Style.RESET_ALL}")
        else:
            print(error_msg)
        raise

if __name__ == "__main__":
    main()
