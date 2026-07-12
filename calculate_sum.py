from typing import List, Union


def calculate_sum(numbers: List[Union[int, float]]) -> Union[int, float]:
    """Calculate the sum of a list of numbers.

    Args:
        numbers: A list of numeric values (int or float) to be summed.

    Returns:
        The sum of all numbers in the list. Returns 0 for an empty list.
        The return type matches the dominant type in the input
        (int if all inputs are int, float if any input is float).

    Raises:
        TypeError: If numbers is not a list or contains non-numeric types.
        ValueError: If numbers is None.

    Examples:
        Basic usage with integers:
        >>> calculate_sum([1, 2, 3, 4, 5])
        15

        Usage with floats:
        >>> calculate_sum([1.5, 2.5, 3.0])
        7.0

        Mixed types:
        >>> calculate_sum([1, 2.5, 3])
        6.5

        Empty list:
        >>> calculate_sum([])
        0

        Invalid input - not a list:
        >>> calculate_sum("not a list")
        Traceback (most recent call last):
            ...
        TypeError: Input must be a list, got str

        Invalid input - non-numeric values:
        >>> calculate_sum([1, 2, "three"])
        Traceback (most recent call last):
            ...
        TypeError: All elements must be numeric (int or float), got str at index 2
    """
    # Validate input is not None
    if numbers is None:
        raise ValueError("Input list cannot be None")

    # Validate input type
    if not isinstance(numbers, list):
        raise TypeError(
            f"Input must be a list, got {type(numbers).__name__}"
        )

    # Validate all elements are numeric
    for index, item in enumerate(numbers):
        if not isinstance(item, (int, float)):
            raise TypeError(
                f"All elements must be numeric (int or float), "
                f"got {type(item).__name__} at index {index}"
            )

    # Return 0 for empty list (consistent with sum() built-in)
    if not numbers:
        return 0

    # Calculate and return the sum
    return sum(numbers)
