# SI 201 HW4 (Library Checkout System)
# Your name: Annika Gurnani 
# Your student id: 29363715
# Your email: agurnani@umich.edu
# Who or what you worked with on this homework (including generative AI like ChatGPT): n/a
# If you worked with generative AI also add a statement for how you used it. used ChatGPT for hints on debugging
# e.g.:
# Asked ChatGPT for hints on debugging and for suggestions on overall code structure
#
# Did your use of GenAI on this assignment align with your goals and guidelines in your Gen AI contract? If not, why? yes
#
# --- ARGUMENTS & EXPECTED RETURN VALUES PROVIDED --- #
# --- SEE INSTRUCTIONS FOR FULL DETAILS ON METHOD IMPLEMENTATION --- #

from bs4 import BeautifulSoup
import re
import os
import csv
import unittest
import requests  # kept for extra credit parity


# IMPORTANT NOTE:
"""
If you are getting "encoding errors" while trying to open, read, or write from a file, add the following argument to any of your open() functions:
    encoding="utf-8-sig"
"""


def load_listing_results(html_path) -> list[tuple]:
    """
    Load file data from html_path and parse through it to find listing titles and listing ids.

    Args:
        html_path (str): The path to the HTML file containing the search results

    Returns:
        list[tuple]: A list of tuples containing (listing_title, listing_id)
    """
    with open(html_path, encoding="utf-8-sig") as f:
        soup = BeautifulSoup(f, "html.parser")

    results = []

    listings = soup.find_all("div", class_="t1jojoys dir dir-ltr")

    for listing in listings:
        title = listing.get_text().strip()

        parent = listing.find_parent("a")
        if parent and "href" in parent.attrs:
            listing_id = parent["href"].split("/")[-1]
            results.append((title, listing_id))

    return results


def get_listing_details(listing_id) -> dict:
    """
    Parse through listing_<id>.html to extract listing details.

    Args:
        listing_id (str): The listing id of the Airbnb listing

    Returns:
        dict: Nested dictionary in the format:
        {
            "<listing_id>": {
                "policy_number": str,
                "host_type": str,
                "host_name": str,
                "room_type": str,
                "location_rating": float
            }
        }
    """
    base_path = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(base_path, "html_files", f"listing_{listing_id}.html")

    with open(file_path, encoding="utf-8-sig") as f:
        soup = BeautifulSoup(f, "html.parser")

    data = {}

    # policy number
    policy_tag = soup.find(string=re.compile("Policy"))
    policy_number = "Pending"
    if policy_tag:
        match = re.search(r"(STR-\d+)", policy_tag)
        if match:
            policy_number = match.group()

    # host type
    host_type = "Regular"
    if soup.find(string=re.compile("Superhost")):
        host_type = "Superhost"

    # host name
    host_name = ""
    host_tag = soup.find("div", class_=re.compile("host"))
    if host_tag:
        host_name = host_tag.get_text().strip()

    # room type
    room_type = ""
    room_tag = soup.find(string=re.compile("room"))
    if room_tag:
        room_type = room_tag.strip()

    # location rating
    rating = 0.0
    rating_tag = soup.find(string=re.compile("Location"))
    if rating_tag:
        match = re.search(r"(\d\.\d)", rating_tag)
        if match:
            rating = float(match.group())

    data[listing_id] = {
        "policy_number": policy_number,
        "host_type": host_type,
        "host_name": host_name,
        "room_type": room_type,
        "location_rating": rating
    }
    return data


def create_listing_database(html_path) -> list[tuple]:
    """
    Use prior functions to gather all necessary information and create a database of listings.

    Args:
        html_path (str): The path to the HTML file containing the search results

    Returns:
        list[tuple]: A list of tuples. Each tuple contains:
        (listing_title, listing_id, policy_number, host_type, host_name, room_type, location_rating)
    """
    listings = load_listing_results(html_path)
    database = []

    for title, listing_id in listings:
        details = get_listing_details(listing_id)[listing_id]

        database.append((
            title,
            listing_id,
            details["policy_number"],
            details["host_type"],
            details["host_name"],
            details["room_type"],
            details["location_rating"]
        ))

    return database


def output_csv(data, filename) -> None:
    """
    Write data to a CSV file with the provided filename.

    Sort by Location Rating (descending).

    Args:
        data (list[tuple]): A list of tuples containing listing information
        filename (str): The name of the CSV file to be created and saved to

    Returns:
        None
    """
    sorted_data = sorted(data, key=lambda x: x[-1], reverse=True)

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        writer.writerow([
            "title", "id", "policy_number",
            "host_type", "host_name",
            "room_type", "location_rating"
        ])

        for row in sorted_data:
            writer.writerow(row)


