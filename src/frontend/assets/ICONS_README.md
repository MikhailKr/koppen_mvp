# Renewable Energy Icons

This directory contains custom SVG icons designed for the renewable energy forecasting platform.

## Available Icons

### Core Icons
- **`wind_turbine.svg`** - Animated wind turbine with rotating blades
- **`wind_farm.svg`** - Multiple wind turbines in a farm setting
- **`weather.svg`** - Weather icon with sun, clouds, and wind indicators
- **`forecast.svg`** - Chart/graph icon showing forecast trends
- **`analytics.svg`** - Bar chart icon for data analytics
- **`generation.svg`** - Power generation icon with lightning bolt and wind turbines
- **`data_lab.svg`** - Flask/beaker icon for data experimentation
- **`ai_assistant.svg`** - AI/brain icon with neural network visualization

### UI Icons
- **`add_icon.svg`** - Plus/add icon with renewable energy theme
- **`info_icon.svg`** - Information icon with renewable energy accents
- **`api_icon.svg`** - Network/API icon showing data connections
- **`solar_panel.svg`** - Solar panel icon (for future solar forecasting feature)

## Usage in Streamlit

To use these icons in your Streamlit pages, you can:

### Option 1: Display as Image
```python
import streamlit as st
from pathlib import Path

icon_path = Path("frontend/assets/wind_turbine.svg")
st.image(str(icon_path), width=50)
```

### Option 2: Inline SVG (HTML)
```python
import streamlit as st

with open("frontend/assets/wind_turbine.svg", "r") as f:
    svg_content = f.read()
    
st.markdown(svg_content, unsafe_allow_html=True)
```

### Option 3: As Favicon/Page Icon
```python
st.set_page_config(
    page_title="Wind Farm Management",
    page_icon="frontend/assets/wind_farm.svg",
)
```

## Design Features

- **Color Scheme**: Uses a renewable energy color palette (blues, greens, purples)
- **Scalable**: SVG format allows infinite scaling without quality loss
- **Dark Theme Compatible**: Designed to work well on dark backgrounds
- **Modern Look**: Clean, minimalist design with gradients and subtle animations

## Customization

All icons are SVG files and can be easily customized by:
1. Editing the SVG code directly
2. Changing colors by modifying the `fill` and `stroke` attributes
3. Adjusting sizes by changing the `viewBox` or `width`/`height` attributes
4. Modifying gradients in the `<defs>` section

