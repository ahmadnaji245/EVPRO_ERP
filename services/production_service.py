from models.sales_order import SalesOrder


def list_production_orders():
    return SalesOrder.query.filter_by(is_deleted=False, approval_status="approved").order_by(SalesOrder.created_at.desc()).all()
