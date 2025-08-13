#!/usr/bin/env python3
"""
PTPPing - Network-wide Audio Latency Probe
Main orchestrator script for audio generation, capture, and dashboard management.
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

import click
import toml

from ptpping.core.config import Config
from ptpping.core.logger import setup_logging
from ptpping.generator.audio_generator import AudioGenerator
from ptpping.capture.audio_capture import AudioCapture
from ptpping.dashboard.dashboard_manager import DashboardManager


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logging.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


@click.command()
@click.option('--role', type=click.Choice(['generator', 'capture', 'dashboard']), 
              required=True, help='Role to run')
@click.option('--config', '-c', default='config.toml', 
              help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--daemon', '-d', is_flag=True, help='Run as daemon')
def main(role: str, config: str, verbose: bool, daemon: bool):
    """PTPPing - Network-wide Audio Latency Probe"""
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Load configuration
        config_path = Path(config)
        if not config_path.exists():
            click.echo(f"Error: Configuration file {config} not found", err=True)
            sys.exit(1)
        
        cfg = Config.from_file(config_path)
        
        # Setup logging
        log_level = logging.DEBUG if verbose else getattr(logging, cfg.logging.level.upper())
        setup_logging(cfg.logging, log_level)
        
        logging.info(f"Starting PTPPing in {role} mode")
        logging.info(f"Configuration loaded from {config_path}")
        
        # Run the appropriate role
        if role == 'generator':
            run_generator(cfg)
        elif role == 'capture':
            run_capture(cfg)
        elif role == 'dashboard':
            run_dashboard(cfg)
            
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        if verbose:
            logging.exception("Full traceback:")
        sys.exit(1)


def run_generator(config: Config):
    """Run the audio generator role."""
    logging.info("Starting audio generator...")
    
    generator = AudioGenerator(config)
    
    try:
        generator.start()
        logging.info("Audio generator started successfully")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logging.info("Stopping audio generator...")
    finally:
        generator.stop()
        logging.info("Audio generator stopped")


def run_capture(config: Config):
    """Run the audio capture role."""
    logging.info("Starting audio capture...")
    
    capture = AudioCapture(config)
    
    try:
        capture.start()
        logging.info("Audio capture started successfully")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logging.info("Stopping audio capture...")
    finally:
        capture.stop()
        logging.info("Audio capture stopped")


def run_dashboard(config: Config):
    """Run the dashboard management role."""
    logging.info("Starting dashboard manager...")
    
    dashboard = DashboardManager(config)
    
    try:
        dashboard.start()
        logging.info("Dashboard manager started successfully")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logging.info("Stopping dashboard manager...")
    finally:
        dashboard.stop()
        logging.info("Dashboard manager stopped")


if __name__ == '__main__':
    main()
