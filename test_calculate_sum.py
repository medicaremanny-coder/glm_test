import doctest

from calculate_sum import calculate_sum


def run_tests() -> None:
    # Happy-path cases
    assert calculate_sum([1, 2, 3, 4, 5]) == 15
    assert calculate_sum([1.5, 2.5, 3.0]) == 7.0
    assert calculate_sum([1, 2.5, 3]) == 6.5
    assert calculate_sum([]) == 0
    assert calculate_sum([-5, 5]) == 0
    assert calculate_sum([True, False, 1]) == 2  # bool is subclass of int

    # Error cases
    try:
        calculate_sum(None)
        raise AssertionError("Expected ValueError for None input")
    except ValueError:
        pass

    try:
        calculate_sum("not a list")
        raise AssertionError("Expected TypeError for non-list input")
    except TypeError:
        pass

    try:
        calculate_sum([1, 2, "three"])
        raise AssertionError("Expected TypeError for non-numeric element")
    except TypeError:
        pass

    print("All assertion tests passed.")


if __name__ == "__main__":
    run_tests()
    results = doctest.testmod(
        __import__("calculate_sum"), verbose=False
    )
    print(f"Doctests: {results.attempted} run, {results.failed} failed.")
    if results.failed == 0:
        print("All doctests passed.")
