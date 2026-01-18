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
    """Interactive demo page - Professional glassmorphism UI."""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chemical Saver | Dosage Optimization</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            color: #e2e8f0;
            padding: 24px;
        }
        .container { max-width: 1400px; margin: 0 auto; }

        /* Header */
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
        .logo { font-size: 24px; font-weight: 700; color: #f8fafc; letter-spacing: -0.5px; }
        .logo span { color: #3b82f6; }
        .header-badge { background: rgba(59, 130, 246, 0.2); color: #60a5fa; padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 500; border: 1px solid rgba(59, 130, 246, 0.3); }

        /* Glass Card */
        .glass {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
        }

        /* KPI Cards */
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 24px; }
        .kpi-card { padding: 24px; position: relative; overflow: hidden; }
        .kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
        .kpi-card.success::before { background: linear-gradient(90deg, #22c55e, #4ade80); }
        .kpi-card.warning::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
        .kpi-card.error::before { background: linear-gradient(90deg, #ef4444, #f87171); }
        .kpi-card.info::before { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
        .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #94a3b8; margin-bottom: 8px; font-weight: 500; }
        .kpi-value { font-size: 32px; font-weight: 700; color: #f8fafc; margin-bottom: 4px; }
        .kpi-card.success .kpi-value { color: #4ade80; }
        .kpi-card.warning .kpi-value { color: #fbbf24; }
        .kpi-card.error .kpi-value { color: #f87171; }
        .kpi-card.info .kpi-value { color: #60a5fa; }
        .kpi-sub { font-size: 12px; color: #64748b; }

        /* Status Banner */
        .status-banner { padding: 20px; margin-bottom: 24px; text-align: center; }
        .status-text { font-size: 18px; font-weight: 600; letter-spacing: 0.5px; }
        .status-banner.optimal { background: rgba(34, 197, 94, 0.1); border-color: rgba(34, 197, 94, 0.3); }
        .status-banner.optimal .status-text { color: #4ade80; }
        .status-banner.over { background: rgba(239, 68, 68, 0.1); border-color: rgba(239, 68, 68, 0.3); }
        .status-banner.over .status-text { color: #f87171; }
        .status-banner.under { background: rgba(245, 158, 11, 0.1); border-color: rgba(245, 158, 11, 0.3); }
        .status-banner.under .status-text { color: #fbbf24; }
        .status-banner.off { background: rgba(100, 116, 139, 0.1); border-color: rgba(100, 116, 139, 0.3); }
        .status-banner.off .status-text { color: #94a3b8; }

        /* Input Section */
        .input-section { padding: 28px; margin-bottom: 24px; }
        .section-title { font-size: 14px; font-weight: 600; color: #f8fafc; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }
        .input-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .input-group label { display: block; font-size: 12px; color: #94a3b8; margin-bottom: 8px; font-weight: 500; }
        .input-group input {
            width: 100%; padding: 14px 16px; font-size: 16px; font-weight: 500;
            background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px; color: #f8fafc; transition: all 0.2s;
        }
        .input-group input:focus { outline: none; border-color: #3b82f6; background: rgba(15, 23, 42, 0.8); }
        .input-group .unit { font-size: 11px; color: #64748b; margin-top: 6px; }

        /* Buttons */
        .btn-group { display: flex; gap: 12px; margin-top: 24px; flex-wrap: wrap; }
        .btn {
            padding: 14px 24px; font-size: 14px; font-weight: 600; border: none; border-radius: 10px;
            cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 8px;
        }
        .btn-primary { background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3); }
        .btn-success { background: linear-gradient(135deg, #22c55e, #16a34a); color: white; }
        .btn-success:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(34, 197, 94, 0.3); }
        .btn-danger { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }
        .btn-secondary { background: rgba(255, 255, 255, 0.1); color: #e2e8f0; border: 1px solid rgba(255, 255, 255, 0.1); }

        /* Summary Cards */
        .summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px; }
        .summary-card { padding: 24px; text-align: center; }
        .summary-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 8px; }
        .summary-value { font-size: 28px; font-weight: 700; color: #f8fafc; }
        .summary-value span { font-size: 14px; color: #64748b; font-weight: 400; }

        /* Chart */
        .chart-section { padding: 28px; margin-bottom: 24px; }
        .chart-container { position: relative; height: 300px; }

        /* Footer */
        .footer { text-align: center; padding: 20px; color: #475569; font-size: 13px; }
        .footer a { color: #3b82f6; text-decoration: none; }

        @media (max-width: 768px) {
            .summary-grid { grid-template-columns: 1fr; }
            .btn-group { flex-direction: column; }
            .btn { width: 100%; justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">Chemical<span>Saver</span></div>
            <div class="header-badge">Live Demo</div>
        </div>

        <div class="kpi-grid">
            <div class="glass kpi-card warning" id="kpi-waste">
                <div class="kpi-label">Daily Savings / Waste</div>
                <div class="kpi-value">$0.00</div>
                <div class="kpi-sub">per day</div>
            </div>
            <div class="glass kpi-card success" id="kpi-corrosion">
                <div class="kpi-label">Corrosion Risk</div>
                <div class="kpi-value">--</div>
                <div class="kpi-sub">Protection status</div>
            </div>
            <div class="glass kpi-card info" id="kpi-ppm">
                <div class="kpi-label">Current PPM</div>
                <div class="kpi-value">0</div>
                <div class="kpi-sub">Target: 200 PPM</div>
            </div>
            <div class="glass kpi-card info" id="kpi-water">
                <div class="kpi-label">Water Production</div>
                <div class="kpi-value">0</div>
                <div class="kpi-sub">Barrels per day</div>
            </div>
        </div>

        <div class="glass status-banner off" id="status-banner">
            <div class="status-text" id="status-text">Enter production data and click Calculate</div>
        </div>

        <div class="glass input-section">
            <div class="section-title">Production Data Input</div>
            <div class="input-grid">
                <div class="input-group">
                    <label>Gross Fluid Rate</label>
                    <input type="number" id="sim-fluid" value="1000" min="0">
                    <div class="unit">BPD (Barrels Per Day)</div>
                </div>
                <div class="input-group">
                    <label>Water Cut</label>
                    <input type="number" id="sim-watercut" value="75" min="0" max="100">
                    <div class="unit">Percentage (0-100)</div>
                </div>
                <div class="input-group">
                    <label>Current Injection Rate</label>
                    <input type="number" id="sim-injection" value="5.0" step="0.1" min="0">
                    <div class="unit">GPD (Gallons Per Day)</div>
                </div>
            </div>
            <div class="btn-group">
                <button class="btn btn-primary" onclick="runOptimization()">Calculate Optimal Rate</button>
                <button class="btn btn-success" onclick="startAutoSimulation()">Auto Simulation</button>
                <button class="btn btn-danger" onclick="stopAutoSimulation()">Stop</button>
                <button class="btn btn-secondary" onclick="clearData()">Clear Data</button>
            </div>
        </div>

        <div class="summary-grid">
            <div class="glass summary-card">
                <div class="summary-label">Recommended Rate</div>
                <div class="summary-value" id="rec-rate">0.00 <span>GPD</span></div>
            </div>
            <div class="glass summary-card">
                <div class="summary-label">Actual Rate</div>
                <div class="summary-value" id="act-rate">0.00 <span>GPD</span></div>
            </div>
            <div class="glass summary-card">
                <div class="summary-label">Rate Difference</div>
                <div class="summary-value" id="rate-diff">0.00 <span>GPD</span></div>
            </div>
        </div>

        <div class="glass chart-section">
            <div class="section-title">Injection Rate Comparison</div>
            <div class="chart-container">
                <canvas id="mainChart"></canvas>
            </div>
        </div>

        <div class="footer">
            Developed by <strong>PRABHAT</strong> | <a href="/">API Documentation</a>
        </div>
    </div>

    <script>
        let chartData = { labels: [], actual: [], recommended: [] };
        let autoSimInterval = null;
        let chart = null;

        document.addEventListener('DOMContentLoaded', function() {
            Chart.defaults.color = '#94a3b8';
            Chart.defaults.borderColor = 'rgba(255,255,255,0.05)';
            const ctx = document.getElementById('mainChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: [
                        { label: 'Actual Rate (GPD)', data: chartData.actual, borderColor: '#f87171', backgroundColor: 'rgba(248,113,113,0.1)', tension: 0.4, fill: true, borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#f87171' },
                        { label: 'Recommended Rate (GPD)', data: chartData.recommended, borderColor: '#4ade80', backgroundColor: 'rgba(74,222,128,0.1)', tension: 0.4, fill: true, borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#4ade80' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
                        x: { grid: { display: false }, ticks: { color: '#64748b' } }
                    },
                    plugins: { legend: { position: 'top', labels: { usePointStyle: true, padding: 20 } } }
                }
            });
        });

        async function runOptimization() {
            const grossFluid = parseFloat(document.getElementById('sim-fluid').value) || 0;
            const waterCut = parseFloat(document.getElementById('sim-watercut').value) || 0;
            const injection = parseFloat(document.getElementById('sim-injection').value) || 0;

            try {
                const response = await fetch('/api/optimize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ asset_id: 'demo', gross_fluid_rate: grossFluid, water_cut: waterCut, current_injection_rate: injection })
                });
                const data = await response.json();
                if (data.success) { updateDashboard(data.result); updateChart(data.result); }
                else { console.error('Error:', data.error); }
            } catch (err) { console.error('API Error:', err.message); }
        }

        function updateDashboard(r) {
            const wasteCard = document.getElementById('kpi-waste');
            const savingsVal = Math.abs(r.savings_opportunity_usd);
            wasteCard.querySelector('.kpi-value').textContent = '$' + savingsVal.toFixed(2);
            wasteCard.classList.remove('error', 'success', 'warning');
            if (r.savings_opportunity_usd > 1) { wasteCard.classList.add('error'); wasteCard.querySelector('.kpi-sub').textContent = 'Wasting (over-dosing)'; }
            else if (r.savings_opportunity_usd < -1) { wasteCard.classList.add('warning'); wasteCard.querySelector('.kpi-sub').textContent = 'Additional cost needed'; }
            else { wasteCard.classList.add('success'); wasteCard.querySelector('.kpi-sub').textContent = 'Optimal dosing'; }

            const corrosionCard = document.getElementById('kpi-corrosion');
            const isHighRisk = r.status_flag === 'UNDER_DOSING' || r.current_ppm < r.target_ppm * 0.9;
            corrosionCard.querySelector('.kpi-value').textContent = isHighRisk ? 'HIGH' : 'LOW';
            corrosionCard.classList.remove('error', 'success');
            corrosionCard.classList.add(isHighRisk ? 'error' : 'success');
            corrosionCard.querySelector('.kpi-sub').textContent = isHighRisk ? 'Increase dosing recommended' : 'Adequate protection';

            document.getElementById('kpi-ppm').querySelector('.kpi-value').textContent = r.current_ppm.toFixed(0);
            document.getElementById('kpi-ppm').querySelector('.kpi-sub').textContent = 'Target: ' + r.target_ppm + ' PPM';
            document.getElementById('kpi-water').querySelector('.kpi-value').textContent = r.water_bpd.toFixed(0);

            const banner = document.getElementById('status-banner');
            const statusText = document.getElementById('status-text');
            banner.classList.remove('optimal', 'over', 'under', 'off');
            const statusMap = {
                'OPTIMAL': { class: 'optimal', text: 'OPTIMAL - Dosing within target range' },
                'OVER_DOSING': { class: 'over', text: 'OVER-DOSING - Reduce injection rate to optimize costs' },
                'UNDER_DOSING': { class: 'under', text: 'UNDER-DOSING - Increase injection rate for corrosion protection' },
                'PUMP_OFF': { class: 'off', text: 'PUMP OFF - No production detected' }
            };
            const status = statusMap[r.status_flag] || statusMap['PUMP_OFF'];
            banner.classList.add(status.class);
            statusText.textContent = status.text;

            document.getElementById('rec-rate').innerHTML = r.recommended_rate_gpd.toFixed(2) + ' <span>GPD</span>';
            document.getElementById('act-rate').innerHTML = r.actual_rate_gpd.toFixed(2) + ' <span>GPD</span>';
            const diff = r.actual_rate_gpd - r.recommended_rate_gpd;
            document.getElementById('rate-diff').innerHTML = (diff >= 0 ? '+' : '') + diff.toFixed(2) + ' <span>GPD</span>';
        }

        function updateChart(r) {
            const time = new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
            chartData.labels.push(time);
            chartData.actual.push(r.actual_rate_gpd);
            chartData.recommended.push(r.recommended_rate_gpd);
            if (chartData.labels.length > 15) { chartData.labels.shift(); chartData.actual.shift(); chartData.recommended.shift(); }
            chart.update();
        }

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

        function stopAutoSimulation() { if (autoSimInterval) { clearInterval(autoSimInterval); autoSimInterval = null; } }

        function clearData() {
            chartData = { labels: [], actual: [], recommended: [] };
            chart.data.labels = []; chart.data.datasets[0].data = []; chart.data.datasets[1].data = [];
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
