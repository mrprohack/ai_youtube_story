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

class StoryPlanner:
    """Handles story planning and generation using the Groq API for YouTube content."""
    
    def __init__(self, model: str = "llama-3.3-70b-versatile", language: str = "en", show_logs: bool = False):
        """Initialize the StoryPlanner with API configuration."""
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
            
        self.client = Groq(api_key=self.api_key)
        self.model = model
        
        # Add language configuration
        self.language = language
        self.lang_config = get_language_config(language)
        self.script_template = get_script_template(self.lang_config['script_style'])
        
        # Setup logging with error handling
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
            if show_logs:
                print(f"Failed to initialize logging: {str(e)}")
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

def main():
    """Main execution function."""
    # Initialize colorama
    init()

    # Set up argument parser
    parser = argparse.ArgumentParser(description='YouTube Book Video Script Generator')
    parser.add_argument('--log', action='store_true', help='Show detailed logs instead of pretty output')
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
        
        # Initialize planner with show_logs parameter
        planner = StoryPlanner(language=language, show_logs=args.log)
        
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
        
        success_msg = "Video script generation completed successfully"
        planner.logger.info(success_msg)
        if not args.log:
            print(f"\n{Fore.GREEN}🎉 {success_msg}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}📂 Generated files:{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}1. Full Script (JSON):{Style.RESET_ALL} {paths['script']}/full_script.json")
            print(f"  {Fore.YELLOW}2. Voice-over Scripts:{Style.RESET_ALL} {paths['voice_over']}/sections/")
            print(f"  {Fore.YELLOW}3. Main Voice-over Script:{Style.RESET_ALL} {paths['voice_over']}/voice_over_script.txt")
            print(f"  {Fore.YELLOW}4. Production Script:{Style.RESET_ALL} {paths['script']}/production_script.txt")
        
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
