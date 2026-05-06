from mcp_server import ModelQueryToolset
from apps.vendors.models import PaymentMethod, Vendor


class VendorMCP(ModelQueryToolset):
    model = Vendor

class PaymentMethodMCP(ModelQueryToolset):
    model = PaymentMethod
    