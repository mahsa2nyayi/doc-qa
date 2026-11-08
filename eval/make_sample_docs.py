"""Regenerate the sample PDFs in eval/docs (needs `pip install reportlab`).

All three documents are invented for this repository; none describes a real
company or product. Every section sits on its own page, so the page number is
a reliable ground truth for the evaluation.
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).parent / "docs"

DOCUMENTS = {
    "nordlicht_handbook.pdf": (
        "Nordlicht Energy - Employee Handbook",
        [
            (
                "Working hours and remote work",
                "Core working hours at Nordlicht Energy are 10:00 to 15:00 on weekdays. Outside "
                "these hours employees may arrange their time freely, as long as the weekly "
                "contractual hours are met. Employees may work remotely up to three days per week "
                "after completing the six-month probation period. During probation, remote work "
                "requires written approval from the team lead. Remote workers must be reachable on "
                "the team chat during core hours and must use the company VPN when accessing "
                "internal systems. Each employee receives a laptop and a monitor. Additional "
                "peripherals such as keyboards or headsets can be ordered through the IT portal up "
                "to a value of 150 euros per year.",
            ),
            (
                "Leave policy",
                "Full-time employees receive 28 days of paid annual leave per calendar year. Unused "
                "days can be carried over to the next year until 31 March; after that date they "
                "expire. Leave requests of more than five consecutive days must be submitted at "
                "least four weeks in advance. Sick leave: employees must notify their team lead "
                "before 09:00 on the first day of illness. A medical certificate is required from "
                "the fourth consecutive day of absence. Parental leave: both parents are entitled "
                "to up to 12 weeks of paid parental leave, which can be taken in blocks within the "
                "first two years of the child's life.",
            ),
            (
                "Expenses and travel",
                "Business travel must be booked through the company travel portal. Train travel is "
                "preferred for distances under 600 kilometres; flights are approved only above that "
                "distance or when the train journey exceeds eight hours. Hotel costs are reimbursed "
                "up to 140 euros per night in major cities and 100 euros elsewhere. Meals during "
                "business trips are covered with a daily allowance of 35 euros. Expense reports "
                "must be submitted within 30 days after the trip, together with the original "
                "receipts. Reports submitted later than 60 days will not be reimbursed. "
                "Reimbursements are paid with the next monthly salary.",
            ),
        ],
    ),
    "aurora7_manual.pdf": (
        "Aurora-7 Wireless Router - User Manual",
        [
            (
                "Setup",
                "Connect the Aurora-7 to your modem with the yellow Ethernet cable and plug in the "
                "power adapter. Wait about two minutes until the status light turns solid green. On "
                "a phone or laptop, join the network named Aurora-7-Setup; the initial password is "
                "printed on the label under the router. Open the address 192.168.50.1 in a browser "
                "to start the setup wizard, which asks you to choose a new network name, a new "
                "Wi-Fi password and a new administrator password. The wizard finishes by checking "
                "for firmware updates.",
            ),
            (
                "Firmware and maintenance",
                "To update the firmware manually, open the administration page, choose Maintenance "
                "and then Firmware, and upload the file downloaded from the support site. Do not "
                "unplug the router during the update, which takes about four minutes. The router "
                "restarts twice. Automatic updates are enabled by default and run at 03:00 local "
                "time on Sundays. A factory reset is performed by holding the recessed reset button "
                "for ten seconds with a paperclip until the status light flashes white. A factory "
                "reset erases all settings, including the Wi-Fi password.",
            ),
            (
                "Troubleshooting",
                "A slowly blinking orange light means the router cannot reach the internet; check "
                "the cable between the router and the modem, then restart both devices. A solid red "
                "light indicates a hardware fault and the device should be returned under warranty. "
                "If the Wi-Fi signal is weak in distant rooms, place the router in a central, "
                "elevated location away from microwave ovens and metal shelves, and switch to the "
                "5 GHz band for short distances and the 2.4 GHz band for longer distances. Up to 32 "
                "devices can be connected at the same time. The warranty period is 24 months from "
                "the date of purchase.",
            ),
        ],
    ),
    "fernwood_contributing.pdf": (
        "Fernwood Project - Contributor Guide",
        [
            (
                "Getting started and branches",
                "Fork the repository and create a topic branch from the main branch. Branch names "
                "follow the pattern type/short-description, for example fix/null-pointer-on-login "
                "or feature/csv-export. Run the full test suite locally with make test before "
                "opening a pull request. Commit messages use the imperative mood, such as 'Add "
                "retry logic', and the first line must not exceed 72 characters. Large changes "
                "should be split into several small commits, each of which builds and passes the "
                "tests.",
            ),
            (
                "Code review",
                "Every pull request needs at least two approving reviews, one of which must come "
                "from a maintainer listed in the CODEOWNERS file. The continuous integration checks "
                "must pass before merging. Reviewers aim to respond within three working days; if "
                "nobody responds after five working days, the author may ping the maintainers "
                "channel. Authors should not force-push to a branch after the review has started, "
                "because this makes it hard to see what changed. Pull requests are merged with the "
                "squash strategy so that the main branch keeps a linear history.",
            ),
            (
                "Releases and security",
                "Fernwood follows semantic versioning. A new minor release is published on the "
                "first Tuesday of every month, and patch releases are made whenever a security fix "
                "is merged. Release candidates are tagged with the suffix -rc followed by a number "
                "and are tested for one week before the final release. The changelog is generated "
                "from the pull request titles, so titles should describe the user-visible change. "
                "Security vulnerabilities must not be reported in public issues; send a private "
                "report to the security contact listed in SECURITY.md, and expect an "
                "acknowledgement within 48 hours.",
            ),
        ],
    ),
}


def build(filename: str, title: str, sections: list[tuple[str, str]]) -> None:
    styles = getSampleStyleSheet()
    story = []
    for position, (heading, body) in enumerate(sections):
        if position:
            story.append(PageBreak())
        story.append(Paragraph(title, styles["Title"]))
        story.append(Paragraph(heading, styles["Heading2"]))
        story.append(Spacer(1, 8))
        story.append(Paragraph(body, styles["BodyText"]))
    SimpleDocTemplate(str(OUT / filename), pagesize=A4, title=title).build(story)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, (doc_title, doc_sections) in DOCUMENTS.items():
        build(name, doc_title, doc_sections)
        print("wrote", OUT / name)
