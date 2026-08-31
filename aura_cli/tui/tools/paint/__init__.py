"""AuraPaint, the native terminal art editor for AuraCli.

The editor originated from the Textual Paint project and remains compatible
with its MIT-licensed document formats.  AuraPaint is now maintained and
launched as an AuraCli capability rather than as an external dependency.
"""

from os.path import dirname, exists
import sys

__author__ = "Isaiah Odhner"
__copyright__ = "Copyright Isaiah Odhner"
__credits__ = ["Isaiah Odhner"]
__maintainer__ = "Isaiah Odhner"
__email__ = "isaiahodhner@gmail.com"
__version__ = "0.4.0"
__license__ = "MIT"

AURA_PAINT_NAME = "AuraPaint"
"""Canonical user-facing name for the bundled editor."""

LEGACY_PROJECT_NAME = "Textual Paint"
"""Upstream project name retained for attribution and compatibility."""

DEVELOPMENT = exists(dirname(__file__) + "/../../.git")
"""Whether running from a Git repository."""

PYTEST = "pytest" in sys.modules
"""Whether running from pytest."""

if PYTEST:
    __version__ = "snapshot test edition :)"
elif DEVELOPMENT:
    try:
        from subprocess import check_output

        __version__ = (
            "development "
            + check_output(["git", "describe", "--tags"], cwd=dirname(__file__))
            .strip()
            .decode()
        )
    except Exception:
        __version__ = "development (git unavailable)"
