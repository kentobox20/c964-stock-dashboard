// Global variables to store data
let sentimentData = null;
let mentionsData = null;
let engagementData = null;
let selectedTicker = null;
let globalDates = [];
let tickerColors = {};
let stockPricesCache = {}; // Cache for stock prices to avoid repeated API calls

// Global state
let allData = [];
const API_KEY = '6SZERRM8P37D447V'; // Replace with your new Alpha Vantage API key

// Load data when the page loads
document.addEventListener('DOMContentLoaded', async function() {
    try {
        // Load all JSON files
        sentimentData = await fetch('data/sentiment_over_time.json').then(r => r.json());
        mentionsData = await fetch('data/mentions_over_time.json').then(r => r.json());
        engagementData = await fetch('data/engagement_by_ticker.json').then(r => r.json());

        // Initialize filters
        initializeFilters();
        
        // Create initial plots
        createSentimentPlot();
        createMentionsPlot();
        createEngagementPlot();
    } catch (error) {
        console.error('Error loading data:', error);
    }
});


// Initialize filters
function initializeFilters() {
    globalDates = [...new Set(sentimentData.map(d => d.date))].sort();
    const tickers = [...new Set(sentimentData.map(d => d.ticker).concat(mentionsData.map(d => d.ticker)))].sort();

    // Assign colors to tickers
    const colors = getColorPalette(tickers.length);
    tickerColors = {};
    tickers.forEach((ticker, i) => {
        tickerColors[ticker] = colors[i];
    });

    // Debug logging for slider initialization
    console.log('globalDates:', globalDates);
    console.log('Slider start:', [0, globalDates.length - 1]);
    
    const dateRange = document.getElementById('dateRange');
    const label = document.getElementById('dateRangeLabel');
    
    if (globalDates.length < 2) {
        // Only one unique date, disable slider and show message
        dateRange.setAttribute('disabled', 'true');
        if (label) label.textContent = `${globalDates[0]} (only one date available)`;
    } else {
        // Clear any existing slider first
        if (dateRange.noUiSlider) {
            dateRange.noUiSlider.destroy();
        }
        
        // Enable slider and initialize as range
        dateRange.removeAttribute('disabled');
        
        const maxIndex = globalDates.length - 1;
        
        noUiSlider.create(dateRange, {
            start: [0, maxIndex], // Start with full range
            connect: true,
            range: {
                'min': 0,
                'max': maxIndex
            },
            step: 1,
            tooltips: false // Disable tooltips for now to avoid conflicts
        });
        
        // Force set to full range after a brief delay to ensure DOM is ready
        setTimeout(() => {
            console.log('Setting slider to full range:', [0, maxIndex]);
            dateRange.noUiSlider.set([0, maxIndex]);
            // Set label to full range
            if (label) {
                label.textContent = `${globalDates[0]} - ${globalDates[maxIndex]}`;
            }
            console.log('Slider set to:', [0, maxIndex]);
            console.log('Current slider values after set:', dateRange.noUiSlider.get());
            
            // Force trigger update to ensure plots are created with full range
            updatePlots();
        }, 200);
        
        // Add event listener that converts slider values to dates
        dateRange.noUiSlider.on('update', function(values) {
            // Convert numeric indices to date strings
            const startIndex = Math.round(parseFloat(values[0]));
            const endIndex = Math.round(parseFloat(values[1]));
            const dateValues = [globalDates[startIndex], globalDates[endIndex]];
            console.log('Slider updated - indices:', [startIndex, endIndex], 'dates:', dateValues);
            updateDateRangeLabel(dateValues);
            updatePlots();
        });
    }

    // Initialize ticker select with Select2
    const tickerSelect = $('#tickerSelect');
    tickers.forEach((ticker) => {
        tickerSelect.append(new Option(ticker, ticker));
    });
    tickerSelect.select2({
        placeholder: 'Select tickers...',
        allowClear: true
    });
    tickerSelect.on('change', updatePlots);
    
    // Initial stock price update
    updateStockPrices();
}

