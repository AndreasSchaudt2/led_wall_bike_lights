"""
Simple web server for Wi-Fi setup and control.
Runs on AP interface for initial configuration.
"""

import logging
import json
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from flask import Flask, render_template, request, jsonify
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    logger.warning("Flask not available, web server disabled")


class WebServer:
    """
    Lightweight web server for setup and control.
    """
    
    def __init__(self, config_manager, wifi_service, port: int = 5000):
        """
        Initialize web server.
        
        Args:
            config_manager: ConfigManager instance
            wifi_service: WiFiService instance
            port: Port to listen on (default 5000)
        """
        self.config_manager = config_manager
        self.wifi_service = wifi_service
        self.port = port
        self.app = None
        self.is_running = False
        
        if HAS_FLASK:
            self._setup_flask()
        
        logger.info(f"Web server initialized on port {port}")
    
    def _setup_flask(self) -> None:
        """Set up Flask application."""
        self.app = Flask(__name__, 
                        template_folder=Path(__file__).parent / 'templates')
        
        # Routes
        @self.app.route('/')
        def index():
            return render_template('setup.html')
        
        @self.app.route('/api/status')
        def status():
            connected = self.wifi_service.is_connected()
            info = self.wifi_service.get_connection_info() or {}
            return jsonify({
                'connected': connected,
                'ap_mode': self.wifi_service.is_ap_mode,
                'info': info
            })
        
        @self.app.route('/api/networks')
        def networks():
            # TODO: Implement Wi-Fi scan
            return jsonify({'networks': []})
        
        @self.app.route('/api/connect', methods=['POST'])
        def connect():
            data = request.get_json()
            ssid = data.get('ssid')
            password = data.get('password', '')
            
            if not ssid:
                return jsonify({'error': 'SSID required'}), 400
            
            success, message = self.wifi_service.connect_result(ssid, password)
            
            if success:
                # Save credentials to config
                self.config_manager.config['wifi']['ssid'] = ssid
                self.config_manager.config['wifi']['password'] = password
                self.config_manager.save()
                
                return jsonify({'success': True, 'message': 'Connected'})
            else:
                return jsonify({'success': False, 'error': message}), 500
        
        logger.info("Flask app configured")
    
    def start(self) -> bool:
        """
        Start web server.
        
        Returns:
            True if started successfully
        """
        if not HAS_FLASK:
            logger.error("Flask not available, cannot start web server")
            return False
        
        try:
            logger.info(f"Starting web server on 0.0.0.0:{self.port}")
            self.is_running = True
            self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
            return True
        
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            return False
        finally:
            self.is_running = False
    
    def stop(self) -> None:
        """Stop web server."""
        self.is_running = False
        logger.info("Web server stopped")
