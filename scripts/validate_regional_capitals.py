#!/usr/bin/env python3
"""Compatibility entry point for top-90 regional-capital validation."""
from validate_regional_capitals_top90 import main, validation_report


def validate_regional_capitals() -> list[str]:
    return validation_report()[1]


if __name__ == "__main__":
    raise SystemExit(main())