// Updated filter data function to handle slider values properly
function filterData(data, aggregate = false) {
    const dateRange = document.getElementById('dateRange');
    let dateRangeValues;
    
    if (dateRange.noUiSlider) {
        const sliderValues = dateRange.noUiSlider.get();
        // Convert slider indices to actual dates
        const startIndex = Math.round(parseFloat(sliderValues[0]));
        const endIndex = Math.round(parseFloat(sliderValues[1]));
        dateRangeValues = [globalDates[startIndex], globalDates[endIndex]];
        console.log('Filter data - slider values:', sliderValues, 'converted to dates:', dateRangeValues);
    } else {
        // Fallback to full range if slider not initialized
        dateRangeValues = [globalDates[0], globalDates[globalDates.length - 1]];
    }
    
    const selectedTickers = $('#tickerSelect').val() || [];
    
    let filtered = data.filter(d => {
        // For engagementData, some rows may not have a date field (legacy), so include them
        const dateMatch = !d.date || (d.date >= dateRangeValues[0] && d.date <= dateRangeValues[1]);
        const tickerMatch = selectedTickers.length === 0 || selectedTickers.includes(d.ticker);
        return dateMatch && tickerMatch;
    });

    if (aggregate && filtered.length > 0) {
        // Aggregate by ticker: sum mention_count, avg avg_overall_score
        const agg = {};
        filtered.forEach(d => {
            if (!agg[d.ticker]) {
                agg[d.ticker] = {
                    ticker: d.ticker,
                    mention_count: 0,
                    avg_overall_score_sum: 0,
                    avg_overall_score_count: 0
                };
            }
            agg[d.ticker].mention_count += d.mention_count || 0;
            if (d.avg_overall_score !== undefined && d.avg_overall_score !== null) {
                agg[d.ticker].avg_overall_score_sum += d.avg_overall_score;
                agg[d.ticker].avg_overall_score_count += 1;
            }
        });
        // Convert to array and compute average
        return Object.values(agg).map(d => ({
            ticker: d.ticker,
            mention_count: d.mention_count,
            avg_overall_score: d.avg_overall_score_count > 0 ? d.avg_overall_score_sum / d.avg_overall_score_count : null
        }));
    }
    return filtered;
}

// Updated engagement plot function
function createEngagementPlot() {
    const dateRange = document.getElementById('dateRange');
    let dateRangeValues;
    
    if (dateRange.noUiSlider) {
        const sliderValues = dateRange.noUiSlider.get();
        // Convert slider indices to actual dates
        const startIndex = Math.round(parseFloat(sliderValues[0]));
        const endIndex = Math.round(parseFloat(sliderValues[1]));
        dateRangeValues = [globalDates[startIndex], globalDates[endIndex]];
    } else {
        // Fallback to full range if slider not initialized
        dateRangeValues = [globalDates[0], globalDates[globalDates.length - 1]];
    }
    
    const selectedTickers = $('#tickerSelect').val() || [];

    // Format date range for title (M/D - M/D) using the exact strings
    function formatShort(dateStr) {
        const [year, month, day] = dateStr.split('-');
        return `${parseInt(month)}/${parseInt(day)}`;
    }
    const dateRangeStr = `(${formatShort(dateRangeValues[0])} - ${formatShort(dateRangeValues[1])})`;

    // Filter mentions and sentiment data by date range and tickers
    let filteredMentions = mentionsData.filter(d => d.date >= dateRangeValues[0] && d.date <= dateRangeValues[1]);
    let filteredSentiment = sentimentData.filter(d => d.date >= dateRangeValues[0] && d.date <= dateRangeValues[1]);
    if (selectedTickers.length > 0) {
        filteredMentions = filteredMentions.filter(d => selectedTickers.includes(d.ticker));
        filteredSentiment = filteredSentiment.filter(d => selectedTickers.includes(d.ticker));
    }

    // Build a set of all tickers present in either dataset
    const tickersSet = new Set([
        ...filteredMentions.map(d => d.ticker),
        ...filteredSentiment.map(d => d.ticker)
    ]);
    let tickers = Array.from(tickersSet);

    // Aggregate by ticker
    let aggArr = tickers.map(ticker => {
        // Sum mentions
        const tickerMentions = filteredMentions.filter(d => d.ticker === ticker);
        const mention_count = tickerMentions.reduce((sum, d) => sum + (d.mention_count || 0), 0);
        // Average sentiment
        const tickerSentiments = filteredSentiment.filter(d => d.ticker === ticker && d.avg_overall_score !== undefined && d.avg_overall_score !== null);
        const avg_overall_score = tickerSentiments.length > 0 ? tickerSentiments.reduce((sum, d) => sum + d.avg_overall_score, 0) / tickerSentiments.length : null;
        return {
            ticker,
            mention_count,
            avg_overall_score
        };
    });
    // Sort by mention_count descending
    aggArr = aggArr.sort((a, b) => b.mention_count - a.mention_count);

    const trace = {
        x: aggArr.map(d => d.ticker),
        y: aggArr.map(d => d.mention_count),
        type: 'bar',
        marker: {
            color: aggArr.map(d => tickerColors[d.ticker] || undefined),
        },
        text: aggArr.map(d => `Score: ${d.avg_overall_score ? d.avg_overall_score.toFixed(2) : 'N/A'}`),
        hoverinfo: 'text'
    };

    const layout = {
        title: `Engagement by Ticker ${dateRangeStr}`,
        xaxis: { title: 'Ticker' },
        yaxis: { title: 'Number of Mentions' },
        hovermode: 'closest',
        showlegend: false
    };

    const config = {
        responsive: true,
        displayModeBar: false
    };

    Plotly.newPlot('engagementPlot', [trace], layout, config);
}

