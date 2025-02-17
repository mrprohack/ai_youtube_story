# 📚 AI YouTube Book Summary Generator

An advanced tool that automatically generates engaging YouTube video scripts and voice-overs from book summaries using AI.

## ✨ Features

- 🎬 Generates complete YouTube video scripts
- 🎙️ Creates professional voice-overs with ElevenLabs AI
- 📝 Produces structured content with sections and titles
- 🌍 Supports multiple languages
- 🎨 Includes visual suggestions and background music recommendations
- ⚡ Automatic API key rotation for uninterrupted generation

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Groq API key
- ElevenLabs API key(s)

### Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment:
   - Create a `.env` file in the root directory
   - Add your API keys:
```env
GROQ_API_KEY=your_groq_api_key
```

4. Set up ElevenLabs API keys:
   - Create `elevenlabs_apis` file
   - Add your ElevenLabs API keys in the format:
```
email:api_key
```

## 💫 Usage

Run the script with:
```bash
python maltilang.py
```

Optional flags:
- `--log`: Show detailed logging information

The script will:
1. Ask for your preferred language
2. Prompt for the book name
3. Generate comprehensive video script
4. Create voice-overs for all sections
5. Save everything in organized directories

## 📁 Output Structure

```
youtube_content/
└── [book_name]/
    ├── script/
    │   ├── full_script.json
    │   └── production_script.txt
    └── voice_over/
        ├── titles/
        │   ├── 01_title_script.txt
        │   ├── 01_title_audio.mp3
        │   └── ...
        └── sections/
            ├── 01_section_script.txt
            ├── 01_section_audio.mp3
            └── ...
```

## ⚙️ Configuration Options

### Voice Settings
- Voice ID: "JBFqnCBsd6RMkjVDRZzb" (Default)
- Model: "eleven_multilingual_v2"
- Output Format: "mp3_44100_128"

### API Settings
- Model: "llama-3.3-70b-versatile"
- Temperature: 0.7
- Max Tokens: 4000
- Top P: 0.9

## 🔄 API Key Rotation

The system automatically handles ElevenLabs API key rotation:
- Detects quota exceeded errors
- Switches to the next available key
- Continues processing without interruption
- Supports unlimited keys in `elevenlabs_apis` file

## 🛠️ Error Handling

The application includes robust error handling for:
- API quota limitations
- Network failures
- Invalid inputs
- File system errors
- JSON parsing issues

## 📊 Logging

- Location: `logs/story_planner_[timestamp].log`
- Captures:
  - API calls
  - Generation progress
  - Error details
  - Key rotations
  - File operations

## 🔮 Upcoming Features

- [ ] Custom voice selection
- [ ] Background music generation
- [ ] Automatic video assembly
- [ ] Thumbnail generation
- [ ] Multiple language templates
- [ ] Batch processing
- [ ] Progress saving and resuming
- [ ] Web interface

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🆘 Troubleshooting

### Common Issues

1. **API Quota Exceeded**
   - Add more API keys to `elevenlabs_apis`
   - Increase delay between requests
   - Check key validity

2. **Memory Issues**
   - Reduce chunk size in settings
   - Process fewer sections at once
   - Clear temporary files

3. **Generation Failures**
   - Check API key validity
   - Verify internet connection
   - Review log files for details

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Groq](https://groq.com/) for their powerful LLM API
- [ElevenLabs](https://elevenlabs.io/) for text-to-speech capabilities
- Open source community for inspiration and tools

---

Created with 🤖 for content creators | Last updated: May 2024
