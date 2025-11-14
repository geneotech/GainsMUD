#!/usr/bin/env python3
"""
Script to fetch the current total GNS supply from gains.trade
"""

import requests
import json


def get_gns_total_supply():
    """
    Fetch the current total GNS supply from the Gains Trade API.

    Returns:
        float: The current total GNS supply
    """
    try:
        # API endpoint for Arbitrum network stats
        url = "https://backend-polygon.gains.trade/stats"

        # Make the request
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse JSON response
        data = response.json()

        # Get the most recent entry (first item in the stats array)
        if data and 'stats' in data and len(data['stats']) > 0:
            latest_stats = data['stats'][0]
            total_supply = latest_stats['token_supply']
            date = latest_stats['date']

            print(f"Total GNS Supply: {total_supply:,.0f}")
            print(f"As of: {date}")

            return total_supply
        else:
            print("Error: No data found in response")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Error parsing response: {e}")
        return None


if __name__ == "__main__":
    supply = get_gns_total_supply()
    if supply:
        print(f"\nCurrent total supply: {supply}")
