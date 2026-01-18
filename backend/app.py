"""
Chemical Saver - Production Flask API for Cloud Run
Developer: PRABHAT
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS

from backend.lambda_function import (
    ChemicalOptimizer,
    WellSettings,
    ProductionData,
    DefaultSettings
)

app = Flask(__name__)
CORS(app)

# In-memory settings storage (replace with database in production)
settings_store = {}


@app.route('/', methods=['GET'])
def home():
    """Home page with API documentation."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chemical Saver API</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #2e7d32; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 8px; }
            code { background: #e0e0e0; padding: 2px 6px; border-radius: 4px; }
            .method { color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
            .get { background: #4caf50; }
            .post { background: #2196f3; }
            .demo-btn { background: #ff9800; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .demo-btn:hover { background: #f57c00; }
        </style>
    </head>
    <body>
        <h1>🧪 Chemical Saver API</h1>
        <p>Dosage Optimization for Oil & Gas Production</p>

        <p><a href="/demo"><button class="demo-btn">🚀 Try Live Demo</button></a></p>

        <h2>API Endpoints</h2>

        <div class="endpoint">
            <span class="method get">GET</span> <code>/health</code>
            <p>Health check endpoint</p>
        </div>

        <div class="endpoint">
            <span class="method post">POST</span> <code>/api/optimize</code>
            <p>Calculate optimal chemical injection rate</p>
            <pre>{
  "asset_id": "well123",
  "gross_fluid_rate": 1000,
  "water_cut": 80,
  "current_injection_rate": 5.0
}</pre>
        </div>

        <div class="endpoint">
            <span class="method post">POST</span> <code>/api/batch</code>
            <p>Batch optimization for multiple records</p>
        </div>

        <div class="endpoint">
            <span class="method get">GET</span> <code>/api/settings/{asset_id}</code>
            <p>Get settings for an asset</p>
        </div>

        <div class="endpoint">
            <span class="method post">POST</span> <code>/api/settings/{asset_id}</code>
            <p>Save settings for an asset</p>
        </div>

        <p><strong>Developer:</strong> PRABHAT</p>
    </body>
    </html>
    ''', 200


@app.route('/demo', methods=['GET'])
def demo():
    """Interactive demo page - Easy to use for everyone."""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chemical Saver - Live Demo</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #333; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        .badge { background: #4caf50; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; }

        /* KPI Cards */
        .kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .kpi-card { background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #9e9e9e; }
        .kpi-card.error { border-left-color: #f44336; }
        .kpi-card.warning { border-left-color: #ff9800; }
        .kpi-card.success { border-left-color: #4caf50; }
        .kpi-card.info { border-left-color: #2196f3; }
        .kpi-title { font-size: 12px; color: #666; text-transform: uppercase; margin-bottom: 8px; }
        .kpi-value { font-size: 28px; font-weight: 700; }
        .kpi-card.error .kpi-value { color: #f44336; }
        .kpi-card.warning .kpi-value { color: #ff9800; }
        .kpi-card.success .kpi-value { color: #4caf50; }
        .kpi-card.info .kpi-value { color: #2196f3; }
        .kpi-subtitle { font-size: 12px; color: #999; margin-top: 4px; }

        /* Status */
        .status-indicator { text-align: center; padding: 16px; margin-bottom: 24px; }
        .status-chip { display: inline-block; padding: 12px 32px; border-radius: 25px; font-weight: 600; font-size: 16px; }
        .status-optimal { background: #e8f5e9; color: #2e7d32; }
        .status-over { background: #ffebee; color: #c62828; }
        .status-under { background: #fff3e0; color: #ef6c00; }
        .status-off { background: #f5f5f5; color: #757575; }

        /* Input Panel */
        .input-panel { background: white; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .input-panel h3 { margin-bottom: 16px; color: #333; }
        .input-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }
        .input-group { display: flex; flex-direction: column; gap: 4px; }
        .input-group label { font-size: 14px; color: #333; font-weight: 600; }
        .input-group input { padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; }
        .input-group input:focus { outline: none; border-color: #1976d2; }
        .input-group .unit { font-size: 12px; color: #666; }

        /* Buttons */
        .btn { padding: 14px 28px; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn-primary { background: #1976d2; color: white; }
        .btn-primary:hover { background: #1565c0; }
        .btn-success { background: #4caf50; color: white; }
        .btn-success:hover { background: #43a047; }
        .btn-danger { background: #f44336; color: white; }
        .btn-secondary { background: #e0e0e0; color: #333; }
        .button-row { display: flex; gap: 12px; margin-top: 20px; flex-wrap: wrap; }

        /* Chart */
        .chart-container { background: white; border-radius: 8px; padding: 20px; margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .chart-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; }

        /* Summary */
        .summary-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
        .summary-card { background: white; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .summary-label { font-size: 12px; color: #666; margin-bottom: 8px; text-transform: uppercase; }
        .summary-value { font-size: 28px; font-weight: 700; color: #1976d2; }
        .summary-unit { font-size: 14px; font-weight: 400; color: #999; }

        @media (max-width: 768px) { .summary-row { grid-template-columns: 1fr; } }

        .footer { text-align: center; margin-top: 30px; color: #666; }
        .footer a { color: #1976d2; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 Chemical Saver <span class="badge">LIVE DEMO</span></h1>

        <!-- KPI Row -->
        <div class="kpi-row">
            <div class="kpi-card warning" id="kpi-waste">
                <div class="kpi-title">💸 Savings/Waste</div>
                <div class="kpi-value">$0.00</div>
                <div class="kpi-subtitle">per day</div>
            </div>
            <div class="kpi-card success" id="kpi-corrosion">
                <div class="kpi-title">🛡️ Corrosion Risk</div>
                <div class="kpi-value">--</div>
                <div class="kpi-subtitle">Protection level</div>
            </div>
            <div class="kpi-card info" id="kpi-ppm">
                <div class="kpi-title">🧪 Current PPM</div>
                <div class="kpi-value">0</div>
                <div class="kpi-subtitle">Target: 200 PPM</div>
            </div>
            <div class="kpi-card info" id="kpi-water">
                <div class="kpi-title">💧 Water Production</div>
                <div class="kpi-value">0</div>
                <div class="kpi-subtitle">BPD</div>
            </div>
        </div>

        <!-- Status -->
        <div class="status-indicator">
            <span class="status-chip status-off" id="status-chip">⏸ Enter Data & Click Calculate</span>
        </div>

        <!-- Input Panel -->
        <div class="input-panel">
            <h3>📊 Enter Production Data</h3>
            <div class="input-grid">
                <div class="input-group">
                    <label>Gross Fluid Rate</label>
                    <input type="number" id="sim-fluid" value="1000" min="0">
                    <span class="unit">BPD (Barrels Per Day)</span>
                </div>
                <div class="input-group">
                    <label>Water Cut</label>
                    <input type="number" id="sim-watercut" value="75" min="0" max="100">
                    <span class="unit">% (0-100)</span>
                </div>
                <div class="input-group">
                    <label>Current Injection Rate</label>
                    <input type="number" id="sim-injection" value="5.0" step="0.1" min="0">
                    <span class="unit">GPD (Gallons Per Day)</span>
                </div>
            </div>
            <div class="button-row">
                <button class="btn btn-primary" onclick="runOptimization()">⚡ Calculate Optimal Rate</button>
                <button class="btn btn-success" onclick="startAutoSimulation()">🔄 Auto Demo</button>
                <button class="btn btn-danger" onclick="stopAutoSimulation()">⏹ Stop</button>
                <button class="btn btn-secondary" onclick="clearData()">🗑 Clear</button>
            </div>
        </div>

        <!-- Summary Row -->
        <div class="summary-row">
            <div class="summary-card">
                <div class="summary-label">Recommended Rate</div>
                <div class="summary-value" id="rec-rate">0.00 <span class="summary-unit">GPD</span></div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Actual Rate</div>
                <div class="summary-value" id="act-rate">0.00 <span class="summary-unit">GPD</span></div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Rate Difference</div>
                <div class="summary-value" id="rate-diff">0.00 <span class="summary-unit">GPD</span></div>
            </div>
        </div>

        <!-- Chart -->
        <div class="chart-container">
            <div class="chart-title">📈 Injection Rate Comparison (Actual vs Recommended)</div>
            <canvas id="mainChart" height="100"></canvas>
        </div>

        <p class="footer">Developer: <strong>PRABHAT</strong> | <a href="/">API Documentation</a></p>
    </div>

    <script>
        let chartData = { labels: [], actual: [], recommended: [] };
        let autoSimInterval = null;
        let chart = null;

        // Initialize chart
        document.addEventListener('DOMContentLoaded', function() {
            const ctx = document.getElementById('mainChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: [
                        { label: 'Actual Rate (GPD)', data: chartData.actual, borderColor: '#f44336', backgroundColor: 'rgba(244, 67, 54, 0.1)', tension: 0.3, fill: false, borderWidth: 3 },
                        { label: 'Recommended Rate (GPD)', data: chartData.recommended, borderColor: '#4caf50', backgroundColor: 'rgba(76, 175, 80, 0.1)', tension: 0.3, fill: false, borderWidth: 3 }
                    ]
                },
                options: {
                    responsive: true,
                    scales: { y: { beginAtZero: true, title: { display: true, text: 'Injection Rate (GPD)' } } },
                    plugins: { legend: { position: 'top' } }
                }
            });
        });

        // Run optimization - calls the LIVE API
        async function runOptimization() {
            const grossFluid = parseFloat(document.getElementById('sim-fluid').value) || 0;
            const waterCut = parseFloat(document.getElementById('sim-watercut').value) || 0;
            const injection = parseFloat(document.getElementById('sim-injection').value) || 0;

            try {
                const response = await fetch('/api/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        asset_id: 'demo',
                        gross_fluid_rate: grossFluid,
                        water_cut: waterCut,
                        current_injection_rate: injection
                    })
                });

                const data = await response.json();
                console.log('API Response:', data);

                if (data.success) {
                    updateDashboard(data.result);
                    updateChart(data.result);
                } else {
                    alert('Error: ' + data.error);
                }
            } catch (err) {
                alert('API Error: ' + err.message);
            }
        }

        // Update dashboard
        function updateDashboard(r) {
            // Savings/Waste KPI
            const wasteCard = document.getElementById('kpi-waste');
            const savingsVal = Math.abs(r.savings_opportunity_usd);
            wasteCard.querySelector('.kpi-value').textContent = '$' + savingsVal.toFixed(2);
            wasteCard.classList.remove('error', 'success', 'warning');
            if (r.savings_opportunity_usd > 1) {
                wasteCard.classList.add('error');
                wasteCard.querySelector('.kpi-subtitle').textContent = 'wasting (over-dosing)';
            } else if (r.savings_opportunity_usd < -1) {
                wasteCard.classList.add('warning');
                wasteCard.querySelector('.kpi-subtitle').textContent = 'needed (under-dosing)';
            } else {
                wasteCard.classList.add('success');
                wasteCard.querySelector('.kpi-subtitle').textContent = 'optimal';
            }

            // Corrosion Risk
            const corrosionCard = document.getElementById('kpi-corrosion');
            const isHighRisk = r.status_flag === 'UNDER_DOSING' || r.current_ppm < r.target_ppm * 0.9;
            corrosionCard.querySelector('.kpi-value').textContent = isHighRisk ? 'HIGH' : 'LOW';
            corrosionCard.classList.remove('error', 'success');
            corrosionCard.classList.add(isHighRisk ? 'error' : 'success');
            corrosionCard.querySelector('.kpi-subtitle').textContent = isHighRisk ? 'Increase dosing!' : 'Good protection';

            // PPM
            document.getElementById('kpi-ppm').querySelector('.kpi-value').textContent = r.current_ppm.toFixed(0);
            document.getElementById('kpi-ppm').querySelector('.kpi-subtitle').textContent = 'Target: ' + r.target_ppm + ' PPM';

            // Water
            document.getElementById('kpi-water').querySelector('.kpi-value').textContent = r.water_bpd.toFixed(0);

            // Status chip
            const statusChip = document.getElementById('status-chip');
            statusChip.className = 'status-chip';
            const statusMap = {
                'OPTIMAL': { class: 'status-optimal', text: '✅ OPTIMAL - Perfect dosing!' },
                'OVER_DOSING': { class: 'status-over', text: '⚠️ OVER-DOSING - Reduce rate to save money!' },
                'UNDER_DOSING': { class: 'status-under', text: '🔶 UNDER-DOSING - Increase rate for protection!' },
                'PUMP_OFF': { class: 'status-off', text: '⏸ PUMP OFF - No production' }
            };
            const status = statusMap[r.status_flag] || statusMap['PUMP_OFF'];
            statusChip.classList.add(status.class);
            statusChip.textContent = status.text;

            // Summary cards
            document.getElementById('rec-rate').innerHTML = r.recommended_rate_gpd.toFixed(2) + ' <span class="summary-unit">GPD</span>';
            document.getElementById('act-rate').innerHTML = r.actual_rate_gpd.toFixed(2) + ' <span class="summary-unit">GPD</span>';
            const diff = r.actual_rate_gpd - r.recommended_rate_gpd;
            document.getElementById('rate-diff').innerHTML = (diff >= 0 ? '+' : '') + diff.toFixed(2) + ' <span class="summary-unit">GPD</span>';
        }

        // Update chart
        function updateChart(r) {
            const time = new Date().toLocaleTimeString();
            chartData.labels.push(time);
            chartData.actual.push(r.actual_rate_gpd);
            chartData.recommended.push(r.recommended_rate_gpd);
            if (chartData.labels.length > 20) {
                chartData.labels.shift();
                chartData.actual.shift();
                chartData.recommended.shift();
            }
            chart.update();
        }

        // Auto simulation
        function startAutoSimulation() {
            if (autoSimInterval) return;
            autoSimInterval = setInterval(() => {
                const fluid = 1000 + (Math.random() - 0.5) * 200;
                const waterCut = Math.max(0, Math.min(100, 75 + (Math.random() - 0.5) * 10));
                const injection = Math.max(0, 4.0 + (Math.random() - 0.3) * 3);
                document.getElementById('sim-fluid').value = fluid.toFixed(0);
                document.getElementById('sim-watercut').value = waterCut.toFixed(1);
                document.getElementById('sim-injection').value = injection.toFixed(1);
                runOptimization();
            }, 2000);
        }

        function stopAutoSimulation() {
            if (autoSimInterval) { clearInterval(autoSimInterval); autoSimInterval = null; }
        }

        function clearData() {
            chartData = { labels: [], actual: [], recommended: [] };
            chart.data.labels = [];
            chart.data.datasets[0].data = [];
            chart.data.datasets[1].data = [];
            chart.update();
        }
    </script>
</body>
</html>
    ''', 200


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run."""
    return jsonify({'status': 'healthy', 'app': 'chemical-saver'}), 200


@app.route('/api/optimize', methods=['POST'])
def optimize():
    """
    Main optimization endpoint.

    Request body:
    {
        "asset_id": 12345,
        "gross_fluid_rate": 1000,
        "water_cut": 80,
        "current_injection_rate": 5.0
    }
    """
    try:
        data = request.get_json()

        asset_id = data.get('asset_id', 'default')

        # Get settings for this asset
        settings_dict = settings_store.get(asset_id, None)
        settings = WellSettings.from_database(settings_dict)

        # Create optimizer
        optimizer = ChemicalOptimizer(settings)

        # Create production data
        prod_data = ProductionData(
            timestamp=int(data.get('timestamp', 0)),
            gross_fluid_rate=float(data.get('gross_fluid_rate', 0)),
            water_cut=float(data.get('water_cut', 0)),
            current_injection_rate=float(data.get('current_injection_rate', 0)),
            pump_status=float(data.get('gross_fluid_rate', 0)) > 0
        )

        # Run optimization
        result = optimizer.optimize(prod_data)

        return jsonify({
            'success': True,
            'result': result.to_dict()
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/settings/<asset_id>', methods=['GET'])
def get_settings(asset_id):
    """Get settings for an asset."""
    settings_dict = settings_store.get(asset_id, None)

    if settings_dict:
        return jsonify({'success': True, 'settings': settings_dict}), 200
    else:
        # Return defaults
        defaults = DefaultSettings()
        return jsonify({
            'success': True,
            'settings': {
                'target_ppm': defaults.TARGET_PPM,
                'chemical_density': defaults.CHEMICAL_DENSITY,
                'active_intensity': defaults.ACTIVE_INTENSITY,
                'cost_per_gallon': defaults.COST_PER_GALLON,
                'min_pump_rate': defaults.MIN_PUMP_RATE,
                'max_pump_rate': defaults.MAX_PUMP_RATE
            }
        }), 200


@app.route('/api/settings/<asset_id>', methods=['POST'])
def save_settings(asset_id):
    """Save settings for an asset."""
    try:
        data = request.get_json()
        settings_store[asset_id] = data
        return jsonify({'success': True, 'message': 'Settings saved'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/batch', methods=['POST'])
def batch_optimize():
    """
    Batch optimization for multiple records.

    Request body:
    {
        "asset_id": 12345,
        "records": [
            {"timestamp": 123, "gross_fluid_rate": 1000, "water_cut": 80, "current_injection_rate": 5.0},
            ...
        ]
    }
    """
    try:
        data = request.get_json()

        asset_id = data.get('asset_id', 'default')
        records = data.get('records', [])

        # Get settings
        settings_dict = settings_store.get(asset_id, None)
        settings = WellSettings.from_database(settings_dict)

        # Create optimizer
        optimizer = ChemicalOptimizer(settings)

        results = []
        previous_rate = None

        for record in records:
            prod_data = ProductionData(
                timestamp=int(record.get('timestamp', 0)),
                gross_fluid_rate=float(record.get('gross_fluid_rate', 0)),
                water_cut=float(record.get('water_cut', 0)),
                current_injection_rate=float(record.get('current_injection_rate', 0)),
                pump_status=float(record.get('gross_fluid_rate', 0)) > 0
            )

            result = optimizer.optimize(prod_data, previous_rate)
            results.append(result.to_dict())
            previous_rate = prod_data.gross_fluid_rate

        return jsonify({
            'success': True,
            'processed': len(results),
            'results': results
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
