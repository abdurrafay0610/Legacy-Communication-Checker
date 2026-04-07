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
    checksum = calculate_checksum(packet[0:len(packet) - 1])
    packet[len(packet) - 1] = checksum
    return packet


def calculate_revs_checksum(numbers):
    """
    Calculates reversed checksum for a list of numbers.
    The reversed checksum is the bitwise NOT of the regular checksum, masked to 8 bits.

    :param numbers: List of integers (0-255)
    :return: Reversed checksum value (0-255)
    """
    if not all(isinstance(num, int) and 0 <= num <= 255 for num in numbers):
        raise ValueError("All elements must be integers between 0 and 255")

    revs_checksum = (~sum(numbers) & 0xFF)
    return revs_checksum


def add_revs_checksum(packet):
    revs_checksum = calculate_revs_checksum(packet[0:len(packet) - 1])
    packet[len(packet) - 1] = revs_checksum
    return packet


def calculate_crc16(numbers):
    """
    Calculates CRC16 (CRC-16/BUYPASS, polynomial 0x8005) for a list of numbers.
    Returns a 16-bit value split into (LSB, MSB).

    :param numbers: List of integers (0-255)
    :return: Tuple (lsb, msb) each 0-255
    """
    if not all(isinstance(num, int) and 0 <= num <= 255 for num in numbers):
        raise ValueError("All elements must be integers between 0 and 255")

    crc = 0x0000
    polynomial = 0x8005

    for byte in numbers:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFFFF

    lsb = crc & 0xFF
    msb = (crc >> 8) & 0xFF
    return lsb, msb


def add_crc16_lsb_msb(packet):
    """
    Appends CRC16 to the last two bytes of the packet in LSB, MSB order.
    The packet must have at least 2 trailing bytes reserved for the CRC.
    """
    lsb, msb = calculate_crc16(packet[0:len(packet) - 2])
    packet[len(packet) - 2] = lsb
    packet[len(packet) - 1] = msb
    return packet


def add_crc16_msb_lsb(packet):
    """
    Appends CRC16 to the last two bytes of the packet in MSB, LSB order.
    The packet must have at least 2 trailing bytes reserved for the CRC.
    """
    lsb, msb = calculate_crc16(packet[0:len(packet) - 2])
    packet[len(packet) - 2] = msb
    packet[len(packet) - 1] = lsb
    return packet


def calculate_crc32(numbers):
    """
    Calculates CRC32 (ISO 3309 / Ethernet, polynomial 0x04C11DB7) for a list of numbers.
    Returns a 32-bit value split into (byte0, byte1, byte2, byte3) from LSB to MSB.

    :param numbers: List of integers (0-255)
    :return: Tuple (b0, b1, b2, b3) each 0-255, b0 is least significant
    """
    if not all(isinstance(num, int) and 0 <= num <= 255 for num in numbers):
        raise ValueError("All elements must be integers between 0 and 255")

    crc = 0xFFFFFFFF
    polynomial = 0xEDB88320  # Reflected polynomial for CRC-32

    for byte in numbers:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ polynomial
            else:
                crc >>= 1

    crc ^= 0xFFFFFFFF  # Final XOR

    b0 = crc & 0xFF
    b1 = (crc >> 8) & 0xFF
    b2 = (crc >> 16) & 0xFF
    b3 = (crc >> 24) & 0xFF
    return b0, b1, b2, b3


def add_crc32_lsb_msb(packet):
    """
    Appends CRC32 to the last four bytes of the packet in LSB-first order.
    The packet must have at least 4 trailing bytes reserved for the CRC.
    """
    b0, b1, b2, b3 = calculate_crc32(packet[0:len(packet) - 4])
    packet[len(packet) - 4] = b0
    packet[len(packet) - 3] = b1
    packet[len(packet) - 2] = b2
    packet[len(packet) - 1] = b3
    return packet


def add_crc32_msb_lsb(packet):
    """
    Appends CRC32 to the last four bytes of the packet in MSB-first order.
    The packet must have at least 4 trailing bytes reserved for the CRC.
    """
    b0, b1, b2, b3 = calculate_crc32(packet[0:len(packet) - 4])
    packet[len(packet) - 4] = b3
    packet[len(packet) - 3] = b2
    packet[len(packet) - 2] = b1
    packet[len(packet) - 1] = b0
    return packet