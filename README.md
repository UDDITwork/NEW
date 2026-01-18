# Chemical Saver - Dosage Optimization App

A Corva Dev Center application that ingests real-time oil/water production data, calculates optimal chemical injection rates, and visualizes financial savings vs. waste.

## Project Structure

```
chemical-saver/
├── manifest.json              # Corva app configuration
├── backend/
│   ├── lambda_function.py     # Python serverless backend
│   └── requirements.txt       # Python dependencies
├── schemas/
│   ├── settings_schema.json   # Well settings JSON schema
│   └── results_schema.json    # Optimization results schema
└── ui/
    ├── package.json           # Node.js dependencies
    └── src/
        ├── App.js             # Main React application
        ├── components/
        │   ├── Dashboard.js   # Dashboard tab component
        │   ├── Settings.js    # Settings tab component
        │   ├── DualLineChart.js
        │   ├── KPICard.js
        │   └── StatusIndicator.js
        ├── hooks/
        │   └── useCorvaData.js # Corva data hooks
        ├── utils/
        │   ├── constants.js   # App constants
        │   ├── formatters.js  # Formatting utilities
        │   └── validators.js  # Validation utilities
        └── styles/            # CSS stylesheets
```

## Features

### Dashboard Tab
- **KPI Cards**: Current Waste, Corrosion Risk, Current PPM, Cumulative Savings
- **Time Series Chart**: Dual-line chart showing Actual (Red) vs Recommended (Green) injection rates
- **Status Indicator**: Real-time dosing status (OPTIMAL, OVER_DOSING, UNDER_DOSING, PUMP_OFF)

### Settings Tab
- Configure target PPM, chemical density, active intensity
- Set cost per gallon for financial calculations
- Define pump rate constraints (min/max)
- Unit toggle (Gallons/Liters)

## Core Algorithm

### Optimization Logic

1. **Data Validation**: Check flow rate > 0, validate water cut (0-100)
2. **Water Volume**: `Water_BPD = Gross_Fluid_Rate × (Water_Cut / 100)`
3. **Chemical Calculation**:
   - Convert water to mass (350 lbs/bbl)
   - Calculate pure chemical mass: `Mass = Water_Mass × (Target_PPM / 1,000,000)`
   - Adjust for intensity: `Gross_Mass = Mass / (Active_Intensity / 100)`
   - Convert to gallons using chemical density
4. **Apply Constraints**: Enforce min/max pump rates
5. **Financial Impact**: `Daily_Waste = (Actual - Recommended) × Cost_Per_Gallon`

### Safety Features

- **Null Case**: No recommendation output if data stream drops for 5+ minutes
- **Spike Filter**: Ignores 500%+ flow rate changes in 1 minute (sensor error)
- **Default Settings**: Falls back to Target PPM: 200, Cost: $10/gal

## Data Schemas

### Input (production.fluids)
| Field | Type | Unit | Description |
|-------|------|------|-------------|
| timestamp | Unix | Seconds | Data recording time |
| gross_fluid_rate | Float | BPD | Total liquid rate |
| water_cut | Float | % | Water percentage |
| current_injection_rate | Float | GPD | Current pump rate |

### Settings (chemical.saver.settings)
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| target_ppm | Integer | 200 | Required concentration |
| chemical_density | Float | 1.0 | kg/L |
| active_intensity | Float | 100 | % active ingredient |
| cost_per_gallon | Float | 25.00 | USD |
| min_pump_rate | Float | 0.5 | GPD minimum |
| max_pump_rate | Float | 50.0 | GPD maximum |

### Output (chemical.optimization.results)
| Field | Type | Description |
|-------|------|-------------|
| timestamp | Unix | Matches input time |
| recommended_rate_gpd | Float | Optimal setpoint |
| actual_rate_gpd | Float | Current rate |
| savings_opportunity_usd | Float | Daily waste/savings |
| status_flag | String | OPTIMAL/OVER_DOSING/UNDER_DOSING/PUMP_OFF |

## Deployment

### Backend
```bash
cd backend
pip install -r requirements.txt
# Deploy via Corva Dev Center CLI
corva deploy
```

### Frontend
```bash
cd ui
npm install
npm run build
# Build artifacts are deployed with the backend
```

## Development

### Local Testing (Backend)
```python
python lambda_function.py
```

### Local Testing (Frontend)
```bash
cd ui
npm start
```

## License

Proprietary - For use with Corva Dev Center only.