function updateDateRangeLabel(values) {
    const label = document.getElementById('dateRangeLabel');
    if (label) {
        label.textContent = `${values[0]} - ${values[1]}`;
    }
}

// Helper to generate a color palette
function getColorPalette(n) {
    // Use Plotly's default qualitative palette
    const palette = [
        '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A',
        '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52',
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ];
    // Repeat if more tickers than palette
    let colors = [];
    for (let i = 0; i < n; i++) {
        colors.push(palette[i % palette.length]);
    }
    return colors;
}

// Create sentiment plot
function createSentimentPlot() {
    const filteredData = filterData(sentimentData);
    
    const traces = [];
    const tickers = [...new Set(filteredData.map(d => d.ticker))];

    // Get the full date range in order
    const dateRange = document.getElementById('dateRange');
    let dateRangeValues;
    if (dateRange.noUiSlider) {
        const sliderValues = dateRange.noUiSlider.get();
        const startIndex = Math.round(parseFloat(sliderValues[0]));
        const endIndex = Math.round(parseFloat(sliderValues[1]));
        dateRangeValues = [globalDates[startIndex], globalDates[endIndex]];
    } else {
        dateRangeValues = [globalDates[0], globalDates[globalDates.length - 1]];
    }
    // Build the full list of dates in the selected range
    const allDates = globalDates.filter(date => date >= dateRangeValues[0] && date <= dateRangeValues[1]);

    tickers.forEach(ticker => {
        // Map date to avg_overall_score for this ticker
        const tickerData = filteredData.filter(d => d.ticker === ticker);
        const dateToScore = {};
        tickerData.forEach(d => {
            dateToScore[d.date] = d.avg_overall_score;
        });
        // Fill in all dates, use null if missing
        const yValues = allDates.map(date => dateToScore[date] !== undefined ? dateToScore[date] : null);
        traces.push({
            x: allDates,
            y: yValues,
            name: ticker,
            type: 'scatter',
            mode: 'lines+markers',
            line: {
                width: ticker === selectedTicker ? 4 : 1,
                color: tickerColors[ticker] || undefined
            },
            marker: {
                size: ticker === selectedTicker ? 10 : 6,
                color: tickerColors[ticker] || undefined
            }
        });
    });

    const layout = {
        title: 'Sentiment Over Time by Ticker',
        xaxis: { title: 'Date', tickformat: '%Y-%m-%d', type: 'category' },
        yaxis: { title: 'Average Sentiment Score' },
        hovermode: 'closest',
        showlegend: true
    };

    const config = {
        responsive: true,
        displayModeBar: false
    };

    Plotly.newPlot('sentimentPlot', traces, layout, config);
}

// Create mentions plot
function createMentionsPlot() {
    const filteredData = filterData(mentionsData);
    
    const traces = [];
    const tickers = [...new Set(filteredData.map(d => d.ticker))];

    // Get the full date range in order
    const dateRange = document.getElementById('dateRange');
    let dateRangeValues;
    if (dateRange.noUiSlider) {
        const sliderValues = dateRange.noUiSlider.get();
        const startIndex = Math.round(parseFloat(sliderValues[0]));
        const endIndex = Math.round(parseFloat(sliderValues[1]));
        dateRangeValues = [globalDates[startIndex], globalDates[endIndex]];
    } else {
        dateRangeValues = [globalDates[0], globalDates[globalDates.length - 1]];
    }
    // Build the full list of dates in the selected range
    const allDates = globalDates.filter(date => date >= dateRangeValues[0] && date <= dateRangeValues[1]);

    tickers.forEach(ticker => {
        // Map date to mention_count for this ticker
        const tickerData = filteredData.filter(d => d.ticker === ticker);
        const dateToMentions = {};
        tickerData.forEach(d => {
            dateToMentions[d.date] = d.mention_count;
        });
        // Fill in all dates, use 0 if missing
        const yValues = allDates.map(date => dateToMentions[date] !== undefined ? dateToMentions[date] : 0);
        traces.push({
            x: allDates,
            y: yValues,
            name: ticker,
            type: 'scatter',
            mode: 'lines+markers',
            line: {
                width: ticker === selectedTicker ? 4 : 1,
                color: tickerColors[ticker] || undefined
            },
            marker: {
                size: ticker === selectedTicker ? 10 : 6,
                color: tickerColors[ticker] || undefined
            }
        });
    });

    const layout = {
        title: 'Mentions Over Time by Ticker',
        xaxis: { title: 'Date', tickformat: '%Y-%m-%d', type: 'category' },
        yaxis: { title: 'Number of Mentions' },
        hovermode: 'closest',
        showlegend: true
    };

    const config = {
        responsive: true,
        displayModeBar: false
    };

    Plotly.newPlot('mentionsPlot', traces, layout, config);
}



