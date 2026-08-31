"""Build a platform wheel even though the payload is precompiled package data."""

from setuptools import Distribution, setup
from setuptools.command.bdist_wheel import bdist_wheel


class NativeDistribution(Distribution):
    """Tell wheel builders that this distribution contains native artifacts."""

    def has_ext_modules(self) -> bool:
        return True


class PlatformWheel(bdist_wheel):
    """Tag the data-only wheel as Python-agnostic but platform-specific."""

    def get_tag(self) -> tuple[str, str, str]:
        _python, _abi, platform_tag = super().get_tag()
        return "py3", "none", platform_tag


setup(distclass=NativeDistribution, cmdclass={"bdist_wheel": PlatformWheel})
