def calculate_checksum(numbers):
    """
    Calculates checksum for a list of numbers.
    The checksum is the sum of all numbers modulo 256.
    
    :param numbers: List of integers
    :return: Checksum value (0-255)
    """
    if not all(isinstance(num, int) and 0 <= num <= 255 for num in numbers):
        raise ValueError("All elements must be integers between 0 and 255")

    checksum = sum(numbers) % 256
    return checksum
    
def add_checksum(packet):
    checksum = calculate_checksum(packet[0:len(packet)-1])
    packet[len(packet)-1] = checksum
    
    return packet