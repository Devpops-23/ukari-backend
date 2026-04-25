def calculate_fees(item_price: float):
    """
    Simple fee calculation logic.
    Adjust this as needed for your marketplace rules.
    """

    platform_fee = round(item_price * 0.10, 2)   # 10% platform fee
    traveler_fee = round(item_price * 0.15, 2)   # 15% traveler fee
    total_charged = round(item_price + platform_fee + traveler_fee, 2)

    return {
        "platform_fee": platform_fee,
        "traveler_fee": traveler_fee,
        "total_charged": total_charged,
    }
