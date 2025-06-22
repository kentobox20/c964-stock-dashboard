import sqlite3
import pandas as pd
from datetime import datetime
import json
import ast
import os

class RedditDB:
    def __init__(self, db_path='reddit_sentiment.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        
        # Raw posts table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS posts_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                subreddit TEXT,
                post_title TEXT,
                post_content TEXT,
                post_author TEXT,
                post_score REAL,
                num_comments INTEGER,
                post_sentiment TEXT,
                post_word_score REAL,
                comment_sentiment TEXT,
                comment_score REAL,
                overall_sentiment TEXT,
                overall_score REAL,
                num_comments_analyzed INTEGER,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Stock mentions table (normalized)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stock_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                ticker TEXT,
                date TEXT,
                FOREIGN KEY (post_id) REFERENCES posts_raw (id)
            )
        ''')
        
        # Daily summary table (denormalized for fast queries)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS daily_ticker_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                mention_count INTEGER,
                total_posts INTEGER,
                total_comments INTEGER,
                avg_post_score REAL,
                avg_comment_score REAL,
                avg_overall_score REAL,
                sentiment_positive INTEGER,
                sentiment_negative INTEGER,
                sentiment_neutral INTEGER,
                subreddit_breakdown TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, ticker)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized: {self.db_path}")
    
    def save_daily_data(self, df, date=None):
        """Save processed data to database"""
        conn = sqlite3.connect(self.db_path)
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Save to all 3 tables within a single transaction
        self._save_posts_raw(df, conn, date)
        self._save_daily_summary(df, conn, date)
        
        # Commit all changes at the very end
        conn.commit()
        conn.close()
        print(f"Data saved to database for {date}")
    
    def _save_posts_raw(self, df, conn, date):
        """Save posts to posts_raw table (one row per post)"""
        for _, row in df.iterrows():
            cursor = conn.execute('''
                INSERT INTO posts_raw 
                (date, subreddit, post_title, post_content, post_author, post_score,
                 num_comments, post_sentiment, post_word_score, comment_sentiment,
                 comment_score, overall_sentiment, overall_score, num_comments_analyzed, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date,
                row['subreddit'],
                row['post_title'],
                row['post_content'],
                row['post_author'],
                row['post_score'],
                row['num_comments'],
                row['post_sentiment'],
                row['post_word_score'],
                row['comment_sentiment'],
                row['comment_score'],
                row['overall_sentiment'],
                row['overall_score'],
                row['num_comments_analyzed'],
                row['url']
            ))
            
            # Get the post_id for stock_mentions table
            post_id = cursor.lastrowid
            
            # Handle mentioned_tickers (it's a list)
            mentioned_tickers = row['mentioned_tickers']
            if isinstance(mentioned_tickers, list) and mentioned_tickers:
                for ticker in mentioned_tickers:
                    conn.execute('''
                        INSERT INTO stock_mentions (post_id, ticker, date)
                        VALUES (?, ?, ?)
                    ''', (post_id, ticker, date))
            elif isinstance(mentioned_tickers, str) and mentioned_tickers and mentioned_tickers != '[]':
                try:
                    tickers = ast.literal_eval(mentioned_tickers)
                    if isinstance(tickers, list):
                        for ticker in tickers:
                            conn.execute('''
                                INSERT INTO stock_mentions (post_id, ticker, date)
                                VALUES (?, ?, ?)
                            ''', (post_id, ticker, date))
                except:
                    # If it's a single ticker as string
                    conn.execute('''
                        INSERT INTO stock_mentions (post_id, ticker, date)
                        VALUES (?, ?, ?)
                    ''', (post_id, mentioned_tickers, date))
        
    def _save_stock_mentions(self, df, conn, date):
        """Stock mentions are saved in _save_posts_raw to get proper post_id"""
        pass  # This is handled in _save_posts_raw
    
    def _save_daily_summary(self, df, conn, date):
        """Save aggregated daily summary by ticker"""
        # First, delete existing summary for this date to avoid duplicates
        conn.execute('DELETE FROM daily_ticker_summary WHERE date = ?', (date,))

        # Get all stock mentions for today
        mentions_query = '''
            SELECT sm.ticker, pr.subreddit, pr.post_sentiment, pr.comment_sentiment, 
                   pr.overall_sentiment, pr.post_score, pr.comment_score, pr.overall_score,
                   pr.num_comments_analyzed
            FROM stock_mentions sm
            JOIN posts_raw pr ON sm.post_id = pr.id
            WHERE sm.date = ?
        '''
        
        mentions_df = pd.read_sql_query(mentions_query, conn, params=(date,))
        
        if mentions_df.empty:
            return
        
        # Group by ticker and calculate aggregations
        for ticker in mentions_df['ticker'].unique():
            ticker_data = mentions_df[mentions_df['ticker'] == ticker]
            
            mention_count = len(ticker_data)
            total_posts = len(ticker_data)  # Same as mention_count for now
            total_comments = ticker_data['num_comments_analyzed'].sum()
            avg_post_score = ticker_data['post_score'].mean()
            avg_comment_score = ticker_data['comment_score'].mean()
            avg_overall_score = ticker_data['overall_score'].mean()
            
            # Count sentiments
            sentiment_counts = ticker_data['overall_sentiment'].value_counts()
            pos_count = sentiment_counts.get('positive', 0)
            neg_count = sentiment_counts.get('negative', 0)
            neu_count = sentiment_counts.get('neutral', 0)
            
            # Subreddit breakdown
            subreddit_counts = ticker_data['subreddit'].value_counts().to_dict()
            subreddit_breakdown = json.dumps(subreddit_counts)
            
            # Insert new summary data
            conn.execute('''
                INSERT INTO daily_ticker_summary 
                (date, ticker, mention_count, total_posts, total_comments,
                 avg_post_score, avg_comment_score, avg_overall_score,
                 sentiment_positive, sentiment_negative, sentiment_neutral,
                 subreddit_breakdown)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date, ticker, mention_count, total_posts, total_comments,
                round(avg_post_score, 2), round(avg_comment_score, 2), round(avg_overall_score, 2),
                pos_count, neg_count, neu_count, subreddit_breakdown
            ))
    
    def get_ticker_history(self, ticker, days=30):
        """Get historical data for a specific ticker"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT * FROM daily_ticker_summary 
            WHERE ticker = ? 
            ORDER BY date DESC 
            LIMIT ?
        '''
        
        df = pd.read_sql_query(query, conn, params=(ticker, days))
        conn.close()
        return df
    
    def export_for_web(self, output_dir='docs/data'):
        """Export data as JSON files for GitHub Pages"""
        os.makedirs(output_dir, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        
        # 1. Sentiment over time
        sentiment_query = '''
            SELECT DATE(date) as date, ticker, AVG(avg_overall_score) as avg_overall_score
            FROM daily_ticker_summary 
            GROUP BY DATE(date), ticker
            ORDER BY date, ticker
        '''
        sentiment_df = pd.read_sql_query(sentiment_query, conn)
        sentiment_df.to_json(f'{output_dir}/sentiment_over_time.json', orient='records')
        
        # 2. Mentions over time
        mentions_query = '''
            SELECT DATE(date) as date, ticker, SUM(mention_count) as mention_count
            FROM daily_ticker_summary 
            GROUP BY DATE(date), ticker
            ORDER BY date, ticker
        '''
        mentions_df = pd.read_sql_query(mentions_query, conn)
        mentions_df.to_json(f'{output_dir}/mentions_over_time.json', orient='records')
        
        # 3. Latest engagement by ticker
        engagement_query = '''
            SELECT 
                ticker, 
                avg_overall_score, 
                CAST(total_comments AS INTEGER) as total_comments, 
                mention_count 
            FROM daily_ticker_summary 
            WHERE date = (SELECT MAX(date) FROM daily_ticker_summary) 
            ORDER BY mention_count DESC
        '''
        engagement_df = pd.read_sql_query(engagement_query, conn)
        engagement_df.to_json(f'{output_dir}/engagement_by_ticker.json', orient='records')
        
        conn.close()
        print(f"Data exported to {output_dir}")