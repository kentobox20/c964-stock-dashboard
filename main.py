#!/usr/bin/env python3
"""
Main script to run the Reddit scraping, company extraction, and sentiment analysis pipeline
"""

import os
from datetime import datetime
import pandas as pd
from reddit_scrape import get_posts_with_comments
from extract_company import process_reddit_data
from NB_classifier import SentimentAnalyzer
from database import RedditDB

def main():
    # Create output directory if it doesn't exist
    os.makedirs('output', exist_ok=True)
    
    print(f"\n=== Starting Reddit Analysis Pipeline at {datetime.now()} ===\n")
    
    # Step 1: Scrape Reddit
    print("Step 1: Scraping Reddit posts...")
    posts = get_posts_with_comments()
    df = pd.DataFrame(posts)
    
    # Show summary of raw data
    total_comments = df['num_comments'].sum()
    print(f"Total comments collected: {total_comments}")
    
    print("\nTop posts by comment count:")
    top_posts = df.nlargest(5, 'num_comments')
    for _, post in top_posts.iterrows():
        print(f"  {post['num_comments']} comments: {post['post_title'][:60]}...")
    
    # Step 2: Extract company mentions
    print("\nStep 2: Extracting company mentions...")
    df = process_reddit_data(df)
    
    # Show company mentions summary
    print("\nTop mentioned companies:")
    all_tickers = []
    for tickers in df['mentioned_tickers'].dropna():
        all_tickers.extend(tickers)
    
    ticker_counts = pd.Series(all_tickers).value_counts()
    for ticker, count in ticker_counts.head(10).items():
        print(f"  {ticker}: {count} mentions")
    
    # Step 3: Sentiment Analysis
    print("\nStep 3: Performing sentiment analysis...")
    
    # Initialize sentiment analyzer
    analyzer = SentimentAnalyzer()
    
    # Analyze sentiment
    df['post_sentiment'] = None
    df['post_score'] = None
    df['post_word_score'] = None
    df['comment_sentiment'] = None
    df['comment_score'] = None
    df['comment_word_scores'] = None
    df['overall_sentiment'] = None
    df['overall_score'] = None
    df['num_comments_analyzed'] = None
    
    for idx, row in df.iterrows():
        sentiment, confidence = analyzer.predict_sentiment(row.to_dict())
        df.at[idx, 'post_sentiment'] = confidence['post_sentiment']
        df.at[idx, 'post_score'] = float(confidence['post_score'])
        df.at[idx, 'post_word_score'] = float(confidence['post_word_score'])
        df.at[idx, 'comment_sentiment'] = confidence['comment_sentiment']
        df.at[idx, 'comment_score'] = float(confidence['comment_score'])
        df.at[idx, 'comment_word_scores'] = str(confidence['comment_word_scores'])  # Convert list to string for CSV
        df.at[idx, 'overall_sentiment'] = confidence['overall_sentiment']
        df.at[idx, 'overall_score'] = float(confidence['overall_score'])
        df.at[idx, 'num_comments_analyzed'] = int(confidence['num_comments'])
    
    # Convert score columns to float
    score_columns = ['post_score', 'post_word_score', 'comment_score', 'overall_score']
    for col in score_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Step 4: Save to database
    print("\nStep 4: Saving to database...")
    db = RedditDB()
    db.save_daily_data(df)
    
    # Save final results to CSV
    final_output = os.path.join('output', f"reddit_analysis_complete_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
    df.to_csv(final_output, index=False)
    
    print(f"\n=== Pipeline completed successfully at {datetime.now()} ===")
    print(f"Complete analysis saved to: {final_output}")
    
    # Show sentiment summary
    print("\nPost Sentiment Distribution:")
    post_sentiment_counts = df['post_sentiment'].value_counts()
    for sentiment, count in post_sentiment_counts.items():
        print(f"  {sentiment}: {count} posts")
    
    print("\nComment Sentiment Distribution:")
    comment_sentiment_counts = df['comment_sentiment'].value_counts()
    for sentiment, count in comment_sentiment_counts.items():
        print(f"  {sentiment}: {count} posts")
    
    print("\nOverall Sentiment Distribution:")
    overall_sentiment_counts = df['overall_sentiment'].value_counts()
    for sentiment, count in overall_sentiment_counts.items():
        print(f"  {sentiment}: {count} posts")
    
    # Show average scores
    print("\nAverage Scores:")
    print("Post Scores:")
    print(df[['post_score', 'post_word_score']].mean().round(1))
    print("\nComment Scores:")
    print(df[['comment_score']].mean().round(1))
    print("\nOverall Scores:")
    print(df[['overall_score']].mean().round(1))
    
    # Show sentiment by company
    print("\nCompany Sentiment Analysis:")
    
    # Explode the mentioned_tickers column to create separate rows for each ticker
    company_df = df.explode('mentioned_tickers')
    company_df = company_df[company_df['mentioned_tickers'].notna()]
    
    # Group by ticker and calculate statistics
    company_summary = company_df.groupby('mentioned_tickers').agg({
        'post_score': ['count', 'mean'],
        'comment_score': ['mean'],
        'overall_score': ['mean'],
        'num_comments_analyzed': ['sum']
    }).round(1)
    
    # Flatten column names
    company_summary.columns = ['_'.join(col).strip() for col in company_summary.columns.values]
    
    print("\nTop Companies by Mention Count:")
    print(company_summary.sort_values('post_score_count', ascending=False).head(10))

if __name__ == "__main__":
    main() 