## ⚙️ Configuration

- **API Settings**: Modify `model` parameter in `StoryPlanner` class
- **Rate Limiting**: Adjust `time.sleep()` duration in main loop
- **Output Format**: Customize `_clean_text_for_tts()` method

## 🔍 Logging

- Logs are stored in `logs/` directory
- Format: `story_planner_YYYYMMDD_HHMMSS.log`
- Contains detailed operation logs and errors

## ⚠️ Error Handling

The application includes comprehensive error handling for:
- API failures
- File system operations
- Invalid inputs
- JSON parsing errors

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔮 Future Improvements

- [ ] Add support for multiple languages
- [ ] Implement parallel processing for faster generation
- [ ] Add video thumbnail generation
- [ ] Include background music suggestions
- [ ] Add video editing templates

## 🆘 Troubleshooting

Common issues and solutions:

1. **API Key Error**
   - Ensure `.env` file exists
   - Check API key validity

2. **Rate Limiting**
   - Increase sleep duration
   - Implement exponential backoff

3. **Memory Issues**
   - Process fewer episodes
   - Clear temporary files

## 📞 Support

For support, please:
1. Check the documentation
2. Review existing issues
3. Open a new issue with:
   - Error message
   - Log file
   - Steps to reproduce

## 🙏 Acknowledgments

- Groq AI for their powerful API
- Python community for excellent libraries
- YouTube creators for inspiration

---
Created with ❤️ for content creators
