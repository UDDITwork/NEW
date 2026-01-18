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
    """Interactive demo page."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chemical Saver - Live Demo</title>
        <style>
            * { box-sizing: border-box; }
            body { font-family: Arial, sans-serif; background: #1a1a2e; color: #fff; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            h1 { color: #4ade80; text-align: center; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
            .card { background: #16213e; border-radius: 12px; padding: 20px; }
            .card h2 { color: #4ade80; margin-top: 0; border-bottom: 1px solid #333; padding-bottom: 10px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; color: #a0a0a0; }
            input { width: 100%; padding: 10px; border: 1px solid #333; border-radius: 6px; background: #0f0f23; color: #fff; font-size: 16px; }
            input:focus { outline: none; border-color: #4ade80; }
            .btn { width: 100%; padding: 12px; background: #4ade80; color: #000; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; font-weight: bold; }
            .btn:hover { background: #22c55e; }
            .btn:disabled { background: #666; cursor: not-allowed; }
            .kpi-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
            .kpi { background: #0f0f23; border-radius: 8px; padding: 15px; text-align: center; }
            .kpi-value { font-size: 28px; font-weight: bold; color: #4ade80; }
            .kpi-label { font-size: 12px; color: #a0a0a0; margin-top: 5px; }
            .status { padding: 15px; border-radius: 8px; text-align: center; font-size: 18px; font-weight: bold; margin-top: 15px; }
            .status.optimal { background: #166534; color: #4ade80; }
            .status.over { background: #7c2d12; color: #fb923c; }
            .status.under { background: #1e3a5f; color: #60a5fa; }
            .status.idle { background: #333; color: #a0a0a0; }
            .detail-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #333; }
            .detail-label { color: #a0a0a0; }
            .detail-value { color: #fff; font-weight: bold; }
            .savings { color: #4ade80; }
            .loss { color: #f87171; }
            @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } .kpi-grid { grid-template-columns: 1fr; } }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧪 Chemical Saver - Live Demo</h1>
            <p style="text-align:center; color:#a0a0a0;">Enter production data to calculate optimal chemical injection rate</p>

            <div class="grid">
                <div class="card">
                    <h2>📊 Input Parameters</h2>
                    <div class="form-group">
                        <label>Gross Fluid Rate (BBL/day)</label>
                        <input type="number" id="gross_fluid_rate" value="1000" min="0" step="100">
                    </div>
                    <div class="form-group">
                        <label>Water Cut (%)</label>
                        <input type="number" id="water_cut" value="80" min="0" max="100" step="1">
                    </div>
                    <div class="form-group">
                        <label>Current Injection Rate (GPH)</label>
                        <input type="number" id="current_injection_rate" value="5.0" min="0" step="0.1">
                    </div>
                    <button class="btn" id="optimizeBtn" onclick="runOptimization()">⚡ Calculate Optimal Rate</button>

                    <div style="margin-top: 20px; padding: 15px; background: #0f0f23; border-radius: 8px;">
                        <h3 style="margin-top:0; color: #60a5fa;">ℹ️ How it works</h3>
                        <p style="color: #a0a0a0; font-size: 14px; line-height: 1.6;">
                            1. <strong>Water Volume</strong> = Fluid Rate × Water Cut × 350 lbs/BBL<br>
                            2. <strong>Chemical Needed</strong> = Water × Target PPM ÷ Density<br>
                            3. <strong>Optimal Rate</strong> = Chemical ÷ 24 hours<br>
                            4. Compare with current rate to detect over/under dosing
                        </p>
                    </div>
                </div>

                <div class="card">
                    <h2>📈 Optimization Results</h2>
                    <div id="results">
                        <div class="kpi-grid">
                            <div class="kpi">
                                <div class="kpi-value" id="recommended_rate">--</div>
                                <div class="kpi-label">Recommended Rate (GPH)</div>
                            </div>
                            <div class="kpi">
                                <div class="kpi-value" id="daily_chemical">--</div>
                                <div class="kpi-label">Daily Chemical (GAL)</div>
                            </div>
                            <div class="kpi">
                                <div class="kpi-value" id="daily_cost">--</div>
                                <div class="kpi-label">Daily Cost ($)</div>
                            </div>
                            <div class="kpi">
                                <div class="kpi-value" id="water_volume">--</div>
                                <div class="kpi-label">Water Volume (LBS)</div>
                            </div>
                        </div>

                        <div class="status idle" id="status_box">
                            Enter values and click Calculate
                        </div>

                        <div style="margin-top: 20px;">
                            <div class="detail-row">
                                <span class="detail-label">Current Rate</span>
                                <span class="detail-value" id="current_rate_display">--</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Rate Difference</span>
                                <span class="detail-value" id="rate_diff">--</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Financial Impact</span>
                                <span class="detail-value" id="financial_impact">--</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <p style="text-align:center; margin-top: 30px; color:#666;">Developer: PRABHAT | <a href="/" style="color:#4ade80;">Back to API Docs</a></p>
        </div>

        <script>
            async function runOptimization() {
                const btn = document.getElementById('optimizeBtn');
                btn.disabled = true;
                btn.textContent = '⏳ Calculating...';

                const data = {
                    asset_id: 'demo',
                    gross_fluid_rate: parseFloat(document.getElementById('gross_fluid_rate').value) || 0,
                    water_cut: parseFloat(document.getElementById('water_cut').value) || 0,
                    current_injection_rate: parseFloat(document.getElementById('current_injection_rate').value) || 0
                };

                try {
                    const response = await fetch('/api/optimize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });

                    const result = await response.json();

                    if (result.success) {
                        const r = result.result;

                        document.getElementById('recommended_rate').textContent = r.recommended_rate.toFixed(2);
                        document.getElementById('daily_chemical').textContent = r.daily_chemical_volume.toFixed(2);
                        document.getElementById('daily_cost').textContent = '$' + r.daily_cost.toFixed(2);
                        document.getElementById('water_volume').textContent = r.water_volume_lbs.toFixed(0);

                        document.getElementById('current_rate_display').textContent = data.current_injection_rate.toFixed(2) + ' GPH';

                        const diff = r.recommended_rate - data.current_injection_rate;
                        const diffEl = document.getElementById('rate_diff');
                        diffEl.textContent = (diff >= 0 ? '+' : '') + diff.toFixed(2) + ' GPH';
                        diffEl.className = 'detail-value ' + (diff >= 0 ? 'loss' : 'savings');

                        const impact = r.potential_daily_savings;
                        const impactEl = document.getElementById('financial_impact');
                        if (impact >= 0) {
                            impactEl.textContent = '+$' + impact.toFixed(2) + '/day savings';
                            impactEl.className = 'detail-value savings';
                        } else {
                            impactEl.textContent = '-$' + Math.abs(impact).toFixed(2) + '/day needed';
                            impactEl.className = 'detail-value loss';
                        }

                        const statusBox = document.getElementById('status_box');
                        statusBox.className = 'status ' + r.status.toLowerCase().replace('-', '');
                        const statusMessages = {
                            'OPTIMAL': '✅ OPTIMAL - Current dosing is within target range',
                            'OVER-DOSING': '⚠️ OVER-DOSING - Reduce injection rate to save costs',
                            'UNDER-DOSING': '🔵 UNDER-DOSING - Increase injection rate for protection',
                            'PUMP-OFF': '⏸️ PUMP OFF - No production detected'
                        };
                        statusBox.textContent = statusMessages[r.status] || r.status;
                    } else {
                        alert('Error: ' + result.error);
                    }
                } catch (err) {
                    alert('Request failed: ' + err.message);
                }

                btn.disabled = false;
                btn.textContent = '⚡ Calculate Optimal Rate';
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
