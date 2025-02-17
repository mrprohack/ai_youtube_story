import os
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize the client with API key
client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

def text_to_speech(text, output_path="output.mp3"):
    """
    Convert text to speech using Eleven Labs API
    Args:
        text (str): The text to convert to speech
        output_path (str): Path to save the audio file. Defaults to "output.mp3"
    """
    try:
        # Generate audio from text using the text_to_speech API
        audio_stream = client.text_to_speech.convert(
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_multilingual_v2"
        )
        
        # Save the audio file by reading the stream
        with open(output_path, 'wb') as f:
            # Write each chunk from the stream
            for chunk in audio_stream:
                if chunk is not None:
                    f.write(chunk)
        
        print(f"Audio saved to {output_path}")
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    # Example usage
    sample_text = "The first move is what sets everything in motion."
    text_to_speech(sample_text)  # This will save to output.mp3
    
    # Example with custom output path
    # text_to_speech(sample_text, "custom_name.mp3")
