from .auth import register_auth_routes
from .checkout import register_checkout_routes
from .dashboard import register_dashboard_routes
from .marketplace import register_marketplace_routes
from .messages import register_message_routes
from .offers import register_offer_routes
from .service import register_service_routes


def register_routes(app):
    register_auth_routes(app)
    register_marketplace_routes(app)
    register_offer_routes(app)
    register_message_routes(app)
    register_checkout_routes(app)
    register_service_routes(app)
    register_dashboard_routes(app)
