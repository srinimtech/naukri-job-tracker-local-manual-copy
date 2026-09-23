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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        stealth_sync(page)

        print(f"Navigating to: {TARGET_URL}")
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # Naukri job cards typically use 'srp-jobtuple-wrapper' or similar article selectors
        cards = page.locator("div.srp-jobtuple-wrapper").all()
        print(f"Found {len(cards)} job card(s).")

        for card in cards:
            try:
                title_elem = card.locator("a.title")
                title = title_elem.inner_text().strip() if title_elem.count() > 0 else "N/A"
                link = title_elem.get_attribute("href") if title_elem.count() > 0 else "#"

                company_elem = card.locator("a.comp-name")
                company = company_elem.inner_text().strip() if company_elem.count() > 0 else "N/A"

                exp_elem = card.locator("span.expwdth")
                experience = exp_elem.inner_text().strip() if exp_elem.count() > 0 else "N/A"

                loc_elem = card.locator("span.locWdth")
                location = loc_elem.inner_text().strip() if loc_elem.count() > 0 else "N/A"

                jobs.append({
                    "title": title,
                    "company": company,
                    "experience": experience,
                    "location": location,
                    "link": link
                })
            except Exception as e:
                print(f"Error parsing card: {e}")
                continue

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

    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #222; margin: 20px;">
            <h2 style="color: #1a73e8;">Program Manager Jobs in Hyderabad (17 Yrs, Last 24h)</h2>
            <p>Found <strong>{len(jobs)}</strong> listing(s) matching your search criteria.</p>
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
    return html

def send_email(html_content):
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_PASSWORD")
    recipient_email = os.environ.get("RECIPIENT_EMAIL")

    if not sender_email or not sender_password or not recipient_email:
        raise ValueError("Missing email environment secrets.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Daily Alert: Naukri Program Manager Jobs"
    msg["From"] = sender_email
    msg["To"] = recipient_email

    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
    print("Notification email sent successfully.")

if __name__ == "__main__":
    job_listings = scrape_jobs()
    email_body = build_html_email(job_listings)
    send_email(email_body)
