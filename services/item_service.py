from models import MasterItem


def item_components(item_name):
    parts = [part.strip() for part in str(item_name or "").split("+")]
    return [part for part in parts if part]


def qc_enabled_components_for_order(order):
    active_qc = {
        item.name.casefold(): item
        for item in MasterItem.query.filter_by(status="active", perlu_qc=True).all()
    }
    components = []
    seen = set()
    for design in order.designs:
        for component in item_components(design.item_name):
            item = active_qc.get(component.casefold())
            if not item:
                continue
            key = item.name.casefold()
            if key not in seen:
                components.append(item.name)
                seen.add(key)
    return components


def design_components(design):
    return item_components(design.item_name)


def component_key(component):
    return str(component or "").strip().casefold()
