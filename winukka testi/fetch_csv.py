import requests
from io import StringIO
import pandas as pd

import random

def fetch_sensor_data(url):
    """
    Fetches sensor data from a CSV file located at the given URL.

    Args:
        url (str): The URL of the CSV file.

    Returns:
        dict or None: A dictionary containing the sensor type, sensor value, and unit of measurement.
                      Returns None if an error occurs during the data retrieval.

    Raises:
        requests.HTTPError: If an HTTP error occurs while fetching the CSV file.
        ValueError: If there is an error in parsing the CSV data.
        Exception: If any other error occurs during the data retrieval.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        csv_content = StringIO(response.text)

        # Skipping initial non-data lines to directly read the CSV data part
        # Adjust `skiprows` as needed based on the CSV structure
        df = pd.read_csv(csv_content, delimiter=';', header=0, skiprows=2)

        # Selecting the last row of the DataFrame
        last_row = df.iloc[-1]

        sensor_type = last_row['Process value']  # Assuming 'Process value' column contains the sensor type
        sensor_value = last_row['Measurement value']  # Assuming 'Measurement value' contains the sensor value
        unit = last_row['Unit']  # Unit of measurement

        # Converting sensor_value to float if it's in exponential format
        sensor_value = float(sensor_value)

        return {
            "sensor_type": sensor_type,
            "value": sensor_value,
            "unit": unit
        }

    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except ValueError as ve:
        print(ve)
    except Exception as err:
        print(f"An error occurred: {err}")
    return None


def fetch_sensor_data_mock(url):
    """
    Mock version of fetch_sensor_data for testing purposes.
    Returns a dictionary with random sensor values between 1.5 and 2.5.

    Args:
        url (str): The URL of the CSV file. (Not used in this mock function)

    Returns:
        dict: A dictionary containing the sensor type, sensor value, and unit of measurement.
    """
    # Generate a random float between 1.5 and 2.5 with 3 decimal places
    sensor_value = round(random.uniform(1.5, 2.5), 3)

    return {
        "sensor_type": "Temperature",
        "value": sensor_value,
        "unit": "degC"
    }