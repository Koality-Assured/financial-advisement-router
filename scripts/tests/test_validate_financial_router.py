import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from validation.validate_financial_router import (
    validate_case,
    validate_registry,
)


class TestValidateFinancialRouter(unittest.TestCase):
    def setUp(self):
        self.registry_data = {
            "representations": [
                {
                    "id": "mock_route",
                    "aliases": ["mock-alias"],
                    "asset_types": [{"id": "equity", "aliases": ["stock"]}],
                }
            ]
        }
        self.validated_reg = validate_registry(self.registry_data)

    def test_valid_case(self):
        case = {
            "case_id": "TC-001",
            "request": {
                "compliance_and_disclosures": {
                    "advisory_stamp_required": True,
                    "finra_2214_legend_required": True,
                    "no_live_order_tickets": True,
                },
                "constraints": [{"text": "must be awesome", "hardness": "hard"}],
                "representations": [
                    {
                        "role": "primary",
                        "route": "mock_route",
                        "asset": {"type": "equity"},
                    }
                ],
                "review_handoff": {"reviewer": "fiduciary-compliance-auditor"},
            },
            "deliverables": [
                {
                    "advisory_stamp": "NON-DISCRETIONARY FINANCIAL RESEARCH PRODUCT - test",
                    "finra_2214_legend": "hypothetical in nature",
                    "decimal_precision_verified": True,
                    "weights": {"A": "0.5", "B": "0.5"},
                }
            ],
        }
        errors = validate_case(
            case,
            self.validated_reg["representations_by_id"],
            self.validated_reg["medium_aliases"],
        )
        self.assertEqual(len(errors), 0, f"Expected 0 errors, got {errors}")

    def test_failing_case_bad_weights(self):
        case = {
            "case_id": "TC-FAIL",
            "request": {
                "compliance_and_disclosures": {
                    "advisory_stamp_required": True,
                    "finra_2214_legend_required": True,
                    "no_live_order_tickets": True,
                },
                "constraints": [],
                "representations": [
                    {
                        "role": "primary",
                        "route": "mock_route",
                        "asset": {"type": "equity"},
                    }
                ],
                "review_handoff": {"reviewer": "fiduciary-compliance-auditor"},
            },
            "deliverables": [
                {
                    "advisory_stamp": "NON-DISCRETIONARY FINANCIAL RESEARCH PRODUCT",
                    "finra_2214_legend": "hypothetical in nature",
                    "decimal_precision_verified": True,
                    "weights": {"A": "0.5", "B": "0.6"},  # sums to 1.1!
                }
            ],
        }
        errors = validate_case(
            case,
            self.validated_reg["representations_by_id"],
            self.validated_reg["medium_aliases"],
        )
        self.assertTrue(
            any("sum to 1.0" in e for e in errors),
            f"Expected weight error, got {errors}",
        )


if __name__ == "__main__":
    unittest.main()
