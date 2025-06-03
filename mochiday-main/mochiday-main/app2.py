import requests
from bs4 import BeautifulSoup
import re
from enum import Enum
import pandas as pd
from googlesearch import search
import time

# Define Job Site Enum
class JobSite(Enum):
    GREENHOUSE = "boards.greenhouse.io/*/jobs/*"

regex = {
    JobSite.GREENHOUSE: r"https://boards.greenhouse.io/[^/]+/jobs/[^/]+",
}

# Define Time-Based Search Enum
class TBS(Enum):
    PAST_TWELVE_HOURS = "qdr:h12"
    PAST_DAY = "qdr:d"
    PAST_WEEK = "qdr:w"
    PAST_MONTH = "qdr:m"
    PAST_YEAR = "qdr:y"

# Function to find job postings dynamically using Googlesearch-Python
def find_jobs(keyword: str, job_sites: list[JobSite], max_results: int = 50):
    search_sites = " OR ".join([f"site:{site.value}" for site in job_sites])
    search_query = f"{keyword} {search_sites}"

    print(f"🔍 Searching Google for: {search_query}")
    result = list(search(search_query, num_results=50))  # Increase from 10 to 50

    print(f"🌐 Raw search results: {result}")
    job_urls = [url for url in result if re.search(regex[JobSite.GREENHOUSE], url)]
    
    print(f"✅ Filtered Greenhouse job URLs: {job_urls}")
    return job_urls
    
def extract_company_from_url(url: str) -> str:
    match = re.search(r"greenhouse.io/([^/]+)/jobs", url)
    return match.group(1) if match else "Unknown"

def get_greenhouse_job_details(link: str) -> dict:
    retries = 3  # Retry attempts for failed requests
    for attempt in range(retries):
        try:
            response = requests.get(link, timeout=20)
            response.raise_for_status()
            break  # Exit loop if successful
        except requests.exceptions.Timeout:
            print(f"⏳ Timeout on attempt {attempt + 1}: {link}")
            if attempt < retries - 1:
                time.sleep(5)  # Wait before retrying
                continue
            else:
                return {"Company": extract_company_from_url(link), "Title": None, "Image": None, "URL": link, "Status": "Failed", "Error": "Request Timed Out after retries"}
        except requests.exceptions.RequestException as e:
            return {"Company": extract_company_from_url(link), "Title": None, "Image": None, "URL": link, "Status": "Failed", "Error": f"Request Failed: {str(e)}"}

    soup = BeautifulSoup(response.content, "html.parser")

    head = soup.find("head")
    if not head:
        return {"Company": extract_company_from_url(link), "Title": "Head not found", "Image": None, "URL": link, "Status": "Failed", "Error": "Missing <head> section"}

    position_meta = head.find("meta", property="og:title")
    position = position_meta.get("content", "Unknown") if position_meta else "Unknown"

    image_meta = head.find("meta", property="og:image")
    image = image_meta.get("content", None) if image_meta else None

    if "engineer" not in position.lower() and "developer" not in position.lower():
        return {"Company": extract_company_from_url(link), "Title": "Unknown", "Image": None, "URL": link, "Status": "Filtered", "Error": "Job role does not match criteria"}

    return {"Company": extract_company_from_url(link), "Title": position, "Image": image, "URL": link, "Status": "Success", "Error": None}

# 🔥 Run Everything
print("🚀 Starting Job Search in Greenhouse...")
job_links = find_jobs("Software Engineer", [JobSite.GREENHOUSE], max_results=50)

if not job_links:
    print("❌ No job links found! Check search settings.")
else:
    print(f"🔎 Found {len(job_links)} jobs—Fetching details...")

    # Clean URLs before scraping
    job_links = [re.sub(r"\?.*", "", url) for url in job_links]

    job_data = [get_greenhouse_job_details(link) for link in job_links if "greenhouse.io" in link]
    df = pd.DataFrame(job_data)

    display(df)
