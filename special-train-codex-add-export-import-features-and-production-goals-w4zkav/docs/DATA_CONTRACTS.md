# Data Contracts

## Tool Change Entries
**Required fields**:
- `ID`, `Date`, `Time`, `Line`, `Machine`, `Tool_Num`, `Reason`
- `Tool_Changer` (should contain the submitting user)

**Valid values**:
- `Defects_Present`: `Yes` or `No`
- `Quality_Verified`: `Pending`, `Verified`, or `N/A`
- `Leader_Sign`: `Pending` or `Signed`

## Scrap Events
**Required fields**:
- `scrap_id`, `part_number`, `line`, `qty`, `reported_by`

**Valid values**:
- `status`: `Open`, `Closed`

## Gage Checks
**Required fields**:
- `Verify_ID`, `Gage_ID`, `Result`, `Verified_By`

**Valid values**:
- `Result`: `Pass` or `Fail`

## Program Revisions
**Required fields**:
- `filename`, `scope_type`

**Valid values**:
- `scope_type`: `GLOBAL` or `MACHINE`

## Print Revisions
**Required fields**:
- `filename`, `scope_type`

**Valid values**:
- `scope_type`: `GLOBAL` or `MACHINE`

## Machine History Entries
**Required fields**:
- `line`, `machine`, `doc_type`, `doc_name`

**Valid values**:
- `doc_type`: `program` or `print`
