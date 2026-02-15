"""
Response Validation System
Provides comprehensive validation and post-processing for AI model responses
"""

import json
import structlog
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from jsonschema import validate, ValidationError, Draft7Validator
import dateutil.parser

logger = structlog.get_logger(__name__)


class ResponseValidator:
    """Validates and post-processes AI model responses for accuracy and consistency"""

    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.validator = Draft7Validator(schema)

    def validate_response(
        self, response: Dict[str, Any]
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Comprehensive response validation with corrections

        Returns:
            Tuple[bool, List[str], Dict[str, Any]]: (is_valid, error_messages, corrected_response)
        """
        errors = []
        corrected_response = response.copy()

        try:
            # Schema validation
            schema_errors = self._validate_schema(corrected_response)
            errors.extend(schema_errors)

            # Data type validation and correction
            type_errors, corrected_response = self._validate_and_correct_types(
                corrected_response
            )
            errors.extend(type_errors)

            # Date validation and standardization
            date_errors, corrected_response = self._validate_and_correct_dates(
                corrected_response
            )
            errors.extend(date_errors)

            # Amount validation and formatting
            amount_errors, corrected_response = self._validate_and_correct_amounts(
                corrected_response
            )
            errors.extend(amount_errors)

            # Cross-field consistency validation
            consistency_errors, corrected_response = self._validate_consistency(
                corrected_response
            )
            errors.extend(consistency_errors)

            # Confidence scoring
            corrected_response["validation_confidence"] = self._calculate_confidence(
                corrected_response, errors
            )

            is_valid = len(errors) == 0
            return is_valid, errors, corrected_response

        except Exception as e:
            logger.error(f"Validation error: {e}")
            errors.append(f"Validation process failed: {str(e)}")
            return False, errors, corrected_response

    def _validate_schema(self, response: Dict[str, Any]) -> List[str]:
        """Validate response against JSON schema"""
        errors = []
        try:
            self.validator.validate(response)
        except ValidationError as e:
            # Convert JSON schema errors to user-friendly messages
            path = " -> ".join(str(p) for p in e.absolute_path)
            errors.append(f"Schema validation failed at {path}: {e.message}")
        except Exception as e:
            errors.append(f"Schema validation error: {str(e)}")

        return errors

    def _validate_and_correct_types(
        self, response: Dict[str, Any]
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Validate and correct data types"""
        errors = []
        corrected = response.copy()

        properties = self.schema.get("properties", {})

        for field, expected_props in properties.items():
            if field not in corrected:
                continue

            field_type = expected_props.get("type")
            current_value = corrected[field]

            if field_type == "number" or field_type == "integer":
                if isinstance(current_value, str):
                    try:
                        # Try to convert string to number
                        if field_type == "integer":
                            corrected[field] = int(
                                float(current_value.replace(",", ""))
                            )
                        else:
                            corrected[field] = float(current_value.replace(",", ""))
                        logger.debug(f"Converted {field} from string to {field_type}")
                    except ValueError:
                        errors.append(
                            f"Cannot convert {field} '{current_value}' to {field_type}"
                        )

            elif field_type == "string":
                if not isinstance(current_value, str) and current_value is not None:
                    corrected[field] = str(current_value)
                    logger.debug(f"Converted {field} to string")

        return errors, corrected

    def _validate_and_correct_dates(
        self, response: Dict[str, Any]
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Validate and standardize date formats"""
        errors = []
        corrected = response.copy()

        # Check main date field
        if "date" in corrected and corrected["date"]:
            date_errors, corrected_date = self._standardize_date(corrected["date"])
            if date_errors:
                errors.extend([f"Date field: {err}" for err in date_errors])
            else:
                corrected["date"] = corrected_date

        # Check meta dates
        if "meta" in corrected and "dates" in corrected["meta"]:
            dates_obj = corrected["meta"]["dates"]
            if isinstance(dates_obj, dict):
                for date_key, date_value in dates_obj.items():
                    if date_value:
                        date_errors, corrected_date = self._standardize_date(date_value)
                        if date_errors:
                            errors.extend(
                                [f"Meta date {date_key}: {err}" for err in date_errors]
                            )
                        else:
                            corrected["meta"]["dates"][date_key] = corrected_date

        return errors, corrected

    def _standardize_date(self, date_value: Any) -> Tuple[List[str], Optional[str]]:
        """Standardize a single date value to YYYY-MM-DD format"""
        errors = []

        if not date_value:
            return errors, None

        try:
            if isinstance(date_value, str):
                # Parse various date formats
                parsed_date = dateutil.parser.parse(date_value)

                # Validate reasonable date range
                current_year = datetime.now().year
                if parsed_date.year < 1900 or parsed_date.year > current_year + 10:
                    errors.append(
                        f"Date year {parsed_date.year} outside reasonable range"
                    )
                    return errors, None

                return errors, parsed_date.strftime("%Y-%m-%d")
            else:
                errors.append(f"Date value must be string, got {type(date_value)}")

        except Exception as e:
            errors.append(f"Cannot parse date '{date_value}': {str(e)}")

        return errors, None

    def _validate_and_correct_amounts(
        self, response: Dict[str, Any]
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Validate and format monetary amounts"""
        errors = []
        corrected = response.copy()

        # Check meta amounts
        if "meta" in corrected and "amounts" in corrected["meta"]:
            amounts_obj = corrected["meta"]["amounts"]
            if isinstance(amounts_obj, dict):
                for amount_key, amount_value in amounts_obj.items():
                    if amount_value is not None:
                        amount_errors, corrected_amount = self._standardize_amount(
                            amount_value
                        )
                        if amount_errors:
                            errors.extend(
                                [f"Amount {amount_key}: {err}" for err in amount_errors]
                            )
                        else:
                            corrected["meta"]["amounts"][amount_key] = corrected_amount

        return errors, corrected

    def _standardize_amount(
        self, amount_value: Any
    ) -> Tuple[List[str], Optional[float]]:
        """Standardize a single amount value"""
        errors = []

        if amount_value is None:
            return errors, None

        try:
            if isinstance(amount_value, (int, float)):
                if amount_value < 0:
                    errors.append("Amount cannot be negative")
                    return errors, None
                return errors, float(amount_value)

            elif isinstance(amount_value, str):
                # Clean the amount string
                cleaned = (
                    amount_value.strip()
                    .replace("$", "")
                    .replace("€", "")
                    .replace("£", "")
                )
                cleaned = cleaned.replace(" ", "").replace(",", "")

                if not cleaned:
                    return errors, None

                # Handle European decimal format (1.234,56)
                if (
                    "." in cleaned
                    and cleaned.endswith(
                        (
                            ".00",
                            ".01",
                            ".02",
                            ".03",
                            ".04",
                            ".05",
                            ".06",
                            ".07",
                            ".08",
                            ".09",
                        )
                    )
                    and len(cleaned.split(".")[-1]) == 2
                ):
                    # Likely US format
                    amount = float(cleaned)
                elif "," in cleaned and "." in cleaned:
                    # European format: 1.234,56
                    cleaned = cleaned.replace(".", "").replace(",", ".")
                    amount = float(cleaned)
                elif "," in cleaned and "." not in cleaned:
                    # Comma as decimal separator
                    cleaned = cleaned.replace(",", ".")
                    amount = float(cleaned)
                else:
                    amount = float(cleaned)

                if amount < 0:
                    errors.append("Amount cannot be negative")
                    return errors, None

                return errors, round(amount, 2)

            else:
                errors.append(
                    f"Amount must be number or string, got {type(amount_value)}"
                )

        except Exception as e:
            errors.append(f"Cannot parse amount '{amount_value}': {str(e)}")

        return errors, None

    def _validate_consistency(
        self, response: Dict[str, Any]
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Validate cross-field consistency"""
        errors = []
        corrected = response.copy()

        # Check document type consistency
        if "doctype" in corrected:
            doctype = corrected["doctype"].lower() if corrected["doctype"] else ""

            # Invoice-specific validations
            if "invoice" in doctype:
                if "meta" in corrected and "amounts" in corrected["meta"]:
                    amounts = corrected["meta"]["amounts"]
                    if not any(
                        amounts.get(key) for key in ["total", "subtotal", "amount_due"]
                    ):
                        errors.append(
                            "Invoice document should have at least one amount field"
                        )

                # Check for invoice number
                if not corrected.get("reference"):
                    errors.append(
                        "Invoice document should have a reference/invoice number"
                    )

        # Date consistency checks
        dates_to_check = []
        if corrected.get("date"):
            dates_to_check.append(("main_date", corrected["date"]))

        if "meta" in corrected and "dates" in corrected["meta"]:
            for date_key, date_value in corrected["meta"]["dates"].items():
                if date_value:
                    dates_to_check.append((date_key, date_value))

        # Ensure all dates are in reasonable sequence
        if len(dates_to_check) > 1:
            try:
                parsed_dates = [
                    (name, dateutil.parser.parse(date_str))
                    for name, date_str in dates_to_check
                ]
                parsed_dates.sort(key=lambda x: x[1])

                # Check if dates span more than 5 years (might indicate error)
                date_span = (parsed_dates[-1][1] - parsed_dates[0][1]).days
                if date_span > 1825:  # 5 years
                    errors.append(f"Date span of {date_span} days seems unreasonable")

            except Exception as e:
                logger.warning(f"Could not validate date consistency: {e}")

        return errors, corrected

    def _calculate_confidence(
        self, response: Dict[str, Any], errors: List[str]
    ) -> float:
        """Calculate confidence score based on validation results"""
        base_confidence = 1.0

        # Deduct for validation errors
        error_penalty = len(errors) * 0.1
        confidence = base_confidence - error_penalty

        # Bonus for completeness
        required_fields = self.schema.get("required", [])
        filled_required = sum(1 for field in required_fields if response.get(field))
        completeness_bonus = (
            (filled_required / len(required_fields)) * 0.2 if required_fields else 0
        )

        # Bonus for having structured metadata
        if "meta" in response:
            meta = response["meta"]
            has_dates = bool(meta.get("dates"))
            has_amounts = bool(meta.get("amounts"))
            has_entities = bool(meta.get("entities"))
            structure_bonus = (has_dates + has_amounts + has_entities) * 0.05
        else:
            structure_bonus = 0

        final_confidence = min(1.0, confidence + completeness_bonus + structure_bonus)
        return round(max(0.0, final_confidence), 3)

    def get_validation_summary(
        self, errors: List[str], confidence: float
    ) -> Dict[str, Any]:
        """Generate a validation summary"""
        return {
            "is_valid": len(errors) == 0,
            "error_count": len(errors),
            "errors": errors,
            "confidence_score": confidence,
            "validation_status": "passed"
            if len(errors) == 0
            else "failed_with_corrections",
            "recommendations": self._generate_recommendations(errors),
        }

    def _generate_recommendations(self, errors: List[str]) -> List[str]:
        """Generate recommendations based on validation errors"""
        recommendations = []

        if any("date" in error.lower() for error in errors):
            recommendations.append("Ensure all dates are in YYYY-MM-DD format")

        if any("amount" in error.lower() for error in errors):
            recommendations.append(
                "Verify monetary amounts are numeric and properly formatted"
            )

        if any("schema" in error.lower() for error in errors):
            recommendations.append(
                "Check that all required fields are present and correctly named"
            )

        if any("consistency" in error.lower() for error in errors):
            recommendations.append(
                "Review document type classification and related field expectations"
            )

        return recommendations
