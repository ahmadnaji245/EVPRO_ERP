from models.sales_order_design import SalesOrderDesign


def list_designs_for_order(sales_order_id):
    return (
        SalesOrderDesign.query.filter_by(sales_order_id=sales_order_id)
        .order_by(SalesOrderDesign.sort_order, SalesOrderDesign.id)
        .all()
    )
