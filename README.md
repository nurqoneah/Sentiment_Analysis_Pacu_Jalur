# Social Media Sentiment Analysis Project

A comprehensive project for scraping comments from TikTok and Instagram, and performing sentiment analysis with visualizations.

## Project Structure

```
sentimen/
├── data/                           # Centralized data storage
│   ├── instagram/                  # Instagram scraped data
│   ├── tiktok/                    # TikTok scraped data
│   ├── sentiment_analysis_results.csv
│   └── sentiment_summary.json
├── sentiment_analysis/            # Sentiment analysis module
│   └── sentiment_analysis.ipynb   # Main analysis notebook
├── tiktok_scraper.py             # Consolidated TikTok scraper
├── instagram_scraper.py          # Consolidated Instagram scraper
├── requirements.txt              # Project dependencies
├── tiktok_urls.csv              # TikTok video IDs (input)
├── instagram_urls.csv           # Instagram post IDs (input)
└── README.md                    # This file
```

## Features

### Social Media Scrapers
- **TikTok Scraper**: Extracts comments from TikTok videos using video IDs
- **Instagram Scraper**: Extracts comments from Instagram posts using post shortcodes
- **Unified Data Storage**: All scraped data is stored in the `data/` directory

### Sentiment Analysis
- **Text Preprocessing**: Cleans and prepares text for analysis
- **Sentiment Classification**: Uses TextBlob for sentiment analysis (positive, negative, neutral)
- **Word Clouds**: Generates word clouds for overall comments and by sentiment
- **Interactive Visualizations**: Creates interactive charts using Plotly
- **Statistical Analysis**: Provides detailed statistics and breakdowns

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. For NLTK (required for TextBlob):
```python
import nltk
nltk.download('punkt')
nltk.download('brown')
```

## Usage

### TikTok Scraping

1. Create a CSV file with TikTok video IDs (one per row):
```csv
aweme_id
7418294751977327878
7538444199310544184
```

2. Run the TikTok scraper:
```bash
python tiktok_scraper.py --input-file tiktok_urls.csv --output data/tiktok/comments.csv
```

### Instagram Scraping

1. Create a CSV file with Instagram post shortcodes:
```csv
post_id
CXXXXXXXXXx
CYYYYYYYYY
```

2. Get your Instagram cookies (sessionid, ds_user_id, csrftoken, mid) from browser developer tools

3. Run the Instagram scraper:
```bash
python instagram_scraper.py \
  --input-file instagram_urls.csv \
  --output data/instagram/comments.csv \
  --sessionid "your_session_id" \
  --ds-user-id "your_ds_user_id" \
  --csrftoken "your_csrf_token" \
  --mid "your_mid"
```

### Sentiment Analysis

1. Ensure you have scraped data in the `data/` directory
2. Open the Jupyter notebook:
```bash
jupyter notebook sentiment_analysis/sentiment_analysis.ipynb
```
3. Run all cells to perform the complete analysis

## Output

### Scraped Data
- **TikTok**: `data/tiktok/all_comments.csv`
- **Instagram**: `data/instagram/all_comments.csv`

### Analysis Results
- **Combined Analysis**: `data/sentiment_analysis_results.csv`
- **Summary Statistics**: `data/sentiment_summary.json`
- **Visualizations**: Generated in the notebook (word clouds, charts, plots)

## Analysis Features

### Word Clouds
- Overall comments word cloud
- Sentiment-specific word clouds (positive, negative, neutral)
- Platform-specific word clouds

### Visualizations
- Sentiment distribution pie charts
- Sentiment by platform bar charts
- Polarity and subjectivity histograms
- Interactive scatter plots (Polarity vs Subjectivity)
- Interactive sunburst charts
- Box plots for platform comparison

### Statistics
- Platform breakdown and statistics
- Sentiment distribution analysis
- Most common words by sentiment
- Polarity and subjectivity metrics

## Requirements

- Python 3.8+
- pandas, numpy, matplotlib, seaborn
- wordcloud, textblob, scikit-learn, nltk
- plotly for interactive visualizations
- requests, loguru, click for scrapers
- jupyter for notebook interface

## Notes

### TikTok Scraper
- Uses TikTok's public API endpoints
- No authentication required
- Rate limiting is implemented

### Instagram Scraper
- Requires valid Instagram session cookies
- Uses Instagram's GraphQL API
- Includes rate limiting to avoid blocks
- May require periodic cookie updates

### Sentiment Analysis
- Uses TextBlob for sentiment analysis
- Polarity range: -1 (negative) to 1 (positive)
- Subjectivity range: 0 (objective) to 1 (subjective)
- Sentiment classification: positive (>0.1), negative (<-0.1), neutral (-0.1 to 0.1)

## Troubleshooting

1. **Instagram scraper fails**: Update your cookies from browser
2. **TikTok scraper fails**: Check if video IDs are correct and public
3. **Sentiment analysis errors**: Ensure data files exist in `data/` directory
4. **Missing visualizations**: Install all required packages from requirements.txt

## License

This project is for educational and research purposes. Please respect the terms of service of TikTok and Instagram when using these scrapers.