def avg_location_rating_by_room_type(data) -> dict:
    """
    Calculate the average location_rating for each room_type.

    Excludes rows where location_rating == 0.0 (meaning the rating
    could not be found in the HTML).

    Args:
        data (list[tuple]): The list returned by create_listing_database()

    Returns:
        dict: {room_type: average_location_rating}
    """
    totals = {}
    counts = {}

    for row in data:
        room_type = row[5]
        rating = row[6]

        if rating == 0.0:
            continue

        if room_type not in totals:
            totals[room_type] = 0
            counts[room_type] = 0

        totals[room_type] += rating
        counts[room_type] += 1

    averages = {}
    for room_type in totals:
        averages[room_type] = round(totals[room_type] / counts[room_type], 1)

    return averages


def validate_policy_numbers(data) -> list[str]:
    """
    Validate policy_number format for each listing in data.
    Ignore "Pending" and "Exempt" listings.

    Args:
        data (list[tuple]): A list of tuples returned by create_listing_database()

    Returns:
        list[str]: A list of listing_id values whose policy numbers do NOT match the valid format
    """
    invalid = []

    pattern = r"^STR-\d+$"

    for row in data:
        listing_id = row[1]
        policy = row[2]

        if policy in ["Pending", "Exempt"]:
            continue

        if not re.match(pattern, policy):
            invalid.append(listing_id)

    return invalid


# EXTRA CREDIT
def google_scholar_searcher(query):
    """
    EXTRA CREDIT

    Args:
        query (str): The search query to be used on Google Scholar
    Returns:
        List of titles on the first page (list)
    """
    # TODO: Implement checkout logic following the instructions
    # ==============================
    # YOUR CODE STARTS HERE
    # ==============================
    pass
    # ==============================
    # YOUR CODE ENDS HERE
    # ==============================


class TestCases(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.abspath(os.path.dirname(__file__))
        self.search_results_path = os.path.join(self.base_dir, "html_files", "search_results.html")

        self.listings = load_listing_results(self.search_results_path)
        self.detailed_data = create_listing_database(self.search_results_path)

    def test_load_listing_results(self):
        # TODO: Check that the number of listings extracted is 18.
        # TODO: Check that the FIRST (title, id) tuple is  ("Loft in Mission District", "1944564").
        
        self.assertEqual(len(self.listings), 18)
        self.assertEqual(self.listings[0], ("Loft in Mission District", "1944564"))

    def test_get_listing_details(self):
        html_list = ["467507", "1550913", "1944564", "4614763", "6092596"]

        # TODO: Call get_listing_details() on each listing id above and save results in a list.

        # TODO: Spot-check a few known values by opening the corresponding listing_<id>.html files.
        # 1) Check that listing 467507 has the correct policy number "STR-0005349".
        # 2) Check that listing 1944564 has the correct host type "Superhost" and room type "Entire Room".
        # 3) Check that listing 1944564 has the correct location rating 4.9.
        pass

    def test_create_listing_database(self):
        # TODO: Check that each tuple in detailed_data has exactly 7 elements:
        # (listing_title, listing_id, policy_number, host_type, host_name, room_type, location_rating)

        # TODO: Spot-check the LAST tuple is ("Guest suite in Mission District", "467507", "STR-0005349", "Superhost", "Jennifer", "Entire Room", 4.8).
        pass

    def test_output_csv(self):
        out_path = os.path.join(self.base_dir, "test.csv")

        # TODO: Call output_csv() to write the detailed_data to a CSV file.
        # TODO: Read the CSV back in and store rows in a list.
        # TODO: Check that the first data row matches ["Guesthouse in San Francisco", "49591060", "STR-0000253", "Superhost", "Ingrid", "Entire Room", "5.0"].

        os.remove(out_path)

    def test_avg_location_rating_by_room_type(self):
        # TODO: Call avg_location_rating_by_room_type() and save the output.
        # TODO: Check that the average for "Private Room" is 4.9.
        pass

    def test_validate_policy_numbers(self):
        # TODO: Call validate_policy_numbers() on detailed_data and save the result into a variable invalid_listings.
        # TODO: Check that the list contains exactly "16204265" for this dataset.
        pass


def main():
    detailed_data = create_listing_database(os.path.join("html_files", "search_results.html"))
    output_csv(detailed_data, "airbnb_dataset.csv")


if __name__ == "__main__":
    main()
    unittest.main(verbosity=2)