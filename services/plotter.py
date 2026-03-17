import matplotlib.pyplot as plt
import io
import matplotlib.dates as mdates
from datetime import datetime

plt.switch_backend('Agg')

def create_price_plot(history_data, theme='light'): 
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

    if theme == 'dark':
        bg_color = '#212121' 
        text_color = '#ffffff' 
        grid_color = '#424242'   
        line_color = '#00E5FF'    
        face_color = '#212121'   
    else:
        bg_color = '#ffffff'
        text_color = '#000000'
        grid_color = '#cccccc'
        line_color = '#2A9D8F'
        face_color = '#ffffff'

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=face_color)
    ax.set_facecolor(bg_color)

    ax.plot(dates, prices, marker='o', linestyle='-', color=line_color, linewidth=2)
    
    ax.set_title("Динамика цены", fontsize=16, color=text_color)
    ax.set_ylabel("Цена (₽)", fontsize=12, color=text_color)
    ax.set_xlabel("Дата", fontsize=12, color=text_color)
    
    ax.tick_params(axis='x', colors=text_color)
    ax.tick_params(axis='y', colors=text_color)
    for spine in ax.spines.values():
        spine.set_color(text_color)

    ax.grid(True, which='both', linestyle='--', alpha=0.5, color=grid_color)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    fig.autofmt_xdate()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig) 
    
    return buf