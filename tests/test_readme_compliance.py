"""Test that Contributing and Trademarks sections match the canonical template.

The canonical template is the standard Microsoft OSS Contributing + Trademarks
boilerplate. Both sections, including the ``---`` separator between them, must
appear verbatim at the end of README.md.
"""

from __future__ import annotations

import re
from pathlib import Path

BUNDLE_ROOT = Path(__file__).resolve().parent.parent

# The canonical tail: everything from "## Contributing" to EOF, including the
# horizontal rule separator and the Trademarks section.
CANONICAL_TAIL = """\
## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

---

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
"""


def _extract_tail(text: str) -> str:
    """Extract everything from '## Contributing' to end of file."""
    match = re.search(r"(^## Contributing.*)", text, re.MULTILINE | re.DOTALL)
    assert match, "'## Contributing' heading not found in README.md"
    return match.group(1)


class TestReadmeCompliance:
    """Contributing and Trademarks must match the canonical Microsoft OSS template."""

    def test_readme_exists(self) -> None:
        readme_path = BUNDLE_ROOT / "README.md"
        assert readme_path.exists(), f"README.md not found at {readme_path}"

    def test_contributing_and_trademarks_match_canonical(self) -> None:
        readme = (BUNDLE_ROOT / "README.md").read_text()
        tail = _extract_tail(readme)
        assert tail == CANONICAL_TAIL, (
            "Contributing/Trademarks sections do not match canonical template.\n"
            f"Got:\n{tail!r}\n\nExpected:\n{CANONICAL_TAIL!r}"
        )
