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
        </style>
    </head>
    <body>
        <h1>🧪 Chemical Saver API</h1>
        <p>Dosage Optimization for Oil & Gas Production</p>

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
