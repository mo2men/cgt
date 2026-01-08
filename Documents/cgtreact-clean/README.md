# UK RSU/ESPP CGT Calculator

A comprehensive web application for calculating Capital Gains Tax (CGT) on UK employment shares (RSUs and ESPPs). Features a full-stack setup with Flask backend and React frontend, all running in a single server.

## Features

### Core CGT Calculations
- **UK CGT Compliance**: Implements HMRC rules for employment shares, including Section 104 pooling, bed-and-breakfasting (30-day forward matching), and progressive tax rates.
- **Loss Carry-Forward**: Automatic application of previous year losses to reduce taxable gains.
- **Incidental Costs**: Support for adding transaction costs to acquisition or deducting from proceeds.
- **Exchange Rates**: Integrated BoE spot rates with fallback to year-based rates. Manual override available.

### Data Management
- **Transaction Entry**: Intuitive form-based entry for RSU vestings, ESPP purchases, and share sales.
- **Data Validation**: ESPP discount validation (≤15% for qualifying plans), date ordering, and required field checks.
- **Sorted Table View**: All transactions displayed in chronological order with detailed columns for efficient data entry.
- **CRUD Operations**: Full create, read, update, delete for all transaction types.

### Advanced Features
- **Audit Trail**: Detailed calculation steps, snapshots, and JSON traces for every disposal.
- **Tax Summary**: Year-by-year breakdown with progressive banding (basic 10%, higher 20%).
- **CSV Exports**: Download disposals, pool snapshots, and tax summaries for HMRC submission.
- **Exchange Rate Management**: Upload BoE CSV or add manual rates.

### Stock Analytics (Bonus)
- **Current Prices**: Fetch live USD/GBP stock prices via yfinance.
- **Price History**: Historical data with RSI and MACD indicators.
- **Predictions**: SMA, EMA, Linear Regression, and ARIMA forecasting.
- **Sell Optimization**: Simulate optimal sell dates with after-tax profit calculations.

### User Interface
- **Single-Page App**: React frontend with Material-UI components.
- **Responsive Design**: Works on desktop and mobile.
- **Real-Time Updates**: Auto-recalculation on data changes.
- **Tooltips & Guidance**: HMRC links and warnings for accurate tax planning.

## Implemented Fixes from Review

- **CGT Rate Bands**: Progressive rates based on non-savings income.
- **Bed-and-Breakfasting**: 30-day forward matching implemented.
- **Incidental Costs**: Added to all transaction types.
- **ESPP Handling**: Auto-discount calculation with 15% validation.
- **Loss Carry-Forward**: Integrated into calculations.
- **User Guidance**: Tooltips with HMRC references.
- **Testing**: Expanded pytest and Jest coverage.

## Disclaimers and Limitations

- **ESPP Handling**: Assumes qualifying plans; consult HMRC for non-qualifying.
- **Assumptions**: Full UK residency, no split-year or special reliefs. Suitable for RSU/ESPP only.
- **Estimates**: 2024/25 tax rules; monitor Budget changes. FX from BoE.
- **Not Advice**: Tool for SA108 prep; consult tax advisor for professional guidance.
- **Record-Keeping**: Retain exports per HMRC TM2000.

## Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- SQLite (built-in)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/mo2men/cgt.git
   cd cgt
   ```

2. Install Python dependencies:
   ```bash
   pip install flask sqlalchemy flask-sqlalchemy flask-cors requests yfinance numpy pandas scipy statsmodels selenium webdriver-manager
   ```

3. Install Node dependencies:
   ```bash
   npm install
   ```

### Running the Application
1. Start the backend:
   ```bash
   python app.py
   ```

2. In another terminal, start the frontend dev server (optional for dev):
   ```bash
   npm start
   ```

3. Open http://localhost:5000 in your browser.

### Production Build
1. Build the React app:
   ```bash
   npm run build
   ```

2. The Flask server serves the built app from the `/` route.

### Testing
- Backend: `pytest`
- Frontend: `npm test`

## Usage

1. **Editor Page** (`/editor`): Add/edit transactions, manage exchange rates.
2. **Dashboard** (`/`): View calculations, summaries, and analytics.
3. **Audit Page** (`/audit`): Detailed disposal traces and steps.
4. **Stock Tab**: Analyze current stock with predictions and optimization.

## API Endpoints

- `GET /api/transactions` - Paginated disposal list
- `POST /api/recalc` - Trigger full recalculation
- `GET /api/summary/<year>` - Tax year summary
- `GET /api/stock/current` - Live stock prices
- `GET /api/stock/predict` - Price predictions

## Contributing

1. Fork and clone.
2. Create feature branch.
3. Make changes, add tests.
4. Submit PR.

## License

MIT License - see LICENSE file.
