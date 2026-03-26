# CSV Import Format

Upload a CSV file with a header row and one of these column sets:

## Option 1: ticker, quantity, price

```csv
ticker,quantity,price
VTI,150,280.50
VXUS,300,58.20
VGIT,200,58.00
```

## Option 2: ticker, quantity, market_value

```csv
ticker,quantity,market_value
VTI,150,42075.00
VXUS,300,17460.00
VGIT,200,11600.00
```

If `price` is 0 but `market_value` is provided, price is computed as `market_value / quantity`.
If `market_value` is 0 but `price` is provided, market value is computed as `quantity * price`.

Importing replaces all existing holdings in the account.

Tickers not already in the fund list are auto-created as sleeves with metadata from a built-in lookup table (covers Vanguard, iShares, Schwab, SPDR, Avantis, and Dimensional funds). Unknown tickers are added as generic equity sleeves.
