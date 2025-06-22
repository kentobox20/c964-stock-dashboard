import re
import ast
from collections import defaultdict, Counter
import math
from typing import Dict, List, Tuple
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd

class SentimentAnalyzer:
    """
    Hybrid sentiment analyzer for Reddit data
    Uses VADER as base model with ability to add custom training data
    """
    
    def __init__(self):
        # Initialize VADER
        self.vader = SentimentIntensityAnalyzer()
        
        # For custom training data
        self.custom_training_data = []
        self.custom_trained = False
        self.word_counts = defaultdict(lambda: defaultdict(int))
        self.sentiment_counts = defaultdict(int)
        self.vocabulary = set()
        
        # Sentiment thresholds
        self.positive_threshold = 0.05
        self.negative_threshold = -0.05
        
        # Initialize word scores
        self.word_scores = self._initialize_word_scores()
    
    def _initialize_word_scores(self) -> Dict[str, float]:
        """Initialize word sentiment scores with financial-specific terms"""
        scores = {
            # Financial positive terms
            'bullish': 1.0, 'growth': 0.8, 'profit': 0.9, 'gain': 0.8, 'upside': 0.7,
            'opportunity': 0.7, 'potential': 0.6, 'outperform': 0.8, 'buy': 0.7,
            'strong': 0.7, 'positive': 0.7, 'increase': 0.6, 'rise': 0.6, 'surge': 0.8,
            'breakthrough': 0.8, 'innovative': 0.7, 'leading': 0.6, 'premium': 0.6,
            'dividend': 0.5, 'yield': 0.5, 'undervalued': 0.7, 'undervalue': 0.7,
            
            # Financial negative terms
            'bearish': -1.0, 'loss': -0.9, 'decline': -0.7, 'downside': -0.7,
            'risk': -0.6, 'concern': -0.6, 'worry': -0.7, 'sell': -0.7,
            'weak': -0.7, 'negative': -0.7, 'decrease': -0.6, 'fall': -0.6,
            'crash': -0.9, 'plunge': -0.8, 'downtrend': -0.7, 'overvalued': -0.7,
            'overvalue': -0.7, 'bankruptcy': -0.9, 'default': -0.9, 'delist': -0.8,
            'dilution': -0.6, 'short': -0.7, 'bear': -0.8, 'dump': -0.8,
            
            # Neutral/context-dependent terms
            'hold': 0.0, 'neutral': 0.0, 'stable': 0.0, 'flat': 0.0, 'consolidate': 0.0,
            'volatile': 0.0, 'uncertain': 0.0, 'mixed': 0.0, 'range': 0.0,
            'technical': 0.0, 'fundamental': 0.0, 'analysis': 0.0, 'chart': 0.0,
            'support': 0.0, 'resistance': 0.0, 'trend': 0.0, 'pattern': 0.0
        }
        
        # Add VADER's word lists
        vader_words = self.vader.lexicon
        for word, score in vader_words.items():
            if word not in scores:  # Don't override our custom scores
                scores[word] = score
        
        return scores
    
    def _calculate_word_score(self, text: str) -> float:
        """Calculate sentiment score based on word counts"""
        if not isinstance(text, str):
            return 0.0
            
        words = text.lower().split()
        total_score = 0.0
        word_count = 0
        
        for word in words:
            # Remove punctuation and check for word
            clean_word = ''.join(c for c in word if c.isalnum())
            if clean_word in self.word_scores:
                total_score += self.word_scores[clean_word]
                word_count += 1
        
        # Normalize score to 0-100 range
        if word_count > 0:
            normalized_score = ((total_score / word_count + 1) / 2) * 100
            return round(normalized_score, 1)
        return 50.0  # Neutral score if no sentiment words found
    
    def clean_and_tokenize(self, text: str) -> List[str]:
        """Clean text and convert to tokens"""
        if not text or not isinstance(text, str):
            return []
        
        # Remove URLs and markdown links
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Convert to lowercase and extract words
        text = text.lower()
        words = re.findall(r'\b[a-z]+\b', text)
        
        # Filter out very short words
        words = [word for word in words if len(word) > 2]
        
        return words
    
    def parse_comments(self, comments_str: str) -> List[str]:
        """Parse comments string back to list"""
        if not comments_str or comments_str == '[]':
            return []
        
        try:
            comments_list = ast.literal_eval(comments_str)
            return comments_list if isinstance(comments_list, list) else []
        except:
            return [comments_str]  # Treat as single comment if parsing fails
    
    def extract_all_text(self, data_dict: Dict) -> str:
        """Extract and combine title, post content, and comments"""
        texts = []
        
        # Add post title
        if data_dict.get('post_title') and isinstance(data_dict['post_title'], str):
            texts.append(data_dict['post_title'])
        
        # Add post content
        if data_dict.get('post_content') and isinstance(data_dict['post_content'], str):
            texts.append(data_dict['post_content'])
        
        # Add comments
        comments = data_dict.get('comments', [])
        if isinstance(comments, list):
            texts.extend([c for c in comments if isinstance(c, str)])
        elif isinstance(comments, str):
            # If comments is a string, try to parse it
            try:
                parsed_comments = ast.literal_eval(comments)
                if isinstance(parsed_comments, list):
                    texts.extend([c for c in parsed_comments if isinstance(c, str)])
            except:
                # If parsing fails, treat the whole string as one comment
                texts.append(comments)
        
        return ' '.join(texts)
    
    def add_training_example(self, data_dict: Dict, sentiment: str):
        """Add a custom training example"""
        if sentiment not in ['positive', 'negative', 'neutral']:
            raise ValueError("Sentiment must be 'positive', 'negative', or 'neutral'")
        
        self.custom_training_data.append((data_dict, sentiment))
        self.custom_trained = False  # Reset training flag
    
    def train_custom_model(self):
        """Train the custom model on added examples"""
        if not self.custom_training_data:
            return
        
        print(f"Training custom model on {len(self.custom_training_data)} examples...")
        
        # Reset counts
        self.word_counts = defaultdict(lambda: defaultdict(int))
        self.sentiment_counts = defaultdict(int)
        self.vocabulary = set()
        
        for data_dict, sentiment in self.custom_training_data:
            # Extract all text
            combined_text = self.extract_all_text(data_dict)
            
            # Tokenize
            words = self.clean_and_tokenize(combined_text)
            
            # Update counts
            self.sentiment_counts[sentiment] += 1
            for word in words:
                self.word_counts[sentiment][word] += 1
                self.vocabulary.add(word)
        
        self.custom_trained = True
        print(f"Custom training complete. Vocabulary size: {len(self.vocabulary)}")
        print(f"Sentiment distribution: {dict(self.sentiment_counts)}")
    
    def predict_sentiment(self, data_dict: Dict) -> Dict[str, float]:
        """
        Predict sentiment using VADER and custom model if available
        Returns: (predicted_sentiment, confidence_scores)
        """
        # Extract post content (title + post)
        post_text = []
        if data_dict.get('post_title') and isinstance(data_dict['post_title'], str):
            post_text.append(data_dict['post_title'])
        if data_dict.get('post_content') and isinstance(data_dict['post_content'], str):
            post_text.append(data_dict['post_content'])
        post_text = ' '.join(post_text)
        
        # Extract comments
        comments = data_dict.get('comments', [])
        if isinstance(comments, list):
            comment_texts = [c for c in comments if isinstance(c, str)]
        elif isinstance(comments, str):
            try:
                parsed_comments = ast.literal_eval(comments)
                comment_texts = [c for c in parsed_comments if isinstance(c, str)]
            except:
                comment_texts = [comments] if comments else []
        else:
            comment_texts = []
        
        # Analyze post content
        post_vader = self.vader.polarity_scores(post_text)
        post_word_score = self._calculate_word_score(post_text)
        post_compound = (post_vader['compound'] * 0.7) + ((post_word_score - 50) / 50 * 0.3)
        
        # Analyze comments
        comment_scores = []
        for comment in comment_texts:
            comment_vader = self.vader.polarity_scores(comment)
            comment_word_score = self._calculate_word_score(comment)
            comment_compound = (comment_vader['compound'] * 0.7) + ((comment_word_score - 50) / 50 * 0.3)
            comment_scores.append(comment_compound)
        
        # Calculate average comment sentiment
        avg_comment_score = sum(comment_scores) / len(comment_scores) if comment_scores else 0
        
        # Determine post sentiment
        if post_compound >= self.positive_threshold:
            post_sentiment = 'positive'
        elif post_compound <= self.negative_threshold:
            post_sentiment = 'negative'
        else:
            post_sentiment = 'neutral'
            
        # Determine comment sentiment
        if avg_comment_score >= self.positive_threshold:
            comment_sentiment = 'positive'
        elif avg_comment_score <= self.negative_threshold:
            comment_sentiment = 'negative'
        else:
            comment_sentiment = 'neutral'
        
        # Calculate confidence scores
        confidence = {
            'post_sentiment': post_sentiment,
            'post_score': ((post_compound + 1) / 2) * 100,  # Convert to 0-100
            'post_word_score': post_word_score,
            'comment_sentiment': comment_sentiment,
            'comment_score': ((avg_comment_score + 1) / 2) * 100,  # Convert to 0-100
            'comment_word_scores': [((score + 1) / 2) * 100 for score in comment_scores],  # Convert each to 0-100
            'num_comments': len(comment_scores)
        }
        
        # Overall sentiment (weighted average of post and comments)
        if comment_scores:
            overall_score = (post_compound * 0.4) + (avg_comment_score * 0.6)  # 40% post, 60% comments
        else:
            overall_score = post_compound  # Just use post if no comments
            
        if overall_score >= self.positive_threshold:
            overall_sentiment = 'positive'
        elif overall_score <= self.negative_threshold:
            overall_sentiment = 'negative'
        else:
            overall_sentiment = 'neutral'
            
        confidence['overall_sentiment'] = overall_sentiment
        confidence['overall_score'] = ((overall_score + 1) / 2) * 100  # Convert to 0-100
        
        return confidence
    
    def analyze_reddit_data(self, reddit_data: List[Dict]) -> List[Dict]:
        """
        Analyze sentiment for a list of Reddit data dictionaries
        Returns list with sentiment predictions added
        """
        results = []
        
        for data_dict in reddit_data:
            sentiment = self.predict_sentiment(data_dict)
            
            result = data_dict.copy()
            result['predicted_sentiment'] = sentiment['post_sentiment']
            result['sentiment_confidence'] = sentiment
            result['confidence_score'] = sentiment[sentiment['post_sentiment']]
            result['word_score'] = sentiment['post_word_score']
            
            results.append(result)
        
        return results
    
    def save_training_data(self, filepath: str):
        """Save custom training data to CSV"""
        if not self.custom_training_data:
            print("No training data to save")
            return
        
        # Convert to DataFrame
        data = []
        for post_dict, sentiment in self.custom_training_data:
            row = post_dict.copy()
            row['sentiment_label'] = sentiment
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        print(f"Saved {len(data)} training examples to {filepath}")
    
    def load_training_data(self, filepath: str):
        """Load custom training data from CSV"""
        try:
            df = pd.read_csv(filepath)
            for _, row in df.iterrows():
                post_dict = row.to_dict()
                sentiment = post_dict.pop('sentiment_label')
                self.add_training_example(post_dict, sentiment)
            print(f"Loaded {len(df)} training examples from {filepath}")
            self.train_custom_model()
        except Exception as e:
            print(f"Error loading training data: {e}")