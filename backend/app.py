"""
Chemical Saver - Production Flask API for Cloud Run
Developer: PRABHAT
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

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

# Chat rate limiter: {user_hash: {'count': int, 'reset_time': datetime}}
chat_rate_limits = {}
CHAT_RATE_LIMIT = 8  # Max messages per session

# Anthropic API Configuration
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# System prompt for the chatbot - project-specific knowledge only
CHATBOT_SYSTEM_PROMPT = """You are the Chemical Saver Assistant, an AI helper created by Prabhat for the Chemical Saver application.

IMPORTANT RULES:
1. You can ONLY discuss topics related to the Chemical Saver project, oil & gas chemical dosing, and related technical concepts.
2. If anyone asks who made you or created you, respond: "My master Prabhat has created me and this entire Chemical Saver project."
3. If someone asks anything outside the project scope (personal questions, general chat, unrelated topics), politely decline and say you can only assist with Chemical Saver related queries.
4. Be professional, concise, and helpful.

PROJECT KNOWLEDGE:
- Chemical Saver is a dosage optimization application for oil & gas production
- It calculates optimal chemical injection rates based on real-time production data
- Key inputs: Gross Fluid Rate (BPD), Water Cut (%), Current Injection Rate (GPD)
- Key outputs: Recommended Rate, Savings/Waste ($), Corrosion Risk, PPM levels
- The app uses PPM (parts per million) calculations to determine optimal dosing
- Target PPM is typically 200 for corrosion inhibitors
- Status flags: OPTIMAL, OVER_DOSING, UNDER_DOSING, PUMP_OFF
- Over-dosing wastes money, Under-dosing risks corrosion damage
- The formula converts water volume to chemical requirements based on target concentration

DEVELOPER INFO:
- Created by: Prabhat
- Affiliation: IIT(ISM) Dhanbad | RGIPT | PE'27
- This is a production-grade application deployed on Google Cloud Run

