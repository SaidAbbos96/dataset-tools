from datetime import datetime

def get_formatted_datetime(format_type: str = "default") -> str:
    """
    Turli formatlarda sana va vaqtni qaytaradi.
    
    Parametrlar:
        format_type: 
            - "default": yil-oy-kun-soat-daqiqa (2024-01-15-14-30)
            - "reverse": kun-oy-yil-soat-daqiqa (15-01-2024-14-30)
            - "full": to'liq matnli format (15-Yanvar-2024-14:30)
            - "time": faqat vaqt (14:30)
            - "date": faqat sana (2024-01-15)
    """
    now = datetime.now()
    
    if format_type == "default":
        return now.strftime("%Y-%m-%d-%H-%M")
    elif format_type == "reverse":
        return now.strftime("%d-%m-%Y-%H-%M")
    elif format_type == "full":
        # Oyni matn korinishida
        month_names = {
            1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
            5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
            9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"
        }
        return f"{now.day}-{month_names[now.month]}-{now.year}-{now.hour}:{now.minute}"
    elif format_type == "time":
        return now.strftime("%H:%M")
    elif format_type == "date":
        return now.strftime("%Y-%m-%d")
    else:
        return now.strftime("%Y-%m-%d-%H-%M")

# Misollar
if __name__ == "__main__":
    print("Default format:", get_formatted_datetime())
    print("Reverse format:", get_formatted_datetime("reverse"))
    print("Full format:", get_formatted_datetime("full"))
    print("Time format:", get_formatted_datetime("time"))
    print("Date format:", get_formatted_datetime("date"))