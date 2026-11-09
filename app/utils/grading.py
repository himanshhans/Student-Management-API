# Helper function: Calculate grade
def calculate_grade(percentage):
    if percentage >= 90:
        return "A+"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B"
    elif percentage >= 60:
        return "C"
    elif percentage >= 33:
        return "D"
    else:
        return "F"


# Helper function: Calculate percentage
def calculate_percentage(obtained, maximum):
    if maximum == 0:
        return 0

    return round((obtained / maximum) * 100, 2)