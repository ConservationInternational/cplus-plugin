# -*- coding: utf-8 -*-
"""
Contains functions for financial computations.
"""


def compute_discount_value(
    revenue: float, cost: float, year: int, discount: float
) -> float:
    """Calculates the discounted value for the given year.

    :param revenue: Projected total revenue.
    :type revenue: float

    :param cost: Projected total costs.
    :type cost: float

    :param year: Relative year i.e. between 1 and 99.
    :type year: int

    :param discount: Discount value as a percent i.e. between 0 and 100.
    :type discount: float

    :returns: The discounted value for the given year.
    :rtype: float
    """
    return (revenue - cost) / ((1 + discount / 100.0) ** (year - 1))
