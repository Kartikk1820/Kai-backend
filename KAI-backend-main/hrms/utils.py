def amount_to_words_inr(amount) -> str:
    """Convert a rupee amount to words using Indian numbering (Lakh/Crore)."""
    amount = int(round(float(amount)))
    if amount == 0:
        return "Zero Rupees"

    ones = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen",
    ]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two_digit(n):
        if n < 20:
            return ones[n]
        return tens[n // 10] + (f" {ones[n % 10]}" if n % 10 else "")

    def three_digit(n):
        if n >= 100:
            remainder = n % 100
            return f"{ones[n // 100]} Hundred" + (f" {two_digit(remainder)}" if remainder else "")
        return two_digit(n)

    crore, amount = divmod(amount, 10_000_000)
    lakh, amount = divmod(amount, 100_000)
    thousand, amount = divmod(amount, 1_000)
    remainder = amount

    parts = []
    if crore:
        parts.append(f"{three_digit(crore)} Crore")
    if lakh:
        parts.append(f"{two_digit(lakh)} Lakh")
    if thousand:
        parts.append(f"{two_digit(thousand)} Thousand")
    if remainder:
        parts.append(three_digit(remainder))

    return " ".join(parts) + " Rupees"
