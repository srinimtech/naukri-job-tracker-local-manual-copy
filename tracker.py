import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

TARGET_URL = "https://www.naukri.com/program-manager-jobs-in-hyderabad-secunderabad?k=program+manager&l=hyderabad&experience=17&jobAge=1"

def scrape_jobs():
    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata"
        )
        page = context.new_page()
        stealth_sync(page)

        print(f"Opening: {TARGET_URL}")
        response = page.goto(TARGET_URL, wait_until="load", timeout=60000)
        print(f"Response Status Code: {response.status if response else 'None'}")

        page.wait_for_timeout(8000)

        title = page.title()
        print(f"Page Title: {title}")

        # Diagnostic check: check if bot challenged
        body_text = page.locator("body").inner_text()
        first_200_chars = " ".join(body_text.split()[:50])
        print(f"Visible Body Snippet: {first_200_chars}")

        # naukri uses article elements or div[data-job-id] or class contains 'tuple'
        card_selectors = [
            "article.jobTuple",
            "div.srp-jobtuple-wrapper",
            "div[data-job-id]",
            "div.cust-job-tuple",
            "div[class*='styles_job-listing-container'] > div"
        ]

        found_locator = None
        for sel in card_selectors:
            matched = page.locator(sel)
            if matched.count() > 0:
                print(f"Success: Matched {matched.count()} listings using selector: {sel}")
                found_locator = matched
                break

        if found_locator:
            cards = found_locator.all()
            for card in cards:
                try:
                    title_elem = card.locator("a.title, a[class*='title']").first
                    comp_elem = card.locator("a.comp-name, a[class*='comp-name'], a[class*='subTitle']").first
                    exp_elem = card.locator("span.expwdth, span[class*='exp'], span[class*='experience']").first
                    loc_elem = card.locator("span.locWdth, span[class*='loc'], span[class*='location']").first

                    job_title = title_elem.inner_text().strip() if title_elem.count() > 0 else "N/A"
                    job_link = title_elem.get_attribute("href") if title_elem.count() > 0 else "#"
                    company = comp_elem.inner_text().strip() if comp_elem.count() > 0 else "N/A"
                    exp = exp_elem.inner_text().strip() if exp_elem.count() > 0 else "N/A"
                    loc = loc_elem.inner_text().strip() if loc_elem.count() > 0 else "N/A"

                    if job_title != "N/A":
                        jobs.append({
                            "title": job_title,
                            "company": company,
                            "experience": exp,
                            "location": loc,
                            "link": job_link
                        })
                except Exception as e:
                    print(f"Error parsing card: {e}")
                    continue
        else:
            print("No job card elements detected on this render.")

        browser.close()
    return jobs

def build_html_email(jobs):
    if not jobs:
        return """
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h3>Naukri Job Tracker - Daily Digest</h3>
                <p>No new jobs found matching your criteria in the last 24 hours.</p>
            </body>
        </html>
        """

    rows = ""
    for job in jobs:
        rows += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 10px;"><a href="{job['link']}" style="color: #0073b1; font-weight: bold; text-decoration: none;" target="_blank">{job['title']}</a></td>
            <td style="padding: 10px;">{job['company']}</td>
            <td style="padding: 10px;">{job['experience']}</td>
            <td style="padding: 10px;">{job['location']}</td>
        </tr>
        """

    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #222; margin: 20px;">
            <h2 style="color: #1a73e8;">Program Manager Jobs in Hyderabad (17 Yrs, Last 24h)</h2>
            <p>Found <strong>{len(jobs)}</strong> listing(s) matching your criteria.</p>
            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
                <thead>
                    <tr style="background-color: #f1f3f4;">
                        <th style="padding: 10px; border-bottom: 2px solid #ccc;">Role</th>
                        <th style="padding: 10px; border-bottom: 2px solid #ccc;">Company</th>
                        <th style="padding: 10px; border-bottom: 2px solid #ccc;">Experience</th>
                        <th style="padding: 10px; border-bottom: 2px solid #ccc;">Location</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </body>
    </html>
    """

def send_email(html_content):
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_PASSWORD")
    recipient_email = os.environ.get("RECIPIENT_EMAIL")

    if not sender_email or not sender_password or not recipient_email:
        raise ValueError("Missing email environment secrets.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "PgM Jobs from Naukri Tracker"
    msg["From"] = f"Srini's Own Naukri Job Tracker <{sender_email}>"
    msg["To"] = recipient_email

    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
    print("Notification email sent successfully.")

if __name__ == "__main__":
    job_listings = scrape_jobs()
    print(f"Extracted: {len(job_listings)} jobs")
    email_body = build_html_email(job_listings)
    send_email(email_body)