Keep responses brief (2-4 sentences max) and focused on helping users understand the Chemical Saver application."""


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
            background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 50%, #f5f7ff 100%);
            color: #1e293b;
            padding: 24px;
        }
        .container { max-width: 1400px; margin: 0 auto; }

        /* Header */
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; flex-wrap: wrap; gap: 16px; }
        .header-left { display: flex; align-items: center; gap: 12px; }
        .logo { font-size: 24px; font-weight: 700; color: #1e293b; letter-spacing: -0.5px; }
        .logo span { color: #2563eb; }
        .header-badge { background: rgba(37, 99, 235, 0.1); color: #2563eb; padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 500; border: 1px solid rgba(37, 99, 235, 0.2); }
        .dev-profile { display: flex; align-items: center; gap: 12px; }
        .dev-avatar { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; border: 2px solid #e2e8f0; }
        .dev-info { text-align: right; }
        .dev-name { font-size: 14px; font-weight: 600; color: #1e293b; }
        .dev-title { font-size: 11px; color: #64748b; line-height: 1.3; }
        .dev-links { display: flex; gap: 8px; margin-top: 4px; justify-content: flex-end; }
        .dev-link { font-size: 10px; color: #2563eb; text-decoration: none; padding: 2px 8px; background: rgba(37,99,235,0.08); border-radius: 10px; }
        .dev-link:hover { background: rgba(37,99,235,0.15); }
        @media (max-width: 600px) {
            .dev-info { text-align: left; }
            .dev-links { justify-content: flex-start; }
            .dev-title { max-width: 180px; }
        }

        /* Glass Card */
        .glass {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.8);
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
        }

        /* KPI Cards */
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 24px; }
        .kpi-card { padding: 24px; position: relative; overflow: hidden; }
        .kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; }
        .kpi-card.success::before { background: linear-gradient(90deg, #16a34a, #22c55e); }
        .kpi-card.warning::before { background: linear-gradient(90deg, #d97706, #f59e0b); }
        .kpi-card.error::before { background: linear-gradient(90deg, #dc2626, #ef4444); }
        .kpi-card.info::before { background: linear-gradient(90deg, #2563eb, #3b82f6); }
        .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 8px; font-weight: 600; }
        .kpi-value { font-size: 32px; font-weight: 700; color: #1e293b; margin-bottom: 4px; }
        .kpi-card.success .kpi-value { color: #16a34a; }
        .kpi-card.warning .kpi-value { color: #d97706; }
        .kpi-card.error .kpi-value { color: #dc2626; }
        .kpi-card.info .kpi-value { color: #2563eb; }
        .kpi-sub { font-size: 12px; color: #94a3b8; }

        /* Status Banner */
        .status-wrapper { text-align: center; margin-bottom: 24px; }
        .status-banner { padding: 12px 28px; display: inline-block; }
        .status-text { font-size: 15px; font-weight: 600; letter-spacing: 0.3px; white-space: nowrap; }
        .status-banner.optimal { background: rgba(22, 163, 74, 0.08); border-color: rgba(22, 163, 74, 0.2); }
        .status-banner.optimal .status-text { color: #16a34a; }
        .status-banner.over { background: rgba(220, 38, 38, 0.08); border-color: rgba(220, 38, 38, 0.2); }
        .status-banner.over .status-text { color: #dc2626; }
        .status-banner.under { background: rgba(217, 119, 6, 0.08); border-color: rgba(217, 119, 6, 0.2); }
        .status-banner.under .status-text { color: #d97706; }
        .status-banner.off { background: rgba(100, 116, 139, 0.08); border-color: rgba(100, 116, 139, 0.2); }
        .status-banner.off .status-text { color: #64748b; }

        /* Input Section */
        .input-section { padding: 28px; margin-bottom: 24px; }
        .section-title { font-size: 14px; font-weight: 600; color: #1e293b; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }
        .input-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .input-group label { display: block; font-size: 12px; color: #475569; margin-bottom: 8px; font-weight: 600; }
        .input-group input {
            width: 100%; padding: 14px 16px; font-size: 16px; font-weight: 500;
            background: #ffffff; border: 1px solid #e2e8f0;
            border-radius: 10px; color: #1e293b; transition: all 0.2s;
        }
        .input-group input:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
        .input-group .unit { font-size: 11px; color: #94a3b8; margin-top: 6px; }

        /* Buttons */
        .btn-group { display: flex; gap: 12px; margin-top: 24px; flex-wrap: wrap; }
        .btn {
            padding: 14px 24px; font-size: 14px; font-weight: 600; border: none; border-radius: 10px;
            cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 8px;
        }
        .btn-primary { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(37, 99, 235, 0.25); }
        .btn-success { background: linear-gradient(135deg, #16a34a, #15803d); color: white; }
        .btn-success:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(22, 163, 74, 0.25); }
        .btn-danger { background: linear-gradient(135deg, #dc2626, #b91c1c); color: white; }
        .btn-danger:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(220, 38, 38, 0.25); }
        .btn-secondary { background: #ffffff; color: #475569; border: 1px solid #e2e8f0; }
        .btn-secondary:hover { background: #f8fafc; }

        /* Summary Cards */
        .summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px; }
        .summary-card { padding: 24px; text-align: center; }
        .summary-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 8px; }
        .summary-value { font-size: 28px; font-weight: 700; color: #1e293b; }
        .summary-value span { font-size: 14px; color: #94a3b8; font-weight: 400; }

        /* Chart */
        .chart-section { padding: 28px; margin-bottom: 24px; }
        .chart-container { position: relative; height: 300px; }

        /* Footer */
        .footer { text-align: center; padding: 20px; color: #94a3b8; font-size: 13px; }
        .footer a { color: #2563eb; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }

        @media (max-width: 768px) {
            .summary-grid { grid-template-columns: 1fr; }
            .btn-group { flex-direction: column; }
            .btn { width: 100%; justify-content: center; }
        }

        /* Floating Chatbot Styles */
        .chat-fab {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(37, 99, 235, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            z-index: 1000;
        }
        .chat-fab:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 28px rgba(37, 99, 235, 0.5);
        }
        .chat-fab svg {
            width: 28px;
            height: 28px;
            fill: white;
        }
        .chat-fab.active {
            background: linear-gradient(135deg, #dc2626, #b91c1c);
        }

        /* Chat Popup Window */
        .chat-popup {
            position: fixed;
            bottom: 100px;
            right: 24px;
            width: 380px;
            max-width: calc(100vw - 48px);
            height: 500px;
            max-height: calc(100vh - 140px);
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.8);
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
            display: none;
            flex-direction: column;
            overflow: hidden;
            z-index: 999;
        }
        .chat-popup.active {
            display: flex;
            animation: chatSlideIn 0.3s ease;
        }
        @keyframes chatSlideIn {
            from { opacity: 0; transform: translateY(20px) scale(0.95); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        .chat-header {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .chat-header-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: rgba(255,255,255,0.2);
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .chat-header-avatar svg {
            width: 24px;
            height: 24px;
            fill: white;
        }
        .chat-header-info h4 {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 2px;
        }
        .chat-header-info p {
            font-size: 11px;
            opacity: 0.85;
        }
        .chat-remaining {
            margin-left: auto;
            font-size: 10px;
            background: rgba(255,255,255,0.2);
            padding: 4px 10px;
            border-radius: 12px;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .chat-message {
            max-width: 85%;
            padding: 12px 16px;
            border-radius: 16px;
            font-size: 13px;
            line-height: 1.5;
        }
        .chat-message.bot {
            background: #f1f5f9;
            color: #1e293b;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }
        .chat-message.user {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        .chat-message.error {
            background: #fef2f2;
            color: #dc2626;
            border: 1px solid #fecaca;
        }
        .chat-typing {
            display: flex;
            gap: 4px;
            padding: 12px 16px;
            background: #f1f5f9;
            border-radius: 16px;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }
        .chat-typing span {
            width: 8px;
            height: 8px;
            background: #94a3b8;
            border-radius: 50%;
            animation: typingBounce 1.4s infinite;
        }
        .chat-typing span:nth-child(2) { animation-delay: 0.2s; }
        .chat-typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typingBounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-6px); }
        }

        .chat-input-area {
            padding: 16px;
            border-top: 1px solid #e2e8f0;
            display: flex;
            gap: 10px;
        }
        .chat-input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #e2e8f0;
            border-radius: 24px;
            font-size: 13px;
            outline: none;
            transition: border-color 0.2s;
        }
        .chat-input:focus {
            border-color: #2563eb;
        }
        .chat-input:disabled {
            background: #f8fafc;
            cursor: not-allowed;
        }
        .chat-send {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .chat-send:hover:not(:disabled) {
            transform: scale(1.05);
        }
        .chat-send:disabled {
            background: #cbd5e1;
            cursor: not-allowed;
        }
        .chat-send svg {
            width: 20px;
            height: 20px;
            fill: white;
        }

        @media (max-width: 480px) {
            .chat-popup {
                right: 12px;
                bottom: 90px;
                width: calc(100vw - 24px);
                height: calc(100vh - 120px);
            }
            .chat-fab {
                right: 16px;
                bottom: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <div class="logo">Chemical<span>Saver</span></div>
                <div class="header-badge">Live Demo</div>
            </div>
            <div class="dev-profile">
                <div class="dev-info">
                    <div class="dev-name">Prabhat</div>
                    <div class="dev-title">IIT(ISM) Dhanbad | RGIPT | PE'27</div>
                    <div class="dev-links">
                        <a href="https://www.linkedin.com/in/prabhat-0043ba290" target="_blank" class="dev-link">LinkedIn</a>
                        <a href="https://prabhatpetro-build-ilpm.bolt.host/" target="_blank" class="dev-link">Portfolio</a>
                    </div>
                </div>
                <img src="https://media.licdn.com/dms/image/v2/D5603AQHDawzZI4DdUw/profile-displayphoto-crop_800_800/B56ZqDEXo1JoAI-/0/1763135554903?e=1770249600&v=beta&t=AJw__c4gwVJX58Ratf_RCPCr02rBW19l08MnYtG-oJY" alt="Prabhat" class="dev-avatar">
            </div>
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

        <div class="status-wrapper">
            <div class="glass status-banner off" id="status-banner">
                <div class="status-text" id="status-text">Enter production data and click Calculate</div>
            </div>
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
            Chart.defaults.color = '#64748b';
            Chart.defaults.borderColor = 'rgba(0,0,0,0.05)';
            const ctx = document.getElementById('mainChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: [
                        { label: 'Actual Rate (GPD)', data: chartData.actual, borderColor: '#dc2626', backgroundColor: 'rgba(220,38,38,0.08)', tension: 0.4, fill: true, borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#dc2626' },
                        { label: 'Recommended Rate (GPD)', data: chartData.recommended, borderColor: '#16a34a', backgroundColor: 'rgba(22,163,74,0.08)', tension: 0.4, fill: true, borderWidth: 2, pointRadius: 4, pointBackgroundColor: '#16a34a' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { color: '#64748b' } },
                        x: { grid: { display: false }, ticks: { color: '#64748b' } }
                    },
                    plugins: { legend: { position: 'top', labels: { usePointStyle: true, padding: 20, color: '#475569' } } }
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

        // ==================== CHATBOT FUNCTIONALITY ====================
        let chatOpen = false;
        let chatSessionId = 'session_' + Math.random().toString(36).substr(2, 9);
        let remainingMessages = 8;
        let isTyping = false;

        function toggleChat() {
            chatOpen = !chatOpen;
            const popup = document.getElementById('chat-popup');
            const fab = document.getElementById('chat-fab');

            if (chatOpen) {
                popup.classList.add('active');
                fab.classList.add('active');
                fab.innerHTML = '<svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>';
                document.getElementById('chat-input').focus();
            } else {
                popup.classList.remove('active');
                fab.classList.remove('active');
                fab.innerHTML = '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>';
            }
        }

        function addChatMessage(text, type) {
            const messagesDiv = document.getElementById('chat-messages');
            const msgDiv = document.createElement('div');
            msgDiv.className = 'chat-message ' + type;
            msgDiv.textContent = text;
            messagesDiv.appendChild(msgDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function showTypingIndicator() {
            const messagesDiv = document.getElementById('chat-messages');
            const typingDiv = document.createElement('div');
            typingDiv.id = 'typing-indicator';
            typingDiv.className = 'chat-typing';
            typingDiv.innerHTML = '<span></span><span></span><span></span>';
            messagesDiv.appendChild(typingDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        function hideTypingIndicator() {
            const typingDiv = document.getElementById('typing-indicator');
            if (typingDiv) typingDiv.remove();
        }

        function updateRemainingMessages(count) {
            remainingMessages = count;
            document.getElementById('chat-remaining').textContent = count + ' messages left';
            if (count <= 0) {
                document.getElementById('chat-input').disabled = true;
                document.getElementById('chat-send').disabled = true;
                document.getElementById('chat-input').placeholder = 'Message limit reached';
            }
        }

        async function sendChatMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();

            if (!message || isTyping || remainingMessages <= 0) return;

            input.value = '';
            addChatMessage(message, 'user');

            isTyping = true;
            showTypingIndicator();
            document.getElementById('chat-send').disabled = true;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message, session_id: chatSessionId })
                });

                const data = await response.json();
                hideTypingIndicator();

                if (data.success) {
                    addChatMessage(data.response, 'bot');
                    if (data.remaining_messages !== undefined) {
                        updateRemainingMessages(data.remaining_messages);
                    }
                } else if (data.rate_limited) {
                    addChatMessage(data.error, 'error');
                    updateRemainingMessages(0);
                } else {
                    addChatMessage('Sorry, something went wrong. Please try again.', 'error');
                }
            } catch (err) {
                hideTypingIndicator();
                addChatMessage('Unable to connect. Please check your connection.', 'error');
            }

            isTyping = false;
            if (remainingMessages > 0) {
                document.getElementById('chat-send').disabled = false;
            }
        }

        function handleChatKeypress(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        }

        // Initialize chat with welcome message
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(() => {
                const messagesDiv = document.getElementById('chat-messages');
                if (messagesDiv && messagesDiv.children.length === 0) {
                    addChatMessage("Hello! I'm the Chemical Saver Assistant, created by my master Prabhat. I can help you understand this dosage optimization application. What would you like to know?", 'bot');
                }
            }, 500);
        });
    </script>

    <!-- Floating Chat Button -->
    <button class="chat-fab" id="chat-fab" onclick="toggleChat()" title="Chat with AI Assistant">
        <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
    </button>

    <!-- Chat Popup Window -->
    <div class="chat-popup" id="chat-popup">
        <div class="chat-header">
            <div class="chat-header-avatar">
                <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
            </div>
            <div class="chat-header-info">
                <h4>Chemical Saver Assistant</h4>
                <p>Powered by Claude AI</p>
            </div>
            <div class="chat-remaining" id="chat-remaining">8 messages left</div>
        </div>
        <div class="chat-messages" id="chat-messages"></div>
        <div class="chat-input-area">
            <input type="text" class="chat-input" id="chat-input" placeholder="Ask about Chemical Saver..." onkeypress="handleChatKeypress(event)">
            <button class="chat-send" id="chat-send" onclick="sendChatMessage()">
                <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
            </button>
        </div>
    </div>
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


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    AI Chatbot endpoint using Anthropic Claude API.
    Rate limited to 8 messages per user session.
    """
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('session_id', '')

        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400

        # Generate user hash for rate limiting
        user_ip = request.remote_addr or 'unknown'
        user_hash = hashlib.md5(f"{user_ip}:{session_id}".encode()).hexdigest()

        # Check rate limit
        now = datetime.now()
        if user_hash in chat_rate_limits:
            user_limit = chat_rate_limits[user_hash]
            # Reset if more than 1 hour passed
            if now > user_limit['reset_time']:
                chat_rate_limits[user_hash] = {'count': 0, 'reset_time': now + timedelta(hours=1)}
            elif user_limit['count'] >= CHAT_RATE_LIMIT:
                remaining = int((user_limit['reset_time'] - now).total_seconds() / 60)
                return jsonify({
                    'success': False,
                    'error': f'Rate limit exceeded. You can send {CHAT_RATE_LIMIT} messages per session. Please try again in {remaining} minutes.',
                    'rate_limited': True
                }), 429
        else:
            chat_rate_limits[user_hash] = {'count': 0, 'reset_time': now + timedelta(hours=1)}

        # Increment message count
        chat_rate_limits[user_hash]['count'] += 1
        remaining_messages = CHAT_RATE_LIMIT - chat_rate_limits[user_hash]['count']

        # Check if API key is configured
        if not ANTHROPIC_API_KEY:
            return jsonify({
                'success': True,
                'response': "I'm the Chemical Saver Assistant. The AI service is currently being configured. Please check back later or contact Prabhat for assistance.",
                'remaining_messages': remaining_messages
            }), 200

        # Call Anthropic API
        if not HTTPX_AVAILABLE:
            return jsonify({
                'success': True,
                'response': "I'm the Chemical Saver Assistant. My master Prabhat has created me to help you with this dosage optimization application. How can I assist you with Chemical Saver today?",
                'remaining_messages': remaining_messages
            }), 200

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    'https://api.anthropic.com/v1/messages',
                    headers={
                        'Content-Type': 'application/json',
                        'x-api-key': ANTHROPIC_API_KEY,
                        'anthropic-version': '2023-06-01'
                    },
                    json={
                        'model': 'claude-sonnet-4-20250514',
                        'max_tokens': 300,
                        'system': CHATBOT_SYSTEM_PROMPT,
                        'messages': [
                            {'role': 'user', 'content': message}
                        ]
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    assistant_message = result['content'][0]['text']
                    return jsonify({
                        'success': True,
                        'response': assistant_message,
                        'remaining_messages': remaining_messages
                    }), 200
                else:
                    return jsonify({
                        'success': True,
                        'response': "I apologize, I'm having trouble connecting right now. Please try again or contact Prabhat for assistance with Chemical Saver.",
                        'remaining_messages': remaining_messages
                    }), 200

        except Exception as api_error:
            return jsonify({
                'success': True,
                'response': "I'm the Chemical Saver Assistant created by my master Prabhat. I can help you understand this dosage optimization application for oil & gas production. What would you like to know?",
                'remaining_messages': remaining_messages
            }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
