# 🚀 RobinhoodBot - SPY Options Tracker

A powerful automated SPY options tracking and analysis tool with real-time data collection, database storage, and live charting.

## ✨ Features

- **Real-time Data Collection** - Automatically extracts SPY options data from Robinhood
- **Database Storage** - SQLite database for persistent data storage
- **Live Charting** - 6 real-time charts showing price, volume, bid/ask, theta, gamma, and high/low
- **Expanded Contract Tracking** - Keeps contracts in expanded state for continuous monitoring
- **GUI Interface** - Clean, dark-themed interface with live updates
- **Browser Integration** - Connects to existing Chrome sessions for seamless operation

## 🎯 Quick Start

### Prerequisites
- Python 3.13+
- Chrome browser
- Robinhood account

### Installation
```bash
# Clone the repository
git clone https://github.com/StuartGrossman/robinhoodtrader.git
cd robinhoodtrader

# Install dependencies
pip install -r requirements.txt

# Start Chrome with remote debugging
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
--remote-debugging-port=9222 --user-data-dir=$HOME/chrome_robinhood
```

### Usage
```bash
# Run the main application
python main.py
```

1. **Log into Robinhood** in the Chrome window that opens
2. **Choose option type** (CALLS, PUTS, or Both)
3. **Watch the magic happen** - The app will automatically:
   - Find SPY options contracts
   - Expand them for detailed data
   - Start continuous monitoring
   - Display live charts and data

## 📊 What You'll See

### Main Interface
- **Analysis Log** - Real-time updates of data extraction
- **Contract Tabs** - Individual tabs for each tracked contract
- **Live Charts** - 6 different charts showing various metrics

### Data Collected
- **Price Data** - Current price, bid, ask, high, low
- **Volume** - Trading volume and open interest
- **Greeks** - Theta, gamma, delta, vega
- **Timestamps** - All data points timestamped

### Charts Available
1. **Price Over Time** - Premium price trends
2. **Volume** - Trading volume analysis
3. **Bid/Ask Spread** - Spread analysis
4. **Theta Decay** - Time decay visualization
5. **Gamma** - Gamma sensitivity
6. **Daily High/Low** - Price range analysis

## 🗂️ Project Structure

```
RobinhoodBot/
├── main.py                 # 🎯 Main application
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── data/                  # Database and data files
│   └── options_data.db   # SQLite database
├── screenshots/           # Screenshot storage
├── src/                   # Source code modules
├── tests/                 # Test files
│   └── old_tests/        # Legacy test files
├── legacy_gui/           # Old GUI implementations
└── docs/                 # Documentation
```

## 🔧 Configuration

### Database
- **Location**: `data/options_data.db`
- **Tables**: `contracts`, `data_points`
- **Auto-backup**: Data persists between sessions

### Screenshots
- **Location**: `screenshots/`
- **Format**: `expanded_{contract}_live_{timestamp}_{count}.png`
- **Frequency**: Every 1 second during monitoring

## 📈 Data Flow

1. **Browser Connection** → Connects to existing Chrome session
2. **Page Navigation** → Finds Robinhood SPY options page
3. **Contract Discovery** → Locates target contracts (8¢-16¢)
4. **Expansion** → Expands contracts for detailed view
5. **Data Extraction** → Extracts price, volume, Greeks
6. **Database Storage** → Saves to SQLite database
7. **Chart Updates** → Updates live charts in GUI
8. **Continuous Monitoring** → Repeats every 1 second

## 🛠️ Development

### Key Files
- `main.py` - Main application with GUI and monitoring
- `src/` - Core modules for browser automation and data extraction
- `tests/` - Test files for validation

### Adding Features
1. **Data Extraction** - Modify `extract_expanded_contract_data()`
2. **Chart Types** - Add new charts in `create_live_charts()`
3. **Database Schema** - Update `DatabaseManager` class
4. **GUI Elements** - Modify `setup_gui()` and related functions

## 🐛 Troubleshooting

### Common Issues
- **Browser Connection**: Make sure Chrome is running with remote debugging
- **Login Required**: Log into Robinhood in the Chrome window first
- **No Data**: Check if contracts are being found and expanded
- **Chart Issues**: Verify database is being populated

### Debug Mode
- Check the analysis log for detailed error messages
- Look for database entries in `data/options_data.db`
- Review screenshots in `screenshots/` directory

## 📝 License

This project is for educational and personal use only. Please comply with Robinhood's terms of service.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Happy Trading! 📈**
