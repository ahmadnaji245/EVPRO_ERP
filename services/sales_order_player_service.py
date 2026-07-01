from models.sales_order_player import SalesOrderPlayer


def list_players_for_design(design_id):
    return (
        SalesOrderPlayer.query.filter_by(sales_order_design_id=design_id)
        .order_by(SalesOrderPlayer.sort_order, SalesOrderPlayer.id)
        .all()
    )
