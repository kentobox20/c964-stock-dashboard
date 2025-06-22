#!/usr/bin/env python3
"""
Export database data for web dashboard
"""
from database import RedditDB

def main():
    db = RedditDB('reddit_sentiment2.db')
    db.export_for_web('docs/data')
    print("✅ Web data exported successfully!")

if __name__ == "__main__":
    main() 