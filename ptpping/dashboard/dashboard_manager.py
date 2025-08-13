"""
Dashboard manager for PTPPing.
Handles Grafana dashboard provisioning and management.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from ..core.config import Config


class DashboardManager:
    """Manages Grafana dashboards for PTPPing."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self._running = False
        self._headers = {
            'Authorization': f'Bearer {config.grafana.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Dashboard templates
        self._dashboard_templates = self._load_dashboard_templates()
    
    def _load_dashboard_templates(self) -> Dict[str, Any]:
        """Load dashboard templates from JSON files."""
        templates = {}
        templates_dir = Path(__file__).parent / "templates"
        
        if templates_dir.exists():
            for template_file in templates_dir.glob("*.json"):
                try:
                    with open(template_file, 'r') as f:
                        template_name = template_file.stem
                        templates[template_name] = json.load(f)
                    self.logger.debug(f"Loaded dashboard template: {template_name}")
                except Exception as e:
                    self.logger.error(f"Failed to load template {template_file}: {e}")
        
        return templates
    
    def start(self) -> None:
        """Start the dashboard manager."""
        if self._running:
            self.logger.warning("Dashboard manager already running")
            return
        
        self._running = True
        
        try:
            # Test Grafana connection
            self._test_connection()
            
            # Provision dashboards
            self._provision_dashboards()
            
            self.logger.info("Dashboard manager started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start dashboard manager: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the dashboard manager."""
        self._running = False
        self.logger.info("Dashboard manager stopped")
    
    def _test_connection(self) -> None:
        """Test connection to Grafana."""
        try:
            response = requests.get(
                f"{self.config.grafana.url}/api/health",
                headers=self._headers,
                timeout=10
            )
            
            if response.status_code == 200:
                health_data = response.json()
                self.logger.info(f"Grafana connection established: {health_data.get('version', 'unknown')}")
            else:
                raise Exception(f"Grafana health check failed: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Grafana: {e}")
            raise
    
    def _provision_dashboards(self) -> None:
        """Provision all dashboard templates."""
        for template_name, template in self._dashboard_templates.items():
            try:
                self._provision_dashboard(template_name, template)
            except Exception as e:
                self.logger.error(f"Failed to provision dashboard {template_name}: {e}")
    
    def _provision_dashboard(self, name: str, template: Dict[str, Any]) -> None:
        """Provision a single dashboard."""
        try:
            # Customize template with configuration
            customized_template = self._customize_template(template)
            
            # Check if dashboard exists
            existing_dashboard = self._get_dashboard_by_name(name)
            
            if existing_dashboard:
                # Update existing dashboard
                self._update_dashboard(existing_dashboard['id'], customized_template)
                self.logger.info(f"Updated dashboard: {name}")
            else:
                # Create new dashboard
                self._create_dashboard(customized_template)
                self.logger.info(f"Created dashboard: {name}")
                
        except Exception as e:
            self.logger.error(f"Failed to provision dashboard {name}: {e}")
            raise
    
    def _customize_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Customize dashboard template with configuration values."""
        customized = template.copy()
        
        # Replace placeholders with actual values
        template_str = json.dumps(customized)
        
        # Replace common placeholders
        replacements = {
            '{{INFLUXDB_URL}}': self.config.influxdb.url,
            '{{INFLUXDB_DATABASE}}': self.config.influxdb.database,
            '{{INFLUXDB_ORG}}': self.config.influxdb.organization,
            '{{SWITCH_NAME}}': self.config.network.switch_name,
            '{{HOST_NAME}}': self.config.network.host_name,
            '{{VLAN_ID}}': str(self.config.network.vlan_id)
        }
        
        for placeholder, value in replacements.items():
            template_str = template_str.replace(placeholder, value)
        
        return json.loads(template_str)
    
    def _get_dashboard_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get dashboard by name from Grafana."""
        try:
            response = requests.get(
                f"{self.config.grafana.url}/api/search",
                headers=self._headers,
                params={'query': name},
                timeout=10
            )
            
            if response.status_code == 200:
                dashboards = response.json()
                for dashboard in dashboards:
                    if dashboard.get('title') == name:
                        return dashboard
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get dashboard {name}: {e}")
            return None
    
    def _create_dashboard(self, dashboard_data: Dict[str, Any]) -> None:
        """Create a new dashboard in Grafana."""
        try:
            payload = {
                'dashboard': dashboard_data,
                'overwrite': False
            }
            
            response = requests.post(
                f"{self.config.grafana.url}/api/dashboards/db",
                headers=self._headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to create dashboard: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Failed to create dashboard: {e}")
            raise
    
    def _update_dashboard(self, dashboard_id: int, dashboard_data: Dict[str, Any]) -> None:
        """Update an existing dashboard in Grafana."""
        try:
            # Get current dashboard version
            response = requests.get(
                f"{self.config.grafana.url}/api/dashboards/uid/{dashboard_data.get('uid', '')}",
                headers=self._headers,
                timeout=10
            )
            
            if response.status_code == 200:
                current_dashboard = response.json()['dashboard']
                dashboard_data['version'] = current_dashboard['version'] + 1
            else:
                dashboard_data['version'] = 1
            
            payload = {
                'dashboard': dashboard_data,
                'overwrite': True
            }
            
            response = requests.post(
                f"{self.config.grafana.url}/api/dashboards/db",
                headers=self._headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to update dashboard: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Failed to update dashboard: {e}")
            raise
    
    def get_dashboard_status(self) -> Dict[str, Any]:
        """Get status of all dashboards."""
        status = {
            'running': self._running,
            'grafana_connected': False,
            'dashboards_provisioned': 0,
            'total_templates': len(self._dashboard_templates)
        }
        
        try:
            # Test connection
            response = requests.get(
                f"{self.config.grafana.url}/api/health",
                headers=self._headers,
                timeout=5
            )
            
            if response.status_code == 200:
                status['grafana_connected'] = True
                
                # Count provisioned dashboards
                response = requests.get(
                    f"{self.config.grafana.url}/api/search",
                    headers=self._headers,
                    params={'type': 'dash-db'},
                    timeout=10
                )
                
                if response.status_code == 200:
                    dashboards = response.json()
                    ptp_dashboards = [d for d in dashboards if 'ptp' in d.get('title', '').lower()]
                    status['dashboards_provisioned'] = len(ptp_dashboards)
                    
        except Exception as e:
            self.logger.debug(f"Error getting dashboard status: {e}")
        
        return status
    
    def refresh_dashboards(self) -> None:
        """Refresh all dashboards."""
        try:
            self._provision_dashboards()
            self.logger.info("Dashboards refreshed successfully")
        except Exception as e:
            self.logger.error(f"Failed to refresh dashboards: {e}")
            raise
