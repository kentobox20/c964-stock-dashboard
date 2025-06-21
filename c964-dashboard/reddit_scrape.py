# simple_reddit_scraper.py
"""
Reddit scraper - gets posts with all their comments grouped together
"""

import praw
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Reddit setup
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent='StockBot/1.0'
)

# Top 5 stock subreddits
subreddits = ['stocks', 'investing', 'wallstreetbets', 'SecurityAnalysis', 'StockMarket']

def get_posts_with_comments():
    """Pull posts and group all their comments together"""
    
    all_posts = []
    cutoff_time = datetime.now() - timedelta(hours=24)
    
    for sub_name in subreddits:
        print(f"Getting data from r/{sub_name}...")
        
        subreddit = reddit.subreddit(sub_name)
        
        # Get top posts from last 24 hours
        for post in subreddit.top(time_filter='day', limit=10):
            post_time = datetime.fromtimestamp(post.created_utc)
            
            if post_time >= cutoff_time:
                # Collect all comments for this post
                comments_list = []
                post.comments.replace_more(limit=0)
                
                for comment in post.comments:
                    comment_time = datetime.fromtimestamp(comment.created_utc)
                    
                    if (comment_time >= cutoff_time and 
                        comment.body not in ['[deleted]', '[removed]'] and
                        len(comment.body.strip()) > 10):  # Skip very short comments
                        
                        comments_list.append(comment.body.strip())
                
                # Add post with all its comments
                post_data = {
                    'subreddit': sub_name,
                    'post_title': post.title,
                    'post_content': post.selftext if post.selftext else '',
                    'post_author': str(post.author) if post.author else 'Unknown',
                    'post_score': post.score,
                    'num_comments': len(comments_list),
                    'created': post_time,
                    'comments': comments_list,  # List of all comment texts
                    'url': f"https://reddit.com{post.permalink}"
                }
                
                all_posts.append(post_data)
                print(f"  Got post: '{post.title[:50]}...' with {len(comments_list)} comments")
    
    return all_posts

def save_to_csv(posts, output_dir='output'):
    """Save posts to CSV in the output directory"""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert to DataFrame
    df = pd.DataFrame(posts)
    
    # Save to CSV
    filename = f"reddit_posts_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    output_path = os.path.join(output_dir, filename)
    df.to_csv(output_path, index=False)
    
    print(f"\nSaved {len(posts)} posts to {output_path}")
    
    # Show summary
    total_comments = sum(post['num_comments'] for post in posts)
    print(f"Total comments collected: {total_comments}")
    
    # Show top posts by comment count
    print(f"\nTop posts by comment count:")
    for post in sorted(posts, key=lambda x: x['num_comments'], reverse=True)[:5]:
        print(f"  {post['num_comments']} comments: {post['post_title'][:60]}...")
    
    return output_path

if __name__ == "__main__":
    print("Pulling Reddit posts with comments from last 24 hours...")
    posts = get_posts_with_comments()
    save_to_csv(posts)