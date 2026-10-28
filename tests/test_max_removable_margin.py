import unittest

from dipcoin_client import DipcoinClient, calculate_max_removable_margin


def position(**overrides):
    value = {
        "margin": "500",
        "oraclePrice": "2505",
        "quantity": "1",
        "avgEntryPrice": "2500",
        "leverage": "5",
        "side": "LONG",
        "fundingDue": "0",
    }
    value.update(overrides)
    return value


class MaxRemovableMarginTest(unittest.TestCase):
    def test_long_and_short_formulas(self):
        self.assertEqual("4", calculate_max_removable_margin(position()))
        self.assertEqual(
            "4",
            calculate_max_removable_margin(position(side="BUY")),
        )
        self.assertEqual(
            "6",
            calculate_max_removable_margin(
                position(side="SELL", oraclePrice="2495")
            ),
        )
        self.assertEqual(
            "6",
            calculate_max_removable_margin(
                position(side="SHORT", oraclePrice="2495")
            ),
        )

    def test_negative_funding_reduces_result_and_positive_is_ignored(self):
        self.assertEqual(
            "3.9",
            calculate_max_removable_margin(position(fundingDue="-0.1")),
        )
        self.assertEqual(
            "4",
            calculate_max_removable_margin(position(fundingDue="0.1")),
        )

    def test_funding_fee_alias_is_supported(self):
        value = position(fundingDue="-0.1")
        value["fundingFee"] = value.pop("fundingDue")
        self.assertEqual("3.9", calculate_max_removable_margin(value))

    def test_result_is_clamped_to_zero_and_margin(self):
        self.assertEqual(
            "0",
            calculate_max_removable_margin(position(oraclePrice="2000")),
        )
        self.assertEqual(
            "500",
            calculate_max_removable_margin(position(oraclePrice="4000")),
        )
        self.assertEqual(
            "0",
            calculate_max_removable_margin(
                position(side="SHORT", oraclePrice="3000")
            ),
        )
        self.assertEqual(
            "500",
            calculate_max_removable_margin(
                position(side="SHORT", oraclePrice="2000")
            ),
        )

    def test_base18_precision_is_preserved_without_float_rounding(self):
        self.assertEqual(
            "0.003753086241975308",
            calculate_max_removable_margin(
                position(
                    margin="0.01",
                    oraclePrice="0.123456789012345678",
                    quantity="0.2",
                    avgEntryPrice="0.13",
                    leverage="5",
                )
            ),
        )

    def test_optional_safety_factor_and_client_convenience_method(self):
        value = position()
        self.assertEqual(
            "3.92",
            DipcoinClient.calculate_max_removable_margin(
                value,
                safety_factor="0.98",
            ),
        )

    def test_validates_required_fields_and_values(self):
        value = position()
        del value["margin"]
        with self.assertRaisesRegex(ValueError, "missing required field: margin"):
            calculate_max_removable_margin(value)

        with self.assertRaisesRegex(ValueError, "leverage must be greater than 0"):
            calculate_max_removable_margin(position(leverage="0"))
        with self.assertRaisesRegex(ValueError, "side must be"):
            calculate_max_removable_margin(position(side="UNKNOWN"))
        with self.assertRaisesRegex(ValueError, "quantity must not be negative"):
            calculate_max_removable_margin(position(quantity="-1"))
        with self.assertRaisesRegex(ValueError, "safety_factor"):
            calculate_max_removable_margin(position(), safety_factor="1.01")
        with self.assertRaisesRegex(ValueError, "finite number"):
            calculate_max_removable_margin(position(margin="NaN"))


if __name__ == "__main__":
    unittest.main()
