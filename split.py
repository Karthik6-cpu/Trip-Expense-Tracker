"""Calculation utilities for expense splitting, amounts, and debt simplification."""

from decimal import Decimal, InvalidOperation


def friend_and_organizer_shares(amount_cents, friend_count):
    """Return the cents each selected friend owes, and the organizer's own cents.
    
    Compatible with PRD: Leftover cents stay with the organizer.
    """
    people = friend_count + 1
    friend_share = amount_cents // people
    organizer_share = amount_cents - friend_share * friend_count
    return friend_share, organizer_share


def format_cents(cents):
    """Show whole cents as a two-decimal amount string."""
    sign = "-" if cents < 0 else ""
    abs_cents = abs(cents)
    return f"{sign}{abs_cents // 100}.{abs_cents % 100:02d}"


def parse_amount_to_cents(amount):
    """Parse string, int, or float amount into whole cents.
    
    Returns integer cents, or raises ValueError if invalid.
    """
    if isinstance(amount, int):
        return amount
    if isinstance(amount, float):
        amount = f"{amount:.2f}"
    if not isinstance(amount, str):
        raise ValueError("Invalid amount format.")
    
    clean = amount.strip()
    if not clean:
        raise ValueError("Amount cannot be empty.")
    
    try:
        dec = Decimal(clean)
    except InvalidOperation:
        raise ValueError("Amount must be a valid number.")
    
    # Check max 2 decimal places
    parts = clean.split(".")
    if len(parts) == 2 and len(parts[1]) > 2:
        raise ValueError("Amount can have at most two decimal places.")
    
    cents = int((dec * 100).to_integral_value())
    return cents


def calculate_splits(amount_cents, payer_id, participants, split_type="equal", custom_values=None):
    """Calculate the share in cents for each participant.
    
    Parameters:
      amount_cents: int
      payer_id: int (0 for organizer, or friend_id)
      participants: list of int (person ids participating, can include 0)
      split_type: 'equal' | 'exact' | 'percent' | 'shares'
      custom_values: dict {person_id: value} (for exact, percent, or shares)
      
    Returns:
      dict {person_id: share_in_cents}
    """
    if not participants:
        raise ValueError("At least one person must participate in the expense.")
    
    n = len(participants)
    splits = {}
    
    if split_type == "equal":
        base_share = amount_cents // n
        remainder = amount_cents - (base_share * n)
        
        for person_id in participants:
            splits[person_id] = base_share
            
        # Distribute leftover cents: give to payer if in participants, else first participant
        if remainder > 0:
            target = payer_id if payer_id in participants else participants[0]
            splits[target] += remainder
            
    elif split_type == "exact":
        if not custom_values:
            raise ValueError("Exact amounts must be provided for all participants.")
        total_assigned = 0
        for p in participants:
            val = custom_values.get(str(p), custom_values.get(p, 0))
            cents = parse_amount_to_cents(val) if not isinstance(val, int) else val
            if cents < 0:
                raise ValueError("Share amount cannot be negative.")
            splits[p] = cents
            total_assigned += cents
            
        if total_assigned != amount_cents:
            diff = format_cents(abs(amount_cents - total_assigned))
            raise ValueError(f"Sum of exact shares does not match total expense amount (difference: {diff}).")
            
    elif split_type == "percent":
        if not custom_values:
            raise ValueError("Percentages must be provided for all participants.")
        total_percent = Decimal(0)
        for p in participants:
            pct = Decimal(str(custom_values.get(str(p), custom_values.get(p, 0))))
            if pct < 0:
                raise ValueError("Percentage cannot be negative.")
            total_percent += pct
            
        if abs(total_percent - Decimal(100)) > Decimal("0.05"):
            raise ValueError(f"Percentages must sum to 100% (currently {total_percent}%).")
            
        allocated = 0
        for p in participants:
            pct = Decimal(str(custom_values.get(str(p), custom_values.get(p, 0))))
            share = int((Decimal(amount_cents) * pct / Decimal(100)).to_integral_value())
            splits[p] = share
            allocated += share
            
        diff = amount_cents - allocated
        if diff != 0:
            target = payer_id if payer_id in participants else participants[0]
            splits[target] += diff
            
    elif split_type == "shares":
        if not custom_values:
            raise ValueError("Share weights must be provided for all participants.")
        total_weights = Decimal(0)
        for p in participants:
            w = Decimal(str(custom_values.get(str(p), custom_values.get(p, 1))))
            if w <= 0:
                raise ValueError("Share weight must be greater than zero.")
            total_weights += w
            
        if total_weights <= 0:
            raise ValueError("Total shares must be greater than zero.")
            
        allocated = 0
        for p in participants:
            w = Decimal(str(custom_values.get(str(p), custom_values.get(p, 1))))
            share = int((Decimal(amount_cents) * w / total_weights).to_integral_value())
            splits[p] = share
            allocated += share
            
        diff = amount_cents - allocated
        if diff != 0:
            target = payer_id if payer_id in participants else participants[0]
            splits[target] += diff
    else:
        raise ValueError(f"Unknown split type: {split_type}")
        
    return splits


def simplify_debts(net_balances):
    """Simplify multi-party debts using the min-cash-flow greedy algorithm.
    
    Parameters:
      net_balances: dict {person_id: net_cents}
        Positive net_cents = creditor (owed money)
        Negative net_cents = debtor (owes money)
        
    Returns:
      list of dict [{'from_id': debtor, 'to_id': creditor, 'amount_cents': cents, 'amount': 'XX.XX'}]
    """
    # Separate into debtors and creditors
    debtors = []  # will store [person_id, amount_owed_positive]
    creditors = []  # will store [person_id, amount_to_receive_positive]
    
    for person_id, net in net_balances.items():
        if net < -1:  # ignore sub-cent rounding
            debtors.append([person_id, -net])
        elif net > 1:
            creditors.append([person_id, net])
            
    transactions = []
    
    # Sort descending by balance to match largest balances first
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)
    
    d_idx = 0
    c_idx = 0
    
    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor_id, debt = debtors[d_idx]
        creditor_id, credit = creditors[c_idx]
        
        amount = min(debt, credit)
        if amount > 0:
            transactions.append({
                "from_id": debtor_id,
                "to_id": creditor_id,
                "amount_cents": amount,
                "amount": format_cents(amount),
            })
            
        debtors[d_idx][1] -= amount
        creditors[c_idx][1] -= amount
        
        if debtors[d_idx][1] <= 0:
            d_idx += 1
        if creditors[c_idx][1] <= 0:
            c_idx += 1
            
    return transactions
