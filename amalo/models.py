from pydantic import BaseModel


class W2Row(BaseModel):
    BorrowerID: int = 1
    Employer: str = ""
    PayType: str = "Salary"
    AnnualSalary: float = 0.0
    HourlyRate: float = 0.0
    HoursPerWeek: float = 0.0
    OT_YTD: float = 0.0
    Bonus_YTD: float = 0.0
    Comm_YTD: float = 0.0
    Months_YTD: float = 0.0
    OT_LY: float = 0.0
    Bonus_LY: float = 0.0
    Comm_LY: float = 0.0
    Months_LY: float = 0.0
    VarAvgMonths: int = 12
    Base_LY: float = 0.0
    IncludeVariable: bool = False


class ScheduleCRow(BaseModel):
    BorrowerID: int = 1
    BusinessName: str = ""
    Year: int = 2024
    NetProfit: float = 0.0
    Nonrecurring: float = 0.0
    Depletion: float = 0.0
    Depreciation: float = 0.0
    NonDedMeals: float = 0.0
    UseOfHome: float = 0.0
    AmortCasualty: float = 0.0
    BusinessMiles: float = 0.0
    MileDepRate: float = 0.0


class K1Row(BaseModel):
    BorrowerID: int = 1
    EntityName: str = ""
    Year: int = 2024
    Type: str = "1065"
    OwnershipPct: float = 0.0
    Ordinary: float = 0.0
    NetRentalOther: float = 0.0
    GuaranteedPmt: float = 0.0
    Nonrecurring: float = 0.0
    Depreciation: float = 0.0
    Depletion: float = 0.0
    AmortCasualty: float = 0.0
    NotesLT1yr: float = 0.0
    NonDed_TandE: float = 0.0


class CCorpRow(BaseModel):
    BorrowerID: int = 1
    CorpName: str = ""
    Year: int = 2024
    OwnershipPct: float = 100.0
    TaxableIncome: float = 0.0
    TotalTax: float = 0.0
    Nonrecurring: float = 0.0
    OtherIncLoss: float = 0.0
    Depreciation: float = 0.0
    Depletion: float = 0.0
    AmortCasualty: float = 0.0
    NotesLT1yr: float = 0.0
    NonDed_TandE: float = 0.0
    DividendsPaid: float = 0.0


class RentalRow(BaseModel):
    BorrowerID: int = 1
    Property: str = ""
    Year: int = 2024
    Rents: float = 0.0
    Expenses: float = 0.0
    Depreciation: float = 0.0


class OtherIncomeRow(BaseModel):
    BorrowerID: int = 1
    Type: str = ""
    GrossMonthly: float = 0.0
    GrossUpPct: float = 0.0


class DebtRow(BaseModel):
    DebtName: str = ""
    MonthlyPayment: float = 0.0


class HousingInfo(BaseModel):
    purchase_price: float = 500000.0
    down_payment_amt: float = 100000.0
    rate_pct: float = 6.75
    term_years: int = 30
    tax_rate_pct: float = 1.0
    hoi_annual: float = 1200.0
    hoa_monthly: float = 0.0
