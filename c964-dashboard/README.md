# Reddit Stock Dashboard

A comprehensive dashboard that analyzes Reddit sentiment for stock tickers and displays current stock prices.

**Live Demo:** [**https://kentobox20.github.io/c964-stock-dashboard/**](https://kentobox20.github.io/c964-stock-dashboard/)

## Features

- **Reddit Sentiment Analysis**: Analyzes sentiment from Reddit posts and comments for various stock tickers
- **Real-time Stock Prices**: Displays current stock prices for selected tickers using Alpha Vantage API
- **Interactive Visualizations**: 
  - Sentiment over time by ticker
  - Mentions over time by ticker  
  - Engagement by ticker
- **Filtering**: Date range selection and ticker filtering
- **Quick Filters**: Top 5 by mentions or sentiment

## Stock Price Feature

The dashboard now includes a real-time stock price display that shows:
- Current stock price
- Daily change (dollar amount and percentage)
- Color-coded cards (green for positive, red for negative, gray for neutral)
- Automatic updates when tickers are selected/deselected
- 5-minute caching to avoid excessive API calls

## Setup and Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the data processing pipeline (to populate database):
```bash
python main.py
```

3. Open the dashboard:
```
Open index.html in your web browser
```

## Usage

1. **Select Tickers**: Use the dropdown to select which stock tickers you want to analyze
2. **Adjust Date Range**: Use the slider to select the date range for analysis
3. **View Stock Prices**: Current stock prices will automatically display for selected tickers
4. **Quick Filters**: Use the quick filter buttons to see top performers
5. **Interactive Charts**: Click on chart elements to highlight specific tickers

## Data Sources

- **Reddit Data**: Scraped from Reddit using PRAW
- **Stock Prices**: Alpha Vantage API (free tier)
- **Sentiment Analysis**: VADER sentiment analysis

## Technical Details

- **Frontend**: HTML, CSS, JavaScript with Plotly.js for visualizations
- **Backend**: Python data processing pipeline
- **Database**: SQLite for storing Reddit analysis data
- **Caching**: 5-minute cache for stock prices to reduce API calls

## Troubleshooting

- If stock prices don't load, check your internet connection
- The Alpha Vantage demo API has rate limits - if you hit them, wait a few minutes
- Check browser console for any JavaScript errors