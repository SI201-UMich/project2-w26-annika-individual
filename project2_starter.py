# SI 201 HW4 (Library Checkout System)
# Your name: Annika Gurnani 
# Your student id: 29363715
# Your email: agurnani@umich.edu
# Who or what you worked with on this homework (including generative AI like ChatGPT): n/a
# If you worked with generative AI also add a statement for how you used it. asked ChatGPT for hints on debugging
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

    with open(html_path, "r", encoding="utf-8-sig") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    results = []
    title_divs = soup.find_all("div", {"data-testid": "listing-card-title"})
    for div in title_divs:
        listing_title = div.get_text().strip()
        listing_id = div.get("id", "").replace("title_", "")
        results.append((listing_title, listing_id))

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
    base_dir = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(base_dir, "html_files", f"listing_{listing_id}.html")

    with open(file_path, "r", encoding="utf-8-sig") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    policy_number = ""
    items = soup.find_all("li", class_="f19phm7j")

    for item in items:
        text = item.get_text()
        if "Policy" in text or "License" in text:
            span = item.find("span", class_="ll4r2nl")

            if span:
                policy_number = span.get_text().strip().replace("\ufeff", "")
            else:
                policy_number = text.replace("Policy number:", "").replace(
                    "License number:", ""
                ).strip()

            lower_policy = policy_number.lower()
            if "pending" in lower_policy:
                policy_number = "Pending"
            elif "exempt" in lower_policy:
                policy_number = "Exempt"
            break

    if soup.find(string=lambda t: t and t.strip() == "Superhost"):
        host_type = "Superhost"
    else:
        host_type = "regular"

    host_name = ""
    for h2 in soup.find_all("h2"):
        text = h2.get_text().replace("\xa0", " ")
        match = re.search(r"[Hh]osted by\s+(.+)", text)
        if match:
            host_name = match.group(1).strip()
            break

    room_type = "Entire Room"
    subtitle = ""

    for h2 in soup.find_all("h2"):
        text = h2.get_text().replace("\xa0", " ")
        if "hosted by" in text.lower():
            subtitle = text
            break

    if "Private" in subtitle:
        room_type = "Private Room"
    elif "Shared" in subtitle:
        room_type = "Shared Room"
    else:
        extra_div = soup.find("div", class_="_kh3xmo")
        if extra_div:
            extra_text = extra_div.get_text()
            if "Private" in extra_text:
                room_type = "Private Room"
            elif "Shared" in extra_text:
                room_type = "Shared Room"

    location_rating = 0.0
    location_div = soup.find("div", class_="_y1ba89", string="Location")

    if location_div:
        parent_text = location_div.parent.get_text().replace("Location", "").strip()
        match = re.search(r"(\d+\.?\d*)", parent_text)
        if match:
            location_rating = float(match.group(1))

    return {
        listing_id: {
            "policy_number": policy_number,
            "host_type": host_type,
            "host_name": host_name,
            "room_type": room_type,
            "location_rating": location_rating,
        }
    }


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
    final_data = []

    for title, listing_id in listings:
        details = get_listing_details(listing_id)
        info = details[listing_id]

        row = (
            title,
            listing_id,
            info["policy_number"],
            info["host_type"],
            info["host_name"],
            info["room_type"],
            info["location_rating"],
        )
        final_data.append(row)

    return final_data


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
    sorted_data = sorted(data, key=lambda row: row[6], reverse=True)

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        writer.writerow(
            [
                "Listing Title",
                "Listing ID",
                "Policy Number",
                "Host Type",
                "Host Name",
                "Room Type",
                "Location Rating",
            ]
        )

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
        room = row[5]
        rating = row[6]

        if rating == 0.0:
            continue

        if room not in totals:
            totals[room] = 0
            counts[room] = 0

        totals[room] += rating
        counts[room] += 1

    averages = {}
    for room in totals:
        averages[room] = round(totals[room] / counts[room], 1)

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
    bad_ids = []

    pattern1 = r"^20\d{2}-00\d{4}STR$"
    pattern2 = r"^STR-000\d{4}$"

    for row in data:
        listing_id = row[1]
        policy_number = row[2]

        if policy_number == "Pending" or policy_number == "Exempt":
            continue

        if not re.match(pattern1, policy_number) and not re.match(
            pattern2, policy_number
        ):
            bad_ids.append(listing_id)

    return bad_ids


# EXTRA CREDIT
def google_scholar_searcher(query):
    """
    EXTRA CREDIT

    Args:
        query (str): The search query to be used on Google Scholar
    Returns:
        List of titles on the first page (list)
    """
    url = "https://scholar.google.com/scholar"
    params = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, params=params, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    titles = []
    for result in soup.find_all("h3", class_="gs_rt"):
        titles.append(result.get_text().strip())

    return titles


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
        results = []
        for listing_id in html_list:
            results.append(get_listing_details(listing_id))

        self.assertEqual(results[0]["467507"]["policy_number"], "STR-0005349")
        self.assertEqual(results[2]["1944564"]["host_type"], "Superhost")
        self.assertEqual(results[2]["1944564"]["room_type"], "Entire Room")
        self.assertEqual(results[2]["1944564"]["location_rating"], 4.9)

    def test_create_listing_database(self):
        # TODO: Check that each tuple in detailed_data has exactly 7 elements:
        # (listing_title, listing_id, policy_number, host_type, host_name, room_type, location_rating)

        # TODO: Spot-check the LAST tuple is ("Guest suite in Mission District", "467507", "STR-0005349", "Superhost", "Jennifer", "Entire Room", 4.8).
        for row in self.detailed_data:
            self.assertEqual(len(row), 7)

        self.assertEqual(
            self.detailed_data[-1],
            ("Guest suite in Mission District", "467507", "STR-0005349", "Superhost", "Jennifer", "Entire Room", 4.8)
        )

    def test_output_csv(self):
        out_path = os.path.join(self.base_dir, "test.csv")

        # TODO: Call output_csv() to write the detailed_data to a CSV file.
        # TODO: Read the CSV back in and store rows in a list.
        # TODO: Check that the first data row matches ["Guesthouse in San Francisco", "49591060", "STR-0000253", "Superhost", "Ingrid", "Entire Room", "5.0"].

        output_csv(self.detailed_data, out_path)

        rows = []
        with open(out_path, encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(row)

        self.assertEqual(
            rows[1],
            ["Guesthouse in San Francisco", "49591060", "STR-0000253", "Superhost", "Ingrid", "Entire Room", "5.0"]
        )

        os.remove(out_path)

    def test_avg_location_rating_by_room_type(self):
        # TODO: Call avg_location_rating_by_room_type() and save the output.
        # TODO: Check that the average for "Private Room" is 4.9.
        averages = avg_location_rating_by_room_type(self.detailed_data)
        self.assertEqual(averages["Private Room"], 4.9)

    def test_validate_policy_numbers(self):
        # TODO: Call validate_policy_numbers() on detailed_data and save the result into a variable invalid_listings.
        # TODO: Check that the list contains exactly "16204265" for this dataset.
        invalid_listings = validate_policy_numbers(self.detailed_data)
        self.assertEqual(invalid_listings, ["16204265"])


def main():
    detailed_data = create_listing_database(os.path.join("html_files", "search_results.html"))
    output_csv(detailed_data, "airbnb_dataset.csv")


if __name__ == "__main__":
    main()
    unittest.main(verbosity=2)