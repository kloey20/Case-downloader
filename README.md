# LawPhil Case Downloader

A Python tool to download Philippine Supreme Court cases from [lawphil.net](https://lawphil.net) and save them as PDF files.

## Features

- Download cases by G.R. number
- Download cases from direct LawPhil URLs
- Automatic Google search to find cases
- Save cases as PDF with proper formatting
- Command-line interface for easy use

## Requirements

- Python 3.7 or higher
- Google Chrome browser installed
- Internet connection

## Installation

1. **Clone this repository:**
```bash
git clone https://github.com/yourusername/lawphil-downloader.git
cd lawphil-downloader
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

The script will automatically download and manage the ChromeDriver for you.

## Usage

### Basic Usage - Download by Case Number

```bash
python lawphil_downloader.py "G.R. No. 238659"
```

### Specify Output Filename

```bash
python lawphil_downloader.py "G.R. No. 227868" -o my_case.pdf
```

### Download from Direct URL

```bash
python lawphil_downloader.py --url "https://lawphil.net/judjuris/juri2019/jun2019/gr_238659_2019.html"
```

### Show Browser Window (for debugging)

```bash
python lawphil_downloader.py "G.R. No. 238659" --no-headless
```

### Get Help

```bash
python lawphil_downloader.py --help
```

## How It Works

1. **Case Number Parsing**: The script parses the G.R. number from your input
2. **Google Search**: Uses Google to search for the case on lawphil.net (since LawPhil doesn't have a built-in search)
3. **Page Loading**: Opens the case page using Selenium WebDriver
4. **PDF Generation**: Uses Chrome's print-to-PDF functionality to save the case

## Supported Case Formats

- `G.R. No. 238659`
- `G.R. No. 227868`
- Direct LawPhil URLs

## Example Output

```
$ python lawphil_downloader.py "G.R. No. 238659"
Looking for G.R. No. 238659
Searching for: G.R. No. 238659
Google search URL: https://www.google.com/search?q=site%3Alawphil.net+G.R.+No.+238659
Found case URL: https://lawphil.net/judjuris/juri2019/jun2019/gr_238659_2019.html
Accessing: https://lawphil.net/judjuris/juri2019/jun2019/gr_238659_2019.html
Generating PDF: G.R._No._238659_20241101_143052.pdf
✓ Successfully saved: G.R._No._238659_20241101_143052.pdf
```

## Notes

- **LawPhil Structure**: LawPhil organizes cases by year and month in their URL structure. The script uses Google search to find the correct URL since there's no centralized search function on LawPhil itself.

- **Rate Limiting**: Be respectful of LawPhil's servers. Avoid downloading large numbers of cases in quick succession.

- **Browser Requirement**: This tool requires Chrome browser to be installed on your system. The ChromeDriver is automatically managed by webdriver-manager.

- **Headless Mode**: By default, the browser runs in headless mode (no window shown). Use `--no-headless` if you want to see what's happening.

## Troubleshooting

### "Required packages not installed"
Run: `pip install -r requirements.txt`

### "ChromeDriver not found"
The webdriver-manager should handle this automatically. If issues persist, ensure Chrome browser is installed and updated.

### "Could not find the case"
- Verify the case number is correct
- Check if the case exists on lawphil.net by searching manually
- Try using the direct URL instead: `--url "https://lawphil.net/..."`

### Google search blocking
If Google blocks automated searches, you can:
1. Use the direct URL method if you know the URL
2. Run with `--no-headless` to complete any CAPTCHA manually
3. Wait a few minutes before trying again

## Legal Notice

This tool is for educational and research purposes only. Please respect:
- LawPhil's [Acceptable Use Policy](https://lawphil.net/usepolicy.html)
- Copyright notices on individual cases
- Fair use principles for legal research

LawPhil is provided by the Arellano Law Foundation as a free service. Please consider supporting them if you find their database useful.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - feel free to use and modify for your needs.

## Acknowledgments

- [LawPhil Project](https://lawphil.net) - Arellano Law Foundation
- Thanks to all contributors to Philippine legal education

## Support

If you encounter issues or have questions:
1. Check the Troubleshooting section above
2. Open an issue on GitHub
3. Verify the case exists on lawphil.net first

---

**Made for Philippine law students and legal researchers 🇵🇭⚖️**
