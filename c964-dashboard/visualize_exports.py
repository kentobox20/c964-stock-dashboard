import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Load data
sentiment_df = pd.read_json('docs/data/sentiment_over_time.json')
mentions_df = pd.read_json('docs/data/mentions_over_time.json')
engagement_df = pd.read_json('docs/data/engagement_by_ticker.json')

# 1. Sentiment over time (line plot, one line per ticker)
fig1 = px.line(
    sentiment_df,
    x='date',
    y='avg_overall_score',
    color='ticker',
    title='Sentiment Over Time by Ticker',
    markers=True
)
fig1.show()
fig1.write_html('sentiment_over_time.html')

# 2. Mentions over time (line plot, one line per ticker)
fig2 = px.line(
    mentions_df,
    x='date',
    y='mention_count',
    color='ticker',
    title='Mentions Over Time by Ticker',
    markers=True
)
fig2.show()
fig2.write_html('mentions_over_time.html')

# 3. Engagement by ticker (bar chart)
fig3 = px.bar(
    engagement_df,
    x='ticker',
    y='mention_count',
    color='avg_overall_score',
    title='Engagement by Ticker (Latest Date)',
    hover_data=['total_comments', 'avg_overall_score']
)
fig3.show()
fig3.write_html('engagement_by_ticker.html') 