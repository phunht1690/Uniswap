"""Reserved provider interface; no fabricated observations."""
def fetch(*args, **kwargs):
    raise NotImplementedError("Kaiko: chưa triển khai; cần tài khoản và phạm vi dữ liệu được cấp phép.")
