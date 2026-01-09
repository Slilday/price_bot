import matplotlib.pyplot as plt
import io
import matplotlib.dates as mdates
from datetime import datetime

plt.switch_backend('Agg')

def create_price_plot(history_data, theme='light'): # <--- Добавили аргумент theme
    """
    theme: 'light' или 'dark'
    """
    if not history_data:
        return None

    dates = []
    prices = []
    
    for row in history_data:
        date_str, price = row
        try:
            dt = datetime.strptime(date_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.now()
        dates.append(dt)
        prices.append(price)

    # === НАСТРОЙКА ЦВЕТОВ ===
    if theme == 'dark':
        bg_color = '#212121'      # Темно-серый фон (как в Telegram)
        text_color = '#ffffff'    # Белый текст
        grid_color = '#424242'    # Серые линии сетки
        line_color = '#00E5FF'    # Яркий циан для графика
        face_color = '#212121'    # Фон вокруг графика
    else:
        bg_color = '#ffffff'
        text_color = '#000000'
        grid_color = '#cccccc'
        line_color = '#2A9D8F'
        face_color = '#ffffff'
    # ========================

    # Создаем фигуру с нужным цветом фона
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=face_color)
    ax.set_facecolor(bg_color)

    # Рисуем линию
    ax.plot(dates, prices, marker='o', linestyle='-', color=line_color, linewidth=2)
    
    # Настраиваем цвета подписей
    ax.set_title("Динамика цены", fontsize=16, color=text_color)
    ax.set_ylabel("Цена (₽)", fontsize=12, color=text_color)
    ax.set_xlabel("Дата", fontsize=12, color=text_color)
    
    # Цвет осей и галочек
    ax.tick_params(axis='x', colors=text_color)
    ax.tick_params(axis='y', colors=text_color)
    for spine in ax.spines.values():
        spine.set_color(text_color)

    # Сетка
    ax.grid(True, which='both', linestyle='--', alpha=0.5, color=grid_color)
    
    # Формат дат
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    fig.autofmt_xdate()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig) # Важно закрывать фигуру, чтобы память не текла
    
    return buf