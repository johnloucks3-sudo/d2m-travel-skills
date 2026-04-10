def factorial(n):
    """Calculate the factorial of a number recursively.

    Args:
        n (int): The number to calculate factorial for

    Returns:
        int: The factorial of n

    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    elif n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)


# Example usage
if __name__ == "__main__":
    print(f"Factorial of 5: {factorial(5)}")
    print(f"Factorial of 0: {factorial(0)}")
    print(f"Factorial of 1: {factorial(1)}")