// Update all plots when filters change
function updatePlots() {
    // Update stock prices first to ensure they always load
    updateStockPrices();

    // Update the date range label as well
    const dateRangeSlider = document.getElementById('dateRange').noUiSlider.get();
    const startIndex = Math.round(parseFloat(dateRangeSlider[0]));
    const endIndex = Math.round(parseFloat(dateRangeSlider[1]));
    const dateValues = [globalDates[startIndex], globalDates[endIndex]];
    updateDateRangeLabel(dateValues);
    createSentimentPlot();
    createMentionsPlot();
    createEngagementPlot();
}

// Quick filter functions
function filterTopMentions(n) {
    const topTickers = [...new Set(mentionsData.map(d => d.ticker))]
        .map(ticker => ({
            ticker,
            totalMentions: mentionsData
                .filter(d => d.ticker === ticker)
                .reduce((sum, d) => sum + d.mention_count, 0)
        }))
        .sort((a, b) => b.totalMentions - a.totalMentions)
        .slice(0, n)
        .map(d => d.ticker);
    
    $('#tickerSelect').val(topTickers).trigger('change');
}

function filterTopSentiment(n) {
    const topTickers = [...new Set(sentimentData.map(d => d.ticker))]
        .map(ticker => ({
            ticker,
            avgSentiment: sentimentData
                .filter(d => d.ticker === ticker)
                .reduce((sum, d) => sum + d.avg_overall_score, 0) / 
                sentimentData.filter(d => d.ticker === ticker).length
        }))
        .sort((a, b) => b.avgSentiment - a.avgSentiment)
        .slice(0, n)
        .map(d => d.ticker);
    
    $('#tickerSelect').val(topTickers).trigger('change');
}

function resetFilters() {
    const dateRange = document.getElementById('dateRange');
    dateRange.noUiSlider.set([0, globalDates.length - 1]);
    $('#tickerSelect').val(null).trigger('change');
    selectedTicker = null;
    updatePlots();
}

// Add click event listeners to plots
const sentimentPlot = document.getElementById('sentimentPlot');
if (sentimentPlot) {
    sentimentPlot.addEventListener('plotly_click', function(data) {
        const ticker = data.points[0].data.name;
        selectedTicker = selectedTicker === ticker ? null : ticker;
        updatePlots();
    });
}

const mentionsPlot = document.getElementById('mentionsPlot');
if (mentionsPlot) {
    mentionsPlot.addEventListener('plotly_click', function(data) {
        const ticker = data.points[0].data.name;
        selectedTicker = selectedTicker === ticker ? null : ticker;
        updatePlots();
    });
}

const engagementPlot = document.getElementById('engagementPlot');
if (engagementPlot) {
    engagementPlot.addEventListener('plotly_click', function(data) {
        const ticker = data.points[0].x;
        selectedTicker = selectedTicker === ticker ? null : ticker;
        updatePlots();
    });
}

