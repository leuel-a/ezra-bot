NEEDS_DESCRIPTION_LABEL = "needs description"


THANK_YOU_COMMENT = "✅ Thank you for updating the issue description!"

REQUIRED_SECTIONS = [
    "## Summary",
    "## Steps to Reproduce",
    "## Expected Behavior",
    "## Actual Behavior",
    "## Environment",
]

TEMPLATE_COMMENT = f"""
Hello! Thank you for opening this issue. 🙏

To help us investigate effectively, please use the template below to provide more details.

```markdown
{chr(10).join(REQUIRED_SECTIONS)}
# Please fill out the sections above
"""

REMINDER_COMMENT = f"""
Hi there! This is a friendly reminder to please update the issue description to follow our template guidelines. This helps us triage and resolve issues faster.

{TEMPLATE_COMMENT}
"""


def validate_issue_body(body: str) -> bool:
    """
    Checks if the issue body contains all required markdown sections.

    :param body: the body(description) of the issue
    :ptype body: str

    :returns: True, if the body is a valid description for an event
    :rtype: bool
    """
    if not body:
        return False
    return all(section in body for section in REQUIRED_SECTIONS)
