def validar_cpf(cpf):
    """Valida um CPF"""
    cpf = ''.join(filter(str.isdigit, cpf))
    
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    
    def calculate_digit(digits):
        total = sum((len(digits) + 1 - i) * int(digit) for i, digit in enumerate(digits))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder
    
    return (
        calculate_digit(cpf[:9]) == int(cpf[9]) and
        calculate_digit(cpf[:10]) == int(cpf[10])
    )