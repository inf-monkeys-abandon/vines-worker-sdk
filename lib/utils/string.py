import string
import random


def generate_random_string(length):
    # Define the characters that can be used in the random string
    characters = string.ascii_letters + string.digits

    # Generate a random string of specified length
    random_string = ''.join(random.choice(characters) for _ in range(length))

    return random_string
