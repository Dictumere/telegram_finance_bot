import gspread
from oauth2client.service_account import ServiceAccountCredentials


# Настройка доступа
def get_sheet(sheet_title: str):
    scope = ["https://spreadsheets.google.com/feeds", 
             "https://www.googleapis.com/auth/spreadsheets", 
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    # Открываем таблицу по названию
    spreadsheet = client.open(sheet_title)
    return spreadsheet


def add_expense(sheet_title: str, month_sheet: str, category: str, day: str, amount: float):
    scope = ["https://spreadsheets.google.com/feeds", 
             "https://www.googleapis.com/auth/spreadsheets", 
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    spreadsheet = client.open(sheet_title)
    sheet = spreadsheet.worksheet(month_sheet)

    values = sheet.get_all_values()

    # 🔹 1. Найдём строку категории
    row_index = None
    for i, row in enumerate(values):
        if category in row:
            row_index = i + 1
            break
    if not row_index:
        raise Exception("Категория не найдена в таблице")

    # 🔹 2. Столбец по числу (строка 13 = index 12)
    header_row = values[12]
    col_index = None
    for j, cell in enumerate(header_row):
        if cell.strip() == str(day):
            col_index = j + 1
            break
    if not col_index:
        raise Exception("Число не найдено в строке 13")

    # 🔹 3. Обновляем ячейку
    sheet.update_cell(row_index, col_index, amount)

    # 🔹 4. Чтение доп. значений
    total_balance = sheet.acell("J6").value

    # Остаток по группе
    group_to_cell = {
        "Обязательные расходы": "J22",
        "Отдых и развлечение": "J28",
        "Накопление и кредиты": "J34"
    }
    group_cell = group_to_cell.get(category_group(category))  # нужна функция ниже
    group_balance = sheet.acell(group_cell).value if group_cell else "?"

    # Потрачено за день
    daily_spent_cell = f"{header_to_col(col_index)}35"  # строка 35 + колонка
    daily_spent = sheet.acell(daily_spent_cell).value

    return total_balance, group_balance, daily_spent


def category_group(category):
    for group, cats in CATEGORIES.items():
        if category in cats:
            return group
    return None


def header_to_col(col_index):
    """Преобразуем номер столбца в букву Excel (например, 26 → Z)"""
    col = ""
    while col_index > 0:
        col_index, remainder = divmod(col_index - 1, 26)
        col = chr(65 + remainder) + col
    return col


def get_summary(sheet_title: str, month_sheet: str, group: str, day: str):
    scope = ["https://spreadsheets.google.com/feeds", 
             "https://www.googleapis.com/auth/spreadsheets", 
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]
    
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open(sheet_title).worksheet(month_sheet)

    # Общий остаток: J6
    total = sheet.acell("J6").value

    # Остаток по группе
    group_cells = {
        "Обязательные расходы": "J22",
        "Отдых и развлечение": "J28",
        "Накопление и кредиты": "J34"
    }
    group_cell = group_cells.get(group)
    group_rest = sheet.acell(group_cell).value if group_cell else "?"

    # Потрачено за день: Z35 = колонка по числу, но строка фиксирована
    # Найдём колонку по дню в строке 13
    headers = sheet.row_values(13)
    col_letter = None
    for i, val in enumerate(headers):
        if val.strip() == str(day):
            col_letter = gspread.utils.rowcol_to_a1(1, i + 1)[0]  # получим букву столбца
            break

    daily_cell = f"{col_letter}35" if col_letter else None
    daily = sheet.acell(daily_cell).value if daily_cell else "?"

    return total, group_rest, daily
