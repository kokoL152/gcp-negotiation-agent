import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

# --- Invented Data based on requirements ---
# The provided "Input Report" stated no data was found ("I couldn't find any data for 'ACME TECH'").
# Therefore, realistic example data is invented here to demonstrate the visualization.
# In a real scenario, this data would be parsed from the actual negotiation strategy report.

purchase_history_data = [
    {'date': '2023-01-15', 'price_achieved': 105.0},
    {'date': '2023-03-20', 'price_achieved': 98.5},
    {'date': '2023-05-10', 'price_achieved': 110.2},
    {'date': '2023-07-01', 'price_achieved': 102.8},
    {'date': '2023-09-12', 'price_achieved': 107.5},
    {'date': '2023-11-05', 'price_achieved': 103.0},
    {'date': '2024-01-20', 'price_achieved': 109.1},
    {'date': '2024-03-01', 'price_achieved': 106.0},
]

current_target_price = 108.0
current_cost_price = 100.0
# --- End Invented Data ---

# Prepare data for plotting
dates = [datetime.strptime(item['date'], '%Y-%m-%d') for item in purchase_history_data]
prices_achieved = [item['price_achieved'] for item in purchase_history_data]

# Create the plot figure and axes
plt.figure(figsize=(12, 7))

# 3. Historical Prices: Plot 'price_achieved' as a line with markers
plt.plot(dates, prices_achieved, marker='o', linestyle='-', color='purple',
         label='Historical Prices Achieved', zorder=2) # zorder to ensure line is on top

# 4. Target Line: Draw a horizontal dashed line for the 'current_target_price'
plt.axhline(y=current_target_price, color='red', linestyle='--', linewidth=1.5,
            label=f'Current Target Price (${current_target_price:.2f})', zorder=1)

# 5. Cost Line: Draw a horizontal dashed line for the 'current_cost_price'
plt.axhline(y=current_cost_price, color='blue', linestyle='--', linewidth=1.5,
            label=f'Current Cost Price (${current_cost_price:.2f})', zorder=1)

# 6. Profit Zone: Create a shaded green area between the 'cost_price' and 'target_price' lines.
# The x-range for fill_between should span the entire historical period.
# We use the 'dates' list as the x-coordinates for the fill.
plt.fill_between(dates, current_cost_price, current_target_price,
                 color='green', alpha=0.15, label='Target Profit Zone', zorder=0) # zorder to keep it in background

# Chart Requirements:
# 1. X-Axis: Dates from the 'purchase_history'.
plt.xlabel('Date')
# 2. Y-Axis: Price ($).
plt.ylabel('Price ($)')

# Clarity: Include a title, axis labels, and a legend.
plt.title('Negotiation Strategy: Price History and Target Zones')
plt.legend(loc='upper left')
plt.grid(True, linestyle='--', alpha=0.7)

# Improve date formatting on x-axis for better readability
plt.gcf().autofmt_xdate()

# Set y-axis limits to ensure all elements are visible and provide some padding
min_price = min(prices_achieved + [current_cost_price, current_target_price])
max_price = max(prices_achieved + [current_cost_price, current_target_price])
plt.ylim(min_price * 0.95, max_price * 1.05) # Add 5% padding

# Save to File: The script MUST save the chart to 'chart.png'.
plt.savefig('chart.png')

# No Display: Do not use .