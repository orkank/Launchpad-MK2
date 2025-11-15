"""Flask API for Launchpad MK2 control."""

from .flask_app import create_app, get_app_instance

__all__ = ['create_app', 'get_app_instance']
