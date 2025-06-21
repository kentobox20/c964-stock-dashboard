import pandas as pd
import re
from typing import List, Dict
import os

class StockIdentifier:
    def __init__(self):
        # Common stock ticker patterns (2-5 uppercase letters)
        self.ticker_pattern = r'\b[A-Z]{2,5}\b'
        
        # Known company names to ticker mappings
        self.company_to_ticker = {
            'apple': 'AAPL',
            'microsoft': 'MSFT',
            'meta': 'META',
            'facebook': 'META',
            'google': 'GOOG',
            'alphabet': 'GOOG',
            'amazon': 'AMZN',
            'nvidia': 'NVDA',
            'tesla': 'TSLA',
            'visa': 'V',
            'mastercard': 'MA',
            'boeing': 'BA',
            'costco': 'COST',
            'target': 'TGT',
            'nike': 'NKE',
            'pepsi': 'PEP',
            'oracle': 'ORCL',
            'walmart': 'WMT',
            'expedia': 'EXPE',
            'palantir': 'PLTR',
            'carvana': 'CVNA',
            'tyson': 'TSN',
            'adobe': 'ADBE',
            'ups': 'UPS',
            'unitedhealth': 'UNH',
            'devon energy': 'DVN',
            'pultegroup': 'PHM',
            'stellantis': 'STLA',
            'mercadolibre': 'MELI',
            'uber': 'UBER',
            'asml': 'ASML',
            'oklo': 'OKLO',
            'ionq': 'IONQ'
        }
        
        # Common false positives to filter out
        self.false_positives = {
            'USD', 'USA', 'CEO', 'IPO', 'ETF', 'AI', 'IT', 'US', 'UK', 'EU', 'Q1', 'Q2', 'Q3', 'Q4',
            'YOY', 'QOQ', 'PE', 'EPS', 'ROI', 'GDP', 'CPI', 'PPI', 'FED', 'SEC', 'IRA', 'THE', 'AND',
            'FOR', 'BUT', 'NOT', 'ALL', 'CAN', 'GET', 'NEW', 'WAY', 'ONE', 'TWO', 'MAX', 'MIN', 'TOP',
            'END', 'SET', 'PUT', 'CALL', 'BUY', 'SELL', 'HOLD', 'LONG', 'SHORT', 'BULL', 'BEAR'
        }
        
        # ETF patterns
        self.etf_patterns = {
            'VOO': 'Vanguard S&P 500 ETF',
            'VTI': 'Vanguard Total Stock Market ETF',
            'VT': 'Vanguard Total World Stock ETF',
            'VXUS': 'Vanguard Total International Stock ETF',
            'SPY': 'SPDR S&P 500 ETF',
            'VIX': 'Volatility Index'
        }
        
        # Initialize valid tickers list
        self.valid_tickers = self._initialize_valid_tickers()
    
    def _initialize_valid_tickers(self) -> List[str]:
        """Initialize the list of valid tickers"""
        # Get all tickers from our mappings
        tickers = set(self.company_to_ticker.values())
        
        # Add ETF tickers
        tickers.update(self.etf_patterns.keys())
        
        return list(tickers)
    
    def extract_tickers(self, text: str) -> List[str]:
        """Extract stock tickers from text"""
        if not isinstance(text, str):
            return []
        
        # Convert to lowercase for company name matching
        text_lower = text.lower()
        
        # Find potential tickers (2-5 letter words in all caps)
        potential_tickers = set(re.findall(self.ticker_pattern, text))
        
        # Remove false positives
        potential_tickers = potential_tickers - self.false_positives
        
        # Filter to only valid tickers
        found_tickers = [ticker for ticker in potential_tickers if ticker in self.valid_tickers]
        
        # Check for company names
        for company, ticker in self.company_to_ticker.items():
            if company in text_lower and ticker not in found_tickers:
                found_tickers.append(ticker)
        
        return list(set(found_tickers))  # Remove any duplicates

def process_reddit_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process Reddit data to extract company mentions"""
    # Initialize stock identifier
    stock_id = StockIdentifier()
    
    # Add a new column for ticker mentions
    df['mentioned_tickers'] = None
    
    # Process each post and its comments
    for idx, row in df.iterrows():
        # Combine post title and content
        post_text = f"{row['post_title']} {row['post_content']}"
        
        # Get tickers from post
        post_tickers = stock_id.extract_tickers(post_text)
        
        # Get tickers from comments
        comment_tickers = []
        if isinstance(row['comments'], str):
            # Convert string representation of list to actual list
            comments = eval(row['comments'])
            for comment in comments:
                comment_tickers.extend(stock_id.extract_tickers(comment))
        
        # Combine all tickers found and remove duplicates
        all_tickers = list(set(post_tickers + comment_tickers))
        
        # Add to the DataFrame
        df.at[idx, 'mentioned_tickers'] = all_tickers
    
    return df

if __name__ == "__main__":
    # Get the most recent CSV file in the current directory
    import glob
    import os
    
    csv_files = glob.glob("output/reddit_posts_*.csv")
    if not csv_files:
        print("No Reddit post CSV files found in output directory!")
        exit(1)
    
    latest_csv = max(csv_files, key=os.path.getctime)
    print(f"Processing {latest_csv}...")
    
    # Process the data
    df = pd.read_csv(latest_csv)
    result_df = process_reddit_data(df)
    
    # Save results
    output_file = f"reddit_posts_with_tickers_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv"
    output_path = os.path.join('output', output_file)
    result_df.to_csv(output_path, index=False)
    
    print(f"\nSaved {len(result_df)} posts to {output_path}")
    
    # Show summary
    print("\nTop mentioned companies:")
    # Count all tickers across all posts
    all_tickers = []
    for tickers in result_df['mentioned_tickers'].dropna():
        all_tickers.extend(tickers)
    
    ticker_counts = pd.Series(all_tickers).value_counts()
    for ticker, count in ticker_counts.head(10).items():
        print(f"  {ticker}: {count} mentions")
