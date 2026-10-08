from validator import repair_gstin

COMPANY = "27AAPFU0939F1ZZ"


def test_ocr_extra_char_matches_company():
    assert repair_gstin("27AAPFU0939F1Z2Z", COMPANY) == COMPANY
    assert repair_gstin("27AAPFU0939F12ZZ", COMPANY) == COMPANY


def test_spaces_and_case_cleaned():
    assert repair_gstin("27 aapfu 0939 f1zz", COMPANY) == COMPANY


def test_valid_other_gstin_unchanged():
    assert repair_gstin("29AAGCB4567K1Z6", COMPANY) == "29AAGCB4567K1Z6"


def test_extra_char_fixed_by_checksum():
    # 27AFKPS7788M1Z7 is valid; OCR read it as 27AFKPS7788M12Z7
    assert repair_gstin("27AFKPS7788M12Z7", COMPANY) == "27AFKPS7788M1Z7"
    assert repair_gstin("27ABCDE1234F12Z0", COMPANY) == "27ABCDE1234F1Z0"


def test_unrelated_gstin_not_forced_to_company():
    assert repair_gstin("29AAGCB4567K1Z6", COMPANY) != COMPANY


def test_empty():
    assert repair_gstin(None, COMPANY) is None
    assert repair_gstin("", COMPANY) == ""


def test_other_state_branch_not_matched():
    assert repair_gstin("29AAPFU0939F1ZZ", COMPANY) != COMPANY