// Stock Price Functions
async function fetchStockPrice(ticker) {
    try {
        // Use Alpha Vantage API with your personal key from config.js
        const response = await fetch(`https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=${ticker}&apikey=${API_KEY}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Log the raw data to the console for validation
        console.log(`Data for ${ticker} from Alpha Vantage:`, data);
        
        // Handle API rate limit error
        if (data["Note"]) {
            throw new Error('API rate limit reached.');
        }

        if (data['Global Quote']) {
            const quote = data['Global Quote'];
            const currentPrice = parseFloat(quote['05. price']);
            const previousClose = parseFloat(quote['08. previous close']);
            const change = parseFloat(quote['09. change']);
            const changePercent = parseFloat(quote['10. change percent'].replace('%', ''));
            
            return {
                ticker: ticker,
                price: currentPrice,
                change: change,
                changePercent: changePercent,
                timestamp: new Date().toISOString()
            };
        } else {
            throw new Error('No quote data available');
        }
    } catch (error) {
        console.error(`Error fetching stock price for ${ticker}:`, error);
        return {
            ticker: ticker,
            price: null,
            change: null,
            changePercent: null,
            error: error.message,
            timestamp: new Date().toISOString()
        };
    }
}

async function updateStockPrices() {
    const selectedTickers = $('#tickerSelect').val() || [];
    const container = document.getElementById('stockTickerBar');
    
    if (selectedTickers.length === 0) {
        container.innerHTML = '<div class="ticker-item">Select tickers to see current stock prices</div>';
        return;
    }
    
    // Show loading state
    container.innerHTML = `
        <div class="stock-loading" style="padding: 0 2rem;">
            <div class="spinner"></div>
            <span style="margin-left: 8px;">Loading stock prices...</span>
        </div>
    `;
    
    try {
        // Check cache first for all tickers
        const tickersToFetch = [];
        const cachedResults = [];
        
        for (const ticker of selectedTickers) {
            const cached = stockPricesCache[ticker];
            if (cached && (new Date() - new Date(cached.timestamp)) < 5 * 60 * 1000) {
                cachedResults.push(cached);
            } else {
                tickersToFetch.push(ticker);
            }
        }
        
        let fetchedResults = [];
        if (tickersToFetch.length > 0) {
            // Fetch prices for uncached tickers (Alpha Vantage requires individual calls)
            const pricePromises = tickersToFetch.map(async (ticker) => {
                const priceData = await fetchStockPrice(ticker);
                stockPricesCache[ticker] = priceData;
                return priceData;
            });
            
            fetchedResults = await Promise.all(pricePromises);
        }
        
        // Combine cached and fetched results
        const allResults = [...cachedResults, ...fetchedResults];
        
        // Display the results
        displayStockPrices(allResults);
        
    } catch (error) {
        console.error('Error updating stock prices:', error);
        container.innerHTML = '<div class="ticker-item text-danger">Error loading stock prices.</div>';
    }
}

function displayStockPrices(priceData) {
    const container = document.getElementById('stockTickerBar');
    const wrap = container.parentElement;

    // Reset styles and clear content
    container.innerHTML = '';
    wrap.style.justifyContent = 'flex-start';
    container.style.animation = '';

    if (priceData.length === 0) {
        container.innerHTML = '<div class="ticker-item">No tickers selected</div>';
        wrap.style.justifyContent = 'center';
        return;
    }
    
    const itemsHTML = priceData.map(data => {
        let item;
        if (data.error || !data.price) {
            let errorMessage = "Error";
            if (data.error.includes('API rate limit')) {
                errorMessage = "API Limit";
            }
            item = `
                <div class="ticker-item">
                    <span class="ticker-symbol">${data.ticker}</span>
                    <span class="ticker-price" style="color: #dc3545;">${errorMessage}</span>
                </div>
            `;
        } else {
            const changeClass = data.change > 0 ? 'positive' : data.change < 0 ? 'negative' : 'neutral';
            const changeSymbol = data.change > 0 ? '▲' : data.change < 0 ? '▼' : '–';
            
            item = `
                <div class="ticker-item">
                    <span class="ticker-symbol">${data.ticker}</span>
                    <span class="ticker-price">$${data.price.toFixed(2)}</span>
                    <span class="ticker-change ${changeClass}">
                        ${changeSymbol} ${Math.abs(data.change).toFixed(2)} (${data.changePercent.toFixed(2)}%)
                    </span>
                </div>
            `;
        }
        return item;
    }).join('');

    // Create a content block
    const contentBlock1 = document.createElement('div');
    contentBlock1.className = 'ticker__content';
    contentBlock1.innerHTML = itemsHTML;
    container.appendChild(contentBlock1);

    // Use requestAnimationFrame to measure after rendering
    requestAnimationFrame(() => {
        const wrapWidth = wrap.offsetWidth;
        const contentWidth = contentBlock1.offsetWidth;

        if (contentWidth > wrapWidth) {
            // If content overflows, duplicate it and start animation
            const contentBlock2 = document.createElement('div');
            contentBlock2.className = 'ticker__content';
            contentBlock2.innerHTML = itemsHTML;
            container.appendChild(contentBlock2);

            // Calculate a dynamic duration for consistent speed
            const scrollSpeed = 80; // pixels per second
            const duration = contentWidth / scrollSpeed;
            container.style.animation = `ticker-scroll ${duration}s linear infinite`;
        } else {
            // If content fits, just center it with no animation
            wrap.style.justifyContent = 'center';
        }
    });
} 