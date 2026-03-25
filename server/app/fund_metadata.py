"""Known ETF/fund metadata for auto-populating sleeve attributes on import.

Each entry maps a ticker to its characteristics:
  asset_class, geography, region_us/dev/em %, factor_value, factor_size,
  is_safe_asset, is_cash_like, label
"""

# (asset_class, geography, us%, dev%, em%, factor_value, factor_size, is_safe, is_cash, label)
FUND_DB: dict[str, tuple[str, str, int, int, int, str | None, str | None, bool, bool, str]] = {
    # --- US Total Market ---
    "VTI":   ("equity", "us", 100, 0, 0, "blend", "blend", False, False, "Vanguard Total US Stock"),
    "ITOT":  ("equity", "us", 100, 0, 0, "blend", "blend", False, False, "iShares Core S&P Total US"),
    "SPTM":  ("equity", "us", 100, 0, 0, "blend", "blend", False, False, "SPDR Portfolio S&P 1500"),
    "SCHB":  ("equity", "us", 100, 0, 0, "blend", "blend", False, False, "Schwab US Broad Market"),

    # --- US Large Cap Blend ---
    "VOO":   ("equity", "us", 100, 0, 0, "blend", "large", False, False, "Vanguard S&P 500"),
    "SPY":   ("equity", "us", 100, 0, 0, "blend", "large", False, False, "SPDR S&P 500"),
    "IVV":   ("equity", "us", 100, 0, 0, "blend", "large", False, False, "iShares Core S&P 500"),
    "SPLG":  ("equity", "us", 100, 0, 0, "blend", "large", False, False, "SPDR Portfolio S&P 500"),

    # --- US Large Cap Value ---
    "VTV":   ("equity", "us", 100, 0, 0, "tilted", "large", False, False, "Vanguard Value"),
    "SCHV":  ("equity", "us", 100, 0, 0, "tilted", "large", False, False, "Schwab US Large-Cap Value"),
    "IUSV":  ("equity", "us", 100, 0, 0, "tilted", "large", False, False, "iShares Core S&P US Value"),

    # --- US Small Cap Blend ---
    "VB":    ("equity", "us", 100, 0, 0, "blend", "small", False, False, "Vanguard Small-Cap"),
    "IJR":   ("equity", "us", 100, 0, 0, "blend", "small", False, False, "iShares Core S&P Small-Cap"),
    "SCHA":  ("equity", "us", 100, 0, 0, "blend", "small", False, False, "Schwab US Small-Cap"),

    # --- US Small Cap Value ---
    "AVUV":  ("equity", "us", 100, 0, 0, "tilted", "small", False, False, "Avantis US Small Cap Value"),
    "AVLV":  ("equity", "us", 100, 0, 0, "tilted", "large", False, False, "Avantis US Large Cap Value"),
    "VBR":   ("equity", "us", 100, 0, 0, "tilted", "small", False, False, "Vanguard Small-Cap Value"),
    "VIOV":  ("equity", "us", 100, 0, 0, "tilted", "small", False, False, "Vanguard S&P Small-Cap 600 Value"),
    "IJS":   ("equity", "us", 100, 0, 0, "tilted", "small", False, False, "iShares S&P Small-Cap 600 Value"),
    "SLYV":  ("equity", "us", 100, 0, 0, "tilted", "small", False, False, "SPDR S&P 600 Small Cap Value"),
    "DFSV":  ("equity", "us", 100, 0, 0, "tilted", "small", False, False, "Dimensional US Small Cap Value"),

    # --- US Mid Cap ---
    "VO":    ("equity", "us", 100, 0, 0, "blend", "blend", False, False, "Vanguard Mid-Cap"),
    "VOE":   ("equity", "us", 100, 0, 0, "tilted", "blend", False, False, "Vanguard Mid-Cap Value"),

    # --- International Total ---
    "VXUS":  ("equity", "international", 0, 80, 20, "blend", "blend", False, False, "Vanguard Total Intl Stock"),
    "IXUS":  ("equity", "international", 0, 80, 20, "blend", "blend", False, False, "iShares Core MSCI Total Intl"),
    "SPDW":  ("equity", "international", 0, 85, 15, "blend", "blend", False, False, "SPDR Portfolio Developed World ex-US"),

    # --- International Developed ---
    "VEA":   ("equity", "international", 0, 100, 0, "blend", "blend", False, False, "Vanguard FTSE Developed Markets"),
    "IDEV":  ("equity", "international", 0, 100, 0, "blend", "blend", False, False, "iShares Core MSCI Intl Developed"),
    "SCHF":  ("equity", "international", 0, 100, 0, "blend", "blend", False, False, "Schwab International Equity"),
    "EFA":   ("equity", "international", 0, 100, 0, "blend", "large", False, False, "iShares MSCI EAFE"),

    # --- International Developed Small Cap Value ---
    "AVDV":  ("equity", "international", 0, 100, 0, "tilted", "small", False, False, "Avantis Intl Small Cap Value"),
    "DLS":   ("equity", "international", 0, 100, 0, "blend", "small", False, False, "WisdomTree Intl SmallCap Dividend"),
    "DISV":  ("equity", "international", 0, 100, 0, "tilted", "small", False, False, "Dimensional Intl Small Cap Value"),

    # --- International Value ---
    "VTRIX": ("equity", "international", 0, 100, 0, "tilted", "blend", False, False, "Vanguard International Value"),
    "EFV":   ("equity", "international", 0, 100, 0, "tilted", "large", False, False, "iShares MSCI EAFE Value"),

    # --- Emerging Markets ---
    "VWO":   ("equity", "international", 0, 0, 100, "blend", "blend", False, False, "Vanguard FTSE Emerging Markets"),
    "IEMG":  ("equity", "international", 0, 0, 100, "blend", "blend", False, False, "iShares Core MSCI Emerging Markets"),
    "SCHE":  ("equity", "international", 0, 0, 100, "blend", "blend", False, False, "Schwab Emerging Markets Equity"),
    "AVEM":  ("equity", "international", 0, 0, 100, "tilted", "blend", False, False, "Avantis Emerging Markets Equity"),
    "DFEM":  ("equity", "international", 0, 0, 100, "tilted", "blend", False, False, "Dimensional Emerging Markets Core"),

    # --- Emerging Markets Small Cap Value ---
    "AVES":  ("equity", "international", 0, 0, 100, "tilted", "small", False, False, "Avantis Emerging Markets Value"),
    "DGS":   ("equity", "international", 0, 0, 100, "tilted", "small", False, False, "WisdomTree EM SmallCap Dividend"),

    # --- US Bonds ---
    "BND":   ("nominal_bond", "us", 100, 0, 0, None, None, True, False, "Vanguard Total Bond Market"),
    "AGG":   ("nominal_bond", "us", 100, 0, 0, None, None, True, False, "iShares Core US Aggregate Bond"),
    "SCHZ":  ("nominal_bond", "us", 100, 0, 0, None, None, True, False, "Schwab US Aggregate Bond"),

    # --- US Treasury ---
    "VGSH":  ("nominal_bond", "us", 100, 0, 0, None, None, True, True, "Vanguard Short-Term Treasury"),
    "VGIT":  ("nominal_bond", "us", 100, 0, 0, None, None, True, False, "Vanguard Intermediate-Term Treasury"),
    "VGLT":  ("nominal_bond", "us", 100, 0, 0, None, None, True, False, "Vanguard Long-Term Treasury"),
    "SHV":   ("nominal_bond", "us", 100, 0, 0, None, None, True, True, "iShares Short Treasury Bond"),
    "SHY":   ("nominal_bond", "us", 100, 0, 0, None, None, True, True, "iShares 1-3 Year Treasury Bond"),
    "IEF":   ("nominal_bond", "us", 100, 0, 0, None, None, True, False, "iShares 7-10 Year Treasury Bond"),
    "TLT":   ("nominal_bond", "us", 100, 0, 0, None, None, True, False, "iShares 20+ Year Treasury Bond"),
    "SGOV":  ("nominal_bond", "us", 100, 0, 0, None, None, True, True, "iShares 0-3 Month Treasury Bond"),
    "BIL":   ("nominal_bond", "us", 100, 0, 0, None, None, True, True, "SPDR Bloomberg 1-3 Month T-Bill"),

    # --- TIPS ---
    "VTIP":  ("tips", "us", 100, 0, 0, None, None, True, False, "Vanguard Short-Term Inflation-Protected"),
    "SCHP":  ("tips", "us", 100, 0, 0, None, None, True, False, "Schwab US TIPS"),
    "TIP":   ("tips", "us", 100, 0, 0, None, None, True, False, "iShares TIPS Bond"),
    "STIP":  ("tips", "us", 100, 0, 0, None, None, True, False, "iShares 0-5 Year TIPS Bond"),

    # --- International Bonds ---
    "BNDX":  ("nominal_bond", "international", 0, 80, 20, None, None, True, False, "Vanguard Total International Bond"),
    "IAGG":  ("nominal_bond", "international", 0, 80, 20, None, None, True, False, "iShares Core International Aggregate Bond"),

    # --- I Bonds / Series I (manual entry) ---
    "IBOND": ("tips", "us", 100, 0, 0, None, None, True, True, "US Series I Savings Bond"),

    # --- Money Market / Cash ---
    "VMFXX": ("nominal_bond", "us", 100, 0, 0, None, None, True, True, "Vanguard Federal Money Market"),
    "SPAXX": ("nominal_bond", "us", 100, 0, 0, None, None, True, True, "Fidelity Government Money Market"),
    "SWVXX": ("nominal_bond", "us", 100, 0, 0, None, None, True, True, "Schwab Value Advantage Money Fund"),

    # --- REITs ---
    "VNQ":   ("equity", "us", 100, 0, 0, "tilted", "blend", False, False, "Vanguard Real Estate"),
    "VNQI":  ("equity", "international", 0, 80, 20, "tilted", "blend", False, False, "Vanguard Global ex-US Real Estate"),
    "SCHH":  ("equity", "us", 100, 0, 0, "tilted", "blend", False, False, "Schwab US REIT"),
}


def lookup_fund(ticker: str) -> dict | None:
    """Look up fund metadata by ticker. Returns dict of sleeve attributes or None."""
    ticker = ticker.upper()
    entry = FUND_DB.get(ticker)
    if not entry:
        return None

    asset_class, geo, us, dev, em, f_val, f_size, is_safe, is_cash, label = entry
    return {
        "label": label,
        "asset_class": asset_class,
        "geography": geo,
        "region_us_pct": us,
        "region_developed_pct": dev,
        "region_emerging_pct": em,
        "factor_value": f_val,
        "factor_size": f_size,
        "is_safe_asset": is_safe,
        "is_cash_like": is_cash,
    }
