from elevenlabs import ElevenLabs
import time
from pathlib import Path
from colorama import init, Fore, Style
from datetime import datetime
import argparse

def load_api_keys(api_file='elevenlabs_apis'):
    """Load API keys from file."""
    keys = []
    try:
        with open(api_file, 'r') as f:
            for line in f:
                if ':' in line:
                    email, key = line.strip().split(':')
                    if key.startswith('sk_'):
                        keys.append((email, key))
        return keys
    except Exception as e:
        print(f"{Fore.RED}Error loading API keys: {str(e)}{Style.RESET_ALL}")
        return []

def test_audio_generation(api_key: str) -> bool:
    """Test if the key can generate audio."""
    try:
        client = ElevenLabs(api_key=api_key)
        # Try to generate a very short audio
        audio = client.text_to_speech.convert(
            text="Test.",
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            output_format="mp3_44100_128",
            model_id="eleven_multilingual_v2"
        )
        # If we get here, audio generation worked
        return True
    except Exception as e:
        return False

def check_key_balance(email: str, api_key: str, test_audio: bool = False) -> dict:
    """Check balance for a single API key."""
    try:
        client = ElevenLabs(api_key=api_key)
        subscription = client.user.get_subscription()
        
        if subscription:
            # Convert Unix timestamp to readable date
            next_reset = datetime.fromtimestamp(subscription.next_character_count_reset_unix)
            next_reset_str = next_reset.strftime('%Y-%m-%d %H:%M:%S')
            
            result = {
                'email': email,
                'tier': subscription.tier,
                'characters_remaining': subscription.character_count,
                'character_limit': subscription.character_limit,
                'status': subscription.status,
                'next_reset': next_reset_str,
                'voice_limit': subscription.voice_limit,
                'voice_slots_used': subscription.voice_slots_used,
                'billing_period': subscription.billing_period,
                'error': None
            }
            
            # Add audio test result if requested
            if test_audio:
                result['can_generate_audio'] = test_audio_generation(api_key)
            
            return result
        else:
            return {
                'email': email,
                'error': 'No subscription information available'
            }
            
    except Exception as e:
        return {
            'email': email,
            'error': str(e)
        }

def format_number(num):
    """Format large numbers with commas."""
    return f"{num:,}" if num is not None else "N/A"

def print_progress_bar(current, total, width=50):
    """Print a progress bar."""
    filled = int(width * current // total)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {current}/{total}"

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Check ElevenLabs API Key Balances')
    parser.add_argument('--audio', action='store_true', help='Test audio generation capability for each key')
    args = parser.parse_args()
    
    # Initialize colorama
    init()
    
    print(f"\n{Fore.CYAN}🔍 Checking ElevenLabs API Key Balances...{Style.RESET_ALL}\n")
    if args.audio:
        print(f"{Fore.YELLOW}🎵 Audio generation testing enabled{Style.RESET_ALL}\n")
    
    # Load API keys
    api_keys = load_api_keys()
    if not api_keys:
        print(f"{Fore.RED}No valid API keys found!{Style.RESET_ALL}")
        return
    
    print(f"Found {len(api_keys)} API keys to check.\n")
    print("=" * 100)
    
    # Check each key and show running totals
    results = []
    running_total = 0
    active_count = 0
    inactive_count = 0
    error_count = 0
    audio_capable_count = 0
    
    for i, (email, key) in enumerate(api_keys, 1):
        # Print progress bar
        progress = print_progress_bar(i, len(api_keys))
        print(f"\r{Fore.CYAN}Progress: {progress}{Style.RESET_ALL}", end='')
        
        # Check key balance
        result = check_key_balance(email, key, args.audio)
        results.append(result)
        
        # Clear progress bar line
        print('\r' + ' ' * 100 + '\r', end='')
        
        # Print result for this key
        if not result.get('error'):
            chars = result.get('characters_remaining', 0)
            running_total += chars
            active_count += 1
            
            # Determine status color
            status_color = Fore.GREEN if result['status'] == 'active' else Fore.YELLOW
            
            print(f"{status_color}[{result['tier'].upper()}] Key {i:2d}/{len(api_keys)}: {Fore.YELLOW}{email}{Style.RESET_ALL}")
            print(f"   Characters: {Fore.GREEN}{format_number(chars)}/{format_number(result['character_limit'])}{Style.RESET_ALL}")
            print(f"   Voice Slots: {result['voice_slots_used']}/{result['voice_limit']}")
            print(f"   Status: {status_color}{result['status']}{Style.RESET_ALL}")
            print(f"   Billing Period: {result['billing_period']}")
            print(f"   Next Reset: {result['next_reset']}")
            print(f"   Running Total: {Fore.CYAN}{format_number(running_total)}{Style.RESET_ALL}")
            
            if args.audio:
                audio_status = result.get('can_generate_audio', False)
                if audio_status:
                    audio_capable_count += 1
                    print(f"   Audio Generation: {Fore.GREEN}✓ Working{Style.RESET_ALL}")
                else:
                    print(f"   Audio Generation: {Fore.RED}✗ Not Working{Style.RESET_ALL}")
            
        else:
            error_count += 1
            print(f"{Fore.RED}❌ Key {i:2d}/{len(api_keys)}: {email}")
            print(f"   Error: {result['error']}{Style.RESET_ALL}")
        
        print("-" * 100)
        time.sleep(1)  # Prevent rate limiting
    
    # Print final summary
    print("\n" + "=" * 100)
    print(f"\n{Fore.CYAN}📈 Final Summary:{Style.RESET_ALL}")
    print(f"Total Keys Checked: {len(api_keys)}")
    print(f"Active Keys: {Fore.GREEN}{active_count}{Style.RESET_ALL}")
    print(f"Error Keys: {Fore.RED}{error_count}{Style.RESET_ALL}")
    if args.audio:
        print(f"Audio Capable Keys: {Fore.GREEN}{audio_capable_count}{Style.RESET_ALL}")
    print(f"\nTotal Characters Available: {Fore.GREEN}{format_number(running_total)}{Style.RESET_ALL}")
    
    # Calculate and show average characters per active key
    if active_count > 0:
        avg_chars = running_total / active_count
        print(f"Average Characters per Active Key: {Fore.CYAN}{format_number(int(avg_chars))}{Style.RESET_ALL}")

if __name__ == "__main__":
    main() 